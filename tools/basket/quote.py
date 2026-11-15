"""Basket · archivio quote (15/11/2026). Partite di oggi e domani dei 7 campionati: quote di tutti i book (API-Basketball) sui mercati principali.
Per ogni partita due letture: "o" = la prima vista (apertura), "c" = l'ultima prima dell'inizio (chiusura). Archivio PRIVATO: il file sta
cifrato sul ramo basket-quote (il workflow lo decifra, aggiorna e ricifra); nel sito si pubblicheranno solo linee del giorno e numeri aggregati.
Uso: python tools/basket/quote.py ARCHIVIO.json [MAX_RICHIESTE]
Formato: {"partite": {id: {"lg", "d" (inizio UTC), "h", "a", "o": [ora, Q], "c": [ora, Q]}}}  Q = {mercato: {valore: {book: quota}}}"""
import json, os, sys, re, datetime, urllib.request, urllib.parse
FN = sys.argv[1] if len(sys.argv) > 1 else "quote_basket.json"
MAXR = int(sys.argv[2]) if len(sys.argv) > 2 else 200
KEY = os.environ["APIFOOTBALL_KEY"].strip(); BASE = "https://v1.basketball.api-sports.io/"
LEGHE = {12: "NBA", 120: "EL", 194: "EC", 52: "ITA", 117: "ACB", 40: "BBL", 2: "LNB"}
KEEP = re.compile(r"^(Home/Away|3Way Result|Asian Handicap|Over/Under|Asian Handicap First Half|Over/Under 1st Half|1st Half 3Way Result|Home/Away \(1st Half\))$|Team Total (Goals|Points) ?\((Including OT|1st Half)\)", re.I)
used = 0
def get(p, **q):
    global used; used += 1
    req = urllib.request.Request(BASE + p + "?" + urllib.parse.urlencode(q), headers={"x-apisports-key": KEY})
    with urllib.request.urlopen(req, timeout=60) as r: return json.loads(r.read().decode())
A = json.load(open(FN)) if os.path.exists(FN) else {"partite": {}}
now = datetime.datetime.now(datetime.timezone.utc); nows = now.strftime("%Y-%m-%dT%H:%M")
games = []
for k in (0, 1):
    d = (now + datetime.timedelta(days=k)).strftime("%Y-%m-%d")
    for g in get("games", date=d).get("response") or []:
        lid = (g.get("league") or {}).get("id")
        if lid in LEGHE and (g.get("status") or {}).get("short") == "NS": games.append((g, LEGHE[lid]))
n_new = n_upd = 0
for g, cod in games:
    if used >= MAXR: break
    gid = str(g["id"]); start = (g.get("date") or "")[:16]
    if start and start <= nows: continue
    od = get("odds", game=gid).get("response") or []
    Q = {}
    for o in od:
        for bk in o.get("bookmakers") or []:
            for b in bk.get("bets") or []:
                nm = b.get("name") or ""
                if not KEEP.search(nm): continue
                for v in b.get("values") or []:
                    try: q = float(v.get("odd"))
                    except Exception: continue
                    Q.setdefault(nm, {}).setdefault(str(v.get("value")), {})[bk["name"]] = q
    if not Q: continue
    e = A["partite"].setdefault(gid, {"lg": cod, "d": start, "h": g["teams"]["home"]["name"], "a": g["teams"]["away"]["name"]})
    e["d"] = start
    if "o" not in e: e["o"] = [nows, Q]; n_new += 1
    e["c"] = [nows, Q]; n_upd += 1
# pulizia: oltre 400 giorni via
lim = (now - datetime.timedelta(days=400)).strftime("%Y-%m-%d")
A["partite"] = {k: v for k, v in A["partite"].items() if v.get("d", "9") >= lim}
A["agg"] = nows
json.dump(A, open(FN, "w"), separators=(",", ":"))
bk = sorted({b for e in A["partite"].values() if e.get("c") for m in e["c"][1].values() for v in m.values() for b in v})
print(f"::notice title=Basket · quote::{len(games)} partite in programma oggi e domani · nuove {n_new} · aggiornate {n_upd} · archivio {len(A['partite'])} partite · book {', '.join(bk)} · richieste {used}")
