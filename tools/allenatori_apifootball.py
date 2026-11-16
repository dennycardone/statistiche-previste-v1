"""Calcio · cambi di allenatore (16/11/2026, Denny: "voglio che mi venga segnalato quando c'è un cambio di allenatore, cambia il gioco
della squadra e le statistiche diventano meno attendibili").
API-Football /coachs?team=ID (una richiesta per squadra): allenatore attuale = voce della carriera su quella squadra senza fine, con
l'inizio più recente; il precedente = la voce chiusa più recente. Id delle squadre dai loghi pubblicati (data/loghi.json: nome dell'app → logo
https://media.api-sports.io/football/teams/<id>.png). Prima le squadre che giocano nelle prossime 36 ore (data/prossime.json) non controllate
da 20 ore, poi le altre dal controllo più vecchio. Solo le richieste che avanzano dopo la riserva dell'app (af_budget), al massimo 800 a giro.
Uso: python tools/allenatori_apifootball.py LOGHI.json PROSSIME.json CARTELLA (CARTELLA/stato.json = stato privato, CARTELLA/allenatori.json = sito)"""
import json, os, re, sys, time, datetime, urllib.request, urllib.parse
sys.path.insert(0, os.path.dirname(__file__)); import af_budget
LOGHI, PROSS, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
KEY = os.environ["APIFOOTBALL_KEY"].strip()
os.makedirs(OUT, exist_ok=True); SP = os.path.join(OUT, "stato.json")
ST = json.load(open(SP)) if os.path.exists(SP) else {}
NOW = datetime.datetime.now(datetime.timezone.utc); NOWS = NOW.strftime("%Y-%m-%dT%H:%M")
def get(p, **q):
    req = urllib.request.Request("https://v3.football.api-sports.io/" + p + ("?" + urllib.parse.urlencode(q) if q else ""), headers={"x-apisports-key": KEY})
    with urllib.request.urlopen(req, timeout=60) as r: return json.loads(r.read().decode())
TEAMS = {}   # id → [(lega, nome dell'app)]
for lg, m in json.load(open(LOGHI)).items():
    for nm, url in m.items():
        mm = re.search(r"/teams/(\d+)\.png", url or "")
        if mm: TEAMS.setdefault(mm.group(1), []).append((lg, nm))
soon = set()
try:
    for p in json.load(open(PROSS)):
        for side in ("h", "a"):
            for tid, L in TEAMS.items():
                if (p["lg"], p[side]) in L: soon.add(tid)
except Exception as e: print("::warning title=Allenatori::prossime partite non lette: " + str(e)[:100])
def age_h(tid):
    c = (ST.get(tid) or {}).get("chk")
    return (NOW - datetime.datetime.fromisoformat(c + ":00+00:00")).total_seconds() / 3600 if c else 1e9
order = sorted([t for t in TEAMS if t in soon and age_h(t) >= 20], key=age_h, reverse=True) + sorted([t for t in TEAMS if t not in soon and age_h(t) >= 20], key=age_h, reverse=True)
budget = min(800, af_budget.test_budget(af_budget.requests_of(get("status"))))
print(f"squadre {len(TEAMS)} · da controllare {len(order)} (prossime 36 ore: {sum(1 for t in order if t in soon)}) · richieste usabili {budget}")
done, changes = 0, []
for tid in order:
    if done >= budget: break
    try: R = get("coachs", team=tid).get("response") or []
    except Exception as e: print("errore", tid, str(e)[:80]); time.sleep(2); continue
    done += 1; time.sleep(0.25)
    cur, prev = None, None
    for c in R:
        for k in c.get("career") or []:
            if str((k.get("team") or {}).get("id")) != tid or not k.get("start"): continue
            if not k.get("end"):
                if not cur or k["start"] > cur[2]: cur = (c.get("id"), c.get("name"), k["start"])
            elif not prev or k["end"] > prev[2]: prev = (c.get("id"), c.get("name"), k["end"])
    old = ST.get(tid) or {}
    e = {"chk": NOWS}
    if cur:
        e.update({"cid": cur[0], "c": cur[1], "da": cur[2]})
        if prev: e.update({"prev": prev[1], "fine_prev": prev[2]})
        if old.get("cid") and old["cid"] != cur[0]:   # cambiato tra due controlli: la data di inizio potrebbe non essere ancora aggiornata
            e["visto"] = NOWS[:10]; e.setdefault("prev", old.get("c")); changes.append(f"{TEAMS[tid][0][1]}: {old.get('c')} → {cur[1]}")
        elif old.get("visto") and old.get("cid") == cur[0]: e["visto"] = old["visto"]
    else: e.update({k: old[k] for k in ("cid", "c", "da", "prev", "fine_prev", "visto") if k in old})   # nessun allenatore in corso nei dati: si tiene l'ultimo
    ST[tid] = e
json.dump(ST, open(SP, "w"), ensure_ascii=False, separators=(",", ":"))
# sul sito: solo le squadre con un allenatore arrivato negli ultimi 120 giorni (l'app lo segnala finché ha meno di 8 partite con lui)
lim = (NOW - datetime.timedelta(days=120)).strftime("%Y-%m-%d"); PUB = {}
for tid, e in ST.items():
    da = max(e.get("da") or "", e.get("visto") or "")
    if not e.get("c") or da < lim: continue
    for lg, nm in TEAMS.get(tid, []):
        PUB.setdefault(lg, {})[nm] = {"c": e["c"], "da": da, **({"prev": e["prev"]} if e.get("prev") else {})}
json.dump({"agg": NOWS, "squadre": PUB}, open(os.path.join(OUT, "allenatori.json"), "w"), ensure_ascii=False, separators=(",", ":"))
n_pub = sum(len(v) for v in PUB.values())
print(f"::notice title=Calcio · allenatori::richieste {done} · controllate in tutto {sum(1 for t in TEAMS if t in ST)}/{len(TEAMS)} · allenatori nuovi (120 giorni) {n_pub}"
      + (" · cambi visti ora: " + "; ".join(changes[:15]) if changes else ""))
