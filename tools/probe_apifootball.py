"""Prova di API-Football (piano gratuito, massimo ~60 richieste): copertura, statistiche, xG, quote, confronto con football-data.
Scrive probe/apifootball.json. Non modifica i dati dell'app."""
import csv, io, json, os, time, urllib.request, urllib.parse, datetime
KEY = os.environ.get("APIFOOTBALL_KEY", "").strip()
# riserva dell'app: la prova parte solo con le richieste che avanzano (tools/af_budget.py), altrimenti si rinvia
import sys as _s, os as _o; _s.path.insert(0, _o.path.dirname(_o.path.abspath(__file__))); import af_budget as _ab, urllib.request as _u, json as _j
_rq = _ab.requests_of(_j.loads(_u.urlopen(_u.Request("https://v3.football.api-sports.io/status", headers={"x-apisports-key": KEY}), timeout=30).read().decode()))
if _ab.test_budget(_rq) < 50: print("::notice title=Prova rinviata::richieste riservate all'app (" + str(_rq.get("current")) + " su " + str(_rq.get("limit_day")) + ")"); _s.exit(0)

BASE = "https://v3.football.api-sports.io/"
used = 0
def api(path, **q):
    global used
    used += 1
    url = BASE + path + ("?" + urllib.parse.urlencode(q) if q else "")
    req = urllib.request.Request(url, headers={"x-apisports-key": KEY})
    with urllib.request.urlopen(req, timeout=60) as r:
        d = json.loads(r.read().decode())
    time.sleep(7)   # piano gratuito: 10 richieste al minuto
    return d
out = {"quando": datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")}
if not KEY:
    out["errore"] = "segreto APIFOOTBALL_KEY mancante"
else:
    st = api("status"); out["status"] = st.get("response"); out["errori_status"] = st.get("errors")
    # 1. copertura dei campionati della stagione in corso
    L = api("leagues", current="true")
    out["errori_leagues"] = L.get("errors")
    COUNTRIES = {"Italy", "England", "Spain", "France", "Germany", "Netherlands", "Portugal", "Scotland", "Belgium", "Turkey", "Greece",
                 "Argentina", "Austria", "Brazil", "China", "Denmark", "Japan", "Mexico", "Norway", "Russia", "Sweden", "USA", "Finland",
                 "Ireland", "Poland", "Romania", "Switzerland"}
    cov = []
    for x in L.get("response", []):
        if x["country"]["name"] not in COUNTRIES or x["league"]["type"] != "League": continue
        s = (x.get("seasons") or [{}])[-1]; c = s.get("coverage", {})
        cov.append({"id": x["league"]["id"], "paese": x["country"]["name"], "nome": x["league"]["name"], "stagione": s.get("year"),
                    "inizio": s.get("start"), "fine": s.get("end"), "statistiche": c.get("fixtures", {}).get("statistics_fixtures"),
                    "quote": c.get("odds"), "previsioni": c.get("predictions"), "infortuni": c.get("injuries")})
    out["copertura"] = sorted(cov, key=lambda v: (v["paese"], v["id"]))
    # 2. partite di ieri: risultati, arbitro, stagione accessibile col piano gratuito?
    ieri = str(datetime.date.today() - datetime.timedelta(days=1))
    F = api("fixtures", date=ieri)
    out["errori_fixtures_ieri"] = F.get("errors")
    fx = F.get("response", [])
    out["partite_ieri"] = len(fx)
    out["partite_ieri_esempi"] = [{"lega": f["league"]["name"], "paese": f["league"]["country"], "id_lega": f["league"]["id"], "casa": f["teams"]["home"]["name"],
                                   "trasferta": f["teams"]["away"]["name"], "gol": [f["goals"]["home"], f["goals"]["away"]], "stato": f["fixture"]["status"]["short"],
                                   "arbitro": f["fixture"].get("referee")} for f in fx if f["league"]["country"] in COUNTRIES][:60]
    # 3. statistiche di 3 partite di ieri (campionati minori)
    out["statistiche_ieri"] = []
    for f in [f for f in fx if f["fixture"]["status"]["short"] == "FT" and f["league"]["country"] in ("England", "Spain", "Scotland", "Argentina")][:3]:
        S = api("fixtures/statistics", fixture=f["fixture"]["id"])
        out["statistiche_ieri"].append({"partita": f["teams"]["home"]["name"] + " - " + f["teams"]["away"]["name"], "lega": f["league"]["name"],
                                        "errori": S.get("errors"), "stat": {t["team"]["name"]: {s["type"]: s["value"] for s in t["statistics"]} for t in S.get("response", [])}})
    # 4. confronto con football-data: Serie A e Premier 2024/25 (stagione inclusa nel piano gratuito?), 12 partite ciascuna
    def fd_rows(name):
        try:
            rd = list(csv.DictReader(io.StringIO(open(os.path.join("data", name), encoding="utf-8").read())))
            return rd
        except Exception as e:
            return []
    out["confronto"] = []
    for lid, fdname in ((135, "I1_2425.csv"), (39, "E0_2425.csv")):
        rows = fd_rows(fdname)
        A = api("fixtures", league=lid, season=2024)
        out["confronto"].append({"lega": lid, "errori": A.get("errors"), "partite_api": len(A.get("response", [])), "righe_fd": len(rows)})
        apif = [f for f in A.get("response", []) if f["fixture"]["status"]["short"] == "FT"]
        for f in apif[100:112]:
            S = api("fixtures/statistics", fixture=f["fixture"]["id"])
            st = {t["team"]["id"]: {s["type"]: s["value"] for s in t["statistics"]} for t in S.get("response", [])}
            H, Aw = st.get(f["teams"]["home"]["id"], {}), st.get(f["teams"]["away"]["id"], {})
            d = datetime.datetime.fromisoformat(f["fixture"]["date"][:10]).strftime("%d/%m/%Y")
            cand = [r for r in rows if r.get("Date") == d and r.get("FTHG") == str(f["goals"]["home"]) and r.get("FTAG") == str(f["goals"]["away"])]
            out["confronto"].append({"data": d, "api": f["teams"]["home"]["name"] + " - " + f["teams"]["away"]["name"], "gol": [f["goals"]["home"], f["goals"]["away"]],
                                     "arbitro": f["fixture"].get("referee"),
                                     "api_stat": {k: [H.get(k), Aw.get(k)] for k in ("Corner Kicks", "Total Shots", "Shots on Goal", "Fouls", "expected_goals")},
                                     "fd_candidati": [{"partita": r["HomeTeam"] + " - " + r["AwayTeam"], "HC": [r.get("HC"), r.get("AC")], "HS": [r.get("HS"), r.get("AS")],
                                                       "HST": [r.get("HST"), r.get("AST")], "HF": [r.get("HF"), r.get("AF")]} for r in cand]})
    # 5. quote: bookmaker, mercati, partite di oggi
    B = api("odds/bookmakers"); out["bookmakers"] = B.get("response"); out["errori_bookmakers"] = B.get("errors")
    M = api("odds/bets"); out["mercati"] = [m["name"] for m in M.get("response", [])]
    O = api("odds", date=str(datetime.date.today()))
    out["errori_quote_oggi"] = O.get("errors"); out["quote_oggi_paging"] = O.get("paging"); r = O.get("response", [])
    out["quote_oggi_partite_pagina1"] = len(r)
    if r:
        e = r[0]; out["quote_esempio"] = {"lega": e["league"]["name"], "fixture": e["fixture"]["id"], "aggiornate": e.get("update"),
                                          "bookmakers": [{"nome": b["name"], "mercati": [x["name"] for x in b["bets"]]} for b in e["bookmakers"]]}
    out["richieste_usate"] = used
os.makedirs("probe", exist_ok=True)
json.dump(out, open("probe/apifootball.json", "w"), indent=1, ensure_ascii=False)
print("richieste usate", used)
