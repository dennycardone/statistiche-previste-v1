"""Quota 2 / Quota 3 · studio walk-forward sull'archivio privato delle quote 1xBet (25/10/2026). Stampa SOLO numeri aggregati.

Input: q23_candidati.json (tools/quota23.js): per ogni esito quotato da 1xBet in una partita già giocata, probabilità di Prevista con i
soli dati precedenti, quota "prima" (prima vista) e "ultima" (ultima prima del fischio), esito reale.

Per ogni giorno e per ogni metodo si sceglie AL MASSIMO una proposta per obiettivo:
  Quota 2 = quota 1xBet totale tra 1,85 e 2,20 · Quota 3 = tra 2,75 e 3,35
  struttura: singola, doppia, tripla (partite diverse; variante "campionati diversi")
  mercati: tutti · solo gol (1X2, Over/Under, Gol/No gol) · solo statistiche (1X2 corner, tiri, tiri in porta, falli, gialli, fuorigioco, cartellini)
  ordinamento: P (probabilità congiunta massima) · EV (valore atteso massimo P·Q−1) · P70 (solo esiti al 70% o più, poi P massima)
  astensione: "sempre" (si propone se c'è una combinazione nella fascia) · "EV≥0" (solo se il valore atteso del modello non è negativo)
Probabilità dichiarata: grezza (prodotto delle probabilità) e calibrata in walk-forward (fattore reale/dichiarata stimato sulle sole
giornate precedenti, ristretto verso 1), per misurare la distorsione da selezione del massimo.
Metriche: giorni con proposta, quota media, probabilità dichiarata media (grezza e calibrata), % prese con intervallo al 95%, ROI a
puntata fissa, log-loss, calibrazione per fasce, prima metà contro seconda metà del periodo.
Regola di decisione fissata il 25/10/2026 (prima di vedere i risultati): un metodo si può scegliere solo con almeno 100 giorni di
archivio; scelta sui primi due terzi dei giorni, verifica sull'ultimo terzo; deve avere probabilità calibrata entro ±5 punti dalla
frequenza reale nella verifica e ROI non peggiore di −margine medio di 1xBet. Prima di allora il rapporto dice solo "campione insufficiente".
26/10/2026 (decisioni di Denny): solo l'archivio reale 1xBet (niente quote storiche di altri bookmaker); la probabilità CORRETTA per esito
(Prevista + 1xBet senza margine, walk-forward) è lo standard; la grezza resta solo come riferimento. Focus settimanale su "solo statistiche"
e "statistiche + formazioni ufficiali sui falli", singola contro doppia; checkpoint intermedio di sola lettura a 60 giorni, decisione a 100:
la doppia sulle statistiche deve restare calibrata entro ±5 punti e battere le combinazioni che contengono i gol."""
import json, math, itertools, collections, statistics, os, sys, traceback
sys.excepthook = lambda t, v, tb: print("::error title=Quota 2/3::" + " | ".join(traceback.format_exception(t, v, tb)).replace("\n", " ")[-1500:])
C = json.load(open("q23_candidati.json"))
GOL = {"1X2 gol", "Over/Under 1.5", "Over/Under 2.5", "Over/Under 3.5", "Gol/No gol"}
TGT = {"Quota 2": (1.85, 2.20), "Quota 3": (2.75, 3.35)}
MIN_DAYS = 100
import numpy as np
SCEN = os.environ.get("Q23_SCEN", "q1")   # quale quota usare in questo passaggio (q1 = ultima prima del fischio, q0 = prima vista)
# probabilità di 1xBet senza margine per ogni esito (stesso mercato della stessa partita)
for c in C: c["pX"] = c.get("pxi") if c.get("pxi") is not None else c["p"]
grp = collections.defaultdict(list)
for c in C: grp[(c["key"], c["mk"])].append(c)
for L in grp.values():
    for qk in ("q0", "q1"):
        s_ = sum(1 / c[qk] for c in L if c.get(qk))
        for c in L: c["m" + qk] = (1 / c[qk]) / s_ if c.get(qk) and s_ > 0 and len([x for x in L if x.get(qk)]) == len(L) else None
# 25/10/2026: distorsione da selezione. Scegliendo la combinazione con la probabilità più alta a parità di quota si scelgono gli esiti dove
# Prevista è più lontana da 1xBet, e lì in media sbaglia di più. Correzione per ESITO (non per giorno: migliaia di esiti invece di 21 giorni):
# regressione logistica su logit(probabilità di Prevista) e logit(probabilità di 1xBet senza margine), per gruppo di mercati (gol,
# statistiche), stimata sulle sole giornate precedenti (almeno 7 giorni e 300 esiti). Le combinazioni usano poi le probabilità corrette.
lg_ = lambda p: math.log(min(max(p, 1e-4), 1 - 1e-4) / (1 - min(max(p, 1e-4), 1 - 1e-4)))
def fit_lr(X, y, l2=1.0):
    X = np.hstack([np.ones((len(X), 1)), np.array(X)]); y = np.array(y, float); b = np.zeros(X.shape[1])
    for _ in range(50):
        p = 1 / (1 + np.exp(-X @ b)); W = p * (1 - p); g = X.T @ (y - p) - l2 * np.r_[0, b[1:] - 1 * (np.arange(1, len(b)) == 1)]
        H = X.T @ (X * W[:, None]) + l2 * np.diag(np.r_[0, np.ones(len(b) - 1)]); b = b + np.linalg.solve(H, g)
    return b
days_all = sorted({c["d"] for c in C})
calrep = {}
for base in ("p", "pX"):
  for grp_name, test in (("gol", lambda c: c["mk"] in GOL), ("statistiche", lambda c: c["mk"] not in GOL)):
    if base == "pX" and grp_name == "gol": continue
    E = [c for c in C if test(c) and c.get("m" + SCEN)]
    ev = collections.defaultdict(list)
    for c in E: ev[c["d"]].append(c)
    out_m, out_b, out_p, ys = [], [], [], []
    tag = ("pc_" if base == "p" else "pcX_") + SCEN
    for i, d in enumerate(days_all):
        tr = [c for dd in days_all[:i] for c in ev.get(dd, [])]
        te = ev.get(d, [])
        if i < 7 or len(tr) < 300:
            for c in te: c[tag] = None
            continue
        b = fit_lr([[lg_(c[base]), lg_(c["m" + SCEN])] for c in tr], [c["y"] for c in tr])
        for c in te:
            z = b[0] + b[1] * lg_(c[base]) + b[2] * lg_(c["m" + SCEN]); c[tag] = 1 / (1 + math.exp(-z))
            out_m.append(c[base]); out_b.append(c["m" + SCEN]); out_p.append(c[tag]); ys.append(c["y"])
    if ys:
        L_ = lambda P: -statistics.mean(math.log(max(1e-6, p if y else 1 - p)) for p, y in zip(P, ys))
        bfull = fit_lr([[lg_(c[base]), lg_(c["m" + SCEN])] for c in E], [c["y"] for c in E])
        nm = grp_name + (" con formazioni sui falli" if base == "pX" else "")
        calrep[nm] = f"{nm}: {len(ys)} esiti fuori campione · log-loss Prevista {L_(out_m):.4f} · 1xBet senza margine {L_(out_b):.4f} · corretta {L_(out_p):.4f} · pesi oggi Prevista {bfull[1]:.2f}, 1xBet {bfull[2]:.2f}"
# 26/10/2026: le probabilità corrette (walk-forward) passano al simulatore di capitale (tools/bankroll.py). File SOLO nel runner, mai pubblicato.
json.dump([{k: c.get(k) for k in ("key", "d", "lg", "t", "mk", "side", "y", "q0", "q1", "pc_" + SCEN, "pcX_" + SCEN)} for c in C],
          open(f"q23_corrette_{SCEN}.json", "w"))
nxi = sum(1 for c in C if c.get("pxi") is not None)
byday = collections.defaultdict(list)
for c in C: byday[c["d"]].append(c)
days = sorted(byday)
note = lambda t, m: print(f"::notice title={t}::" + m.replace("%", "%25").replace("\n", " "))
note("Quota 2/3 · archivio", f"giorni con partite giocate e quote {len(days)} (dal {days[0] if days else '-'} al {days[-1] if days else '-'}), esiti quotati {len(C)}, "
     f"regola: si sceglie un metodo solo con almeno {MIN_DAYS} giorni ({'RAGGIUNTI' if len(days) >= MIN_DAYS else 'non ancora: campione insufficiente, i numeri sotto sono solo indicativi'})")

def best(cands, n, lo, hi, order, qk, diff_lg, pk="p"):
    pool = [c for c in cands if c.get(qk) and c.get(pk) is not None and c[qk] <= hi and (order != "P70" or c[pk] >= 0.70)]
    if not pool: return None
    if order == "EV": pool.sort(key=lambda c: -(c[pk] * c[qk] - 1))
    else: pool.sort(key=lambda c: -c[pk])
    pool = pool[: {1: 400, 2: 60, 3: 28}[n]]
    top = None
    for comb in itertools.combinations(pool, n):
        if len({c["key"] for c in comb}) < n or (diff_lg and len({c["lg"] for c in comb}) < n): continue
        Q = math.prod(c[qk] for c in comb)
        if not (lo <= Q <= hi): continue
        P = math.prod(c[pk] for c in comb); ev = P * Q - 1
        sc = ev if order == "EV" else P
        if top is None or sc > top[0]: top = (sc, P, Q, int(all(c["y"] for c in comb)), ev)
    return top

def run(qk, tgt, n, mset, order, abst, diff_lg=False, pk="p"):
    lo, hi = TGT[tgt]; R = []
    for d in days:
        cands = [c for c in byday[d] if (mset == "tutti" or (mset == "gol") == (c["mk"] in GOL))]
        b = best(cands, n, lo, hi, order, qk, diff_lg, pk)
        if b is None or (abst == "EV≥0" and b[4] < 0): R.append(None); continue
        R.append(dict(d=d, P=b[1], Q=b[2], y=b[3]))
    # calibrazione walk-forward (sole giornate precedenti)
    hy = hp = 0.0
    for r in R:
        if r is None: continue
        k = (hy + 5) / (hp + 5); r["Pc"] = min(0.99, r["P"] * k); hy += r["y"]; hp += r["P"]
    return R

def stats(R):
    X = [r for r in R if r]
    if not X: return None
    n = len(X); h = sum(r["y"] for r in X) / n
    ll = -statistics.mean(math.log(max(1e-6, r["Pc"] if r["y"] else 1 - r["Pc"])) for r in X)
    roi = statistics.mean(r["y"] * r["Q"] - 1 for r in X)
    half = len(R) // 2; A = [r for r in R[:half] if r]; B = [r for r in R[half:] if r]
    f = lambda L: f"{sum(r['y'] for r in L)}/{len(L)}" if L else "0/0"
    return dict(n=n, q=statistics.mean(r["Q"] for r in X), p=statistics.mean(r["P"] for r in X), pc=statistics.mean(r["Pc"] for r in X), h=h,
                ci=1.96 * math.sqrt(h * (1 - h) / n), roi=roi, ll=ll, a=f(A), b=f(B))

qk = SCEN; qlab = "quota ultima prima del fischio" if qk == "q1" else "quota prima vista"
stage = "DECISIONE (100 giorni raggiunti)" if len(days) >= MIN_DAYS else "CHECKPOINT INTERMEDIO di sola lettura (60 giorni)" if len(days) >= 60 else f"in raccolta: checkpoint a 60 giorni, decisione a {MIN_DAYS}"
if calrep: note(f"Quota 2/3 · correzione per esito ({qlab})", " ‖ ".join(calrep.values()) + f" ‖ esiti di falli con formazione ufficiale: {nxi}")
PC = "pc_" + qk
for tgt in TGT:
    for n in (1, 2, 3):
        lines = []
        st_ = stats(run(qk, tgt, n, "tutti", "P", "sempre", pk="p"))
        if st_: lines.append(f"riferimento, probabilità grezza/tutti/P/sempre: {st_['n']} g · dich {st_['p']*100:.0f}% · presa {st_['h']*100:.0f}% ±{st_['ci']*100:.0f} · ROI {st_['roi']*100:+.0f}%")
        for mset in ("tutti", "gol", "statistiche"):
            for order in ("P", "EV", "P70"):
                for abst in ("sempre", "EV≥0"):
                    st_ = stats(run(qk, tgt, n, mset, order, abst, pk=PC))
                    if not st_: continue
                    lines.append(f"{mset}/{order}/{abst}: {st_['n']} g · q {st_['q']:.2f} · dich {st_['p']*100:.0f}% · presa {st_['h']*100:.0f}% ±{st_['ci']*100:.0f} · ROI {st_['roi']*100:+.0f}% · LL {st_['ll']:.3f} · {st_['a']} | {st_['b']}")
        if n > 1:
            st_ = stats(run(qk, tgt, n, "tutti", "P", "sempre", diff_lg=True, pk=PC))
            if st_: lines.append(f"tutti/P/sempre/CAMPIONATI DIVERSI: {st_['n']} g · q {st_['q']:.2f} · dich {st_['p']*100:.0f}% · presa {st_['h']*100:.0f}% ±{st_['ci']*100:.0f} · ROI {st_['roi']*100:+.0f}%")
        note(f"{tgt} {['', 'singola', 'doppia', 'tripla'][n]} · {qlab} · probabilità corretta", " ‖ ".join(lines) if lines else "nessuna proposta possibile")
# focus: solo statistiche (e statistiche + formazioni sui falli), singola contro doppia, contro le combinazioni che contengono i gol
foc = [f"fase: {stage} · giorni {len(days)}"]
for tgt in TGT:
    for n in (1, 2):
        for lab, mset, pk in (("statistiche", "statistiche", PC), ("statistiche + formazioni falli", "statistiche", "pcX_" + qk), ("tutti (con gol)", "tutti", PC), ("solo gol", "gol", PC)):
            for order in ("P", "EV"):
                R = run(qk, tgt, n, mset, order, "sempre", pk=pk); st_ = stats(R)
                if not st_: continue
                X = [r for r in R if r]; gap = (st_["h"] - st_["p"]) * 100
                foc.append(f"{tgt} {['', 'singola', 'doppia'][n]} · {lab} · {order}: {st_['n']} g · dich {st_['p']*100:.0f}% · presa {st_['h']*100:.0f}% ±{st_['ci']*100:.0f} (scarto {gap:+.0f} punti, {'entro' if abs(gap) <= 5 else 'FUORI'} ±5) · ROI {st_['roi']*100:+.0f}%")
note(f"Quota 2/3 · FOCUS statistiche · {qlab}", " ‖ ".join(foc))
