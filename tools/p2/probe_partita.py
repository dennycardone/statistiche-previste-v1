"""Controllo di una partita su API-Football (9/11/2026: Las Palmas–Eldense, Segunda División, data che non torna). 3 richieste dalla riserva."""
import json, os, sys, urllib.request, urllib.parse
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import af_budget
K = os.environ["APIFOOTBALL_KEY"].strip()
def af(p, **q):
    r = urllib.request.Request("https://v3.football.api-sports.io/" + p + "?" + urllib.parse.urlencode(q), headers={"x-apisports-key": K})
    return json.loads(urllib.request.urlopen(r, timeout=60).read().decode())
if af_budget.test_budget(af_budget.requests_of(af("status"))) < 20: print("::notice title=Prova::riserva insufficiente"); sys.exit(0)
out = []
for d in ("2026-11-08", "2026-11-09", "2026-11-10"):
    for f in af("fixtures", league=141, season=2026, date=d, timezone="Europe/Rome").get("response", []):
        out.append(f"{d}: {f['teams']['home']['name']}-{f['teams']['away']['name']} {f['fixture']['date'][:16]} {f['fixture']['status']['short']} id {f['fixture']['id']}")
print("::notice title=Prova · Segunda 8-10/11::" + " ‖ ".join(out))
os.makedirs("probe", exist_ok=True); json.dump(out, open("probe/apifootball.json", "w"))
