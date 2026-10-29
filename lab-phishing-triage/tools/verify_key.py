#!/usr/bin/env python3
"""Instructor-only: re-derives every flag from the generated .eml / scenario files."""
import email, json, re
from email import policy
from pathlib import Path
from urllib.parse import urlparse

base = Path(__file__).resolve().parent
key = json.loads((base / "answer_key.json").read_text())
sim = json.loads((base.parent / "sim" / "scenarios.json").read_text(encoding="utf-8"))
mail = {p.stem: email.message_from_bytes(p.read_bytes(), policy=policy.default) for p in sorted((base.parent / "mail").glob("*.eml"))}
html = lambda m: m.get_body(("html",)).get_content()
hrefs = lambda m: re.findall(r'href="([^"]+)"', html(m))
addr = lambda m: m["From"].addresses[0].addr_spec
errs = []

def check(name, got):
    exp = key[name]
    print(("OK  " if got == exp else "FAIL"), name, got, "" if got == exp else f"(expected {exp})")
    if got != exp: errs.append(name)

check("F1", sim["flag"])
check("F2", addr(mail["m03"]))
check("F3", addr(mail["m12"]))
check("F4", urlparse(hrefs(mail["m02"])[0]).hostname.split(".")[-2])
check("F5", [p.get_filename() for p in mail["m05"].iter_attachments()][0].rsplit(".", 1)[1])
check("F6", re.search(r"(\d+) €</b> για έξοδα", html(mail["m06"])).group(1))
check("F7", re.search(r"<b>(my\.[a-z.\-]+)</b>", html(mail["m04"])).group(1))
check("F8", addr(mail["m07"]).split("@")[1])
check("F9", re.search(r"«κωδικό επιβεβαίωσης (SMS)»", " ".join(st["text"] for st in sim["emails"]["m02"]["outcome"]["steps"])).group(1).lower())
check("F10", re.search(r"άλλαξε (IBAN)", " ".join(st["text"] for st in sim["emails"]["m03"]["outcome"]["steps"])).group(1).lower())

# consistency: truth in the simulation == key; every link host is served; hosts.txt and compose in sync
assert sorted(k for k, v in sim["emails"].items() if v["truth"] == "scam") == sorted(key["malicious"]), "sim truth != key"
assert sorted(key["malicious"] + key["legit"]) == sorted(mail), "key does not cover every message"
for k, m in mail.items():
    for h in hrefs(m):
        if urlparse(h).hostname not in sim["sites"]: errs.append(f"unserved host in {k}")
hosts = (base.parent / "sim" / "hosts.txt").read_text().split()
assert hosts == list(sim["sites"]), "hosts.txt out of sync"
# docker-compose extra_hosts vs hosts.txt is checked for all labs by tools/check_hosts.py at the repository root
subjects = [e["subject"].strip() for e in sim["emails"].values()]
assert len(set(subjects)) == len(subjects), "duplicate subjects (report matching is by subject)"
for i, m in mail.items():
    assert str(m["Subject"]).strip() == sim["emails"][i]["subject"].strip(), f"subject mismatch {i}"

blob = b"".join(p.read_bytes() for p in (base.parent / "mail").glob("*.eml")).lower()
for bad in (b"[spam", b"{disarmed", b"uniwa", b"teiath", b"eurobank", b"piraeus", b"alpha bank", b"aade", b"@gmail", b"@outlook"):
    if bad in blob: errs.append(f"leak:{bad!r}")
print("RESULT", "PASS" if not errs else f"FAIL {errs}")
raise SystemExit(bool(errs))
