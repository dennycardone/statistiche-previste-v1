"""Prova: API-Football dà le statistiche per tempo (corner, falli, tiri, tiri in porta)? fixtures/statistics?fixture=&half=true
su partite di stagioni e campionati diversi; confronto con fixtures?ids=. Risultato in probe/apifootball.json."""
import json, os, urllib.request, urllib.parse, time
KEY = os.environ["APIFOOTBALL_KEY"].strip()
# riserva dell'app: la prova parte solo con le richieste che avanzano (tools/af_budget.py), altrimenti si rinvia
import sys as _s, os as _o; _s.path.insert(0, _o.path.dirname(_o.path.abspath(__file__))); import af_budget as _ab, urllib.request as _u, json as _j
_rq = _ab.requests_of(_j.loads(_u.urlopen(_u.Request("https://v3.football.api-sports.io/status", headers={"x-apisports-key": KEY}), timeout=30).read().decode()))
if _ab.test_budget(_rq) < 50: print("::notice title=Prova rinviata::richieste riservate all'app (" + str(_rq.get("current")) + " su " + str(_rq.get("limit_day")) + ")"); _s.exit(0)

def get(p, **q):
    req = urllib.request.Request("https://v3.football.api-sports.io/" + p + "?" + urllib.parse.urlencode(q), headers={"x-apisports-key": KEY})
    with urllib.request.urlopen(req, timeout=60) as r: d = json.loads(r.read().decode())
    time.sleep(0.3); return d
AP = json.load(open("data/apif.json"))["partite"]
pick = {}
for fid, v in AP.items():
    if v[9] != "FT": continue
    for lg in ("E0", "I1", "SP2", "ARG", "SC1", "EC"):
        y = v[0][:4]
        k = (lg, y)
        if v[1] == lg and k not in pick and y in ("2022", "2023", "2024", "2025", "2026"): pick[k] = fid
out = {"status": get("status").get("response", {}).get("requests"), "prove": []}
for (lg, y), fid in sorted(pick.items()):
    d = get("fixtures/statistics", fixture=fid, half="true")
    r = d.get("response", [])
    item = {"lg": lg, "anno": y, "fixture": fid, "errori": d.get("errors"), "squadre": len(r)}
    if r:
        t = r[0]; item["chiavi"] = list(t.keys())
        for k in t:
            if k.startswith("statistics"):
                item[k] = {s["type"]: s["value"] for s in (t[k] or [])}
    out["prove"].append(item)
d = get("fixtures", ids="-".join(list(pick.values())[:3]))
f = d["response"][0] if d.get("response") else {}
out["fixtures_ids_statistics_keys"] = [list(t.keys()) for t in f.get("statistics", [])]
out["status_fine"] = get("status").get("response", {}).get("requests")
os.makedirs("probe", exist_ok=True); json.dump(out, open("probe/apifootball.json", "w"), indent=1, ensure_ascii=False)
print(json.dumps(out, indent=1, ensure_ascii=False)[:3000])
