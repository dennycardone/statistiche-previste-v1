"""Eventi delle partite con il minuto (28/10/2026, priorità 1 di Denny): cartellini e gol per tempo dal 2022, per i test del 1° tempo.
Una richiesta fixtures?ids=a-b-… restituisce fino a 20 partite con gli eventi (tipo, minuto, squadra) e il risultato del 1° tempo:
~4.000 richieste per tutto lo storico dei nostri campionati invece di una a partita. Dalle partite più recenti; solo le richieste che
avanzano dopo la riserva dell'app (tools/af_budget.py). Riprende da eventi/*.json (ramo eventi).
Formato: eventi/<campionato>.json = {id: [data, casa, ospite, gol 1°T casa, gol 1°T ospite, cartellini, gol]}
  cartellini: [[minuto, recupero, lato (0 casa, 1 ospite), "G" giallo | "R" rosso | "GR" secondo giallo], …]
  gol:        [[minuto, recupero, lato, "N" normale | "R" rigore | "A" autogol], …]   (lato = squadra a cui va il gol)"""
import json, os, re, sys, time, urllib.request, urllib.parse, traceback
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.excepthook = lambda t, v, tb: print("::error title=Eventi::" + " | ".join(traceback.format_exception(t, v, tb)).replace("\n", " ")[-1500:])
import af_budget
KEY = os.environ["APIFOOTBALL_KEY"].strip(); used = 0
def get(p, **q):
    global used; used += 1
    req = urllib.request.Request("https://v3.football.api-sports.io/" + p + "?" + urllib.parse.urlencode(q), headers={"x-apisports-key": KEY})
    for t in range(3):
        try:
            with urllib.request.urlopen(req, timeout=90) as r: d = json.loads(r.read().decode())
            time.sleep(0.2); return d
        except Exception as e: print("retry", e); time.sleep(5)
    return {"errors": ["rete"]}
rq = af_budget.requests_of(get("status")); budget = af_budget.test_budget(rq) - 5
print(f"::notice title=Eventi::richieste {rq.get('current')} su {rq.get('limit_day')}, disponibili {max(0, budget)}" if rq else "::notice title=Eventi::stato API non disponibile")
src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "update_data.py")).read()
rm = re.search(r"REMOVED = \{(.*?)\}", src); REM = set(re.findall(r'"(\w+)"', rm.group(1))) if rm else set()
AP = json.load(open("data/apif.json"))["partite"]
os.makedirs("eventi", exist_ok=True)
D = {fn[:-5]: json.load(open("eventi/" + fn)) for fn in os.listdir("eventi") if fn.endswith(".json")}
done = {fid for L in D.values() for fid in L}
todo = sorted(((v[0], fid, v[1]) for fid, v in AP.items() if v[9] in ("FT", "AET", "PEN") and v[0] >= "2022-07-01"
               and v[1] not in REM and v[1] not in ("UCL", "UEL", "UECL") and fid not in done), reverse=True)
print("da scaricare", len(todo), "partite")
n_new = 0
for i in range(0, len(todo), 20):
    if budget < 1: break
    chunk = todo[i:i + 20]; lgof = {fid: lg for _, fid, lg in chunk}
    R = get("fixtures", ids="-".join(fid for _, fid, _ in chunk)); budget -= 1
    for f in R.get("response") or []:
        fid = str(f["fixture"]["id"]); lg = lgof.get(fid)
        if not lg: continue
        hid = f["teams"]["home"]["id"]; ht = (f.get("score") or {}).get("halftime") or {}
        cards, goals = [], []
        for e in f.get("events") or []:
            tm = e.get("time") or {}; mi, ex = tm.get("elapsed"), tm.get("extra")
            side = 0 if (e.get("team") or {}).get("id") == hid else 1; det = e.get("detail") or ""
            if e.get("type") == "Card":
                k = "GR" if "Second" in det else "R" if "Red" in det else "G"
                cards.append([mi, ex, side, k])
            elif e.get("type") == "Goal" and "Missed" not in det:
                goals.append([mi, ex, side, "A" if "Own" in det else "R" if "Penalty" in det else "N"])
        D.setdefault(lg, {})[fid] = [f["fixture"]["date"][:16], f["teams"]["home"]["name"], f["teams"]["away"]["name"], ht.get("home"), ht.get("away"), cards, goals]
        n_new += 1
for lg, L in D.items(): json.dump(L, open(f"eventi/{lg}.json", "w"), separators=(",", ":"), ensure_ascii=False)
tot = sum(len(L) for L in D.values())
print(f"::notice title=Eventi::nuove {n_new} partite con {used - 1} richieste · archivio {tot} partite · mancano {max(0, len(todo) - n_new)}")
