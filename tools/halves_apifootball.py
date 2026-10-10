"""Statistiche per tempo (corner, tiri, tiri in porta; i falli per tempo API-Football non li dà) per il backtest dell'1X2 per tempo.
fixtures/statistics?fixture=&half=true, una richiesta per partita, dalle più recenti; disponibili circa dalla stagione 2024-25.
Partite: data/apif.json (giocate dal 1/7/2024). Riprende da tempi/*.json; usa solo le richieste che avanzano dopo la riserva dell'app (tools/af_budget.py)."""
import json, os, time, urllib.request, urllib.parse
KEY = os.environ["APIFOOTBALL_KEY"].strip()
NOSTATS = {"EC", "SC1", "SC2", "SC3"}
used = 0
def get(p, **q):
    global used
    used += 1
    req = urllib.request.Request("https://v3.football.api-sports.io/" + p + "?" + urllib.parse.urlencode(q), headers={"x-apisports-key": KEY})
    for t in range(3):
        try:
            with urllib.request.urlopen(req, timeout=60) as r: d = json.loads(r.read().decode())
            time.sleep(0.15); return d
        except Exception as e:
            print("retry", e); time.sleep(5)
    return {"errors": ["rete"]}
import sys; sys.path.insert(0, os.path.dirname(__file__)); import af_budget
rq = af_budget.requests_of(get("status")); budget = af_budget.test_budget(rq)   # solo le richieste che avanzano dopo la riserva dell'app
print("richieste oggi", rq, "disponibili", budget)
print(f"::notice title=Tempi::richieste {rq.get('current')} su {rq.get('limit_day')}, disponibili per i tempi {budget}" if rq else "::notice title=Tempi::stato API non disponibile (richieste del giorno finite): nessun download stasera")
os.makedirs("tempi", exist_ok=True)
AP = json.load(open("data/apif.json"))["partite"]
todo = sorted(((v[0], fid, v[1], v[2], v[3]) for fid, v in AP.items() if v[9] in ("FT", "AET", "PEN") and v[0] >= "2024-07-01" and v[1] not in NOSTATS), reverse=True)
D = {}
for fn in os.listdir("tempi"):
    if fn.endswith(".json"): D[fn[:-5]] = json.load(open("tempi/" + fn))
done = {fid for L in D.values() for fid in L}
KS = ["Corner Kicks", "Total Shots", "Shots on Goal"]
def vals(t, k):
    out = []
    for s in KS:
        v = next((x["value"] for x in (t.get(k) or []) if x["type"] == s), None)
        try: out.append(int(v) if v is not None else None)
        except Exception: out.append(None)
    return out
n_new = 0
for d, fid, lg, h, a in todo:
    if fid in done: continue
    if budget < 1: break
    R = get("fixtures/statistics", fixture=fid, half="true"); budget -= 1
    r = R.get("response", [])
    rec = [d, h, a, None, None, None, None]
    if len(r) == 2 and any(k.startswith("statistics_1h") for k in r[0]):
        rec = [d, h, a, vals(r[0], "statistics_1h"), vals(r[1], "statistics_1h"), vals(r[0], "statistics_2h"), vals(r[1], "statistics_2h")]
    D.setdefault(lg, {})[fid] = rec; n_new += 1
for lg, L in D.items(): json.dump(L, open(f"tempi/{lg}.json", "w"), separators=(",", ":"), ensure_ascii=False)
tot = sum(len(L) for L in D.values()); ok = sum(1 for L in D.values() for v in L.values() if v[3])
print("nuove", n_new, "· totale", tot, "su", len(todo), "· con statistiche per tempo", ok, "· richieste usate", used)
