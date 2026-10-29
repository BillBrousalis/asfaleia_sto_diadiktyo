"""Cadmus Lab A — simulation server.

Host-based dispatch:
  * a hostname listed in scenarios.json["sites"]  -> simulated website (clone or genuine)
  * anything else (e.g. http://<ip>:8080)         -> start screen (/home) and progress page (/progress)
The Roundcube plugin (cadmus_report) calls /api/report when the player reports a mail.
Nothing typed into the simulated pages is sent to the server: only the *fact* that
the form was submitted is recorded.
"""
import json
import os
import threading

from flask import Flask, abort, jsonify, render_template, request

BASE = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(BASE, "scenarios.json"), encoding="utf-8") as fh:
    DATA = json.load(fh)
EMAILS, SITES, FLAG = DATA["emails"], DATA["sites"], DATA["flag"]
ORDER = sorted(EMAILS)
BY_SUBJECT = {e["subject"].strip(): i for i, e in EMAILS.items()}
SCAMS = [i for i in ORDER if EMAILS[i]["truth"] == "scam"]

LOCK = threading.Lock()
STATE = {i: {"reported": False, "opened": False, "submitted": False} for i in ORDER}
# RESTART: the genuine mail the player reported (the exercise must be restarted); DONE: all 8 scams reported;
# RESTORE: the Roundcube plugin must move the reported mails back to the inbox (after a reset)
FLAGS = {"restart": None, "done": False, "restore": False}

app = Flask(__name__)


def _host():
    return request.host.split(":")[0].lower()


def _outcome(email_id):
    e = EMAILS[email_id]
    o = e["outcome"]
    return {"id": email_id, "title": o["title"], "steps": o["steps"], "loss": o["loss"],
            "missed": o["missed"], "do_now": o["do_now"], "truth": e["truth"]}


@app.before_request
def site_dispatch():
    if request.path.startswith("/static/"):
        return None
    site = SITES.get(_host())
    if site is None:
        return None
    if request.path == "/api/event" and request.method == "POST":
        return None
    eid = site.get("email") or site["scenario"]
    if eid and request.method == "GET":
        with LOCK:
            STATE[eid]["opened"] = True
    return render_template("site.html", site=site)


@app.route("/api/event", methods=["POST"])
def event():
    """The player submitted a form. No form data is received or stored; the answer carries the outcome."""
    site = SITES.get(_host())
    if site is None:
        abort(404)
    if not site["scenario"]:
        return jsonify({"legit": True, "title": "Η φόρμα υποβλήθηκε",
                        "text": "Η σελίδα είναι γνήσια. Εδώ δεν συμβαίνει τίποτα κακό με τα στοιχεία σου."})
    with LOCK:
        STATE[site["scenario"]]["opened"] = True
        STATE[site["scenario"]]["submitted"] = True
    return jsonify({"legit": False, "outcome": _outcome(site["scenario"])})


def _progress(snap):
    """(all scams reported, number of false reports) for the current state."""
    scams_done = all(snap[i]["reported"] for i in SCAMS)
    false = sum(1 for i in ORDER if EMAILS[i]["truth"] == "legit" and snap[i]["reported"])
    return scams_done, false


@app.route("/api/report", methods=["POST"])
def report():
    subject = ((request.get_json(silent=True) or {}).get("subject") or "").strip()
    i = BY_SUBJECT.get(subject)
    if i is None:
        abort(404)
    e = EMAILS[i]
    with LOCK:
        STATE[i]["reported"] = True
        if e["truth"] == "legit" and FLAGS["restart"] is None:
            FLAGS["restart"] = i                       # genuine mail reported: explain, then restart the exercise
    scams_done, false = _progress(_status())
    complete = scams_done and false == 0
    if complete:
        FLAGS["done"] = True
    body = {"id": i, "truth": e["truth"], "ok": e["truth"] == "scam", "why": e["why"], "outcome": _outcome(i),
            "all_scams_reported": scams_done, "false_reports": false, "complete": complete,
            "restart": e["truth"] == "legit"}
    if complete:
        body["flag"] = FLAG
    return jsonify(body)


@app.route("/api/reset", methods=["POST"])
def reset():
    """Start the exercise again. The reported mails go back to the inbox the next time the webmail loads."""
    with LOCK:
        for v in STATE.values():
            v.update(reported=False, opened=False, submitted=False)
        FLAGS.update(restart=None, done=False, restore=True)
    return ("", 204)


@app.route("/api/plugin_state")
def plugin_state():
    """Asked by the Roundcube plugin on every page: restore mails? send the player to the progress page?"""
    return jsonify({"restore": FLAGS["restore"], "restart": FLAGS["restart"] is not None})


@app.route("/api/restore_done", methods=["POST"])
def restore_done():
    FLAGS["restore"] = False
    return ("", 204)


def _status():
    with LOCK:
        snap = {i: dict(v) for i, v in STATE.items()}
    return snap


@app.route("/api/status")
def status():
    snap = _status()
    rows = [{"id": i, "from_name": EMAILS[i]["from_name"], "subject": EMAILS[i]["subject"], "date": EMAILS[i]["date"],
             **snap[i]} for i in ORDER]
    body = {"rows": rows, "reported": sum(r["reported"] for r in rows), "total_scams": len(SCAMS),
            "complete": FLAGS["done"] and FLAGS["restart"] is None, "restart": None}
    if body["complete"]:
        body["flag"] = FLAG
    if FLAGS["restart"] is not None:
        i = FLAGS["restart"]
        body["restart"] = {"id": i, "subject": EMAILS[i]["subject"], "from_name": EMAILS[i]["from_name"],
                           "why": EMAILS[i]["why"], "outcome": _outcome(i)}
    return jsonify(body)


@app.route("/")
@app.route("/home")
def home():
    return render_template("start.html")


@app.route("/progress")
def progress():
    return render_template("status.html", total=len(ORDER), scams=len(SCAMS))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=False)
