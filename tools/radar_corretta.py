"""Radar Mercato con la probabilità corretta (28/10/2026, punto 3 di Denny). Gira nel runner; stampa SOLO numeri aggregati.
Il Radar dichiara in media ~9 punti di riuscita in più di quella reale: sceglie le linee dove Prevista è più lontana da 1xBet, e lì
Prevista sbaglia di più. Probabilità corretta = regressione logistica su logit(Prevista) e logit(Over senza margine di 1xBet), per
famiglia di mercato, stimata sulle sole giornate precedenti (almeno 7 giorni e 300 linee, come Quota 2/3).
Confronto, sugli stessi giorni (quelli con la corretta disponibile):
  A  Radar di oggi: lato con valore atteso più alto se ≥ +5% e riuscita ≥ 65% (Prevista)
  B  sostituzione: stesso criterio ma valore atteso e riuscita con la probabilità corretta
  C  affiancamento: le giocate di A che restano con la corretta (valore atteso corretto > 0 e corretta ≥ 60%)
Per ciascuno: giocate al giorno, presa contro riuscita dichiarata (scarto), rendimento a puntata fissa (IC 95% raggruppato per partita),
e le due metà dei giorni. In più log-loss di Prevista, 1xBet senza margine e corretta su tutte le linee (Over sì/no)."""
import json, math, os, sys, collections, traceback
import numpy as np
sys.excepthook = lambda t, v, tb: print("::error title=Radar corretta::" + " | ".join(traceback.format_exception(t, v, tb)).replace("\n", " ")[-1500:])
note = lambda t, m: print(f"::notice title={t}::" + m.replace("%", "%25").replace("\n", " "))
A = json.load(open(os.environ.get("RM_DUMP", "rm_all.json")))
lg_ = lambda p: math.log(min(max(p, 1e-4), 1 - 1e-4) / (1 - min(max(p, 1e-4), 1 - 1e-4)))
def fit_lr(X, y, l2=1.0):
    X = np.hstack([np.ones((len(X), 1)), np.array(X)]); y = np.array(y, float); b = np.zeros(X.shape[1])
    for _ in range(50):
        p = 1 / (1 + np.exp(-X @ b)); W = p * (1 - p); g = X.T @ (y - p) - l2 * np.r_[0, b[1:] - 1 * (np.arange(1, len(b)) == 1)]
        H = X.T @ (X * W[:, None]) + l2 * np.diag(np.r_[0, np.ones(len(b) - 1)]); b = b + np.linalg.solve(H, g)
    return b
for r in A: r["pb"] = (1 / r["o"]) / (1 / r["o"] + 1 / r["u"])
days = sorted({r["d"] for r in A}); byd = collections.defaultdict(list)
for r in A: byd[r["d"]].append(r)
W = {}
for i, d in enumerate(days):
    for fam in {r["fam"] for r in byd[d]}:
        tr = [r for dd in days[:i] for r in byd[dd] if r["fam"] == fam]
        if i < 7 or len(tr) < 300: continue
        b = fit_lr([[lg_(r["po"]), lg_(r["pb"])] for r in tr], [r["over"] for r in tr]); W[(d, fam)] = b
        for r in byd[d]:
            if r["fam"] == fam: r["pc"] = 1 / (1 + math.exp(-(b[0] + b[1] * lg_(r["po"]) + b[2] * lg_(r["pb"]))))
E = [r for r in A if r.get("pc") is not None]
if not E: note("Radar corretta", f"linee {len(A)} in {len(days)} giorni: corretta non ancora disponibile"); sys.exit(0)
ys = np.array([r["over"] for r in E])
LL = lambda k: float(-np.mean([math.log(max(1e-6, r[k] if r["over"] else 1 - r[k])) for r in E]))
last = {fam: W[max(k for k in W if k[1] == fam)] for fam in {k[1] for k in W}}
note("Radar corretta · linee", f"linee con la corretta {len(E)} su {len(A)} (dal {E[0]['d'] if E else '-'}; giorni {len({r['d'] for r in E})}) · log-loss Over sì/no: Prevista {LL('po'):.4f} · 1xBet senza margine {LL('pb'):.4f} · corretta {LL('pc'):.4f} ‖ pesi oggi (Prevista, 1xBet): " +
     ", ".join(f"{f} {b[1]:.2f}/{b[2]:.2f}" for f, b in sorted(last.items())))
def pick(r, pk, evmin=0.05, pmin=0.65):
    p = r[pk]; eo, eu = p * r["o"] - 1, (1 - p) * r["u"] - 1
    side = "O" if eo >= eu else "U"; ev = max(eo, eu); ps = p if side == "O" else 1 - p
    if ev < evmin or round(ps * 100) < round(pmin * 100): return None
    return dict(key=r["key"], d=r["d"], fam=r["fam"], side=side, p=ps, pc=r["pc"] if side == "O" else 1 - r["pc"],
                odd=r["o"] if side == "O" else r["u"], hit=(r["over"] == 1) == (side == "O"))
def st(R, pk="p"):
    if not R: return "nessuna"
    n = len(R); h = np.mean([x["hit"] for x in R]); p = np.mean([x[pk] for x in R]); pl = np.array([x["hit"] * x["odd"] - 1 for x in R]); roi = pl.mean()
    G = collections.defaultdict(float)
    for x, v in zip(R, pl): G[x["key"]] += v - roi
    ci = 1.96 * math.sqrt(sum(v * v for v in G.values())) / n
    return f"{n} ({n / nd:.1f} al giorno) · presa {100 * h:.0f}% contro dichiarata {100 * p:.0f}% (scarto {100 * (h - p):+.0f}) · quota media {np.mean([x['odd'] for x in R]):.2f} · rendimento {100 * roi:+.1f}% ±{100 * ci:.0f}"
ED = sorted({r["d"] for r in E}); nd = len(ED); half = ED[len(ED) // 2]
SA = [x for x in (pick(r, "po") for r in E) if x]
SB = [x for x in (pick(r, "pc") for r in E) if x]
SC = [x for x in SA if x["pc"] >= 0.60 and x["pc"] * x["odd"] - 1 > 0]
for lab, S, pk in (("A Radar di oggi (Prevista)", SA, "p"), ("A con la corretta come riuscita dichiarata", SA, "pc"), ("B sostituzione (corretta)", SB, "p"), ("C affiancamento (A confermate dalla corretta)", SC, "pc")):
    note(f"Radar corretta · {lab}", f"tutti i giorni: {st(S, pk)} ‖ prima metà: {st([x for x in S if x['d'] < half], pk)} ‖ seconda metà: {st([x for x in S if x['d'] >= half], pk)}")
note("Radar corretta · B per mercato", " ‖ ".join(f"{f}: {st([x for x in SB if x['fam'] == f])}" for f in sorted({x['fam'] for x in SB})))
# soglie della corretta (sostituzione): quante giocate e come vanno
note("Radar corretta · B per soglia di riuscita", " ‖ ".join(f"dal {int(t * 100)}%: {st([x for x in (pick(r, 'pc', 0.05, t) for r in E) if x])}" for t in (0.55, 0.60, 0.65, 0.70)))
