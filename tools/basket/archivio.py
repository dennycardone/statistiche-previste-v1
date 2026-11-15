"""Basket · archivio (15/11/2026, Denny: "inserisci basketball, stesse sezioni del calcio").
API-Basketball (piano Pro, limite separato dal calcio). Per ogni campionato e stagione: partite (punteggi per quarto), statistiche di squadra
e dei giocatori per partita. Ramo privato "basket" (un file per campionato-stagione). Le partite già complete non si riscaricano.
Riserva: le prove e l'archivio non scendono sotto RISERVA richieste rimaste nel giorno (servono all'app per partite e quote).

Uso: python tools/basket/archivio.py CARTELLA [MAX_RICHIESTE]
Formato file <COD>_<stagione>.json:
  {"lega": COD, "id": id_api, "stagione": "...", "agg": "...", "squadre": {id: nome}, "nomi": {id_giocatore: nome},
   "partite": {id: [data_utc, stato, id_casa, id_ospite, [q1,q2,q3,q4,ot,tot] casa, [...] ospite, settimana/fase]},
   "stat": {id: {"h": S, "a": S}}  S = [fg, fga, p3, p3a, ft, fta, reb, oreb, dreb, ast, stl, blk, tov, pf]
   "gioc": {id: [[id_giocatore, lato 0/1, titolare 1/0, minuti, punti, fg, fga, p3, p3a, ft, fta, reb, ast], ...]},
   "fatte": [id partite con statistiche già scaricate (anche se vuote)]}"""
import json, os, sys, time, datetime, urllib.request, urllib.parse
DIR = sys.argv[1] if len(sys.argv) > 1 else "basket"
MAXR = int(sys.argv[2]) if len(sys.argv) > 2 else 6000
KEY = os.environ["APIBASKET_KEY"].strip() if os.environ.get("APIBASKET_KEY") else os.environ["APIFOOTBALL_KEY"].strip()
BASE = "https://v1.basketball.api-sports.io/"
RISERVA = 800
LEGHE = {"NBA": 12, "EL": 120, "EC": 194, "ITA": 52, "ACB": 117, "BBL": 40, "LNB": 2}   # Eurolega/Eurocup: stagione anno solare
DA = 2019   # prime stagioni archiviate (2019-2020 / 2019)
used, left = 0, None
os.makedirs(DIR, exist_ok=True)

def get(p, **q):
    global used, left
    for t in range(4):
        try:
            req = urllib.request.Request(BASE + p + ("?" + urllib.parse.urlencode(q) if q else ""), headers={"x-apisports-key": KEY})
            with urllib.request.urlopen(req, timeout=60) as r:
                used += 1
                rem = r.headers.get("x-ratelimit-requests-remaining")
                if rem is not None: left = int(rem)
                d = json.loads(r.read().decode())
            if d.get("errors") and "rateLimit" in json.dumps(d["errors"]): time.sleep(20); continue
            time.sleep(0.15)   # resta sotto 300 al minuto e lascia spazio alle quote
            return d
        except Exception as e:
            if t == 3: raise
            time.sleep(5 * (t + 1))
    return {}
def can(): return used < MAXR and (left is None or left > RISERVA)
def num(x):
    try: return None if x is None or x == "" else float(x)
    except Exception: return None
def mins(s):
    if s is None: return None
    if isinstance(s, (int, float)): return float(s)
    try:
        a = str(s).split(":"); return round(int(a[0]) + (int(a[1]) / 60 if len(a) > 1 else 0), 2)
    except Exception: return None
def sc(s):
    s = s or {}
    return [s.get("quarter_1"), s.get("quarter_2"), s.get("quarter_3"), s.get("quarter_4"), s.get("over_time"), s.get("total")]

st = get("status").get("response") or {}
req_ = st.get("requests") or {}
left = (req_.get("limit_day") or 0) - (req_.get("current") or 0)
print(f"::notice title=Basket · budget::piano {(st.get('subscription') or {}).get('plan')} · rimaste oggi {left} · tetto di questo giro {MAXR} · riserva {RISERVA}")
lg_info = {l["id"]: l for l in (get("leagues").get("response") or []) if l["id"] in LEGHE.values()}
summary, now = [], datetime.datetime.now(datetime.timezone.utc)
for cod, lid in LEGHE.items():
    seasons = sorted({str(s.get("season")) for s in (lg_info.get(lid, {}).get("seasons") or [])})
    seasons = [s for s in seasons if int(s[:4]) >= DA]
    for season in seasons:
        if not can(): break
        fn = os.path.join(DIR, f"{cod}_{season}.json")
        D = json.load(open(fn)) if os.path.exists(fn) else {"lega": cod, "id": lid, "stagione": season, "squadre": {}, "nomi": {}, "partite": {}, "stat": {}, "gioc": {}, "fatte": []}
        corrente = season == seasons[-1]
        if corrente or not D["partite"]:
            G = get("games", league=lid, season=season).get("response") or []
            for g in G:
                h, a = g["teams"]["home"], g["teams"]["away"]
                D["squadre"][str(h["id"])] = h["name"]; D["squadre"][str(a["id"])] = a["name"]
                D["partite"][str(g["id"])] = [g.get("date", "")[:16], (g.get("status") or {}).get("short"), h["id"], a["id"],
                                             sc((g.get("scores") or {}).get("home")), sc((g.get("scores") or {}).get("away")), g.get("week") or g.get("stage")]
        fatte = set(D["fatte"])
        todo = [k for k, v in D["partite"].items() if v[1] in ("FT", "AOT") and k not in fatte]
        n0 = len(todo)
        for i in range(0, len(todo), 20):
            if not can(): break
            chunk = todo[i:i + 20]; ids = "-".join(chunk)
            T = get("games/statistics/teams", ids=ids).get("response") or []
            for t in T:
                gid = str((t.get("game") or {}).get("id")); tid = (t.get("team") or {}).get("id")
                v = D["partite"].get(gid)
                if not v: continue
                side = "h" if tid == v[2] else "a" if tid == v[3] else None
                if not side: continue
                fg, p3, ft, rb = t.get("field_goals") or {}, t.get("threepoint_goals") or {}, t.get("freethrows_goals") or {}, t.get("rebounds") or {}
                D["stat"].setdefault(gid, {})[side] = [num(fg.get("total")), num(fg.get("attempts")), num(p3.get("total")), num(p3.get("attempts")),
                    num(ft.get("total")), num(ft.get("attempts")), num(rb.get("total")), num(rb.get("offence")), num(rb.get("defense")),
                    num(t.get("assists")), num(t.get("steals")), num(t.get("blocks")), num(t.get("turnovers")), num(t.get("personal_fouls"))]
            if not can(): break
            P = get("games/statistics/players", ids=ids).get("response") or []
            for r in P:
                gid = str((r.get("game") or {}).get("id")); tid = (r.get("team") or {}).get("id"); pl = r.get("player") or {}
                v = D["partite"].get(gid)
                if not v or not pl.get("id"): continue
                side = 0 if tid == v[2] else 1 if tid == v[3] else None
                if side is None: continue
                if pl.get("name"): D["nomi"][str(pl["id"])] = pl["name"]
                fg, p3, ft, rb = r.get("field_goals") or {}, r.get("threepoint_goals") or {}, r.get("freethrows_goals") or {}, r.get("rebounds") or {}
                D["gioc"].setdefault(gid, []).append([pl["id"], side, 1 if r.get("type") == "starters" else 0, mins(r.get("minutes")), num(r.get("points")),
                    num(fg.get("total")), num(fg.get("attempts")), num(p3.get("total")), num(p3.get("attempts")), num(ft.get("total")), num(ft.get("attempts")),
                    num(rb.get("total")), num(r.get("assists"))])
            fatte.update(chunk)
        D["fatte"] = sorted(fatte); D["agg"] = now.strftime("%Y-%m-%d %H:%M")
        json.dump(D, open(fn, "w"), ensure_ascii=False, separators=(",", ":"))
        finite = {k for k, v in D["partite"].items() if v[1] in ("FT", "AOT")}
        summary.append(f"{cod} {season}: {len(D['partite'])} partite, finite {len(finite)}, con statistiche {len(D['stat'])}, mancanti {len(finite - fatte)}")
print("::notice title=Basket · archivio::" + f"richieste {used} · rimaste {left} · " + " | ".join(summary)[:3500])
