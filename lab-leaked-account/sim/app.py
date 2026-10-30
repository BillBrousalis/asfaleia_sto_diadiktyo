"""Cadmus Lab B — «Ασφάλιση λογαριασμών μετά από διαρροή κωδικού».

One Flask app plays the whole world, chosen by the Host header:
  vault / email / shop / social / bank / breach-check  -> the simulated services
  anything else (the IP address)                        -> start screen + progress page
Single player, state in memory. The attacker plays a round only when the player asks for one (no clock).
Nothing typed by the player leaves the browser except what the simulated services need.
"""
import os
import re
import secrets
import threading

from flask import Flask, abort, jsonify, render_template, request

ORDER = ["email", "shop", "social", "bank"]                 # the attacker's order inside a round
FLAG = "FLAG{0f2c952afe849ec22051abb9fed9af3d}"
LEAK = "Eleni1985"
MY_MAIL = "eleni.markou@aigaio-mail.example"
HOSTS = {
    "mail.aigaio-mail.example": "email",
    "shop.kyklades-store.example": "shop",
    "www.sinomilia.example": "social",
    "ebanking.elara-bank.example": "bank",
    "vault.passkeeper.example": "vault",
    "breachcheck.example": "breach",
}
LABEL = {"email": "το email σου", "shop": "τον λογαριασμό στο κατάστημα", "social": "το κοινωνικό δίκτυο",
         "bank": "την τράπεζα"}
BANNED = ("elen", "luna", "1985", "password", "123", "markou", "aigaio", "kyklad", "sinomilia", "elara")

HINTS = {
    "Κωδικός": "ο κωδικός πρέπει να είναι μακρύς, μοναδικός (όχι ίδιος με άλλον λογαριασμό) και χωρίς ονόματα ή έτη",
    "Διπλή επαλήθευση": "δεν έχει ενεργοποιηθεί διπλή επαλήθευση",
    "Συσκευές": "υπάρχει ακόμα άγνωστη συσκευή συνδεδεμένη",
    "Συσκευές και κανόνες": "υπάρχει ακόμα άγνωστη συσκευή ή κανόνας προώθησης",
    "Συσκευές και δικαιούχοι": "υπάρχει ακόμα άγνωστη συσκευή ή δικαιούχος",
    "Αναρτήσεις και απόρρητο": "υπάρχουν ακόμα δημόσιες αναρτήσεις με προσωπικές πληροφορίες που βοηθούν κάποιον να σε μαντέψει ή να σε στοχεύσει",
    "Ειδοποιήσεις": "οι ειδοποιήσεις συναλλαγών είναι ανενεργές",
}

app = Flask(__name__)
LOCK = threading.RLock()
S = {}


def _sess(sid, device, attacker=False):
    return {"id": sid, "device": device, "attacker": attacker}


def new_state():
    me = lambda: [_sess("me", "Ο υπολογιστής της Ελένης · Αθήνα"), _sess("ph", "Το κινητό της Ελένης · Αθήνα")]
    return {
        "round": 0, "last_open": None, "done": False, "ran": set(), "tokens": {}, "pending": {}, "events": [],
        "mails": [
            {"id": 1, "from": "Breach Check", "subj": "Η διεύθυνσή σου βρέθηκε σε διαρροή δεδομένων", "date": "Σήμερα 08:12",
             "body": "Η διεύθυνση eleni.markou@aigaio-mail.example εμφανίζεται σε διαρροή δεδομένων.\nΔες τι ακριβώς εκτέθηκε:",
             "links": [["Έλεγχος διαρροής", "http://breachcheck.example/"]]},
            {"id": 2, "from": "Κυκλαδικό Κατάστημα", "subj": "Η παραγγελία σας #A-48213 παραδόθηκε", "date": "Χθες 15:40",
             "body": "Η παραγγελία σου παραδόθηκε. Ευχαριστούμε!", "links": []},
            {"id": 3, "from": "Elara Bank", "subj": "Το μηνιαίο σου αντίγραφο κινήσεων είναι διαθέσιμο", "date": "Χθες 09:00",
             "body": "Μπες στο e-banking για να δεις το αντίγραφο κινήσεων του μήνα.", "links": []},
            {"id": 4, "from": "Συνομιλία", "subj": "Έχεις 3 νέες ειδοποιήσεις", "date": "Δευτέρα 19:20",
             "body": "Σου έγραψαν και σε σημείωσαν σε μια φωτογραφία.", "links": []},
        ],
        "acc": {
            "email": {"user": MY_MAIL, "pw": LEAK, "mfa": False, "sessions": me(), "rules": []},
            "shop": {"user": MY_MAIL, "pw": LEAK, "mfa": None, "sessions": me(), "orders": ["#A-48213 · Toner HL-3170 · Παραδόθηκε"],
                     "address": "Οδός Ερμού 12, Αθήνα"},
            "social": {"user": "eleni.markou", "pw": "Luna1985", "mfa": False, "sessions": me(), "posts": [
                {"id": "p1", "text": "Η Luna μόλις έγινε 6 ετών! Η πιο γλυκιά σκυλίτσα του κόσμου 🐶", "vis": "public", "tag": "pet"},
                {"id": "p2", "text": "Σήμερα γίνομαι 41! Γεννήθηκα το 1985 και ακόμα δεν το πιστεύω 🎂", "vis": "public", "tag": "birth"},
                {"id": "p3", "text": "Διακοπές στη Νάξο μέχρι τις 30/10! Το σπίτι μένει άδειο 🌴", "vis": "public", "tag": "away"},
                {"id": "p4", "text": "Καλημέρα με έναν καφέ ☕", "vis": "public", "tag": None},
                {"id": "p5", "text": "Μπράβο στην ομάδα για τη χθεσινή παρουσίαση!", "vis": "public", "tag": None}]},
            "bank": {"user": "emarkou", "pw": "Ar1stoK#9vTq", "mfa": False, "alerts": False, "sessions": me(),
                     "payees": [{"id": "d1", "name": "Μαρία Κ. · ενοίκιο", "attacker": False}]},
        },
    }


S.update(new_state())


# ---------------------------------------------------------------- rules
def classes(pw):
    return sum(bool(re.search(p, pw)) for p in (r"[a-z]", r"[A-Z]", r"\d", r"[^\w\s]"))


def strong(svc, pw):
    low = pw.lower()
    if len(pw) < 12 or classes(pw) < 3 or any(w in low for w in BANNED) or pw == LEAK:
        return False
    return all(S["acc"][o]["pw"] != pw for o in S["acc"] if o != svc)


def attacker_in(svc):
    a = S["acc"][svc]
    return any(s["attacker"] for s in a["sessions"]) or bool(a.get("rules")) or any(p["attacker"] for p in a.get("payees", []))


def sensitive_public():
    return [p for p in S["acc"]["social"]["posts"] if p["tag"] and p["vis"] == "public"]


def checks():
    """{service: {check name: bool}} — the completion criteria."""
    a = S["acc"]
    c = {}
    c["email"] = {"Κωδικός": strong("email", a["email"]["pw"]), "Διπλή επαλήθευση": a["email"]["mfa"],
                  "Συσκευές και κανόνες": not attacker_in("email")}
    c["shop"] = {"Κωδικός": strong("shop", a["shop"]["pw"]), "Συσκευές": not attacker_in("shop")}
    c["social"] = {"Κωδικός": strong("social", a["social"]["pw"]), "Διπλή επαλήθευση": a["social"]["mfa"],
                   "Συσκευές": not attacker_in("social"), "Αναρτήσεις και απόρρητο": not sensitive_public()}
    c["bank"] = {"Κωδικός": strong("bank", a["bank"]["pw"]), "Διπλή επαλήθευση": a["bank"]["mfa"],
                 "Ειδοποιήσεις": a["bank"]["alerts"], "Συσκευές και δικαιούχοι": not attacker_in("bank")}
    return c


def all_ok():
    return all(all(v.values()) for v in checks().values())


# ---------------------------------------------------------------- attacker
def _mail(frm, subj, body):
    S["mails"].insert(0, {"id": max([m["id"] for m in S["mails"]] + [0]) + 1, "from": frm, "subj": subj, "date": "Τώρα",
                          "body": body, "links": []})


def _event(svc, ok, title, steps, reason="", cause=None):
    S["events"].append({"round": S["round"], "svc": svc, "ok": ok, "title": title,
                        "steps": steps, "reason": reason, "cause": cause or []})


def run_stage(svc):
    a = S["acc"]
    S["ran"].add(svc)
    if attacker_in(svc):
        return _event(svc, True, "Ο απατεώνας έχει ακόμα πρόσβαση: " + LABEL[svc], [
            "Η πρόσβαση που απέκτησε νωρίτερα δεν έχει αφαιρεθεί (άγνωστη συσκευή, κανόνας ή δικαιούχος).",
            "Αλλαγή κωδικού μόνη της δεν τον διώχνει. Έλεγξε συνδέσεις και ρυθμίσεις."],
            cause=["Η πρόσβασή του παραμένει επειδή η άγνωστη συσκευή, ο κανόνας ή ο δικαιούχος που άφησε δεν έχουν αφαιρεθεί."])
    if svc == "email":
        if a["email"]["pw"] != LEAK:
            blocked = "Ο κωδικός είχε αλλάξει."
        elif a["email"]["mfa"]:
            blocked = "Ζητήθηκε δεύτερος παράγοντας και ο απατεώνας δεν είχε το κινητό σου."
        else:
            blocked = None
        if blocked:
            _mail("Aigaio Mail", "Αποτυχημένη προσπάθεια σύνδεσης", "Κάποιος προσπάθησε να συνδεθεί στο email σου από τη Βραζιλία και μπλοκαρίστηκε.")
            return _event(svc, False, "Ο απατεώνας δοκίμασε το email σου και μπλοκαρίστηκε", [], blocked)
        a["email"]["sessions"].append(_sess("x", "Άγνωστη συσκευή · Βραζιλία", True))
        a["email"]["rules"].append({"id": "r1", "text": "Προώθηση κάθε νέου μηνύματος στο drop.box.4471@mailbox-free.example", "attacker": True})
        return _event(svc, True, "Ο απατεώνας μπήκε στο email σου", [
            "Συνδέεται στο email με τον κωδικό που διέρρευσε, από τη Βραζιλία.",
            "Διαβάζει τα μηνύματά σου και βρίσκει όσα αφορούν την τράπεζα και το κατάστημα.",
            "Φτιάχνει κανόνα προώθησης: αντίγραφο κάθε νέου μηνύματος πηγαίνει σε εκείνον.",
            "Από εδώ και πέρα μπορεί να ζητά «επαναφορά κωδικού» σε άλλους λογαριασμούς σου. Οι σύνδεσμοι έρχονται στο email που ελέγχει."],
            cause=["Ο κωδικός που διέρρευσε ήταν ακόμα ο ίδιος και το email δεν είχε διπλή επαλήθευση."])
    if svc == "shop":
        if a["shop"]["pw"] != LEAK:
            _mail("Κυκλαδικό Κατάστημα", "Αποτυχημένη προσπάθεια σύνδεσης", "Κάποιος προσπάθησε να συνδεθεί στον λογαριασμό σου από τη Βραζιλία και μπλοκαρίστηκε.")
            return _event(svc, False, "Ο απατεώνας δοκίμασε το κατάστημα και μπλοκαρίστηκε", [], "Ο κωδικός είχε αλλάξει.")
        a["shop"]["sessions"].append(_sess("x", "Άγνωστη συσκευή · Βραζιλία", True))
        a["shop"]["orders"].append("#A-51907 · Δωροκάρτες · Σε επεξεργασία")
        a["shop"]["address"] = "Άγνωστη διεύθυνση παράδοσης"
        _mail("Κυκλαδικό Κατάστημα", "Νέα σύνδεση και νέα παραγγελία", "Έγινε σύνδεση από νέα συσκευή (Βραζιλία) και νέα παραγγελία στον λογαριασμό σου.")
        return _event(svc, True, "Ο απατεώνας μπήκε στον λογαριασμό σου στο κατάστημα", [
            "Συνδέεται με τον ίδιο κωδικό, γιατί τον είχες χρησιμοποιήσει και εδώ.",
            "Αλλάζει τη διεύθυνση παράδοσης.",
            "Παραγγέλνει δωροκάρτες με την αποθηκευμένη κάρτα σου."],
            cause=["Χρησιμοποιούσες στο κατάστημα τον ίδιο κωδικό που διέρρευσε, και ο λογαριασμός δεν έχει διπλή επαλήθευση."])
    if svc == "social":
        pw = a["social"]["pw"]
        public_tags = {p["tag"] for p in a["social"]["posts"] if p["vis"] == "public"}
        can = pw == LEAK or (pw == "Luna1985" and {"pet", "birth"} <= public_tags)
        if not can:
            blocked = "Ο κωδικός είχε αλλάξει."
        elif a["social"]["mfa"]:
            blocked = "Ζητήθηκε δεύτερος παράγοντας και ο απατεώνας δεν είχε το κινητό σου."
        else:
            blocked = None
        if blocked:
            _mail("Συνομιλία", "Αποτυχημένη προσπάθεια σύνδεσης", "Κάποιος προσπάθησε να μπει στον λογαριασμό σου από τη Βραζιλία και μπλοκαρίστηκε.")
            return _event(svc, False, "Ο απατεώνας δοκίμασε το κοινωνικό σου δίκτυο και μπλοκαρίστηκε", [], blocked)
        a["social"]["sessions"].append(_sess("x", "Άγνωστη συσκευή · Βραζιλία", True))
        _mail("Συνομιλία", "Νέα σύνδεση από άγνωστη συσκευή", "Έγινε σύνδεση στον λογαριασμό σου από νέα συσκευή (Βραζιλία).")
        how = ("με τον κωδικό που διέρρευσε" if pw == LEAK else
               "μαντεύοντας τον κωδικό από δημόσιες αναρτήσεις σου: το όνομα του σκύλου σου και το έτος γέννησής σου")
        return _event(svc, True, "Ο απατεώνας μπήκε στο κοινωνικό σου δίκτυο", [
            f"Μπαίνει {how}.",
            "Στέλνει σε όλους τους φίλους σου μήνυμα: «Δες τι είδα για σένα» με κακόβουλο σύνδεσμο.",
            "Οι φίλοι σου πατούν, γιατί το μήνυμα έρχεται από εσένα."],
            cause=(["Ο κωδικός ήταν ο ίδιος που διέρρευσε και δεν υπήρχε διπλή επαλήθευση."] if pw == LEAK else
                   ["Ο κωδικός ήταν φτιαγμένος από πληροφορίες που είχες δημοσιεύσει δημόσια και δεν υπήρχε διπλή επαλήθευση."]))
    # bank: reset through the e-mail the attacker may control
    email_access = attacker_in("email")
    if not email_access:
        blocked = "Ο απατεώνας ζήτησε επαναφορά κωδικού, αλλά ο σύνδεσμος ήρθε στο email σου και δεν είχε πρόσβαση σε αυτό."
    elif a["bank"]["mfa"]:
        blocked = "Ο απατεώνας ζήτησε επαναφορά κωδικού και πήρε τον σύνδεσμο από το email σου, αλλά η τράπεζα ζήτησε κωδικό SMS από το κινητό σου."
    else:
        blocked = None
    if blocked:
        _mail("Elara Bank", "Αίτημα επαναφοράς κωδικού", "Έγινε αίτημα επαναφοράς κωδικού από άγνωστη συσκευή και δεν ολοκληρώθηκε.")
        return _event(svc, False, "Ο απατεώνας δοκίμασε την τράπεζά σου και μπλοκαρίστηκε", [], blocked)
    a["bank"]["sessions"].append(_sess("x", "Άγνωστη συσκευή · Βραζιλία", True))
    a["bank"]["payees"].append({"id": "d2", "name": "Εταιρεία Δωροκαρτών Ltd", "attacker": True})
    a["bank"]["pw"] = "attacker-" + secrets.token_hex(4)
    _mail("Elara Bank", "Άλλαξε ο κωδικός σου", "Ο κωδικός του e-banking άλλαξε. Αν δεν ήσουν εσύ, επικοινώνησε αμέσως με την τράπεζα.")
    return _event(svc, True, "Ο απατεώνας μπήκε στην τράπεζά σου", [
        "Ζητά «επαναφορά κωδικού» στην τράπεζα. Ο σύνδεσμος έρχεται στο email που ήδη ελέγχει.",
        "Ορίζει νέο κωδικό και συνδέεται στο e-banking.",
        "Προσθέτει νέο δικαιούχο, μια «εταιρεία δωροκαρτών».",
        "Ετοιμάζει μεταφορά χρημάτων προς αυτόν."],
        cause=["Ο απατεώνας είχε ήδη πρόσβαση στο email σου, απ' όπου περνούν οι σύνδεσμοι επαναφοράς κωδικού.",
               "Η τράπεζα δεν είχε διπλή επαλήθευση, οπότε ο σύνδεσμος από το email έφτανε για να αλλάξει τον κωδικό."])


def attack_round():
    """One pass of the attacker over all accounts, in order; earlier break-ins carry over to later ones."""
    S["round"] += 1
    S["ran"] = set()
    for svc in ORDER:
        run_stage(svc)
    S["last_open"] = {svc: [k for k, v in cc.items() if not v] for svc, cc in checks().items()}   # snapshot: only changes with a round
    if all_ok():
        S["done"] = True


# ---------------------------------------------------------------- helpers
def svc_of_host():
    return HOSTS.get(request.host.split(":")[0].lower())


def need_svc(*allowed):
    svc = svc_of_host()
    if svc is None or (allowed and svc not in allowed):
        abort(404)
    return svc


def authed(svc):
    tok = request.cookies.get("tok_" + svc)
    if not tok or S["tokens"].get(tok) != svc:
        abort(401)
    return S["acc"][svc]


@app.before_request
def host_pages():
    if request.path.startswith(("/static/", "/api/")):
        return None
    svc = svc_of_host()
    if svc and request.path == "/":
        return render_template("service.html", svc=svc)
    if svc and request.path not in ("/home", "/progress"):
        abort(404)
    return None


# ---------------------------------------------------------------- pages without a service host
@app.route("/")
def start():
    return render_template("start.html")


@app.route("/home")
def home():
    return render_template("start.html")


@app.route("/progress")
def progress():
    return render_template("progress.html")


@app.route("/api/attack", methods=["POST"])
def api_attack():
    with LOCK:
        if not S["done"]:
            attack_round()
    return ("", 204)


@app.route("/api/reset", methods=["POST"])
def api_reset():
    with LOCK:
        S.clear()
        S.update(new_state())
    return ("", 204)


@app.route("/api/bar")
def api_bar():
    with LOCK:
        body = {"done": S["done"]}
        if S["done"]:
            body["flag"] = FLAG
        return jsonify(body)


@app.route("/api/progress")
def api_progress():
    with LOCK:
        tiles = {}
        for svc in ORDER:
            if attacker_in(svc):
                tiles[svc] = "compromised"
            elif svc in S["ran"]:
                # blocked in the last round, but the security of this account is not complete yet
                tiles[svc] = "partial" if (S["last_open"] or {}).get(svc) else "blocked"
            else:
                tiles[svc] = "pending"
        body = {"round": S["round"], "done": S["done"], "tiles": tiles, "open": S["last_open"], "hints": HINTS,
                "events": S["events"], "labels": LABEL}
        if S["done"]:
            body["flag"] = FLAG
        return jsonify(body)


@app.route("/api/report")
def api_report():
    with LOCK:
        c = checks()
        return jsonify({"open": {svc: [k for k, v in cc.items() if not v] for svc, cc in c.items()},
                        "hints": HINTS,
                        "ok": all_ok(), "done": S["done"]})


# ---------------------------------------------------------------- service API
@app.route("/api/me")
def api_me():
    svc = need_svc()
    with LOCK:
        tok = request.cookies.get("tok_" + svc)
        body = {"svc": svc, "logged_in": S["tokens"].get(tok) == svc}
        if svc in S["acc"]:
            body["user"] = S["acc"][svc]["user"]
        return jsonify(body)


@app.route("/api/login", methods=["POST"])
def api_login():
    svc = need_svc("email", "shop", "social", "bank")
    d = request.get_json(silent=True) or {}
    with LOCK:
        a = S["acc"][svc]
        if (d.get("user") or "").strip().lower() != a["user"].lower() or d.get("pw") != a["pw"]:
            return jsonify({"ok": False, "error": "Λάθος όνομα χρήστη ή κωδικός."}), 200
        if a["mfa"]:
            if not d.get("code"):
                code = "%06d" % secrets.randbelow(10**6)
                S["pending"][svc] = code
                return jsonify({"ok": False, "need_code": True, "sms": code})
            if d.get("code") != S["pending"].get(svc):
                return jsonify({"ok": False, "need_code": True, "error": "Λάθος κωδικός SMS."})
        tok = secrets.token_hex(16)
        S["tokens"][tok] = svc
        resp = jsonify({"ok": True})
        resp.set_cookie("tok_" + svc, tok)
        return resp


@app.route("/api/recover", methods=["POST"])
def api_recover():
    """«Ξέχασες τον κωδικό;» — reset through the SMS to the owner's phone. Signs out every other device."""
    svc = need_svc("bank")
    d = request.get_json(silent=True) or {}
    with LOCK:
        a = S["acc"][svc]
        if not d.get("code"):
            code = "%06d" % secrets.randbelow(10**6)
            S["pending"]["rec_" + svc] = code
            return jsonify({"ok": False, "need_code": True, "sms": code})
        if d.get("code") != S["pending"].get("rec_" + svc):
            return jsonify({"ok": False, "error": "Λάθος κωδικός SMS."})
        if not strong(svc, d.get("new") or ""):
            return jsonify({"ok": False, "error": "Ο νέος κωδικός είναι αδύναμος ή έχει ξαναχρησιμοποιηθεί σε άλλον λογαριασμό."})
        a["pw"] = d["new"]
        a["sessions"] = [x for x in a["sessions"] if not x["attacker"]]
        return jsonify({"ok": True})


@app.route("/api/logout", methods=["POST"])
def api_logout():
    svc = need_svc()
    S["tokens"].pop(request.cookies.get("tok_" + svc), None)
    return ("", 204)


@app.route("/api/data")
def api_data():
    svc = need_svc("email", "shop", "social", "bank")
    with LOCK:
        a = authed(svc)
        body = {"svc": svc, "user": a["user"], "mfa": a["mfa"], "sessions": a["sessions"]}
        if svc == "email":
            body.update(mails=S["mails"], rules=a["rules"])
        elif svc == "shop":
            body.update(orders=a["orders"], address=a["address"], card="Κάρτα •••• 4821")
        elif svc == "social":
            body.update(posts=a["posts"])
        else:
            body.update(payees=a["payees"], alerts=a["alerts"], account="Λογαριασμός ταμιευτηρίου •••• 4417")
        return jsonify(body)


@app.route("/api/password", methods=["POST"])
def api_password():
    svc = need_svc("email", "shop", "social", "bank")
    d = request.get_json(silent=True) or {}
    with LOCK:
        a = authed(svc)
        new = d.get("new") or ""
        if d.get("old") != a["pw"]:
            return jsonify({"ok": False, "error": "Ο τρέχων κωδικός δεν είναι σωστός."})
        if not strong(svc, new):
            return jsonify({"ok": False, "error": "Ο νέος κωδικός είναι αδύναμος ή έχει ξαναχρησιμοποιηθεί σε άλλον λογαριασμό."})
        a["pw"] = new
        if d.get("signout_others"):
            a["sessions"] = [s for s in a["sessions"] if s["id"] == "me"]
        return jsonify({"ok": True})


@app.route("/api/mfa", methods=["POST"])
def api_mfa():
    svc = need_svc("email", "social", "bank")
    d = request.get_json(silent=True) or {}
    with LOCK:
        a = authed(svc)
        if not d.get("code"):
            code = "%06d" % secrets.randbelow(10**6)
            S["pending"]["mfa_" + svc] = code
            return jsonify({"ok": False, "need_code": True, "sms": code})
        if d.get("code") != S["pending"].get("mfa_" + svc):
            return jsonify({"ok": False, "need_code": True, "error": "Λάθος κωδικός SMS."})
        a["mfa"] = True
        return jsonify({"ok": True})


@app.route("/api/revoke", methods=["POST"])
def api_revoke():
    svc = need_svc("email", "shop", "social", "bank")
    sid = (request.get_json(silent=True) or {}).get("id")
    with LOCK:
        a = authed(svc)
        if sid != "me":
            a["sessions"] = [s for s in a["sessions"] if s["id"] != sid]
        return ("", 204)


@app.route("/api/rule/delete", methods=["POST"])
def api_rule_delete():
    svc = need_svc("email")
    rid = (request.get_json(silent=True) or {}).get("id")
    with LOCK:
        a = authed(svc)
        a["rules"] = [r for r in a["rules"] if r["id"] != rid]
        return ("", 204)


@app.route("/api/payee/delete", methods=["POST"])
def api_payee_delete():
    svc = need_svc("bank")
    pid = (request.get_json(silent=True) or {}).get("id")
    with LOCK:
        a = authed(svc)
        a["payees"] = [p for p in a["payees"] if p["id"] != pid]
        return ("", 204)


@app.route("/api/alerts", methods=["POST"])
def api_alerts():
    svc = need_svc("bank")
    with LOCK:
        authed(svc)["alerts"] = bool((request.get_json(silent=True) or {}).get("on"))
        return ("", 204)


@app.route("/api/post", methods=["POST"])
def api_post():
    svc = need_svc("social")
    d = request.get_json(silent=True) or {}
    with LOCK:
        a = authed(svc)
        if d.get("action") == "delete":
            a["posts"] = [p for p in a["posts"] if p["id"] != d.get("id")]
        elif d.get("action") in ("public", "friends", "me"):
            for p in a["posts"]:
                if p["id"] == d.get("id"):
                    p["vis"] = d["action"]
        return ("", 204)


# ---------------------------------------------------------------- vault
@app.route("/api/vault")
def api_vault():
    need_svc("vault")
    with LOCK:
        a = S["acc"]
        sites = [("email", "Aigaio Mail", "mail.aigaio-mail.example"), ("shop", "Κυκλαδικό Κατάστημα", "shop.kyklades-store.example"),
                 ("social", "Συνομιλία", "www.sinomilia.example"), ("bank", "Elara Bank", "ebanking.elara-bank.example")]
        rows = []
        for svc, name, host in sites:
            pw = a[svc]["pw"]
            reused = sum(1 for o in a if a[o]["pw"] == pw) > 1
            rows.append({"svc": svc, "name": name, "url": "http://" + host + "/", "user": a[svc]["user"], "pw": pw,
                         "reused": reused, "leaked": pw == LEAK, "weak": not strong(svc, pw) and not reused and pw != LEAK})
        return jsonify({"rows": rows})


@app.route("/api/generate", methods=["POST"])
def api_generate():
    need_svc("vault")
    alpha = "abcdefghjkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789!#$%&*?"
    while True:
        pw = "".join(secrets.choice(alpha) for _ in range(16))
        if classes(pw) == 4:
            return jsonify({"pw": pw})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "80")), debug=False, threaded=True)
