"""Recupero dello storico delle statistiche in più (17/10/2026): per ogni partita giocata dalla stagione 2022 a ieri, nei campionati
dell'app e nelle coppe europee, tutte le statistiche per squadra di API-Football nella stessa forma dell'archivio giornaliero
(update_data.py, KS_): tiri, tiri in porta, corner, falli, gialli, rossi, xG, tiri in area, fuori area, bloccati, fuori porta,
possesso, parate, fuorigioco. fixtures?ids= (20 partite per richiesta). Partite: ramo storico (storico/*_AAAA.json) e, se c'è,
data/apif.json. Riprende da statextra/*.json (gira anche alle 00:20 UTC, quando restano più richieste libere); usa SOLO le richieste che avanzano dopo la riserva dell'app (tools/af_budget.py)."""
import json, os, time, glob, datetime, urllib.request, urllib.parse, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import af_budget
KEY = os.environ["APIFOOTBALL_KEY"].strip()
KS = ["Total Shots", "Shots on Goal", "Corner Kicks", "Fouls", "Yellow Cards", "Red Cards", "expected_goals",
      "Shots insidebox", "Shots outsidebox", "Blocked Shots", "Shots off Goal", "Ball Possession", "Goalkeeper Saves", "Offsides"]
SKIP = {"CYP", "BLR", "SVK", "UKR"}   # campionati non presenti nell'app
OUTD = "statextra"; os.makedirs(OUTD, exist_ok=True)
used = 0
def get(p, **q):
    global used
    used += 1
    req = urllib.request.Request("https://v3.football.api-sports.io/" + p + ("?" + urllib.parse.urlencode(q) if q else ""), headers={"x-apisports-key": KEY})
    for t in range(3):
        try:
            with urllib.request.urlopen(req, timeout=60) as r: d = json.loads(r.read().decode())
            time.sleep(0.25); return d
        except Exception as e:
            print("retry", p, e); time.sleep(5)
    return {"errors": ["rete"]}
def stat(t, k):
    for s in t.get("statistics", []):
        if s["type"] == k:
            v = s["value"]
            if v is None: return 0 if k in ("Yellow Cards", "Red Cards") else None
            try: return float(str(v).replace("%", ""))
            except Exception: return None
    return None
today = datetime.date.today().isoformat(); recent = (datetime.date.today() - datetime.timedelta(days=3)).isoformat()
# partite da coprire: giocate (risultato presente), stagione ≥ 2022, fino a ieri
todo = {}
for fn in glob.glob("storico/*_20[0-9][0-9].json"):
    try: D = json.load(open(fn))
    except Exception: continue
    if not isinstance(D, dict) or "lega" not in D or D["lega"] in SKIP or int(D.get("stagione", 0)) < 2022: continue
    for fid, v in D.get("partite", {}).items():
        if v[3] is not None and v[0][:10] < today: todo[fid] = (v[0], D["lega"], v[1], v[2])
if os.path.exists("data/apif.json"):
    for fid, v in json.load(open("data/apif.json"))["partite"].items():
        if v[9] in ("FT", "AET", "PEN") and "2022-07-01" <= v[0][:10] < today and v[1] not in SKIP: todo.setdefault(fid, (v[0], v[1], v[2], v[3]))
DONE = {}
for fn in glob.glob(os.path.join(OUTD, "*.json")): DONE.update({k: (os.path.basename(fn)[:-5], v) for k, v in json.load(open(fn)).items()})
need = sorted((x for x in todo if x not in DONE), key=lambda f: todo[f][0], reverse=True)
rq = af_budget.requests_of(get("status")); budget = af_budget.test_budget(rq)
print(f"::notice title=Statistiche in più · recupero::partite da coprire {len(todo)} · già fatte {len(todo) - len(need)} · da fare {len(need)} (~{(len(need) + 19) // 20} richieste) · disponibili ora {budget} (richieste oggi {rq.get('current')} su {rq.get('limit_day')})")
def save():
    by = {}
    for fid, (lg, rec) in DONE.items(): by.setdefault(lg, {})[fid] = rec
    for lg, L in by.items(): json.dump(L, open(os.path.join(OUTD, lg + ".json"), "w"), separators=(",", ":"), ensure_ascii=False)
n_new = n_req = 0
for i in range(0, len(need), 20):
    if budget < 1: break
    ids = need[i:i + 20]
    R = get("fixtures", ids="-".join(ids)); budget -= 1; n_req += 1
    if R.get("errors"): print("errori API:", R["errors"]); break
    got = set()
    for f in R.get("response", []):
        fid = str(f["fixture"]["id"]); st = {t["team"]["id"]: t for t in f.get("statistics", [])}
        H, A = st.get(f["teams"]["home"]["id"], {}), st.get(f["teams"]["away"]["id"], {})
        rec = [todo[fid][0], todo[fid][2], todo[fid][3], [stat(H, k) for k in KS] if H else None, [stat(A, k) for k in KS] if A else None]
        if rec[3] is None and todo[fid][0][:10] >= recent: continue   # statistiche non ancora pubblicate: si riprova al giro dopo
        DONE[fid] = (todo[fid][1], rec); got.add(fid); n_new += 1
    if n_req % 100 == 0: save()
save()
left = sum(1 for x in todo if x not in DONE); ok = sum(1 for lg, r in DONE.values() if r[3] and r[4] and r[3][13] is not None and r[4][13] is not None)
print(f"::notice title=Statistiche in più · recupero::nuove {n_new} con {n_req} richieste · mancano {left} partite (~{(left + 19) // 20} richieste) · con fuorigioco {ok} · {'COMPLETO' if left == 0 else 'continua al prossimo giro'}")
