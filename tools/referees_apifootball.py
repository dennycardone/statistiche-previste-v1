"""Arbitri delle stagioni 2022-2024 da API-Football (una richiesta per campionato e stagione), per il backtest del modello falli.
Riprende da referees/referees.json (ramo arbitri); si ferma quando finiscono le richieste del giorno (ne lascia 20 per le quote)."""
import json, os, time, urllib.request, urllib.parse
KEY = os.environ["APIFOOTBALL_KEY"].strip()
LEAGUES = [("I1", 135), ("E0", 39), ("SP1", 140), ("D1", 78), ("F1", 61), ("I2", 136), ("E1", 40), ("N1", 88), ("P1", 94), ("B1", 144), ("T1", 203),
           ("G1", 197), ("SC0", 179), ("SP2", 141), ("F2", 62), ("D2", 79), ("E2", 41), ("E3", 42), ("SC1", 180), ("SC2", 183), ("SC3", 184),
           ("BRA", 71), ("ARG", 128), ("USA", 253), ("MEX", 262), ("CHN", 169)]
SEASONS = [2024, 2023, 2022]
path = "referees/referees.json"
try: R = json.load(open(path))
except Exception: R = {}
def get(p, **q):
    req = urllib.request.Request("https://v3.football.api-sports.io/" + p + ("?" + urllib.parse.urlencode(q) if q else ""), headers={"x-apisports-key": KEY})
    with urllib.request.urlopen(req, timeout=60) as r: return json.loads(r.read().decode())
st = get("status").get("response", {}).get("requests", {})
budget = int(st.get("limit_day", 100)) - int(st.get("current", 0)) - 20
print("richieste disponibili", budget)
for s in SEASONS:
    for lg, lid in LEAGUES:
        k = f"{lg}|{s}"
        if k in R or budget <= 0: continue
        d = get("fixtures", league=lid, season=s); budget -= 1; time.sleep(6.5)
        if d.get("errors"): print(k, d["errors"]); continue
        R[k] = [[f["fixture"]["date"][:10], f["teams"]["home"]["name"], f["teams"]["away"]["name"], f["goals"]["home"], f["goals"]["away"], f["fixture"].get("referee")]
                for f in d.get("response", []) if f["fixture"]["status"]["short"] in ("FT", "AET", "PEN")]
        print(k, len(R[k]), "partite,", sum(1 for x in R[k] if x[5]), "con arbitro")
os.makedirs("referees", exist_ok=True)
json.dump(R, open(path, "w"), ensure_ascii=False)
print("fatte", len(R), "di", len(LEAGUES) * len(SEASONS))
