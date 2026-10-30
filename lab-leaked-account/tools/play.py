#!/usr/bin/env python3
"""Instructor-only: plays the lab through the HTTP API against a running server and checks the rules.
Usage: play.py <base url> <scenario>"""
import json, os, sys, time, urllib.request, http.cookiejar

BASE = sys.argv[1].rstrip("/")
HOST = {"email": "mail.aigaio-mail.example", "shop": "shop.kyklades-store.example", "social": "www.sinomilia.example",
        "bank": "ebanking.elara-bank.example", "vault": "vault.passkeeper.example", "start": os.environ.get("START_HOST", "accounts.labs.example")}
jar = {k: http.cookiejar.CookieJar() for k in HOST}

def call(svc, path, body=None):
    req = urllib.request.Request(BASE + path, method="POST" if body is not None else "GET",
                                 data=json.dumps(body or {}).encode() if body is not None else None,
                                 headers={"Host": HOST[svc], "Content-Type": "application/json"})
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar[svc]))
    try:
        with op.open(req) as r:
            raw = r.read()
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        return {"http": e.code}

def login(svc, pw, user=None):
    me = call(svc, "/api/me")
    r = call(svc, "/api/login", {"user": user or me["user"], "pw": pw})
    if r.get("need_code"):
        r = call(svc, "/api/login", {"user": user or me["user"], "pw": pw, "code": r["sms"]})
    assert r.get("ok"), (svc, r)

def mfa(svc):
    r = call(svc, "/api/mfa", {})
    r = call(svc, "/api/mfa", {"code": r["sms"]}); assert r["ok"], r

def newpw(svc, old, signout=True):
    pw = call("vault", "/api/generate", {})["pw"]
    r = call(svc, "/api/password", {"old": old, "new": pw, "signout_others": signout}); assert r["ok"], r
    return pw

def progress(): return call("start", "/api/progress")
def report(): return call("start", "/api/report")
def tiles(): return progress()["tiles"]
def vault(): return {r["svc"]: r for r in call("vault", "/api/vault")["rows"]}

OK = True
def check(name, cond):
    global OK; OK &= bool(cond); print(("OK  " if cond else "FAIL"), name)

LEAK, SOCIAL = "Eleni1985", "Luna1985"
sc = sys.argv[2]
call("start", "/api/reset", {})
v = vault()
check("vault audit: email+shop share the leaked password", v["email"]["reused"] and v["shop"]["reused"] and v["email"]["leaked"])
check("vault audit: bank is fine, social is weak", not v["bank"]["reused"] and v["social"]["weak"])
check("nothing happens until the player asks for a round", progress()["round"] == 0 and not progress()["events"])
def attack(): call("start", "/api/attack", {})

def secure_all(pws, order=("email", "social", "shop", "bank")):
    for s in order:
        login(s, pws[s])
        pws[s] = newpw(s, pws[s])
        if s in ("email", "social", "bank"): mfa(s)
    # social privacy, bank alerts
    for p in call("social", "/api/data")["posts"]:
        if p["tag"]: call("social", "/api/post", {"id": p["id"], "action": "me"})
    call("bank", "/api/alerts", {"on": True})
    return pws

def clean_up_attacker():
    for sname in ("email", "shop", "social", "bank"):
        d = call(sname, "/api/data")
        for x in d["sessions"]:
            if x["attacker"]: call(sname, "/api/revoke", {"id": x["id"]})
        for r in d.get("rules", []): call(sname, "/api/rule/delete", {"id": r["id"]})
        for x in d.get("payees", []):
            if x["attacker"]: call(sname, "/api/payee/delete", {"id": x["id"]})

def take_over_everything():
    attack()
    p = progress()
    check("all four accounts compromised", all(t == "compromised" for t in p["tiles"].values()))
    check("bank takeover happened through the e-mail", any(e["svc"] == "bank" and e["ok"] for e in p["events"]))
    check("not done", not p["done"])

if sc == "perfect":                      # secure everything, then test the defence
    pws = {"email": LEAK, "shop": LEAK, "social": SOCIAL, "bank": "Ar1stoK#9vTq"}
    secure_all(pws)
    check("not done before a round is requested", not progress()["done"])
    attack()
    p = progress()
    check("done and flag", p["done"] and p.get("flag") == "FLAG{0f2c952afe849ec22051abb9fed9af3d}")
    check("all four attacks were blocked", all(e["ok"] is False for e in p["events"]) and len(p["events"]) == 4)

elif sc == "naive":                      # do nothing, let the attacker win, then recover
    take_over_everything()
    attack()
    p = progress()
    check("second round reports they are still inside", sum(1 for e in p["events"] if e["round"] == 2 and e["ok"]) == 4)
    pws = {"email": LEAK, "shop": LEAK, "social": SOCIAL}
    for s in ("email", "shop", "social"):
        login(s, pws[s])
        if s == "email": check("a second round did not duplicate the break-in", sum(x["attacker"] for x in call("email", "/api/data")["sessions"]) == 1)
        pws[s] = newpw(s, pws[s])
    mfa("email"); mfa("social")
    for p_ in call("social", "/api/data")["posts"]:
        if p_["tag"]: call("social", "/api/post", {"id": p_["id"], "action": "me"})
    check("bank cannot be entered with the old password", call("bank", "/api/login", {"user": "emarkou", "pw": "Ar1stoK#9vTq"}).get("ok") is False)
    check("report lists the bank as open", report()["open"]["bank"] != [])
    r = call("bank", "/api/recover", {}); check("recovery sends an SMS", r.get("need_code"))
    newbank = call("vault", "/api/generate", {})["pw"]
    r = call("bank", "/api/recover", {"code": r["sms"], "new": newbank}); check("bank password reset by SMS", r.get("ok"))
    login("bank", newbank); mfa("bank"); call("bank", "/api/alerts", {"on": True})
    b = call("bank", "/api/data"); check("attacker session removed by the reset", not any(x["attacker"] for x in b["sessions"]))
    clean_up_attacker()
    attack()
    pr = progress(); check("lab completed after full recovery", pr["done"] and pr.get("flag"))

elif sc == "order":                      # password changed but the attacker's session kept: he is still inside
    take_over_everything()
    login("email", LEAK); newpw("email", LEAK, signout=False); mfa("email")
    attack()
    p = progress()
    check("email still compromised after password change without signing out", p["tiles"]["email"] == "compromised")
    check("round 2 says he is still inside the e-mail", any(e["round"] == 2 and e["svc"] == "email" and e["ok"] and "ακόμα" in e["title"] for e in p["events"]))

elif sc == "session":                    # the same, but the player signs out other devices and removes the rule
    take_over_everything()
    login("email", LEAK); pw = newpw("email", LEAK, signout=True); mfa("email")
    d = call("email", "/api/data"); [call("email", "/api/rule/delete", {"id": r["id"]}) for r in d["rules"]]
    check("email no longer has attacker access", report()["open"]["email"] == [])
    attack()
    p = progress()
    check("round 2: attacker blocked at the e-mail", any(e["round"] == 2 and e["svc"] == "email" and not e["ok"] for e in p["events"]))

print("RESULT", "PASS" if OK else "FAIL")
sys.exit(0 if OK else 1)
