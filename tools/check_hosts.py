#!/usr/bin/env python3
"""Instructor-only: every simulated name must be unique across the labs, and the same everywhere:
sim/hosts.txt of each lab = the HOSTS dictionary of its app = docker/docker-compose.yml (extra_hosts)."""
import re
from pathlib import Path

root = Path(__file__).resolve().parent.parent
labs = {"lab-phishing-triage": None, "lab-leaked-account": "sim/app.py", "lab-ransomware-friday": "sim/app.py"}
hosts, ok = {}, True
for lab, app in labs.items():
    hosts[lab] = (root / lab / "sim" / "hosts.txt").read_text().split()
    if app:
        in_app = re.findall(r'^\s+"([a-z0-9.\-]+\.example)": "', (root / lab / app).read_text(encoding="utf-8"), re.M)
        if in_app != hosts[lab]:
            ok = False; print("MISMATCH app.py vs hosts.txt in", lab, in_app, hosts[lab])
hub = (root / "hub" / "hosts.txt").read_text().split()
everything = ["mail.meltemi-logistics.example"] + sum(hosts.values(), []) + hub
dups = sorted({h for h in everything if everything.count(h) > 1})
compose = re.findall(r'- "([^":]+):192\.168\.13\.20"', (root / "docker" / "docker-compose.yml").read_text())
if dups: ok = False; print("DUPLICATE names between labs:", dups)
if sorted(compose) != sorted(everything):
    ok = False; print("MISMATCH docker-compose.yml extra_hosts; missing:", sorted(set(everything) - set(compose)), "extra:", sorted(set(compose) - set(everything)))
pb = (root / "provisioning" / "playbook.yml").read_text()
for h in hub:
    if h not in pb and h.split('.')[0] not in pb: ok = False; print("start host not in playbook:", h)
print(f"{len(everything)} names, all unique, in sync" if ok else "PROBLEMS FOUND")
raise SystemExit(0 if ok else 1)
