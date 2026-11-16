"""Calcio · cambi di allenatore (16/11/2026, Denny: "voglio che mi venga segnalato quando c'è un cambio di allenatore, cambia il gioco
della squadra e le statistiche diventano meno attendibili").
16/11: le date di /coachs di API-Football non sono affidabili (Spalletti alla Juve "dal 1/9/2026", è arrivato il 30/10/2025; Thioune al
Werder "dal 1/10/2026", è arrivato a febbraio 2026). Si usa allora l'allenatore scritto nella formazione di ogni partita giocata
(fixtures?ids=, 20 partite per richiesta): allenatore attuale = quello dell'ultima partita; cambio = nelle partite degli ultimi 150 giorni
c'è un allenatore diverso prima della serie attuale. Data = prima partita col nuovo, partite = quante ne ha guidate (tutte le competizioni).
Partite: fixtures?league&season&from&to per campionato (stagione in corso da leagues?current=true). Id delle squadre dai loghi del sito
(nome dell'app → https://media.api-sports.io/football/teams/<id>.png). Solo le richieste che avanzano dopo la riserva dell'app (af_budget).
Uso: python tools/allenatori_apifootball.py LOGHI.json CARTELLA (CARTELLA/stato.json = formazioni lette, CARTELLA/allenatori.json = sito)"""
import json, os, re, sys, time, datetime, urllib.request, urllib.parse
sys.path.insert(0, os.path.dirname(__file__)); import af_budget
LOGHI, OUT = sys.argv[1], sys.argv[2]
KEY = os.environ["APIFOOTBALL_KEY"].strip()
LG = {"I1": 135, "I2": 136, "E0": 39, "E1": 40, "E2": 41, "E3": 42, "SP1": 140, "SP2": 141, "F1": 61, "F2": 62, "D1": 78, "D2": 79, "N1": 88,
      "P1": 94, "SC0": 179, "B1": 144, "T1": 203, "G1": 197, "ARG": 128, "AUT": 218, "BRA": 71, "DNK": 119, "IRL": 357, "JPN": 98, "MEX": 262,
      "NOR": 103, "RUS": 235, "SWE": 113, "SWZ": 207, "USA": 253, "CZE": 345, "UCL": 2, "UEL": 3}
os.makedirs(OUT, exist_ok=True); SP = os.path.join(OUT, "stato.json")
ST = json.load(open(SP)) if os.path.exists(SP) else {}
ST = {k: v for k, v in ST.items() if k in ("fx", "nolu")}   # 16/11: via lo stato della prima versione (/coachs)
ST.setdefault("fx", {}); ST.setdefault("nolu", {})   # fx: id partita → [data, id casa, id all. casa, nome, id trasferta, id all., nome]; nolu: senza formazione (si riprova per 3 giorni)
NOW = datetime.datetime.now(datetime.timezone.utc); D0 = (NOW - datetime.timedelta(days=150)).strftime("%Y-%m-%d"); TODAY = NOW.strftime("%Y-%m-%d")
used = 0
def get(p, **q):
    global used
    used += 1
    req = urllib.request.Request("https://v3.football.api-sports.io/" + p + ("?" + urllib.parse.urlencode(q) if q else ""), headers={"x-apisports-key": KEY})
    with urllib.request.urlopen(req, timeout=60) as r: d = json.loads(r.read().decode())
    time.sleep(0.25); return d
LOG = json.load(open(LOGHI)); TEAMS = {}   # id squadra → [(lega, nome dell'app)]
for lg, m in LOG.items():
    for nm, url in m.items():
        mm = re.search(r"/teams/(\d+)\.png", url or "")
        if mm: TEAMS.setdefault(int(mm.group(1)), []).append((lg, nm))
budget = min(800, af_budget.test_budget(af_budget.requests_of(get("status"))))
print("richieste usabili", budget)
if budget > 60:
    cur = {}
    for x in get("leagues", current="true").get("response", []):
        for s in x.get("seasons") or []:
            if s.get("current"): cur[x["league"]["id"]] = s["year"]
    todo = []
    for code, lid in LG.items():
        if code not in LOG or lid not in cur or used >= budget - 5: continue
        for f in get("fixtures", league=lid, season=cur[lid], **{"from": D0, "to": TODAY}).get("response", []):
            fid = str(f["fixture"]["id"])
            if f["fixture"]["status"]["short"] not in ("FT", "AET", "PEN") or fid in ST["fx"]: continue
            if fid in ST["nolu"] and ST["nolu"][fid] < (NOW - datetime.timedelta(days=3)).strftime("%Y-%m-%d"): continue
            todo.append(fid)
    todo = sorted(set(todo), key=int, reverse=True)   # prima le partite più recenti
    for i in range(0, len(todo), 20):
        if used >= budget: break
        for f in get("fixtures", ids="-".join(todo[i:i + 20])).get("response", []):
            fid = str(f["fixture"]["id"]); L = {str((x.get("team") or {}).get("id")): (x.get("coach") or {}) for x in f.get("lineups") or []}
            h, a = f["teams"]["home"]["id"], f["teams"]["away"]["id"]; ch, ca = L.get(str(h)) or {}, L.get(str(a)) or {}
            if ch.get("id") or ca.get("id"): ST["fx"][fid] = [f["fixture"]["date"][:10], h, ch.get("id"), ch.get("name"), a, ca.get("id"), ca.get("name")]; ST["nolu"].pop(fid, None)
            else: ST["nolu"].setdefault(fid, f["fixture"]["date"][:10])
ST["fx"] = {k: v for k, v in ST["fx"].items() if v[0] >= D0}; ST["nolu"] = {k: v for k, v in ST["nolu"].items() if v >= D0}
json.dump(ST, open(SP, "w"), ensure_ascii=False, separators=(",", ":"))
# allenatore per squadra: partite in ordine di data
BY = {}
for fid, v in ST["fx"].items():
    for tid, cid, nm in ((v[1], v[2], v[3]), (v[4], v[5], v[6])):
        if cid: BY.setdefault(tid, []).append((v[0], cid, nm))
import unicodedata
TR = str.maketrans({"ß": "ss", "ø": "o", "Ø": "o", "æ": "ae", "Æ": "ae", "ł": "l", "Ł": "l", "đ": "d", "ı": "i"})
PART = {"de", "da", "do", "dos", "das", "del", "van", "von", "der", "den", "la", "le", "di", "el", "jr"}
def toks(n): return [t for t in re.sub(r"[^a-z ]", " ", unicodedata.normalize("NFKD", (n or "").translate(TR)).encode("ascii", "ignore").decode().lower()).split() if len(t) >= 3 and t not in PART]
def lev1(a, b):   # distanza di modifica al massimo 1 ("Aranbarri" / "Arambarri")
    if abs(len(a) - len(b)) > 1: return False
    i = 0
    while i < min(len(a), len(b)) and a[i] == b[i]: i += 1
    return a[i + 1:] == b[i + 1:] or a[i + 1:] == b[i:] or a[i:] == b[i + 1:]
def same(a, b):   # 16/11: API-Football ha lo stesso allenatore con id e grafie diverse ("M. Carrick" / "Michael Carrick", "Paiva Renato" / "Renato Paiva")
    if a[1] == b[1]: return True
    ta, tb = toks(a[2]), toks(b[2])
    if not ta or not tb: return False
    if len(set(ta) & set(tb)) >= 2: return True
    for x, y in ((ta[-1], tb), (tb[-1], ta)):   # il cognome (ultima parola) di uno dei due compare nell'altro
        if any(x == t or (len(x) >= 5 and len(t) >= 5 and lev1(x, t)) for t in y): return True
    return False
PUB, n_ch = {}, 0
for tid, L in BY.items():
    L.sort(); j = len(L) - 1
    while j > 0 and same(L[j - 1], L[-1]): j -= 1
    if j == 0: continue   # sempre lo stesso allenatore nella finestra
    n_ch += 1; e = {"c": L[-1][2], "da": L[j][0], "n": len(L) - j, "prev": L[j - 1][2]}
    for lg, nm in TEAMS.get(tid, []): PUB.setdefault(lg, {})[nm] = e
json.dump({"agg": NOW.strftime("%Y-%m-%dT%H:%M"), "squadre": PUB}, open(os.path.join(OUT, "allenatori.json"), "w"), ensure_ascii=False, separators=(",", ":"))
print(f"::notice title=Calcio · allenatori::richieste {used} · partite con allenatore {len(ST['fx'])} (senza formazione {len(ST['nolu'])}) · squadre {len(BY)}/{len(TEAMS)} · cambi negli ultimi 150 giorni {n_ch}")
