"""Statistiche per tempo per il backtest dei mercati del 1° tempo. 28/10/2026: API-Football le dà TUTTE per tempo (verifica su una partita
di Serie A): si salvano corner, tiri, tiri in porta (le prime tre, come prima) più falli, fuorigioco, gialli, rossi, tiri in area, tiri
fuori area, tiri respinti, tiri fuori, punizioni, parate, possesso, passaggi, passaggi riusciti, xG. Prima le partite nuove, poi si
riscaricano quelle salvate col formato vecchio (solo le prime tre statistiche).
fixtures/statistics?fixture=&half=true, una richiesta per partita, dalle più recenti; disponibili circa dalla stagione 2024-25.
Partite: data/apif.json (giocate dal 1/7/2024). Riprende da tempi/*.json; usa solo le richieste che avanzano dopo la riserva dell'app (tools/af_budget.py)."""
import json, os, time, urllib.request, urllib.parse
KEY = os.environ["APIFOOTBALL_KEY"].strip()
NOSTATS = {"EC", "SC1", "SC2", "SC3"}
import re as _re
_src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "update_data.py")).read()
_rm = _re.search(r"REMOVED = \{(.*?)\}", _src); NOSTATS |= set(_re.findall(r'"(\w+)"', _rm.group(1))) if _rm else set()   # campionati tolti
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
KS = ["Corner Kicks", "Total Shots", "Shots on Goal", "Fouls", "Offsides", "Yellow Cards", "Red Cards", "Shots insidebox", "Shots outsidebox",
      "Blocked Shots", "Shots off Goal", "Free Kicks", "Goalkeeper Saves", "Ball Possession", "Total passes", "Passes accurate", "expected_goals"]
def vals(t, k):
    out = []
    for s in KS:
        v = next((x["value"] for x in (t.get(k) or []) if x["type"] == s), None)
        try: out.append(None if v is None else float(str(v).rstrip("%")) if s in ("Ball Possession", "expected_goals") else int(v))
        except Exception: out.append(None)
    return out
n_new = 0
# 28/10/2026: prima le partite mai scaricate, poi quelle col formato vecchio (3 statistiche) da riscaricare con tutte le statistiche
old = {fid for L in D.values() for fid, v in L.items() if v[3] and len(v[3]) < len(KS)}
todo = [x for x in todo if x[1] not in done] + [x for x in todo if x[1] in old]
n_re = 0
for d, fid, lg, h, a in todo:
    if budget < 1: break
    R = get("fixtures/statistics", fixture=fid, half="true"); budget -= 1
    r = R.get("response", [])
    rec = [d, h, a, None, None, None, None]
    if len(r) == 2 and any(k.startswith("statistics_1h") for k in r[0]):
        rec = [d, h, a, vals(r[0], "statistics_1h"), vals(r[1], "statistics_1h"), vals(r[0], "statistics_2h"), vals(r[1], "statistics_2h")]
    if fid in old: n_re += 1
    D.setdefault(lg, {})[fid] = rec; n_new += 1
for lg, L in D.items(): json.dump(L, open(f"tempi/{lg}.json", "w"), separators=(",", ":"), ensure_ascii=False)
tot = sum(len(L) for L in D.values()); ok = sum(1 for L in D.values() for v in L.values() if v[3])
full = sum(1 for L in D.values() for v in L.values() if v[3] and len(v[3]) == len(KS))
print("nuove", n_new - n_re, "· riscaricate", n_re, "· totale", tot, "· con statistiche per tempo", ok, "· con tutte le statistiche", full, "· richieste usate", used)
print(f"::notice title=Tempi::nuove {n_new - n_re} · riscaricate con tutte le statistiche {n_re} · archivio {tot} · complete {full} · da riscaricare {len(old) - n_re} · richieste {used}")
