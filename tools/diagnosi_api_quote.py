"""Diagnosi: quali mercati 1xBet passa oggi API-Football (27/10/2026). Stampa SOLO i nomi dei mercati e i conteggi, mai le quote.
Richieste: 1 status + 1 elenco dei mercati (odds/bets) + 1 calendario + al massimo 4 quote di partita, solo se avanzano dalla riserva
dell'app (tools/af_budget.py)."""
import json, os, sys, datetime, urllib.request, urllib.parse, traceback, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.excepthook = lambda t, v, tb: print("::error title=Diagnosi API quote::" + " | ".join(traceback.format_exception(t, v, tb)).replace("\n", " ")[-1500:])
import af_budget
KEY = os.environ["APIFOOTBALL_KEY"].strip()
def af(path, **q):
    req = urllib.request.Request("https://v3.football.api-sports.io/" + path + ("?" + urllib.parse.urlencode(q) if q else ""), headers={"x-apisports-key": KEY})
    with urllib.request.urlopen(req, timeout=60) as r: return json.loads(r.read().decode())
note = lambda t, m: print(f"::notice title={t}::" + m.replace("%", "%25").replace("\n", " "))
st = af_budget.requests_of(af("status")); free = af_budget.test_budget(st)
note("Diagnosi API · richieste", f"usate {st.get('current')} su {st.get('limit_day')} · disponibili per le prove {free}")
if free < 8: note("Diagnosi API", "riserva dell'app non sufficiente: niente richieste di prova"); sys.exit(0)
B = af("odds/bets").get("response", [])
note("Diagnosi API · mercati con falli/fuorigioco/gialli/tiri nel catalogo", ", ".join(f"{b['id']}:{b['name']}" for b in B if any(w in (b.get("name") or "").lower() for w in ("foul", "offside", "yellow", "shot"))))
LG = {135: "I1", 39: "E0", 140: "SP1", 61: "F1", 78: "D1", 235: "RUS"}
today = datetime.date.today()
picked = []
for k in (0, 1):
    F = af("fixtures", date=str(today + datetime.timedelta(days=k)), timezone="Europe/Rome").get("response", [])
    picked += [f for f in F if f["league"]["id"] in LG and f["fixture"]["status"]["short"] == "NS"]
    if len(picked) >= 4: break
for f in picked[:4]:
    R = af("odds", fixture=f["fixture"]["id"]).get("response", [])
    nm = f"{LG[f['league']['id']]} {f['teams']['home']['name']}–{f['teams']['away']['name']} ({f['fixture']['date'][:16]})"
    if not R: note("Diagnosi API · " + nm, "nessuna quota"); continue
    e = R[0]; books = {b["name"]: [bt["name"] for bt in b.get("bets", [])] for b in e.get("bookmakers", [])}
    xb = books.get("1xBet", [])
    stat = [n for n in xb if n and any(w in n.lower() for w in ("foul", "offside", "yellow", "shot", "corner", "card"))]
    others = sorted({b for b, L in books.items() if any("foul" in (n or "").lower() for n in L)})
    note("Diagnosi API · " + nm, f"aggiornate {e.get('update', '')[:16]} · bookmaker {len(books)} · mercati 1xBet {len(xb)} · statistiche 1xBet: {', '.join(stat) or 'nessuno'} · "
         f"altri bookmaker con falli: {', '.join(others) or 'nessuno'}")
