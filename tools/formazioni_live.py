"""Micro-processo delle formazioni ufficiali (26/10/2026, approvato da Denny). Gira ogni 10 minuti (formazioni_live.yml), indipendente
dall'aggiornamento principale (che GitHub fa partire anche con un'ora di ritardo).

  python tools/formazioni_live.py check   → 1 secondo, 0 richieste: c'è lavoro? (partite che iniziano entro 65 minuti senza formazione,
                                            oppure formazioni prese ma non ancora sul sito). Scrive need=0/1 in $GITHUB_OUTPUT.
  python tools/formazioni_live.py run     → chiede fixtures/lineups a API-Football per quelle partite (una richiesta a partita, al massimo
                                            40 per giro); se a 12–65 minuti dal fischio qualche formazione non è ancora uscita, riprova una
                                            volta dopo 9 minuti nello stesso giro (finestra tra −45 e −15 minuti mai persa). Poi calcola la
                                            correzione dei falli (xi_corr.py, la stessa dell'aggiornamento principale) e scrive
                                            out/formazioni.json se il sito va aggiornato.
File: pub/prossime.json e pub/formazioni.json (ramo pages, dall'aggiornamento principale), xi_live/xi.json (ramo xi, formazioni prese),
valori/valori.json (ramo valori). Solo formazioni prese PRIMA del fischio (nessun dato successivo)."""
import json, os, sys, time, datetime, urllib.request, urllib.parse, traceback
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.excepthook = lambda t, v, tb: print("::error title=Formazioni (micro)::" + " | ".join(traceback.format_exception(t, v, tb)).replace("\n", " ")[-1500:])
WIN, RETRY_LO, RETRY_HI, WAIT, MAXREQ = 65, 12, 65, 9 * 60, 40
rd = lambda p, d: json.load(open(p)) if os.path.exists(p) and os.path.getsize(p) > 0 else d
NEXT = rd("pub/prossime.json", [])
PUB = rd("pub/formazioni.json", {"partite": {}})
XL = rd("xi_live/xi.json", {"xi": {}, "tent": {}})
XL.setdefault("xi", {}); XL.setdefault("tent", {})
now = lambda: datetime.datetime.now(datetime.timezone.utc)
mins = lambda m, t=None: (datetime.datetime.fromisoformat(m["ko"] + ":00+00:00") - (t or now())).total_seconds() / 60
key_of = lambda m: f"{m['lg']}|{m['d']}|{m['h']}|{m['a']}"

def todo(t=None):
    return [m for m in NEXT if m["fid"] not in XL["xi"] and -5 < mins(m, t) <= WIN]

def unpublished():
    pub = PUB.get("partite", {})
    return [x for x in XL["xi"].values() if x.get("key") and x["key"] not in pub and x.get("ko", "") > (now() - datetime.timedelta(hours=3)).strftime("%Y-%m-%dT%H:%M")]

mode = sys.argv[1] if len(sys.argv) > 1 else "run"
if mode == "check":
    T, U = todo(), unpublished()
    need = 1 if (T or U) else 0
    print(f"partite in elenco {len(NEXT)} · senza formazione entro {WIN} minuti {len(T)} · prese non pubblicate {len(U)} → {'lavoro' if need else 'niente da fare'}")
    if os.environ.get("GITHUB_OUTPUT"): open(os.environ["GITHUB_OUTPUT"], "a").write(f"need={need}\n")
    sys.exit(0)

import xi_corr
KEY = os.environ.get("APIFOOTBALL_KEY", "").strip()
nreq, log = 0, []
def fetch(ms):
    global nreq
    left = []
    for m in ms:
        if nreq >= MAXREQ or not KEY: left.append(m); continue
        mm = mins(m)
        try:
            req = urllib.request.Request("https://v3.football.api-sports.io/fixtures/lineups?" + urllib.parse.urlencode({"fixture": m["fid"]}), headers={"x-apisports-key": KEY})
            with urllib.request.urlopen(req, timeout=30) as r: R = json.loads(r.read().decode()).get("response") or []
            nreq += 1; XL["tent"][m["fid"]] = XL["tent"].get(m["fid"], 0) + 1
            got, why = xi_corr.parse_lineups(R, m["ha"], m["aa"])
        except Exception as e_: got, why = None, "errore " + str(e_)[:60]
        if got and mm > -1:   # solo prima del fischio (dato noto prima della partita)
            XL["xi"][m["fid"]] = {"t": now().strftime("%Y-%m-%d %H:%M"), "hid": got[0], "aid": got[1], "h": got[2], "a": got[3],
                                  "key": key_of(m), "ko": m["ko"]}
            log.append(f"{m['h']}–{m['a']} ({mm:.0f}′ prima): presa")
        else:
            log.append(f"{m['h']}–{m['a']} ({mm:.0f}′ prima): {why if not got else 'iniziata'}"); left.append(m)
        time.sleep(0.25)
    return left

left = fetch(todo())
again = [m for m in left if RETRY_LO < mins(m) <= RETRY_HI] if KEY and nreq < MAXREQ and not os.environ.get("FL_LOOP") else []   # nel giro lungo (FL_LOOP) si riprova al controllo dopo, 5 minuti
if again:   # secondo tentativo nello stesso giro: GitHub può ritardare il giro dopo anche di 20-30 minuti
    time.sleep(WAIT)
    fetch([m for m in again if m["fid"] not in XL["xi"]])
# formazioni.json come lo scrive l'aggiornamento principale: partite con formazione fino a 3 ore dopo il fischio
V = rd("valori/valori.json", None)
F = {"pesi": list(xi_corr.W_XI), "partite": {}}
lim = (now() - datetime.timedelta(hours=3)).strftime("%Y-%m-%dT%H:%M")
if V:
    for fid, x in XL["xi"].items():
        if not x.get("key") or x.get("ko", "") < lim: continue
        c_, why = xi_corr.corr(x, V)
        if not c_: log.append(f"{x['key']}: {why}"); continue
        F["partite"][x["key"]] = {"fh": c_[0], "fa": c_[1], "ora": x["t"], "xi": xi_corr.entry(x)}
    # le partite che l'aggiornamento principale ha già (anche prese da lui) restano
    for k, v in PUB.get("partite", {}).items(): F["partite"].setdefault(k, v)
else: log.append("valori dei giocatori non disponibili: correzione non calcolata")
# pulizia: formazioni più vecchie di 3 giorni
old = (now() - datetime.timedelta(days=3)).strftime("%Y-%m-%d %H:%M")
for fid in [f for f, x in XL["xi"].items() if x["t"] < old]: del XL["xi"][fid]
XL["tent"] = {f: n for f, n in XL["tent"].items() if any(m["fid"] == f for m in NEXT) or f in XL["xi"]}
XL["agg"] = now().strftime("%Y-%m-%d %H:%M")
os.makedirs("xi_live", exist_ok=True); json.dump(XL, open("xi_live/xi.json", "w"), ensure_ascii=False, separators=(",", ":"))
changed = V is not None and F["partite"] != PUB.get("partite", {})
if changed:
    os.makedirs("out", exist_ok=True); json.dump(F, open("out/formazioni.json", "w"), ensure_ascii=False, separators=(",", ":"))
print("::notice title=Formazioni (micro)::" + f"{nreq} richieste · " + (" · ".join(log[:14]) if log else "nessun tentativo") +
      f" · sito {'da aggiornare (' + str(len(F['partite'])) + ' partite)' if changed else 'già aggiornato'}")
