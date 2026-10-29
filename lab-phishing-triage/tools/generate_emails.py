#!/usr/bin/env python3
"""Instructor-only: generates the 12 lab .eml files into ../mail and checks them
against answer_key.json. NOT deployed to the VM / Docker image.

All names, brands and domains are fictional. Domains use the reserved .example
TLD; IPs come from the documentation ranges (RFC 5737). No logos, no remote
images, no real links.
"""
import io
import json
import zlib
import sys
import zipfile
from email.message import EmailMessage
from email.utils import format_datetime, make_msgid
from datetime import datetime, timedelta, timezone
from html import escape
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "mail"
KEY = Path(__file__).resolve().parent / "answer_key.json"
TO = ("Ελένη Μάρκου", "eleni.markou@meltemi-logistics.example")


def tz(h):
    return timezone(timedelta(hours=h))


def a(text, href):
    return f'<a href="{escape(href)}" style="color:#1a5fb4">{escape(text)}</a>'


def button(text, href):
    return (f'<p style="margin:22px 0"><a href="{escape(href)}" style="background:#1a5fb4;color:#fff;'
            f'padding:10px 18px;text-decoration:none;border-radius:4px">{escape(text)}</a></p>')


def wrap(brand, body, footer=""):
    return f"""<!DOCTYPE html><html lang="el"><head><meta charset="utf-8"></head>
<body style="margin:0;background:#f2f2f2;font-family:Arial,Helvetica,sans-serif;color:#222">
<div style="max-width:620px;margin:16px auto;background:#fff;border:1px solid #ddd;border-top:5px solid #2d6a8f">
<div style="padding:14px 24px;font-size:18px;font-weight:bold;color:#2d6a8f">{escape(brand)}</div>
<div style="padding:0 24px 20px;font-size:14px;line-height:1.55">{body}</div>
<div style="padding:12px 24px;background:#fafafa;border-top:1px solid #eee;font-size:11px;color:#777">{footer}</div>
</div></body></html>"""


def tagless(html):
    import re
    t = re.sub(r"</(p|div|li|h\d)>", "\n", html)
    t = re.sub(r"<a [^>]*href=\"([^\"]+)\"[^>]*>([^<]*)</a>", r"\2 (\1)", t)
    return re.sub(r"<[^>]+>", "", t).replace("&amp;", "&").strip()


def zip_bytes():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("README.txt", "Αρχείο εκπαιδευτικού εργαστηρίου. Δεν περιέχει κώδικα ή πραγματικό έγγραφο.\n")
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Messages. Order = delivery order (oldest first). Names carry no hint.
# ---------------------------------------------------------------------------
def messages():
    M = []

    def add(**kw):
        M.append(kw)

    # 01 legit HR
    add(frm=("Τμήμα Ανθρώπινου Δυναμικού", "hr@meltemi-logistics.example"),
        subject="Υπόλοιπο αδειών 2026 — διαθέσιμο στην πύλη HR",
        date=datetime(2026, 10, 19, 8, 52, tzinfo=tz(3)), ip="192.0.2.10", mta="mail.meltemi-logistics.example",
        auth="spf=pass dkim=pass dmarc=pass", brand="Meltemi Logistics · HR",
        html=wrap("Meltemi Logistics · HR", """
<p>Αγαπητοί συνάδελφοι,</p>
<p>Το υπόλοιπο αδειών για το 2026 είναι πλέον ενημερωμένο. Μπορείτε να το δείτε στην πύλη HR,
από τον σελιδοδείκτη «Πύλη HR» του προγράμματος περιήγησης ή μέσα από την ενδοεταιρική σελίδα.</p>
<p>Αιτήματα αδείας για τις γιορτές υποβάλλονται έως 30 Νοεμβρίου.
Για απορίες καλέστε στο εσωτερικό 214.</p>
<p>Τμήμα Ανθρώπινου Δυναμικού</p>""", "Εσωτερική ενημέρωση προσωπικού."))

    # 02 phish — bank, subdomain trick
    add(frm=("Elara Bank Ασφάλεια", "security@elara-secure-alerts.example"),
        subject="Τελευταία υπενθύμιση: Επικύρωση ρυθμίσεων ασφαλείας ανά εξάμηνο",
        date=datetime(2026, 10, 19, 9, 30, tzinfo=tz(0)), ip="198.51.100.23", mta="mx1.elara-secure-alerts.example",
        auth="spf=fail dkim=fail dmarc=fail", replyto=None,
        html=wrap("Elara Bank · Ενημέρωση ασφαλείας", f"""
<p>Αγαπητέ πελάτη,</p>
<p>Σύμφωνα με τον κανονισμό ασφαλείας, κάθε έξι μήνες απαιτείται επικύρωση των ρυθμίσεων ασφαλείας του e-banking σας.
Δεν έχουμε λάβει ακόμη την επικύρωσή σας.</p>
<p><b>Αν δεν ολοκληρώσετε τη διαδικασία εντός 24 ωρών, η πρόσβασή σας θα περιοριστεί.</b></p>
{button("Επικύρωση στο e-banking", "http://elara-bank.example.verify-id.example/ebanking/login")}
<p style="font-size:12px;color:#555">Διεύθυνση υπηρεσίας: http://www.elara-bank.example/ebanking</p>
<p>Με εκτίμηση,<br>Τμήμα Ασφάλειας Elara Bank</p>""", "Μην απαντήσετε σε αυτό το μήνυμα."))

    # 03 phish — compromised colleague (passes auth: sent from the real account)
    add(frm=("Νίκος Ρήγας", "nikos.rigas@meltemi-logistics.example"),
        subject="Re: Ο χώρος αποθήκευσης του γραμματοκιβωτίου σας είναι πλήρης",
        date=datetime(2026, 10, 20, 10, 5, tzinfo=tz(0)), ip="192.0.2.10", mta="mail.meltemi-logistics.example",
        auth="spf=pass dkim=pass dmarc=pass", plain=True,
        html=wrap("", f"""
<p>Αγαπητέ χρήστη,</p>
<p>Ο λογαριασμός email σας θα αποκλειστεί επειδή αγνοήσατε τα μηνύματα επιβεβαίωσης και ο χώρος αποθήκευσης είναι πλήρης.</p>
<p>Για να συνεχίσετε να χρησιμοποιείτε το γραμματοκιβώτιο, ολοκληρώστε την επιβεβαίωση εδώ:
{a("Αναβάθμιση χώρου αποθήκευσης", "http://meltemi-mail-upgrade.sites-hosting.example/")}</p>
<p>Διαφορετικά ο λογαριασμός σας θα ΑΠΟΚΛΕΙΣΤΕΙ.</p>
<p>Κέντρο υποστήριξης · Αρ. υπόθεσης 0129476</p>"""))

    # 04 legit IT warning
    add(frm=("IT Helpdesk", "it-helpdesk@meltemi-logistics.example"),
        subject="Ενημέρωση ασφαλείας: μηνύματα που ζητούν επιβεβαίωση λογαριασμού",
        date=datetime(2026, 10, 20, 11, 20, tzinfo=tz(3)), ip="192.0.2.10", mta="mail.meltemi-logistics.example",
        auth="spf=pass dkim=pass dmarc=pass",
        html=wrap("Meltemi Logistics · IT", """
<p>Καλημέρα σας,</p>
<p>Σήμερα κυκλοφορούν μηνύματα, ακόμη και από λογαριασμούς συναδέλφων, που αναφέρουν ότι «ο χώρος αποθήκευσης είναι πλήρης» ή ότι
«ο λογαριασμός θα αποκλειστεί» και ζητούν σύνδεση από σύνδεσμο. Είναι <b>ηλεκτρονικό ψάρεμα (phishing)</b>.
Οι λογαριασμοί των συναδέλφων που τα στέλνουν έχουν παραβιαστεί.</p>
<p>Διαγράψτε τα και μην πατήσετε τους συνδέσμους τους. Αν έχετε ήδη γράψει τον κωδικό σας, αλλάξτε τον
<b>αμέσως</b> μόνο από την επίσημη πύλη <b>my.meltemi-logistics.example</b> (πληκτρολογήστε τη διεύθυνση ή χρησιμοποιήστε
τον σελιδοδείκτη) και ενημερώστε μας στο εσωτερικό 100.</p>
<p>Η υπηρεσία IT δεν θα σας ζητήσει ποτέ τον κωδικό σας με email.</p>
<p>IT Helpdesk</p>""", "Εσωτερική ενημέρωση ασφαλείας."))

    # 05 phish — fake summons with password-protected archive
    add(frm=("ΥΠΗΡΕΣΙΑ ΔΙΚΑΣΤΙΚΩΝ ΚΛΗΣΕΩΝ", "klisi.dikastiki@freemail-service.example"),
        subject="ΔΙΚΑΣΤΙΚΗ ΚΛΗΣΗ — αριθ. 3589/2026",
        date=datetime(2026, 10, 21, 7, 40, tzinfo=tz(0)), ip="203.0.113.77", mta="smtp.freemail-service.example",
        auth="spf=softfail dkim=none dmarc=fail", plain=True,
        attach=("ΚΛΗΣΗ-3589.pdf.zip", zip_bytes()),
        html=wrap("", """
<p><b>ΑΠΟΦΑΣΗ ΔΙΚΑΣΤΗΡΙΟΥ — ΕΠΕΙΓΟΝ</b></p>
<p>Κλητεύεστε να παρουσιαστείτε ενώπιον του δικαστηρίου. Τα στοιχεία της υπόθεσης βρίσκονται στο συνημμένο έγγραφο.</p>
<p>Το αρχείο είναι κρυπτογραφημένο για λόγους προστασίας προσωπικών δεδομένων. Κωδικός ανοίγματος: <b>1234</b></p>
<p>Η μη άμεση ανάγνωση συνεπάγεται πρόστιμο και αναγκαστική εκτέλεση.</p>"""))

    # 06 phish — advance fee
    add(frm=("Αριστοτέλης Καραμάνος", "a.karamanos@fundacion-donaciones.example"),
        subject="Δωρεά για φιλανθρωπικό έργο",
        date=datetime(2026, 10, 21, 9, 15, tzinfo=tz(-4)), ip="198.51.100.91", mta="smtp.fundacion-donaciones.example",
        auth="spf=pass dkim=none dmarc=none", replyto=("Α. Καραμάνος", "karamanos.office@freemail-service.example"), plain=True,
        html=wrap("", f"""
<p>Αγαπητέ φίλε,</p>
<p>Είμαι ο Αριστοτέλης Καραμάνος. Λόγω σοβαρής ασθένειας, οι γιατροί μου έδωσαν λίγους μήνες ζωής και θέλω να δωρίσω
<b>4.500.000 €</b> σε φιλανθρωπικά έργα στην Ελλάδα. Σας επέλεξα επειδή το όνομά σας βρέθηκε σε κατάλογο έμπιστων προσώπων.</p>
<p>Τα χρήματα βρίσκονται σε τράπεζα του εξωτερικού. Για να αποδεσμευτούν χρειάζεται να καταβάλετε <b>350 €</b> για έξοδα νομικής
μεταφοράς. Μόλις τα στείλετε, θα λάβετε το σύνολο.</p>
<p>Παρακαλώ μην το αναφέρετε σε κανέναν. Συμπληρώστε τη φόρμα αποδοχής ή απαντήστε στη διεύθυνση απάντησης:
{a("Φόρμα αποδοχής δωρεάς", "http://donation-claims.fundacion-donaciones.example/accept")}</p>
<p>Ο Θεός να σας ευλογεί,<br>Α. Καραμάνος</p>"""))

    # 07 legit shop order
    add(frm=("Κυκλαδικό Κατάστημα", "orders@kykladiko-shop.example"),
        subject="Η παραγγελία σας #A-48213 αποστέλλεται",
        date=datetime(2026, 10, 21, 12, 0, tzinfo=tz(3)), ip="192.0.2.55", mta="smtp.kykladiko-shop.example",
        auth="spf=pass dkim=pass dmarc=pass",
        html=wrap("Κυκλαδικό Κατάστημα", f"""
<p>Γεια σας Ελένη,</p>
<p>Η παραγγελία σας <b>#A-48213</b> (1 × Toner HL-3170 μαύρο) παραδόθηκε στην μεταφορική και αναμένεται στις 23/10.</p>
<p>Παρακολούθηση: {a("http://www.kykladiko-shop.example/orders/A-48213", "http://www.kykladiko-shop.example/orders/A-48213")}</p>
<p>Σας ευχαριστούμε,<br>Κυκλαδικό Κατάστημα</p>""", "Λάβατε αυτό το μήνυμα επειδή υποβάλατε παραγγελία."))

    # 08 phish — parcel fee
    add(frm=("Ταχυμεταφορές Αιγαίου", "no-reply@taxymetafores-aigaiou-track.example"),
        subject="Η αποστολή σας εξακολουθεί να εκκρεμεί — απαιτούνται οδηγίες",
        date=datetime(2026, 10, 21, 13, 25, tzinfo=tz(0)), ip="203.0.113.140", mta="mta7.taxymetafores-aigaiou-track.example",
        auth="spf=pass dkim=none dmarc=none",
        html=wrap("Ταχυμεταφορές Αιγαίου", f"""
<p>Το δέμα σας δεν μπόρεσε να παραδοθεί λόγω ελλιπούς διεύθυνσης.</p>
<p>Για να επαναπρογραμματιστεί η παράδοση, πληρώστε τέλος <b>1,20 €</b> και επιβεβαιώστε τη διεύθυνσή σας.
Αλλιώς το δέμα θα επιστραφεί αύριο.</p>
{button("Πληρωμή και επιβεβαίωση", "http://pay-parcel.delivery-fee.example/track?id=RK48820")}""",
        "Μην μοιραστείτε αυτό το μήνυμα."))

    # 09 phish — tax refund
    add(frm=("Φορολογικό Κέντρο Αιγίς", "no-reply@refund-state-gov.example"),
        subject="Επιστροφή φόρου 412,80 € — απαιτείται επιβεβαίωση στοιχείων",
        date=datetime(2026, 10, 22, 8, 10, tzinfo=tz(0)), ip="198.51.100.200", mta="mx.refund-state-gov.example",
        auth="spf=pass dkim=none dmarc=none",
        html=wrap("Φορολογικό Κέντρο Αιγίς", f"""
<p>Αγαπητέ φορολογούμενε,</p>
<p>Μετά από έλεγχο της φορολογικής σας δήλωσης δικαιούστε επιστροφή <b>412,80 €</b>.</p>
<p>Για την πίστωση συμπληρώστε το IBAN και τα στοιχεία της κάρτας σας στη φόρμα. Η προθεσμία λήγει σε 48 ώρες.</p>
{button("Είσοδος και είσπραξη επιστροφής", "http://refund-portal.state-services.example/claim")}""",
        "Φορολογικό Κέντρο Αιγίς · Αυτοματοποιημένο μήνυμα."))

    # 10 legit but urgent
    add(frm=("Δίκτυο IT", "it-network@meltemi-logistics.example"),
        subject="ΕΠΕΙΓΟΝ: Απενεργοποίηση παλιού VPN την Παρασκευή 23/10 στις 18:00",
        date=datetime(2026, 10, 22, 10, 45, tzinfo=tz(3)), ip="192.0.2.10", mta="mail.meltemi-logistics.example",
        auth="spf=pass dkim=pass dmarc=pass",
        html=wrap("Meltemi Logistics · Δίκτυο IT", f"""
<p>Συνάδελφοι,</p>
<p>Το παλιό VPN θα απενεργοποιηθεί την Παρασκευή 23/10 στις 18:00. Όποιος εργάζεται εξ αποστάσεως πρέπει να έχει εγκαταστήσει
τον νέο πελάτη πριν από τότε, αλλιώς δεν θα έχει πρόσβαση τη Δευτέρα.</p>
<p>Οδηγίες και λήψη από την ενδοεταιρική σελίδα:
{a("http://intranet.meltemi-logistics.example/vpn", "http://intranet.meltemi-logistics.example/vpn")}</p>
<p>Δεν ζητείται κωδικός με email. Η σύνδεση γίνεται με τον συνήθη λογαριασμό σας στο πρόγραμμα.</p>
<p>Δίκτυο IT</p>""", "Εσωτερική ανακοίνωση."))

    # 11 phish — payment provider compliance
    add(frm=("PayNest Συμμόρφωση", "compliance@pn-notice.example"),
        subject="Σημαντικό: Ενημερώστε τον λογαριασμό PayNest εντός 7 ημερών",
        date=datetime(2026, 10, 22, 14, 0, tzinfo=tz(2)), ip="203.0.113.9", mta="relay.pn-notice.example",
        auth="spf=pass dkim=pass dmarc=none",
        html=wrap("PayNest", f"""
<p>Αγαπητέ έμπορε,</p>
<p>Λόγω νέων κανονισμών συμμόρφωσης, ο λογαριασμός σας PayNest πρέπει να επαληθευτεί εντός 7 ημερών. Μετά την προθεσμία οι
πληρωμές σας θα σταματήσουν.</p>
<p>Ο έλεγχος διαρκεί λιγότερο από δύο λεπτά.</p>
{button("Επαλήθευση λογαριασμού", "http://paynest.account-review.example/login")}
<p style="font-size:12px;color:#555">Συνδεθείτε στη διεύθυνση http://www.paynest.example</p>""", "PayNest Compliance"))

    # 12 phish — homoglyph domain
    add(frm=("Elara Bank", "no-reply@e1ara-bank.example"),
        subject="Υποχρεωτική ενημέρωση PSD2 2026",
        date=datetime(2026, 10, 23, 3, 15, tzinfo=tz(0)), ip="198.51.100.230", mta="mail.e1ara-bank.example",
        auth="spf=pass dkim=pass dmarc=pass",
        html=wrap("Elara Bank", f"""
<p>Αγαπητέ πελάτη,</p>
<p>Σύμφωνα με την οδηγία PSD2, πρέπει να επιβεβαιώσετε τον αριθμό κινητού σας για να συνεχίσετε να εγκρίνετε συναλλαγές.</p>
<p>Η ενημέρωση είναι υποχρεωτική και θα ισχύσει από αύριο.</p>
{button("Ενημέρωση τώρα", "http://e1ara-bank.example/psd2")}""",
        "Elara Bank · Αυτό είναι αυτοματοποιημένο μήνυμα."))
    return M


def build(m, n):
    msg = EmailMessage()
    msg["Received"] = (f"from {m['mta']} ({m['mta']} [{m['ip']}]) by mx.meltemi-logistics.example (Postfix) "
                       f"with ESMTPS id L{n:02d}A9X{n:02d}; {format_datetime(m['date'])}")
    msg["Authentication-Results"] = f"mx.meltemi-logistics.example; {m['auth']}"
    msg["From"] = f'"{m["frm"][0]}" <{m["frm"][1]}>' if m["frm"][0] else m["frm"][1]
    msg["To"] = f'"{TO[0]}" <{TO[1]}>'
    if m.get("replyto"):
        msg["Reply-To"] = f'"{m["replyto"][0]}" <{m["replyto"][1]}>'
    msg["Subject"] = m["subject"]
    msg["Date"] = format_datetime(m["date"])
    msg["Message-ID"] = make_msgid(idstring=f"{n:02d}{zlib.crc32(m['subject'].encode()) % 100000}", domain=m["frm"][1].split("@")[1])
    msg.set_content(tagless(m["html"]))
    msg.add_alternative(m["html"], subtype="html")
    if m.get("attach"):
        name, data = m["attach"]
        msg.add_attachment(data, maintype="application", subtype="zip", filename=name)
    return msg


def main():
    M = messages()
    OUT.mkdir(exist_ok=True)
    for old in OUT.glob("*.eml"):
        old.unlink()
    for i, m in enumerate(M, 1):
        (OUT / f"m{i:02d}.eml").write_bytes(build(m, i).as_bytes())
    # Epoch-prefixed Maildir names + mtimes for the playbook (kept out of mail/).
    manifest = [{"src": f"m{i:02d}.eml", "name": f"{int(m['date'].timestamp())}.M{i:02d}P1.lab",
                 "mtime": m["date"].astimezone(timezone.utc).strftime("%Y%m%d%H%M.00")}
                for i, m in enumerate(M, 1)]
    (OUT.parent / "init" / "mail-manifest.json").write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    print(f"wrote {len(M)} messages")


if __name__ == "__main__":
    main()
