#!/usr/bin/env python3
"""Instructor-only: plays the lab through the HTTP API against a running server and checks the rules.
Usage: play.py <base url> <scenario>
Scenarios: ext (offline disk) | mistake | plugged_restore | hints | cloud_fast | cloud_slow | disk_only | nothing | plugged | dirty | spread"""
import json, os, sys, urllib.request

BASE = sys.argv[1].rstrip("/")
H = {"pc": "pc.protefs-office.example", "start": os.environ.get("START_HOST", "ransomware.cadmus-labs.example")}
OK = True

def call(path, body=None, host="pc"):
    req = urllib.request.Request(BASE + path, method="POST" if body is not None else "GET",
                                 data=json.dumps(body or {}).encode() if body is not None else None,
                                 headers={"Host": H[host], "Content-Type": "application/json"})
    with urllib.request.urlopen(req) as r:
        raw = r.read()
        return json.loads(raw) if raw else {}

def call_status(path):
    req = urllib.request.Request(BASE + path, method="POST", data=b"{}", headers={"Host": H["start"], "Content-Type": "application/json"})
    try:
        return urllib.request.urlopen(req).status
    except urllib.error.HTTPError as e:
        return e.code

def check(name, cond):
    global OK; OK &= bool(cond); print(("OK  " if cond else "FAIL"), name)

def st(): return call("/api/state")
def prog(): return call("/api/progress", host="start")
def finish(): call("/api/finish", {}, "start"); return prog()
def events(): return [e["title"] for e in prog()["events"]]
def readable(): return prog()["readable"]
def verify():
    s = st(); n = 0
    for fid in ("f1", "f4", "f7"):
        r = call("/api/open", {"loc": "pc", "id": fid}); n += bool(r.get("ok"))
    return n

def prep_updates():
    call("/api/update", {"id": "all"}); call("/api/update", {"auto": True})

def ext_backup():
    call("/api/ext", {"plugged": True}); r = call("/api/backup", {"target": "ext"}); assert r["ok"], r
    call("/api/ext", {"plugged": False})

def report_all():
    r = call("/api/mail", {"to": ["it", "police"]}); assert r["ok"], r

sc = sys.argv[2]
call("/api/reset", {}, "start")
check("start: nothing happened, all 9 readable", prog()["phase"] == "prep" and readable() == 9)
check("reporting is not possible before the incident", call("/api/mail", {"to": ["it"]}).get("ok") is False)
check("finish before the incident is refused", "Περιστατικό" in (finish()["open"] or []))

if sc == "ext":
    ext_backup(); prep_updates()
    check("all files still fine in prep", readable() == 9)
    call("/api/gohome", {})
    check("incident: files locked", readable() == 0 and any(f["name"].endswith(".locked") for f in st()["locations"][0]["files"]))
    check("ransom note present", st()["ransom"] and "@" in st()["contact"])
    call("/api/net", {"on": False}); report_all()
    check("infected until scanned", st()["infected"] is True)
    call("/api/scan", {}); check("clean after scan", st()["infected"] is False)
    call("/api/net", {"on": True})
    call("/api/ext", {"plugged": True})
    check("ext backup is intact (listed readable)", not any(f["name"].endswith(".locked") for f in [l for l in st()["locations"] if l["id"] == "ext"][0]["files"]))
    r = call("/api/restore", {"src": "ext"}); check("restore from ext", r.get("ok"))
    check("not done yet: files not verified", "Έλεγχος αρχείων" in (finish()["open"] or []))
    r = call("/api/check", {"loc": "pc"}); check("one-click check reports 9 of 9", r["good"] == 9 and r["total"] == 9)
    p = finish(); check("completed with flag", p["done"] and p.get("flag", "").startswith("CADMUS{"))
    check("no spread happened", not any("άλλους υπολογιστές" in t for t in events()))

elif sc == "cloud_fast":
    call("/api/backup", {"target": "cloud", "on": True}); prep_updates()
    call("/api/gohome", {})
    call("/api/net", {"on": False})                         # first action: cut the network before the sync
    report_all(); call("/api/scan", {}); call("/api/net", {"on": True})
    r = call("/api/restore", {"src": "cloud"}); check("restore from cloud is fine", r.get("ok"))
    check("cloud copy was not overwritten", readable() == 9 and not any("CloudBox συγχρονίστηκε" in t for t in events()))
    verify(); [call("/api/open", {"loc": "pc", "id": f}) for f in ("f2", "f5", "f8")]
    check("completed", finish()["done"])

elif sc == "cloud_slow":
    call("/api/backup", {"target": "cloud", "on": True}); prep_updates()
    call("/api/gohome", {})
    call("/api/update", {"auto": True}); call("/api/update", {"auto": True})     # two actions with the network on: the sync strikes
    check("cloud synced the encrypted files", any("CloudBox συγχρονίστηκε" in t for t in events()))
    call("/api/scan", {})
    call("/api/restore", {"src": "cloud"})
    check("restore from cloud gives locked files", readable() == 0)
    check("not done", not finish()["done"])

elif sc == "disk_only":
    call("/api/backup", {"target": "disk"}); prep_updates()
    call("/api/gohome", {})
    check("backup on the same disk was encrypted", any("φάκελος «Αντίγραφα»" in s for e in prog()["events"] for s in e["steps"]))
    call("/api/net", {"on": False}); report_all(); call("/api/scan", {})
    call("/api/restore", {"src": "disk"})
    check("restore from disk gives locked files", readable() == 0 and not finish()["done"])
    call("/api/reset", {}, "start")
    check("reset returns to a clean Friday", st()["phase"] == "prep" and not st()["disk_backup"] and readable() == 9)
    ext_backup(); prep_updates(); call("/api/gohome", {})
    call("/api/net", {"on": False}); report_all(); call("/api/scan", {}); call("/api/net", {"on": True}); call("/api/ext", {"plugged": True})
    call("/api/restore", {"src": "ext"}); verify(); [call("/api/open", {"loc": "pc", "id": f}) for f in ("f2", "f5", "f8")]
    check("second try completes", finish()["done"])

elif sc == "nothing":
    call("/api/gohome", {})
    call("/api/pay", {})
    check("payment gives no key", readable() == 0 and any("Πλήρωσες" in t for t in events()))
    check("restore without any backup is refused", call("/api/restore", {"src": "disk"}).get("ok") is False)
    check("not done and paid is listed", "Πληρωμή" in (finish()["open"] or []))
    call("/api/reset", {}, "start"); check("reset after paying", st()["phase"] == "prep" and prog()["readable"] == 9)

elif sc == "plugged":
    call("/api/ext", {"plugged": True}); call("/api/backup", {"target": "ext"})   # left plugged in
    call("/api/gohome", {})
    ext = [l for l in st()["locations"] if l["id"] == "ext"][0]
    check("plugged-in disk was encrypted", all(f["name"].endswith(".locked") for f in ext["files"]))

elif sc == "plugged_restore":                 # the disk was left plugged in: the restore must say it brought back locked files
    call("/api/ext", {"plugged": True}); call("/api/backup", {"target": "ext"})
    call("/api/gohome", {}); call("/api/net", {"on": False}); call("/api/scan", {})
    r = call("/api/restore", {"src": "ext"})
    check("restore warns that the copy was already encrypted", r.get("warn") and not r.get("msg"))
    check("a red event explains why", any("ήδη κρυπτογραφημένο" in t for t in events()))
    check("cause says the disk was plugged in", any("συνδεδεμένος" in c for e in prog()["events"] for c in e["cause"]))
    report_all()
    check("hint says no backup is intact", "Κανένα αντίγραφο" in call("/api/hint", host="start")["title"])

elif sc == "mistake":                         # a mistake is explained, blocks the desktop, and only a reset clears it
    check("no mistake pending at start", prog()["mistake"] is None and not call("/api/state")["mistake"])
    call("/api/ext", {"plugged": True}); call("/api/backup", {"target": "ext"}); call("/api/gohome", {})
    p = prog(); check("leaving the disk plugged in is a mistake with a fix", p["mistake"] and "αφαιρέσεις" in p["mistake"]["fix"])
    check("the desktop keeps sending the player to the progress page", call("/api/state")["mistake"] and call("/api/state")["mistake"])
    check("there is no way to dismiss it (no ack endpoint)", urllib.request.Request is not None and call_status("/api/ack") == 404)
    call("/api/reset", {}, "start"); check("reset clears everything", prog()["mistake"] is None and prog()["phase"] == "prep")
    call("/api/gohome", {}); call("/api/pay", {}); check("paying is a mistake", "πληρώσεις" in prog()["mistake"]["fix"])
    call("/api/reset", {}, "start")
    # sending reports is flexible: it neither costs time nor has to come first
    ext_backup(); call("/api/gohome", {}); call("/api/net", {"on": False}); call("/api/scan", {}); call("/api/net", {"on": True})
    for _ in range(4): report_all()
    check("many mails never trigger a mistake", prog()["mistake"] is None)
    check("and the cloud/spread events did not fire", not any("συγχρονίστηκε" in t or "άλλους υπολογιστές" in t for t in events()))

elif sc == "hints":                           # the opt-in help follows the right order, step by step
    def h(): return call("/api/hint", host="start")["title"]
    check("prep: asks for a backup", "αντίγραφο ασφαλείας" in h())
    call("/api/backup", {"target": "disk"}); check("prep: disk copy only -> think about survival", "επιβίωναν" in h())
    call("/api/ext", {"plugged": True}); call("/api/backup", {"target": "ext"}); check("prep: disk still plugged", "συνδεδεμένος" in h())
    call("/api/ext", {"plugged": False}); check("prep: updates next", "ενημερώσεις" in h())
    prep_updates(); check("prep: ready", "έτοιμος" in h())
    call("/api/gohome", {})
    check("incident: disconnect first", "Αποσύνδεσε" in h()); call("/api/net", {"on": False})
    check("then clean before restoring", "Καθάρισε" in h()); call("/api/scan", {})
    check("then restore from a copy that opens", "Επανάφερε" in h())
    call("/api/ext", {"plugged": True}); call("/api/restore", {"src": "ext"})
    check("then verify the files", "ανοίγουν" in h()); call("/api/check", {"loc": "pc"})
    check("then reconnect", "δίκτυο" in h()); call("/api/net", {"on": True})
    check("reporting comes last and may be done any time", "Ενημέρωσε" in h()); report_all()
    check("ready to finish", "Ολοκλήρωσα" in call("/api/hint", host="start")["why"]); check("completed", finish()["done"])

elif sc == "dirty":
    ext_backup(); call("/api/gohome", {})
    call("/api/net", {"on": False})
    call("/api/ext", {"plugged": True})
    check("plugging the backup into the infected computer destroys it", any("εξωτερικό δίσκο" in t for t in events()))
    call("/api/scan", {}); call("/api/restore", {"src": "ext"})
    check("restore gives locked files", readable() == 0)

elif sc == "spread":
    ext_backup(); call("/api/gohome", {})
    call("/api/update", {"auto": True}); call("/api/update", {"auto": True}); call("/api/update", {"auto": True})
    check("spread after 3 actions with the network on", any("άλλους υπολογιστές" in t for t in events()))

print("RESULT", "PASS" if OK else "FAIL")
sys.exit(0 if OK else 1)
