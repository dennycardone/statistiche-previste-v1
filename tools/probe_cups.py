"""Prova: coppe europee (Champions 2, Europa League 3, Conference League 848) e campionati nazionali delle squadre che vi giocano.
Per ogni paese presente nelle coppe (stagioni 2024, 2025, 2026) e non già nell'app: campionato di prima divisione su API-Football,
copertura dichiarata (statistiche partita, quote) e verifica reale su una partita della stagione scorsa (corner, falli, tiri, cartellini).
Scrive probe/apifootball.json. Non modifica i dati dell'app."""
import json, os, time, urllib.request, urllib.parse, datetime, collections
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
    req = urllib.request.Request(BASE + path + ("?" + urllib.parse.urlencode(q) if q else ""), headers={"x-apisports-key": KEY})
    with urllib.request.urlopen(req, timeout=60) as r: d = json.loads(r.read().decode())
    time.sleep(0.4)
    return d
OURS = {"Italy", "England", "Spain", "France", "Germany", "Netherlands", "Portugal", "Scotland", "Belgium", "Turkey", "Greece", "Argentina",
        "Austria", "Brazil", "China", "Denmark", "Japan", "Mexico", "Norway", "Russia", "Sweden", "USA", "Finland", "Ireland", "Poland",
        "Romania", "Switzerland"}
CUPS = {2: "Champions League", 3: "Europa League", 848: "Conference League"}
out = {"quando": datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")}
os.makedirs("probe", exist_ok=True)
try:
    out["status"] = api("status").get("response")
    # 1. squadre delle coppe per stagione e loro paese
    teams = collections.defaultdict(lambda: collections.defaultdict(set))   # paese -> coppa -> squadre
    cupcov = {}
    for lid, nm in CUPS.items():
        L = api("leagues", id=lid).get("response", [])
        cupcov[nm] = [{"stagione": s["year"], "statistiche": s.get("coverage", {}).get("fixtures", {}).get("statistics_fixtures"),
                       "quote": s.get("coverage", {}).get("odds")} for s in (L[0]["seasons"] if L else []) if s["year"] >= 2022]
        for season in (2024, 2025, 2026):
            for t in api("teams", league=lid, season=season).get("response", []):
                teams[t["team"].get("country") or "?"][f"{nm} {season}"].add(t["team"]["name"])
    out["coppe_copertura"] = cupcov
    # 2. campionati di prima divisione dei paesi nuovi
    allL = api("leagues", type="league").get("response", [])
    by_c = collections.defaultdict(list)
    for x in allL: by_c[x["country"]["name"]].append(x)
    paesi = []
    for c, cups in sorted(teams.items(), key=lambda kv: -sum(len(v) for v in kv[1].values())):
        n_teams = len(set().union(*cups.values()))
        row = {"paese": c, "gia_nell_app": c in OURS, "squadre_nelle_coppe_2024_2026": n_teams,
               "presenze": {k: len(v) for k, v in sorted(cups.items())}}
        if c not in OURS and c != "?":
            cand = sorted(by_c.get(c, []), key=lambda x: x["league"]["id"])
            # prima divisione: il campionato del paese con più squadre delle coppe nella stagione 2025
            best = None
            for x in cand[:6]:
                s25 = [s for s in x["seasons"] if s["year"] in (2025, 2024)]
                if not s25: continue
                tl = api("teams", league=x["league"]["id"], season=s25[-1]["year"]).get("response", [])
                names = {t["team"]["name"] for t in tl}
                hit = len(names & set().union(*cups.values()))
                if best is None or hit > best[0]: best = (hit, x, s25[-1]["year"])
            if best and best[0] > 0:
                x, yr = best[1], best[2]
                cov = {s["year"]: {"statistiche": s.get("coverage", {}).get("fixtures", {}).get("statistics_fixtures"), "quote": s.get("coverage", {}).get("odds")}
                       for s in x["seasons"] if s["year"] >= 2022}
                row.update(campionato=x["league"]["name"], id=x["league"]["id"], copertura=cov)
                # verifica reale: statistiche di 3 partite giocate della stagione yr
                fx = [f for f in api("fixtures", league=x["league"]["id"], season=yr, status="FT").get("response", [])]
                row["partite_stagione_" + str(yr)] = len(fx)
                chk = []
                for f in fx[-3:]:
                    st = api("fixtures/statistics", fixture=f["fixture"]["id"]).get("response", [])
                    def val(team, k):
                        for s in team.get("statistics", []):
                            if s["type"] == k: return s["value"]
                    chk.append({"partita": f'{f["teams"]["home"]["name"]}-{f["teams"]["away"]["name"]} {f["fixture"]["date"][:10]}', "arbitro": f["fixture"].get("referee"),
                                "valori": [[val(t, k) for k in ("Corner Kicks", "Fouls", "Total Shots", "Shots on Goal", "Yellow Cards")] for t in st]})
                row["verifica"] = chk
        paesi.append(row)
    out["paesi"] = paesi
except Exception as e:
    out["errore"] = repr(e)
out["richieste"] = used
json.dump(out, open("probe/apifootball.json", "w"), ensure_ascii=False, indent=1)
print("richieste", used)
