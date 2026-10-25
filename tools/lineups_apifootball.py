"""Formazioni, statistiche dei giocatori e infortuni da API-Football, per il backtest (gol attesi e cartellini).
Per ogni partita giocata: titolari delle due squadre e, per ogni giocatore sceso in campo, minuti, gol, assist, gialli, rossi,
falli fatti e subiti, tiri e tiri in porta (fixtures?ids=, 20 partite per richiesta). Infortuni e squalifiche: injuries?league&season.
Partite: ramo storico (2022-2025) + data/apif.json (stagione in corso). Riprende da formazioni/*.json; usa solo le richieste che avanzano
dopo la riserva dell'app (af_budget).
25/10/2026 (Prevista 2.0, fase 1): per ogni giocatore anche fuorigioco, contrasti, intercetti, tiri respinti, duelli (totali e vinti),
dribbling (tentati e riusciti), passaggi (totali e chiave), voto, ruolo e se è entrato dalla panchina (colonne 12-24). Le partite già
scaricate col formato vecchio si riscaricano (elenco "v2")."""
import json, os, time, urllib.request, urllib.parse, glob, sys, traceback
def _hook(t, v, tb):   # 25/10/2026: l'errore compare tra le annotazioni del giro (i log di Actions non sono leggibili da qui)
    print("::error title=Formazioni::" + " | ".join(traceback.format_exception(t, v, tb)).replace("\n", " ")[-1500:]); sys.__excepthook__(t, v, tb)
sys.excepthook = _hook
KEY = os.environ["APIFOOTBALL_KEY"].strip()
AFL = {"I1": 135, "I2": 136, "E0": 39, "E1": 40, "E2": 41, "E3": 42, "EC": 43, "SP1": 140, "SP2": 141, "F1": 61, "F2": 62, "D1": 78, "D2": 79,
       "N1": 88, "P1": 94, "SC0": 179, "SC1": 180, "SC2": 183, "SC3": 184, "B1": 144, "T1": 203, "G1": 197, "ARG": 128, "AUT": 218, "BRA": 71,
       "CHN": 169, "DNK": 119, "FIN": 244, "IRL": 357, "JPN": 98, "MEX": 262, "NOR": 103, "POL": 106, "ROU": 283, "RUS": 235, "SWE": 113, "SWZ": 207, "USA": 253}
os.makedirs("formazioni", exist_ok=True)
used = 0
def get(p, **q):
    global used
    used += 1
    req = urllib.request.Request("https://v3.football.api-sports.io/" + p + ("?" + urllib.parse.urlencode(q) if q else ""), headers={"x-apisports-key": KEY})
    for t in range(3):
        try:
            with urllib.request.urlopen(req, timeout=60) as r: d = json.loads(r.read().decode())
            time.sleep(0.2); return d
        except Exception as e:
            print("retry", p, e); time.sleep(5)
    return {"errors": ["rete"]}
import sys; sys.path.insert(0, os.path.dirname(__file__)); import af_budget
rq = af_budget.requests_of(get("status"))
budget = af_budget.test_budget(rq)   # solo le richieste che avanzano dopo la riserva dell'app
print("richieste oggi", rq, "disponibili per lo scarico", budget)
# elenco partite per campionato e stagione
todo_sets = {}
for fn in glob.glob("storico/*.json"):
    D = json.load(open(fn))
    if not isinstance(D, dict) or "lega" not in D: continue   # es. referees.json (arbitri), aggiunto al ramo storico dopo il 5/10
    todo_sets[(D["lega"], D["stagione"])] = [str(i) for i in D.get("ids", [])]
try:
    AP = json.load(open("data/apif.json"))["partite"]
    cur = {}
    for fid, v in AP.items():
        try:
            if len(v) > 9 and v[9] in ("FT", "AET", "PEN") and v[0] >= "2026-01-01": cur.setdefault(v[1], []).append(fid)
        except Exception: pass
    for lg, ids in cur.items():
        known = {i for (l, s), L in todo_sets.items() if l == lg for i in L}
        todo_sets[(lg, 2026)] = [i for i in ids if i not in known]
    print("::notice title=Formazioni::stagione in corso da apif.json: " + str(sum(len(v) for v in todo_sets.values() if v)) + " partite in elenco, nuove " + str(sum(len(todo_sets.get((lg, 2026), [])) for lg in cur)))
except Exception as e: print("::warning title=Formazioni::apif.json non disponibile: " + str(e))
def num(x):
    try: return int(x) if x is not None else 0
    except Exception: return 0
order = sorted(todo_sets, key=lambda k: ({2025: 0, 2024: 1, 2023: 2, 2026: 3, 2022: 4}.get(k[1], 5), k[0]))
for lg, s in order:
    fn = f"formazioni/{lg}_{s}.json"
    D = json.load(open(fn)) if os.path.exists(fn) else {"lega": lg, "stagione": s, "partite": {}, "infortuni": None}
    if s == 2026: D.setdefault("ids", []); D["ids"] = sorted(set(D["ids"]) | set(todo_sets[(lg, s)]))
    else: D["ids"] = todo_sets[(lg, s)]
    if D.get("infortuni") is None and budget > 5 and lg in AFL:
        inj, page = [], 1
        while True:
            R = get("injuries", league=AFL[lg], season=s if s != 2026 else (2026 if lg in ("ARG", "BRA", "CHN", "FIN", "IRL", "JPN", "NOR", "SWE", "USA") else 2025)); budget -= 1
            for x in R.get("response", []):
                inj.append([x["fixture"]["id"], x["team"]["id"], x["player"]["id"], x["player"].get("type"), x["player"].get("reason")])
            break   # l'endpoint injuries non è paginato
        D["infortuni"] = inj
    v2 = set(D.get("v2", []))
    todo = [i for i in D["ids"] if i not in D["partite"] or i not in v2]
    for k in range(0, len(todo), 20):
        if budget < 5: break
        R = get("fixtures", ids="-".join(todo[k:k + 20])); budget -= 1
        for f in R.get("response", []):
            hid, aid = f["teams"]["home"]["id"], f["teams"]["away"]["id"]
            xi = {l["team"]["id"]: [p["player"]["id"] for p in l.get("startXI", []) if p.get("player")] for l in f.get("lineups", [])}
            P = []
            for t in f.get("players", []):
                side = 0 if t["team"]["id"] == hid else 1
                for p in t.get("players", []):
                    st = (p.get("statistics") or [{}])[0]; g = st.get("games", {}) or {}
                    if not g.get("minutes"): continue
                    P.append([p["player"]["id"], side, num(g.get("minutes")), num((st.get("goals") or {}).get("total")), num((st.get("goals") or {}).get("assists")),
                              num((st.get("cards") or {}).get("yellow")), num((st.get("cards") or {}).get("red")), num((st.get("fouls") or {}).get("committed")),
                              num((st.get("fouls") or {}).get("drawn")), num((st.get("shots") or {}).get("total")), num((st.get("shots") or {}).get("on")), g.get("position") or "",
                              num(st.get("offsides")), num((st.get("tackles") or {}).get("total")), num((st.get("tackles") or {}).get("interceptions")),
                              num((st.get("tackles") or {}).get("blocks")), num((st.get("duels") or {}).get("total")), num((st.get("duels") or {}).get("won")),
                              num((st.get("dribbles") or {}).get("attempts")), num((st.get("dribbles") or {}).get("success")), num((st.get("passes") or {}).get("total")),
                              num((st.get("passes") or {}).get("key")), g.get("rating"), 1 if g.get("substitute") else 0, g.get("number")])
            D["partite"][str(f["fixture"]["id"])] = [f["fixture"]["date"][:16], hid, aid, f["teams"]["home"]["name"], f["teams"]["away"]["name"],
                                                     f["goals"]["home"], f["goals"]["away"], xi.get(hid, []), xi.get(aid, []), P]
            v2.add(str(f["fixture"]["id"]))   # scaricata col formato nuovo (anche se API-Football non ha i giocatori)
        D["v2"] = sorted(v2)
    json.dump(D, open(fn, "w"), ensure_ascii=False, separators=(",", ":"))
    print(lg, s, len(D["partite"]), "/", len(D["ids"]), "infortuni", len(D["infortuni"] or []), "budget", budget)
    if budget < 5: break
print("richieste usate", used, "rimaste", budget)
