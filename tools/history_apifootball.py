"""Storico completo da API-Football (piano a pagamento) per i backtest: per ogni partita giocata data, squadre, gol, arbitro e statistiche
(tiri, tiri in porta, corner, falli, cartellini, xG). fixtures?league&season per l'elenco, poi fixtures?ids= (20 partite per richiesta).
Riprende da storico/*.json (ramo storico); lascia 500 richieste al giorno per le quote."""
import json, os, time, urllib.request, urllib.parse, glob
KEY = os.environ["APIFOOTBALL_KEY"].strip()
LEAGUES = [("I1", 135), ("E0", 39), ("SP1", 140), ("D1", 78), ("F1", 61), ("I2", 136), ("E1", 40), ("N1", 88), ("P1", 94), ("B1", 144), ("T1", 203),
           ("G1", 197), ("SC0", 179), ("SP2", 141), ("F2", 62), ("D2", 79), ("E2", 41), ("E3", 42), ("SC1", 180), ("SC2", 183), ("SC3", 184),
           ("BRA", 71), ("ARG", 128), ("USA", 253), ("MEX", 262), ("CHN", 169), ("JPN", 98), ("AUT", 218), ("DNK", 119), ("NOR", 103), ("SWE", 113),
           ("RUS", 235), ("POL", 106), ("ROU", 283), ("SWZ", 207), ("FIN", 244), ("IRL", 357), ("EC", 43),
           # ottobre 2026: campionati delle squadre delle coppe europee (solo API-Football) e le tre coppe
           ("SRB", 286), ("CRO", 210), ("HUN", 271), ("CZE", 345), ("UKR", 333), ("ISR", 383), ("BUL", 172), ("CYP", 318), ("SVK", 332), ("BLR", 116),
           ("UCL", 2), ("UEL", 3), ("UECL", 848)]
SEASONS = [2025, 2024, 2023, 2022]
os.makedirs("storico", exist_ok=True)
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
import sys; sys.path.insert(0, os.path.dirname(__file__)); import af_budget
rq = af_budget.requests_of(get("status")); budget = af_budget.test_budget(rq)   # solo le richieste che avanzano dopo la riserva dell'app
print("richieste", rq, "disponibili", budget)
def stat(t, k):
    for s in t.get("statistics", []):
        if s["type"] == k:
            v = s["value"]
            if v is None: return 0 if k in ("Yellow Cards", "Red Cards") else None
            try: return float(str(v).replace("%", ""))
            except Exception: return None
    return None
KS = ["Total Shots", "Shots on Goal", "Corner Kicks", "Fouls", "Yellow Cards", "Red Cards", "expected_goals"]
for s in SEASONS:
    for lg, lid in LEAGUES:
        fn = f"storico/{lg}_{s}.json"
        D = json.load(open(fn)) if os.path.exists(fn) else None
        if D and D.get("completo"): continue
        if budget < 30: break
        if not D:
            L = get("fixtures", league=lid, season=s); budget -= 1
            if L.get("errors"): print(lg, s, L["errors"]); continue
            D = {"lega": lg, "stagione": s, "partite": {}, "completo": False,
                 "ids": [f["fixture"]["id"] for f in L.get("response", []) if f["fixture"]["status"]["short"] in ("FT", "AET", "PEN")]}
        todo = [i for i in D["ids"] if str(i) not in D["partite"]]
        for k in range(0, len(todo), 20):
            if budget < 30: break
            R = get("fixtures", ids="-".join(str(i) for i in todo[k:k + 20])); budget -= 1
            for f in R.get("response", []):
                st_ = {t["team"]["id"]: t for t in f.get("statistics", [])}
                H, A = st_.get(f["teams"]["home"]["id"], {}), st_.get(f["teams"]["away"]["id"], {})
                D["partite"][str(f["fixture"]["id"])] = [f["fixture"]["date"][:16], f["teams"]["home"]["name"], f["teams"]["away"]["name"],
                    f["goals"]["home"], f["goals"]["away"], f["fixture"].get("referee"), [stat(H, k_) for k_ in KS], [stat(A, k_) for k_ in KS]]
        D["completo"] = all(str(i) in D["partite"] for i in D["ids"])
        json.dump(D, open(fn, "w"), ensure_ascii=False, separators=(",", ":"))
        print(lg, s, len(D["partite"]), "/", len(D["ids"]), "xG:", sum(1 for v in D["partite"].values() if v[6][6] is not None))
print("richieste usate", used, "rimaste per oggi (oltre la riserva)", budget)
