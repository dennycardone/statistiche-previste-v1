"""Gestione del capitale · simulatore walk-forward sull'archivio privato delle quote 1xBet (26/10/2026). Stampa SOLO numeri aggregati.

Input: q23_corrette_q1.json, scritto nel runner da tools/quota23.py (mai pubblicato): per ogni esito quotato da 1xBet in una partita già
giocata, la probabilità CORRETTA per esito (Prevista + 1xBet senza margine, regressione stimata solo sui giorni precedenti; "pcX" usa anche
le formazioni ufficiali sui falli registrate prima del fischio), la quota ultima vista prima del fischio (q1) e l'esito reale.
Mai la probabilità grezza: con la grezza il dimensionamento della puntata esplode sugli estremi (distorsione da selezione).

Regole fissate il 26/10/2026, PRIMA di vedere i risultati:
  cassa iniziale 100, simulazione giorno per giorno; le puntate di un giorno si decidono con la cassa di inizio giornata e si
  saldano a fine giornata (le vincite non si rigiocano lo stesso giorno, prudente).
  perimetri: solo statistiche · statistiche + formazioni sui falli · tutti i mercati · solo gol
  flussi:   singole  = ogni esito con valore atteso positivo sulla probabilità corretta (P·Q − 1 > 0), al massimo uno per partita
                       (quello con valore atteso più alto: niente esiti correlati della stessa partita)
            Quota 2  = la combinazione (singola, doppia o tripla, partite diverse) con quota 1xBet 1,85–2,20 e valore atteso più alto
                       del giorno, solo se positivo; una al giorno
            Quota 3  = lo stesso tra 2,75 e 3,35
  metodi:   fissa 1%  = 1 (1% della cassa iniziale) per giocata · fissa 2% = 2
            Kelly 1/8 e 1/4 = k · (P·Q − 1)/(Q − 1) della cassa, tetto 3% per giocata
            fasce = unità dell'1% della cassa: singole solo da Grado B in su (scala unica dell'app sulla probabilità corretta:
                    B da 75%, A da 80%, A+ da 85%), 1 unità su A/B, 1,5 su A+; combinazioni 1 unità, 1,5 se valore atteso ≥ 10%
  tetto contemporaneità: la somma delle puntate di un giorno (quindi anche di ogni fascia oraria) non supera il 10% della cassa di
                         inizio giornata; oltre, tutte le puntate del giorno si riducono in proporzione
  astensione: nessun esito con valore atteso positivo → puntata 0
Metriche: cassa finale, giocate, puntato, yield (utile/puntato, intervallo al 95% con errori raggruppati per giorno), ROI sulla cassa,
calo massimo dal picco (sulla cassa di fine giornata), serie di giocate perse più lunga, oscillazione settimanale (deviazione standard del
rendimento settimanale), rendimento corretto per il rischio (media/deviazione del rendimento settimanale), giorni col tetto applicato.
Regola di adozione (come Quota 2/3): si decide solo con almeno 100 giorni di archivio; i primi due terzi dei giorni servono solo a
guardare, l'ultimo terzo è la verifica fuori campione. Un metodo entra nell'app solo se, nella verifica e a parità di perimetro e flusso,
rispetto alla puntata fissa 1%: (a) ha rendimento corretto per il rischio più alto con intervallo al 95% (bootstrap a blocchi settimanali)
del miglioramento sopra zero, oppure (b) calo massimo più basso con rendimento non inferiore; e in ogni caso yield non peggiore del
−margine medio di 1xBet. Checkpoint di sola lettura a 60 giorni (7/12/2026), decisione a 100 (18/1/2027). Mai promesse di guadagno:
nell'app l'eventuale cassa dell'utente resterebbe solo nel localStorage del suo dispositivo."""
import json, math, itertools, collections, statistics, datetime, random, sys, traceback, os
sys.excepthook = lambda t, v, tb: print("::error title=Gestione del capitale::" + " | ".join(traceback.format_exception(t, v, tb)).replace("\n", " ")[-1500:])
SCEN = os.environ.get("Q23_SCEN", "q1")
C = json.load(open(f"q23_corrette_{SCEN}.json"))
GOL = {"1X2 gol", "Over/Under 1.5", "Over/Under 2.5", "Over/Under 3.5", "Gol/No gol"}
TGT = {"Quota 2": (1.85, 2.20), "Quota 3": (2.75, 3.35)}
START, CAP, KCAP, MIN_DAYS = 100.0, 0.10, 0.03, 100
PER = [("solo statistiche", lambda c: c["mk"] not in GOL, "pc_"), ("statistiche + formazioni falli", lambda c: c["mk"] not in GOL, "pcX_"),
       ("tutti i mercati", lambda c: True, "pc_"), ("solo gol", lambda c: c["mk"] in GOL, "pc_")]
METH = ["fissa 1%", "fissa 2%", "Kelly 1/8", "Kelly 1/4", "fasce"]
note = lambda t, m: print(f"::notice title={t}::" + m.replace("%", "%25").replace("\n", " "))
days = sorted({c["d"] for c in C})
byday = collections.defaultdict(list)
for c in C: byday[c["d"]].append(c)
# margine medio di 1xBet sugli esiti dell'archivio (per la regola di adozione)
mg = collections.defaultdict(float); full = collections.defaultdict(lambda: True)
for c in C:
    if c.get(SCEN): mg[(c["key"], c["mk"])] += 1 / c[SCEN]
    else: full[(c["key"], c["mk"])] = False
MARG = statistics.mean(v - 1 for k, v in mg.items() if full[k] and v > 1) if mg else 0.05

def picks(d, test, pk):
    """giocate del giorno d per ogni flusso: liste di (P, Q, esito, orario)"""
    pool = [c for c in byday[d] if test(c) and c.get(pk) is not None and c.get(SCEN)]
    for c in pool: c["_P"], c["_Q"] = c[pk], c[SCEN]; c["_E"] = c["_P"] * c["_Q"] - 1
    best = {}
    for c in pool:
        if c["_E"] > 0 and (c["key"] not in best or c["_E"] > best[c["key"]]["_E"]): best[c["key"]] = c
    out = {"singole": sorted(((c["_P"], c["_Q"], c["y"], c.get("t") or "") for c in best.values()), key=lambda x: x[3])}
    for tgt, (lo, hi) in TGT.items():
        P2 = sorted((c for c in pool if c["_Q"] <= hi), key=lambda c: -c["_E"]); top = None
        for n, lim in ((1, 400), (2, 60), (3, 28)):
            for comb in itertools.combinations(P2[:lim], n):
                if len({c["key"] for c in comb}) < n: continue
                Q = math.prod(c["_Q"] for c in comb)
                if not (lo <= Q <= hi): continue
                P = math.prod(c["_P"] for c in comb)
                if P * Q - 1 > 0 and (top is None or P * Q - 1 > top[0] * top[1] - 1):
                    top = (P, Q, int(all(c["y"] for c in comb)), max(c.get("t") or "" for c in comb))
        out[tgt] = [top] if top else []
    return out

def stake(meth, B, P, Q, combo):
    e = P * Q - 1
    if meth == "fissa 1%": return 1.0
    if meth == "fissa 2%": return 2.0
    if meth.startswith("Kelly"): k = 1 / 8 if "1/8" in meth else 1 / 4; return B * min(KCAP, k * e / (Q - 1))
    if combo: return B * (0.015 if e >= 0.10 else 0.01)
    return B * (0.015 if P >= 0.85 else 0.01 if P >= 0.75 else 0.0)

def simulate(stream_by_day, meth, combo, dset):
    B = START; eq = [(None, B)]; bets = []; capped = 0; daily = []
    for d in dset:
        L = stream_by_day.get(d, [])
        S = [min(stake(meth, B, P, Q, combo), B) for P, Q, y, t in L]
        tot = sum(S)
        if tot > CAP * B and tot > 0: S = [s * CAP * B / tot for s in S]; capped += 1
        pl = 0.0; st = 0.0
        for s, (P, Q, y, t) in zip(S, L):
            if s <= 0: continue
            r = s * (Q - 1) if y else -s; pl += r; st += s; bets.append((d, s, r))
        daily.append((d, st, pl, B)); B += pl; eq.append((d, B))
        if B < 1: break
    return B, eq, bets, capped, daily

def weekly(daily):
    W = collections.OrderedDict()
    for d, st, pl, B0 in daily:
        w = datetime.date.fromisoformat(d).isocalendar()[:2]
        if w not in W: W[w] = [B0, 0.0]
        W[w][1] += pl
    return [pl / b0 for b0, pl in W.values() if b0 > 0]

def metrics(res):
    B, eq, bets, capped, daily = res
    st = sum(s for _, s, _ in bets); pl = sum(r for _, _, r in bets)
    pk, mdd = START, 0.0
    for _, v in eq: pk = max(pk, v); mdd = max(mdd, (pk - v) / pk)
    run = lr = 0
    for _, s, r in bets: run = run + 1 if r < 0 else 0; lr = max(lr, run)
    # yield con errori raggruppati per giorno (stimatore del rapporto)
    D = collections.defaultdict(lambda: [0.0, 0.0])
    for d, s, r in bets: D[d][0] += s; D[d][1] += r
    yl = pl / st if st else 0.0; n = len(D)
    se = math.sqrt(sum((r - yl * s) ** 2 for s, r in D.values()) / (n * (n - 1))) / (st / n) if n > 1 and st else float("nan")
    W = weekly(daily); osc = statistics.pstdev(W) if len(W) > 1 else float("nan")
    sh = statistics.mean(W) / osc if len(W) > 1 and osc > 0 else float("nan")
    return dict(B=B, n=len(bets), st=st, yl=yl, ci=1.96 * se, roi=B / START - 1, mdd=mdd, lr=lr, osc=osc, sh=sh, cap=capped, W=W, gd=n)

def fmt(m):
    if not m["n"]: return "nessuna giocata (astensione)"
    sh = "N/D" if m["sh"] != m["sh"] else f"{m['sh']:+.2f}"; osc = "N/D" if m["osc"] != m["osc"] else f"{m['osc']*100:.1f}%"
    ci = "" if m["ci"] != m["ci"] else f" ±{m['ci']*100:.0f}"
    return (f"cassa {m['B']:.1f} · {m['n']} giocate in {m['gd']} g · puntato {m['st']:.0f} · yield {m['yl']*100:+.1f}%{ci} · ROI cassa {m['roi']*100:+.1f}% · "
            f"calo max {m['mdd']*100:.1f}% · serie persa {m['lr']} · osc. sett. {osc} · rend./rischio {sh} · tetto {m['cap']} g")

stage = "DECISIONE (100 giorni raggiunti)" if len(days) >= MIN_DAYS else "CHECKPOINT INTERMEDIO di sola lettura (60 giorni)" if len(days) >= 60 else "FOTOGRAFIA (campione insufficiente: nessuna conclusione)"
first_bet = None
SEL = os.environ.get("BK_PER")   # un passaggio del workflow per perimetro (limite degli avvisi di GitHub)
for ip, (pname, test, pre) in enumerate(PER):
    if SEL is not None and str(ip) != SEL: continue
    pk = pre + SCEN
    P = {d: picks(d, test, pk) for d in days}
    fb = next((d for d in days if any(P[d][s] for s in P[d])), None)
    if fb and (first_bet is None or fb < first_bet): first_bet = fb
    for stream in ("singole", "Quota 2", "Quota 3"):
        lines = []
        SB = {d: P[d][stream] for d in days}
        for meth in METH:
            m = metrics(simulate(SB, meth, stream != "singole", days))
            lines.append(f"{meth}: {fmt(m)}")
        # regola di adozione: solo con 100 giorni, verifica sull'ultimo terzo
        if len(days) >= MIN_DAYS:
            ver = days[len(days) * 2 // 3:]; base = metrics(simulate(SB, "fissa 1%", stream != "singole", ver))
            for meth in METH[2:]:
                m = metrics(simulate(SB, meth, stream != "singole", ver)); ok = False
                if base["W"] and m["W"] and len(m["W"]) == len(base["W"]) and len(m["W"]) >= 4:
                    rnd = random.Random(7); diffs = []
                    for _ in range(2000):
                        idx = [rnd.randrange(len(m["W"])) for _ in m["W"]]
                        a = [m["W"][i] for i in idx]; b = [base["W"][i] for i in idx]
                        sa, sb = statistics.pstdev(a), statistics.pstdev(b)
                        if sa > 0 and sb > 0: diffs.append(statistics.mean(a) / sa - statistics.mean(b) / sb)
                    diffs.sort(); lo = diffs[int(0.025 * len(diffs))] if diffs else -1
                    ok = lo > 0 or (m["mdd"] < base["mdd"] and m["roi"] >= base["roi"])
                ok = ok and m["yl"] >= -MARG
                lines.append(f"VERIFICA {meth} contro fissa 1%: {'SUPERA' if ok else 'non supera'} la regola (calo max {m['mdd']*100:.1f}% contro {base['mdd']*100:.1f}%, rend./rischio {m['sh']:+.2f} contro {base['sh']:+.2f})")
        note(f"Capitale · {pname} · {stream}", " ‖ ".join(lines))
if SEL in (None, "0"): note("Gestione del capitale · archivio", f"fase: {stage} · giorni con partite giocate e quote {len(days)} (dal {days[0] if days else '-'} al {days[-1] if days else '-'}), "
     f"prima giocata possibile {first_bet or '-'} (la correzione per esito parte dopo 7 giorni e 300 esiti) · margine medio 1xBet {MARG*100:.1f}% · "
     f"cassa 100, tetto giornaliero {CAP*100:.0f}% della cassa, Kelly con tetto {KCAP*100:.0f}% per giocata, quota ultima prima del fischio · "
     f"checkpoint di sola lettura a 60 giorni (7/12/2026), decisione a {MIN_DAYS} (18/1/2027)")
