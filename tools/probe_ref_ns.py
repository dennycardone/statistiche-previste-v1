"""Quante partite non ancora giocate hanno già l'arbitro indicato (oggi + prossimi 6 giorni, nostri campionati)."""
import json, os, urllib.request, urllib.parse, datetime, collections
KEY = os.environ["APIFOOTBALL_KEY"].strip()
# riserva dell'app: la prova parte solo con le richieste che avanzano (tools/af_budget.py), altrimenti si rinvia
import sys as _s, os as _o; _s.path.insert(0, _o.path.dirname(_o.path.abspath(__file__))); import af_budget as _ab, urllib.request as _u, json as _j
_rq = _ab.requests_of(_j.loads(_u.urlopen(_u.Request("https://v3.football.api-sports.io/status", headers={"x-apisports-key": KEY}), timeout=30).read().decode()))
if _ab.test_budget(_rq) < 50: print("::notice title=Prova rinviata::richieste riservate all'app (" + str(_rq.get("current")) + " su " + str(_rq.get("limit_day")) + ")"); _s.exit(0)

IDS = {135,136,39,40,41,42,43,140,141,61,62,78,79,88,94,179,180,183,184,144,203,197,128,218,71,169,119,244,357,98,262,103,106,283,235,113,207,253}
out = {}
for k in range(7):
    d = str(datetime.date.today() + datetime.timedelta(days=k))
    req = urllib.request.Request("https://v3.football.api-sports.io/fixtures?" + urllib.parse.urlencode({"date": d}), headers={"x-apisports-key": KEY})
    F = json.loads(urllib.request.urlopen(req, timeout=60).read().decode()).get("response", [])
    ns = [f for f in F if f["league"]["id"] in IDS and f["fixture"]["status"]["short"] in ("NS", "TBD")]
    out[d] = {"partite": len(ns), "con_arbitro": sum(1 for f in ns if f["fixture"].get("referee")),
              "esempi": [(f["league"]["name"], f["teams"]["home"]["name"], f["teams"]["away"]["name"], f["fixture"].get("referee")) for f in ns][:12]}
os.makedirs("probe", exist_ok=True); json.dump(out, open("probe/apifootball.json", "w"), indent=1, ensure_ascii=False)
print(json.dumps({d: (v["partite"], v["con_arbitro"]) for d, v in out.items()}))
