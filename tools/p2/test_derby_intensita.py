"""Prevista 2.0 · intensità del singolo derby nei cartellini (30/10/2026, segnalazione di Denny su Boca–River: 6,4 previsti, 10-12 reali
negli ultimi scontri). Oggi il modello (cards_model.py v3) dà a TUTTI i derby lo stesso +20% (DB) e gli scontri diretti (H) sono ristretti
verso 1 con K=12, uguale per derby e non derby.
Varianti (pesi stimati mese per mese sulle sole partite precedenti, stesse variabili dell'app, dati API-Football del ramo storico):
  base  le variabili di oggi
  HD    + H×DB: gli scontri diretti contano di più quando è un derby
  HD4   + H4×DB: come HD ma con gli scontri diretti ristretti meno (K=4) nei derby
Giudizio: Over/Under 4,5 e 5,5 cartellini totali (Binomiale Negativa), regola dell'harness; più il confronto sui soli derby."""
import os, sys, json, glob, math, collections
import numpy as np, pandas as pd
from scipy.special import gammaln
REPO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
P2 = os.environ.get("RICERCA", os.path.join(REPO, "ricerca"))
sys.path.insert(0, REPO); sys.path.insert(0, os.path.join(REPO, "tools"))
import cards_model as CM, harness as H
log = lambda *a: print(*a, flush=True)
M = []
for f in glob.glob(P2 + "/storico/*_20*.json"):
    D = json.load(open(f)); lg = D.get("lega") or os.path.basename(f).split("_")[0]
    for fid, v in D["partite"].items():
        sh, sa = v[6], v[7]
        ok = sh and sa and sh[4] is not None and sa[4] is not None
        M.append(dict(lg=lg, d=v[0], h=v[1], a=v[2], ref=v[5], hc=(sh[4] + (sh[5] or 0)) if ok else None, ac=(sa[4] + (sa[5] or 0)) if ok else None,
                      hf=sh[3] if ok else None, af=sa[3] if ok else None))
log("partite", len(M))
F = CM.features(M)
CM.K_H = 4; F4 = CM.features(M); CM.K_H = 12
iH, iDB = CM.FEATS.index("H"), CM.FEATS.index("DB")
R = []
for m, f, f4 in zip(M, F, F4):
    if not f or not f["played"]: continue
    x = f["x"]; db = x[iDB]
    R.append(dict(d=f["d"], lg=f["lg"], T=f["T"], lm=f["lm"], db=db, base=x, HD=x + [x[iH] * db], HD4=x + [f4["x"][iH] * db], pair=f"{m['h']}–{m['a']}"))
R.sort(key=lambda r: r["d"]); log("righe", len(R), "derby", sum(r["db"] for r in R))
def nb_cdf(mu, a, k):
    n = 1 / a; kk = np.arange(k + 1); q = n / (n + mu)
    return float(np.exp(gammaln(kk + n) - gammaln(n) - gammaln(kk + 1) + n * np.log(q) + kk * np.log1p(-q)).sum())
def wf(key):
    mon = sorted({r["d"][:7] for r in R}); out = {}
    for mo in mon:
        if mo < "2023-07": continue
        tr = [r for r in R if r["d"][:7] < mo]
        b, a = CM.fit([dict(x=r[key], lm=r["lm"], T=r["T"]) for r in tr])
        for i, r in enumerate(R):
            if r["d"][:7] == mo:
                out[id(r)] = (math.exp(math.log(r["lm"]) + b[0] + sum(w * v for w, v in zip(b[1:], r[key]))), a)
    return out, b
P = {k: wf(k) for k in ("base", "HD", "HD4")}
for k in ("HD", "HD4"): log(k, "pesi ultimi", [round(v, 3) for v in P[k][1]])
season = lambda d: int(d[:4]) if d[5:7] >= "07" else int(d[:4]) - 1
for k in ("HD", "HD4"):
    for L in (4.5, 5.5):
        rows = []
        for r in R:
            o, n = P["base"][0].get(id(r)), P[k][0].get(id(r))
            if not o or not n: continue
            uo, un = nb_cdf(o[0], o[1], int(L)), nb_cdf(n[0], n[1], int(L))
            rows.append(dict(date=r["d"], lg=r["lg"], season=season(r["d"]), y=0 if r["T"] > L else 2, p_old=np.array([1 - uo, 0, uo]), p_new=np.array([1 - un, 0, un])))
        log(H.riepilogo(f"Cartellini Over {L} · {k}", H.confronta(pd.DataFrame(rows))))
    for per, a_, z_ in (("verifica", "2024-07-01", "2025-06-30"), ("holdout", "2025-07-01", "2099")):
        dd = [r for r in R if r["db"] and a_ <= r["d"] <= z_ and id(r) in P[k][0]]
        if dd: log(f"  derby {per} n={len(dd)}: reali {np.mean([r['T'] for r in dd]):.2f} · base {np.mean([P['base'][0][id(r)][0] for r in dd]):.2f} · {k} {np.mean([P[k][0][id(r)][0] for r in dd]):.2f}")
for r in R:
    if "Boca" in r["pair"] and "River" in r["pair"] and id(r) in P["base"][0]:
        log(f"  {r['d']} {r['pair']}: reali {r['T']} · base {P['base'][0][id(r)][0]:.2f} · HD {P['HD'][0][id(r)][0]:.2f} · HD4 {P['HD4'][0][id(r)][0]:.2f}")

# 30/10/2026 (2): effetto della COPPIA appreso dai residui del modello completo (non solo nei derby): negli scontri precedenti fra le
# stesse due squadre, cartellini reali contro previsti dal modello di base (walk-forward, quindi con derby e arbitro già dentro),
# ristretti verso 1 con K partite fittizie; il peso lo stima il modello mese per mese. Se esistono coppie "calde" in modo stabile,
# il peso esce positivo e Boca–River si alza da sola; se è rumore, il peso va a zero.
base_pred = P["base"][0]
for K in (2, 4, 8):
    hist = collections.defaultdict(list)
    for r in R:
        key = frozenset(r["pair"].split("–"))
        H_ = hist[key]
        r[f"res{K}"] = r["base"] + [math.log((sum(t for t, _ in H_) + K * 5.0) / (sum(p for _, p in H_) + K * 5.0)) if H_ else 0.0]
        if id(r) in base_pred: H_.append((r["T"], base_pred[id(r)][0]))
    P[f"res{K}"] = wf(f"res{K}")
    log(f"res{K}", "peso della coppia (ultimo)", round(P[f"res{K}"][1][-1], 3))
    for L in (4.5, 5.5):
        rows = []
        for r in R:
            o, n = P["base"][0].get(id(r)), P[f"res{K}"][0].get(id(r))
            if not o or not n: continue
            uo, un = nb_cdf(o[0], o[1], int(L)), nb_cdf(n[0], n[1], int(L))
            rows.append(dict(date=r["d"], lg=r["lg"], season=season(r["d"]), y=0 if r["T"] > L else 2, p_old=np.array([1 - uo, 0, uo]), p_new=np.array([1 - un, 0, un])))
        log(H.riepilogo(f"Cartellini Over {L} · effetto coppia K={K}", H.confronta(pd.DataFrame(rows))))
    for r in R:
        if "Boca" in r["pair"] and "River" in r["pair"] and id(r) in P[f"res{K}"][0]:
            log(f"  {r['d']} {r['pair']}: reali {r['T']} · base {P['base'][0][id(r)][0]:.2f} · coppia K={K} {P[f'res{K}'][0][id(r)][0]:.2f}")
