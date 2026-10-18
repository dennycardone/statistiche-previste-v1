"""Prova (19/10/2026): quali statistiche di squadra dà API-Football (cerco xGOT / grandi occasioni). Poche richieste, sopra la riserva dell'app."""
import json, os, sys, urllib.request, urllib.parse, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import af_budget
KEY = os.environ["APIFOOTBALL_KEY"].strip()
def get(p, **q):
    req = urllib.request.Request("https://v3.football.api-sports.io/" + p + "?" + urllib.parse.urlencode(q), headers={"x-apisports-key": KEY})
    with urllib.request.urlopen(req, timeout=60) as r: return json.loads(r.read().decode())
if af_budget.test_budget(af_budget.requests_of(get("status"))) < 10: print("::warning title=Statistiche::richieste non disponibili ora"); sys.exit(0)
types = collections.Counter(); ex = {}
for lid, d in ((135, "2026-10-18"), (39, "2026-10-18"), (140, "2026-10-18")):
    F = [f for f in get("fixtures", league=lid, season=2026, date=d).get("response", []) if f["fixture"]["status"]["short"] in ("FT", "AET", "PEN")][:20]
    if not F: continue
    for f in get("fixtures", ids="-".join(str(x["fixture"]["id"]) for x in F)).get("response", []):
        for t in f.get("statistics", []):
            for s in t.get("statistics", []):
                types[s["type"]] += 1; ex.setdefault(s["type"], f"{f['teams']['home']['name']}-{f['teams']['away']['name']} {t['team']['name']}: {s['value']}")
print("::notice title=Statistiche API-Football::" + f"{len(types)} tipi: " + " · ".join(f"{k} ({v})" for k, v in types.most_common()))
for k in types:
    if any(w in k.lower() for w in ("expected", "prevent", "big", "chance", "xg", "target")): print("::notice title=Esempio " + k + "::" + ex[k])
