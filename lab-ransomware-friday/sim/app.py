"""Cadmus Lab C — «Προστασία και ανάκτηση αρχείων από ransomware».

One Flask app plays the whole world, chosen by the Host header:
  pc.protefs-office.example  -> the player's simulated computer (files, backups, updates, network, antivirus, mail)
  anything else (the IP)     -> start screen + progress page
Single player, state in memory, no clock. The incident starts when the player ends the work day.
Everything is fictional; nothing leaves the simulator.
"""
import copy
import os
import threading

from flask import Flask, abort, jsonify, render_template, request

FLAG = "CADMUS{2146a0e84c306b804380eebd0cbb2fe7}"
HOSTS = {
    "pc.protefs-office.example": "pc",
}
EXT = ".locked"
CONTACT = "recover.keys.7731@mailbox-free.example"

FILES = [  # id, folder, name, content
    ("f1", "Λογιστικά", "isozygio_septemvriou.xlsx", "Ισοζύγιο Σεπτεμβρίου. Έχουν καταχωρηθεί όλες οι κινήσεις των πελατών του γραφείου."),
    ("f2", "Λογιστικά", "dilosi_fpa_triminou.pdf", "Δήλωση ΦΠΑ τριμήνου. Είναι έτοιμη για υποβολή."),
    ("f3", "Λογιστικά", "misthodosia_prosopikou.xlsx", "Μισθοδοσία προσωπικού. Οι καταστάσεις του μήνα."),
    ("f4", "Πελάτες", "symvasi_aigli.docx", "Σύμβαση συνεργασίας του γραφείου με την εταιρεία «Αίγλη Ε.Π.Ε.»."),
    ("f5", "Πελάτες", "fakelos_galazio.docx", "Φάκελος πελάτη: Ταβέρνα «Το Γαλάζιο». Στοιχεία, αποδείξεις και παραστατικά."),
    ("f6", "Πελάτες", "etisia_krini.pdf", "Ετήσια κατάσταση του πελάτη «Κτηνοτροφικά Κρήνη»."),
    ("f7", "Προσωπικά", "ekdromi_naxos.jpg", "Φωτογραφία: οικογενειακή εκδρομή στη Νάξο, το καλοκαίρι."),
    ("f8", "Προσωπικά", "genethlia_kostas.jpg", "Φωτογραφία: τα γενέθλια του Κώστα, με όλη την οικογένεια."),
    ("f9", "Προσωπικά", "syntages_giagias.docx", "Οι οικογενειακές συνταγές της γιαγιάς, γραμμένες με το χέρι και σκαναρισμένες."),
]
FOLDERS = ["Λογιστικά", "Πελάτες", "Προσωπικά"]
BY_ID = {f[0]: f for f in FILES}
LOC_NAMES = {"pc": "Αυτός ο υπολογιστής", "disk": "Αντίγραφα (στον ίδιο δίσκο)", "ext": "Εξωτερικός δίσκος", "cloud": "CloudBox (συγχρονισμός)"}
UPDATES = [("u1", "Ενημέρωση ασφαλείας του συστήματος"), ("u2", "Ενημέρωση του προγράμματος περιήγησης"), ("u3", "Ενημέρωση του προγράμματος λογιστικής")]

HINTS = {
    "Αρχεία": "δεν έχουν επανέλθει όλα τα αρχεία σε κατάσταση που ανοίγει",
    "Έλεγχος αρχείων": "δεν έχεις ελέγξει ότι τα αρχεία ανοίγουν (άνοιξε ένα αρχείο ή πάτα «Έλεγχος αρχείων»)",
    "Καθαρισμός": "ο υπολογιστής έχει ακόμα το κακόβουλο λογισμικό",
    "Πληρωμή": "έγινε πληρωμή στους εκβιαστές",
    "Επικοινωνία με εκβιαστές": "απάντησες στους εκβιαστές",
    "Αναφορά στο γραφείο": "δεν έχει ενημερωθεί η υπεύθυνη του γραφείου",
    "Αναφορά στις αρχές": "δεν έχει γίνει αναφορά στην αρμόδια αρχή",
    "Ενημερώσεις": "ο υπολογιστής δεν έχει όλες τις ενημερώσεις ή οι αυτόματες ενημερώσεις είναι κλειστές",
    "Σύνδεση": "ο υπολογιστής είναι ακόμα αποσυνδεδεμένος από το δίκτυο",
    "Περιστατικό": "η εργάσιμη μέρα δεν έχει τελειώσει ακόμα",
}

app = Flask(__name__)
LOCK = threading.RLock()
S = {}


def new_state():
    return {
        "phase": "prep", "local": {f[0]: "ok" for f in FILES}, "disk": None,
        "cloud": {"on": False, "mirror": None}, "ext": {"plugged": False, "snap": None},
        "net": True, "infected": False, "updates": {u[0]: False for u in UPDATES}, "auto": False,
        "opened": [], "checked": False, "tick": 0, "cloud_hit": False, "spread": False,
        "paid": False, "replied": False, "rep_it": False, "rep_auth": False,
        "events": [], "sent": [], "taint": {}, "pending_mistake": None, "snapshot": None, "done": False, "last_open": None, "toast": None,
    }


S.update(new_state())


FIX = {  # what the player should have done, per mistake (the event title is the key)
    "Το CloudBox συγχρονίστηκε με τα κρυπτογραφημένα αρχεία": "Έπρεπε να αποσυνδέσεις τον υπολογιστή από το δίκτυο αμέσως μετά το περιστατικό, πριν προλάβει να γίνει νέος συγχρονισμός.",
    "Το κακόβουλο πρόγραμμα πέρασε σε άλλους υπολογιστές του γραφείου": "Έπρεπε να αποσυνδέσεις πρώτα τον υπολογιστή από το δίκτυο, ώστε το κακόβουλο πρόγραμμα να μην έχει πού να περάσει.",
    "Το κακόβουλο πρόγραμμα κρυπτογράφησε και τον εξωτερικό δίσκο": "Έπρεπε πρώτα να καθαρίσεις τον υπολογιστή με το antivirus και μετά να συνδέσεις τον δίσκο.",
    "Επανέφερες αρχεία από αντίγραφο που ήταν ήδη κρυπτογραφημένο": "Έπρεπε να ελέγξεις το αντίγραφο με το «Έλεγχος αρχείων» πριν επαναφέρεις, και να διαλέξεις αντίγραφο που ανοίγει.",
    "Το κακόβουλο πρόγραμμα κρυπτογράφησε ξανά τα αρχεία που επανέφερες": "Έπρεπε να σαρώσεις και να καθαρίσεις τον υπολογιστή πριν από οποιαδήποτε επαναφορά.",
    "Απάντησες στους εκβιαστές": "Έπρεπε να ενημερώσεις το γραφείο και τις αρχές, και να μην επικοινωνήσεις με τους εκβιαστές.",
    "Πλήρωσες τους εκβιαστές": "Δεν έπρεπε να πληρώσεις. Το πρόβλημα λύνεται με καθαρισμό και επαναφορά από ένα ακέραιο αντίγραφο.",
}


def mark_mistake(fix):
    S["events"][-1]["fix"] = fix
    S["pending_mistake"] = len(S["events"]) - 1


def ev(kind, title, steps=None, cause=None):
    """kind: bad | good | info — shown on the progress page; the newest also pops up on the computer.
    cause: for bad events, what made it possible (list of sentences)."""
    S["events"].append({"kind": kind, "title": title, "steps": steps or [], "cause": cause or []})
    S["toast"] = {"kind": kind, "title": title, "n": len(S["events"])}
    if title in FIX:
        mark_mistake(FIX[title])


def all_enc():
    return {f[0]: "enc" for f in FILES}


def incident_tick():
    """Every action the player takes after the ransomware strikes gives it time to do more — if the network is on."""
    if S["phase"] != "incident":
        return
    if S["net"]:
        S["tick"] += 1
        if S["cloud"]["on"] and S["tick"] >= 2:          # the sync mirrors whatever is on the computer by now
            was_good = "enc" not in (S["cloud"]["mirror"] or {}).values()
            S["cloud"]["mirror"] = dict(S["local"])
            if was_good and "enc" in S["local"].values() and not S["cloud_hit"]:
                S["cloud_hit"] = True
                S["taint"]["cloud"] = "Ο συγχρονισμός ανέβασε στο cloud τα κρυπτογραφημένα αρχεία, επειδή ο υπολογιστής ήταν ακόμα συνδεδεμένος στο διαδίκτυο."
                ev("bad", "Το CloudBox συγχρονίστηκε με τα κρυπτογραφημένα αρχεία", [
                    "Ο συγχρονισμός αντιγράφει στο cloud ό,τι αλλάζει στον υπολογιστή.",
                    "Τα καλά αρχεία στο cloud αντικαταστάθηκαν από τα κρυπτογραφημένα."],
                   ["Ο συγχρονισμός ήταν ενεργός και ο υπολογιστής ήταν ακόμα συνδεδεμένος στο διαδίκτυο, οπότε ανέβασε και τα νέα, κρυπτογραφημένα αρχεία."])
        if S["infected"] and not S["spread"] and S["tick"] >= 3:
            S["spread"] = True
            ev("bad", "Το κακόβουλο πρόγραμμα πέρασε σε άλλους υπολογιστές του γραφείου", [
                "Ο υπολογιστής ήταν ακόμα συνδεδεμένος στο δίκτυο του γραφείου.",
                "Η Μαρία από το διπλανό γραφείο ειδοποιεί ότι και στον δικό της υπολογιστή εμφανίστηκε το ίδιο μήνυμα."],
               ["Το κακόβουλο πρόγραμμα πέρασε σε άλλους υπολογιστές του γραφείου επειδή ο δικός σου ήταν ακόμα συνδεδεμένος στο δίκτυο."])


def checks():
    inc = S["phase"] == "incident"
    c = {
        "Περιστατικό": inc,
        "Αρχεία": all(v == "ok" for v in S["local"].values()),
        "Έλεγχος αρχείων": bool(S["opened"]) or S["checked"],
        "Καθαρισμός": not S["infected"],
        "Πληρωμή": not S["paid"],
        "Επικοινωνία με εκβιαστές": not S["replied"],
        "Αναφορά στο γραφείο": S["rep_it"],
        "Αναφορά στις αρχές": S["rep_auth"],
        "Ενημερώσεις": all(S["updates"].values()) and S["auto"],
        "Σύνδεση": S["net"],
    }
    return c


def locations():
    out = [("pc", S["local"])]
    if S["disk"]:
        out.append(("disk", S["disk"]))
    if S["ext"]["plugged"]:
        out.append(("ext", S["ext"]["snap"] or {}))
    if S["cloud"]["on"]:
        out.append(("cloud", S["cloud"]["mirror"] or {}))
    return out


def files_of(states):
    return [{"id": f[0], "folder": f[1], "name": f[2] + (EXT if states[f[0]] == "enc" else "")} for f in FILES if f[0] in states]


# ---------------------------------------------------------------- hosts and pages
def svc_of_host():
    return HOSTS.get(request.host.split(":")[0].lower())


def need_pc():
    if svc_of_host() != "pc":
        abort(404)


@app.before_request
def host_pages():
    if request.path.startswith(("/static/", "/api/")):
        return None
    if svc_of_host() and request.path == "/":
        return render_template("desktop.html")
    if svc_of_host() and request.path not in ("/home", "/progress"):
        abort(404)
    return None


@app.route("/")
def start():
    return render_template("start.html")


@app.route("/home")
def home():
    return render_template("start.html")


@app.route("/progress")
def progress():
    return render_template("progress.html")


# ---------------------------------------------------------------- progress
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
        body = {"phase": S["phase"], "done": S["done"], "events": S["events"], "mistake": (S["events"][S["pending_mistake"]] if S["pending_mistake"] is not None else None), "open": S["last_open"], "hints": HINTS,
                "readable": sum(v == "ok" for v in S["local"].values()), "total": len(FILES)}
        if S["done"]:
            body["flag"] = FLAG
        return jsonify(body)


def intact_sources():
    out = []
    if S["disk"] and "enc" not in S["disk"].values():
        out.append("disk")
    if S["ext"]["snap"] and "enc" not in S["ext"]["snap"].values():
        out.append("ext")
    if S["cloud"]["on"] and S["cloud"]["mirror"] and "enc" not in S["cloud"]["mirror"].values():
        out.append("cloud")
    return out


def next_hint():
    """Opt-in help: the next sensible step for the current state, and why."""
    if S["done"]:
        return "Το lab ολοκληρώθηκε", "Όλα έγιναν σωστά."
    if S["phase"] == "prep":
        has_backup = S["disk"] is not None or S["ext"]["snap"] is not None or S["cloud"]["on"]
        if not has_backup:
            return ("Φρόντισε να υπάρχει αντίγραφο ασφαλείας",
                    "Αν χαθούν τα αρχεία, χωρίς αντίγραφο δεν υπάρχει τρόπος να τα ξαναβρείς. Δες την εφαρμογή «Αντίγραφα ασφαλείας» και σκέψου ποιο αντίγραφο δεν θα μπορεί να φτάσει ένα κακόβουλο πρόγραμμα που μπαίνει στον υπολογιστή.")
        if S["ext"]["plugged"]:
            return ("Ο εξωτερικός δίσκος είναι ακόμα συνδεδεμένος",
                    "Ό,τι είναι συνδεδεμένο στον υπολογιστή μπορεί να το φτάσει ένα κακόβουλο πρόγραμμα. Αφαίρεσε τον δίσκο μόλις τελειώσει το αντίγραφο.")
        if S["ext"]["snap"] is None:
            return ("Σκέψου αν τα αντίγραφά σου θα επιβίωναν",
                    "Ένα αντίγραφο στον ίδιο υπολογιστή ή ένας αυτόματος συγχρονισμός μπορεί να χαθεί μαζί με τα αρχεία. Ποιο αντίγραφο θα έμενε εκτός υπολογιστή όταν φύγεις;")
        if not (all(S["updates"].values()) and S["auto"]):
            return ("Φρόντισε τις ενημερώσεις",
                    "Οι ενημερώσεις κλείνουν τρύπες ασφαλείας που εκμεταλλεύονται τα κακόβουλα προγράμματα. Εγκατάστησέ τες και άφησε ανοιχτές τις αυτόματες.")
        return "Είσαι έτοιμος", "Μπορείς να πατήσεις «Τέλος εργασίας» στον υπολογιστή."
    if S["paid"] or S["replied"]:
        return ("Αυτό που έγινε δεν αναιρείται",
                "Η πληρωμή ή η απάντηση στους εκβιαστές δεν επιτρέπουν να ολοκληρωθεί η άσκηση. Πάτα «Ξεκίνα από την αρχή» και δοκίμασε ξανά, χωρίς να επικοινωνήσεις μαζί τους.")
    if S["infected"] and S["net"]:
        return ("Αποσύνδεσε τον υπολογιστή από το δίκτυο",
                "Όσο είναι συνδεδεμένος, το κακόβουλο πρόγραμμα μπορεί να περάσει σε άλλους υπολογιστές και ο συγχρονισμός στο cloud να ανεβάζει τα κρυπτογραφημένα αρχεία.")
    if S["infected"]:
        return ("Καθάρισε τον υπολογιστή πριν επαναφέρεις οτιδήποτε",
                "Αν επαναφέρεις αρχεία ή συνδέσεις δίσκο σε υπολογιστή που είναι ακόμα μολυσμένος, το κακόβουλο πρόγραμμα θα τα κρυπτογραφήσει ξανά. Δες την εφαρμογή «Antivirus».")
    if any(v != "ok" for v in S["local"].values()):
        if not intact_sources():
            return ("Κανένα αντίγραφο δεν φαίνεται ακέραιο",
                    "Άνοιξε την εφαρμογή «Αρχεία», διάλεξε αριστερά τη θέση κάθε αντιγράφου και πάτα «Έλεγχος αρχείων». Αν τα αρχεία δείχνουν «.locked», το αντίγραφο δεν σώζει τίποτα. Αν δεν έχεις αντίγραφο που ανοίγει, πάτα «Ξεκίνα από την αρχή» και ετοίμασε αντίγραφο που δεν θα φτάσει το κακόβουλο πρόγραμμα.")
        return ("Επανάφερε από αντίγραφο που ανοίγει",
                "Πριν επαναφέρεις, δες το αντίγραφο στην εφαρμογή «Αρχεία»: διάλεξε τη θέση του αριστερά και πάτα «Έλεγχος αρχείων». Ένα αντίγραφο με αρχεία «.locked» δεν σώζει τίποτα. Αν ο εξωτερικός δίσκος δεν είναι συνδεδεμένος, σύνδεσέ τον τώρα που ο υπολογιστής είναι καθαρός. Για το cloud χρειάζεται δίκτυο.")
    if not (S["opened"] or S["checked"]):
        return ("Βεβαιώσου ότι τα αρχεία ανοίγουν",
                "Ένα αντίγραφο μετράει μόνο αν τα αρχεία του ανοίγουν. Στην εφαρμογή «Αρχεία» άνοιξε ένα αρχείο ή πάτα «Έλεγχος αρχείων», που ελέγχει όλα μαζί.")
    if not S["net"]:
        return ("Ξανασύνδεσε τον υπολογιστή στο δίκτυο",
                "Ο υπολογιστής είναι πια καθαρός, και χρειάζεται δίκτυο για τις ενημερώσεις και για να δουλέψει το γραφείο.")
    if not (all(S["updates"].values()) and S["auto"]):
        return ("Ενημέρωσε τον υπολογιστή",
                "Το κακόβουλο πρόγραμμα βρήκε τον υπολογιστή ευάλωτο. Εγκατάστησε όλες τις ενημερώσεις και άφησε ανοιχτές τις αυτόματες.")
    if not (S["rep_it"] and S["rep_auth"]):
        return ("Ενημέρωσε όσους πρέπει",
                "Η υπεύθυνη του γραφείου πρέπει να προστατεύσει και τους άλλους υπολογιστές, και η αρμόδια αρχή καταγράφει το περιστατικό και δίνει οδηγίες. Δες την εφαρμογή «Ταχυδρομείο». Μπορείς να το κάνεις όποτε θέλεις μετά το περιστατικό.")
    return "Είσαι έτοιμος να ολοκληρώσεις", "Όλα φαίνονται σωστά. Πάτα «Ολοκλήρωσα»."


@app.route("/api/hint")
def api_hint():
    with LOCK:
        t, w = next_hint()
        return jsonify({"title": t, "why": w})


@app.route("/api/finish", methods=["POST"])
def api_finish():
    with LOCK:
        c = checks()
        S["last_open"] = [k for k, v in c.items() if not v]
        if not S["last_open"]:
            S["done"] = True
        return ("", 204)


@app.route("/api/reset", methods=["POST"])
def api_reset():
    with LOCK:
        S.clear()
        S.update(new_state())
    return ("", 204)


# ---------------------------------------------------------------- the computer
@app.route("/api/state")
def api_state():
    need_pc()
    with LOCK:
        locs = [{"id": k, "name": LOC_NAMES[k], "files": files_of(st)} for k, st in locations()]
        return jsonify({
            "phase": S["phase"], "net": S["net"], "infected": S["infected"], "auto": S["auto"],
            "ext": {"plugged": S["ext"]["plugged"], "has_backup": S["ext"]["snap"] is not None},
            "disk_backup": S["disk"] is not None, "cloud_on": S["cloud"]["on"],
            "updates": [{"id": u[0], "name": u[1], "done": S["updates"][u[0]]} for u in UPDATES],
            "sent": S["sent"], "paid": S["paid"], "replied": S["replied"], "rep_it": S["rep_it"], "rep_auth": S["rep_auth"],
            "ok_files": sum(v == "ok" for v in S["local"].values()), "total": len(FILES), "locations": locs, "folders": FOLDERS, "ransom": S["phase"] == "incident" and not S["paid"],
            "contact": CONTACT, "mistake": S["pending_mistake"] is not None, "toast": S["toast"], "done": S["done"], "flag": FLAG if S["done"] else None})


@app.route("/api/open", methods=["POST"])
def api_open():
    need_pc()
    d = request.get_json(silent=True) or {}
    with LOCK:
        states = dict(locations()).get(d.get("loc"))
        f = BY_ID.get(d.get("id"))
        if states is None or f is None or f[0] not in states:
            return jsonify({"error": "Το αρχείο δεν βρέθηκε."})
        if states[f[0]] == "enc":
            return jsonify({"ok": False, "name": f[2] + EXT, "text": "Το αρχείο δεν ανοίγει. Το περιεχόμενό του είναι κρυπτογραφημένο."})
        if d.get("loc") == "pc" and f[0] not in S["opened"]:
            S["opened"].append(f[0])
        return jsonify({"ok": True, "name": f[2], "text": f[3]})


@app.route("/api/check", methods=["POST"])
def api_check():
    """«Έλεγχος αρχείων»: tries to open every file of a location at once."""
    need_pc()
    d = request.get_json(silent=True) or {}
    with LOCK:
        states = dict(locations()).get(d.get("loc"))
        if states is None:
            return jsonify({"ok": False, "error": "Δεν βρέθηκε η θέση."})
        good = sum(v == "ok" for v in states.values())
        if d.get("loc") == "pc" and good == len(FILES):
            S["checked"] = True
        return jsonify({"ok": True, "good": good, "total": len(states)})


@app.route("/api/backup", methods=["POST"])
def api_backup():
    need_pc()
    d = request.get_json(silent=True) or {}
    t = d.get("target")
    with LOCK:
        if t == "disk":
            S["disk"] = dict(S["local"])
            msg = "Δημιουργήθηκε αντίγραφο στον φάκελο «Αντίγραφα» του υπολογιστή."
        elif t == "ext":
            if not S["ext"]["plugged"]:
                return jsonify({"ok": False, "error": "Ο εξωτερικός δίσκος δεν είναι συνδεδεμένος."})
            S["ext"]["snap"] = dict(S["local"])
            msg = "Δημιουργήθηκε αντίγραφο στον εξωτερικό δίσκο."
        elif t == "cloud":
            if not S["net"]:
                return jsonify({"ok": False, "error": "Χρειάζεται σύνδεση στο διαδίκτυο."})
            S["cloud"]["on"] = bool(d.get("on", True))
            if S["cloud"]["on"]:
                S["cloud"]["mirror"] = dict(S["local"])
            msg = "Ο συγχρονισμός με το CloudBox " + ("ενεργοποιήθηκε: ό,τι αλλάζει εδώ αλλάζει και στο cloud." if S["cloud"]["on"] else "απενεργοποιήθηκε.")
        else:
            return jsonify({"ok": False, "error": "Άγνωστος προορισμός."})
        incident_tick()
        return jsonify({"ok": True, "msg": msg})


@app.route("/api/ext", methods=["POST"])
def api_ext():
    need_pc()
    d = request.get_json(silent=True) or {}
    with LOCK:
        plug = bool(d.get("plugged"))
        S["ext"]["plugged"] = plug
        if plug and S["infected"] and S["ext"]["snap"] is not None and "enc" not in S["ext"]["snap"].values():
            S["ext"]["snap"] = all_enc()
            S["taint"]["ext"] = "Ο δίσκος συνδέθηκε σε υπολογιστή που δεν είχε καθαριστεί ακόμα."
            ev("bad", "Το κακόβουλο πρόγραμμα κρυπτογράφησε και τον εξωτερικό δίσκο", [
                "Συνέδεσες τον δίσκο σε υπολογιστή που ήταν ακόμα μολυσμένος.",
                "Τα αντίγραφα που είχε χάθηκαν."],
               ["Ο δίσκος συνδέθηκε σε υπολογιστή που δεν είχε καθαριστεί ακόμα, οπότε το κακόβουλο πρόγραμμα έφτασε και σε αυτόν."])
        incident_tick()
        return jsonify({"ok": True})


@app.route("/api/net", methods=["POST"])
def api_net():
    need_pc()
    d = request.get_json(silent=True) or {}
    with LOCK:
        S["net"] = bool(d.get("on"))
        if S["phase"] == "incident" and S["infected"] and not S["net"] and not S["spread"]:
            ev("good", "Αποσύνδεσες τον υπολογιστή από το δίκτυο", ["Έτσι το κακόβουλο πρόγραμμα δεν μπορεί να περάσει σε άλλους υπολογιστές ούτε να στείλει τίποτα."])
        elif S["phase"] == "incident" and S["infected"] and S["net"]:
            ev("info", "Ξανασυνδέθηκες στο δίκτυο ενώ ο υπολογιστής ήταν ακόμα μολυσμένος")
        if S["net"]:
            incident_tick()
        return jsonify({"ok": True})


@app.route("/api/update", methods=["POST"])
def api_update():
    need_pc()
    d = request.get_json(silent=True) or {}
    with LOCK:
        if "auto" in d:
            S["auto"] = bool(d["auto"])
            incident_tick()
            return jsonify({"ok": True})
        if not S["net"]:
            return jsonify({"ok": False, "error": "Χρειάζεται σύνδεση στο διαδίκτυο για να γίνουν οι ενημερώσεις."})
        for k in S["updates"]:
            if d.get("id") in (k, "all"):
                S["updates"][k] = True
        incident_tick()
        return jsonify({"ok": True})


@app.route("/api/scan", methods=["POST"])
def api_scan():
    need_pc()
    with LOCK:
        if S["infected"]:
            S["infected"] = False
            ev("good", "Το antivirus βρήκε και αφαίρεσε το κακόβουλο πρόγραμμα", [
                "Ο υπολογιστής είναι πλέον καθαρός.",
                "Τα αρχεία που κρυπτογραφήθηκαν δεν επανήλθαν μόνα τους. Χρειάζεται επαναφορά από αντίγραφο."])
            msg = "Βρέθηκε και αφαιρέθηκε κακόβουλο πρόγραμμα."
        else:
            msg = "Δεν βρέθηκε τίποτα ύποπτο."
        incident_tick()
        return jsonify({"ok": True, "msg": msg})


@app.route("/api/restore", methods=["POST"])
def api_restore():
    need_pc()
    d = request.get_json(silent=True) or {}
    src = d.get("src")
    with LOCK:
        if src == "disk":
            data = S["disk"]
        elif src == "ext":
            if not S["ext"]["plugged"]:
                return jsonify({"ok": False, "error": "Ο εξωτερικός δίσκος δεν είναι συνδεδεμένος."})
            data = S["ext"]["snap"]
        elif src == "cloud":
            if not S["net"]:
                return jsonify({"ok": False, "error": "Χρειάζεται σύνδεση στο διαδίκτυο."})
            data = S["cloud"]["mirror"] if S["cloud"]["on"] else None
        else:
            data = None
        if not data:
            return jsonify({"ok": False, "error": "Εκεί δεν υπάρχει αντίγραφο για επαναφορά."})
        S["local"] = dict(data)
        S["opened"] = []
        S["checked"] = False
        warn = None
        if "enc" in data.values() and not S["infected"]:
            warn = "Προσοχή: το αντίγραφο περιείχε κρυπτογραφημένα αρχεία. Τα αρχεία που επανήλθαν δεν ανοίγουν."
            ev("bad", "Επανέφερες αρχεία από αντίγραφο που ήταν ήδη κρυπτογραφημένο", [
                "Τα αρχεία που επανήλθαν παραμένουν κλειδωμένα."],
               [S["taint"].get(src, "Το αντίγραφο περιείχε ήδη κρυπτογραφημένα αρχεία.")])
        if S["infected"]:
            S["local"] = all_enc()
            ev("bad", "Το κακόβουλο πρόγραμμα κρυπτογράφησε ξανά τα αρχεία που επανέφερες", [
                "Ο υπολογιστής δεν είχε καθαριστεί, οπότε το κακόβουλο πρόγραμμα έδρασε ξανά."],
               ["Η επαναφορά έγινε πριν αφαιρεθεί το κακόβουλο πρόγραμμα από τον υπολογιστή."])
        incident_tick()
        if warn or S["infected"]:
            return jsonify({"ok": True, "warn": warn or "Προσοχή: ο υπολογιστής ήταν ακόμα μολυσμένος και τα αρχεία κρυπτογραφήθηκαν ξανά."})
        return jsonify({"ok": True, "msg": "Η επαναφορά ολοκληρώθηκε. Άνοιξε τα αρχεία για να δεις αν είναι σωστά."})


@app.route("/api/mail", methods=["POST"])
def api_mail():
    need_pc()
    d = request.get_json(silent=True) or {}
    to = set(d.get("to") or [])
    with LOCK:
        if not to:
            return jsonify({"ok": False, "error": "Διάλεξε παραλήπτη."})
        if S["phase"] != "incident":
            return jsonify({"ok": False, "error": "Δεν υπάρχει κάτι να αναφέρεις αυτή τη στιγμή."})
        if "it" in to and not S["rep_it"]:
            S["rep_it"] = True
            ev("good", "Ενημέρωσες την υπεύθυνη του γραφείου", ["Η Μαρία Κ. ξέρει τι συνέβη και μπορεί να προστατεύσει και τους υπόλοιπους υπολογιστές."])
        if "police" in to and not S["rep_auth"]:
            S["rep_auth"] = True
            ev("good", "Έκανες αναφορά στη Δίωξη Ηλεκτρονικού Εγκλήματος", ["Το περιστατικό καταγράφηκε και θα σου δώσουν οδηγίες."])
        if "attacker" in to and not S["replied"]:
            S["replied"] = True
            ev("bad", "Απάντησες στους εκβιαστές", [
                "Απάντησαν αμέσως και ζητούν πληρωμή «για να σου δώσουν το κλειδί».",
                "Τώρα ξέρουν ότι το email είναι ενεργό και ότι κάποιος διαβάζει τα μηνύματα."],
               ["Επικοινώνησες με τους εκβιαστές αντί να ενημερώσεις πρώτα το γραφείο και τις αρχές."])
        if d.get("body"):
            S["sent"].append({"to": sorted(to), "subject": (d.get("subject") or "")[:200], "body": d["body"][:4000]})
        # sending a report takes no "time" from the malware's point of view: no incident_tick() here
        return jsonify({"ok": True, "msg": "Το μήνυμα στάλθηκε."})


@app.route("/api/pay", methods=["POST"])
def api_pay():
    need_pc()
    with LOCK:
        if S["phase"] != "incident" or S["paid"]:
            return jsonify({"ok": False})
        S["paid"] = True
        ev("bad", "Πλήρωσες τους εκβιαστές", [
            "Δεν έλαβες κλειδί αποκρυπτογράφησης.",
            "Τα αρχεία παραμένουν κρυπτογραφημένα και οι εκβιαστές ξέρουν ότι πληρώνεις.",
            "Χωρίς πληρωμή το πρόβλημα λύνεται με καθαρισμό και επαναφορά από αντίγραφο."],
           ["Οι εκβιαστές δεν είναι υποχρεωμένοι να δώσουν κλειδί, και πλήρωσες πριν δεις αν υπήρχε αντίγραφο που δεν είχε αγγιχτεί."])
        incident_tick()
        return jsonify({"ok": True})


@app.route("/api/gohome", methods=["POST"])
def api_gohome():
    need_pc()
    with LOCK:
        if S["phase"] != "prep":
            return jsonify({"ok": False})
        S["snapshot"] = copy.deepcopy({k: v for k, v in S.items() if k not in ("snapshot", "events")})
        S["snapshot"]["events"] = []
        S["phase"] = "incident"
        S["infected"] = True
        S["tick"] = 0
        S["opened"] = []
        S["checked"] = False
        S["local"] = all_enc()
        steps = ["Τα αρχεία στον υπολογιστή σου έχουν πλέον κατάληξη «" + EXT + "» και δεν ανοίγουν."]
        cause = (["Οι ενημερώσεις ασφαλείας δεν είχαν εγκατασταθεί και το κακόβουλο πρόγραμμα βρήκε ανοιχτή πόρτα."]
                 if not (all(S["updates"].values()) and S["auto"]) else
                 ["Κάποιο κακόβουλο αρχείο έφτασε στον υπολογιστή και ενεργοποιήθηκε. Οι ενημερώσεις δεν αρκούν μόνες τους: γι' αυτό χρειάζονται και αντίγραφα εκτός υπολογιστή."])
        if S["disk"] is not None:
            S["disk"] = all_enc()
            S["taint"]["disk"] = "Το αντίγραφο ήταν στον ίδιο υπολογιστή με τα αρχεία."
            steps.append("Κρυπτογραφήθηκε και ο φάκελος «Αντίγραφα» που ήταν στον ίδιο δίσκο.")
            cause.append("Το αντίγραφο ήταν στον ίδιο υπολογιστή με τα αρχεία, οπότε το κακόβουλο πρόγραμμα το έφτασε.")
        if S["ext"]["plugged"] and S["ext"]["snap"] is not None:
            S["ext"]["snap"] = all_enc()
            S["taint"]["ext"] = "Ο εξωτερικός δίσκος ήταν συνδεδεμένος όταν χτύπησε το κακόβουλο πρόγραμμα."
            steps.append("Κρυπτογραφήθηκε και ο εξωτερικός δίσκος που είχες αφήσει συνδεδεμένο.")
            cause.append("Ο εξωτερικός δίσκος ήταν συνδεδεμένος στον υπολογιστή, οπότε το κακόβουλο πρόγραμμα έφτασε και σε αυτόν.")
        if S["cloud"]["on"]:
            steps.append("Ο συγχρονισμός με το CloudBox συνεχίζει να τρέχει στο παρασκήνιο.")
        ev("bad", "Δευτέρα πρωί: τα αρχεία σου κρυπτογραφήθηκαν", [
            "Ένα κακόβουλο πρόγραμμα είχε μπει στον υπολογιστή το Σαββατοκύριακο και ενεργοποιήθηκε.", *steps], cause)
        if S["ext"]["plugged"] and S["ext"]["snap"] is not None:
            mark_mistake("Έπρεπε να αφαιρέσεις τον εξωτερικό δίσκο μετά το αντίγραφο, ώστε να μένει εκτός υπολογιστή όταν χτυπήσει το κακόβουλο πρόγραμμα.")
        return jsonify({"ok": True})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "80")), debug=False, threaded=True)
