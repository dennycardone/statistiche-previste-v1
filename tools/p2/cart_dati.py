"""Cartellini · studio sui soli dati (20/11/2026, Denny: "noi dobbiamo lavorare solo sui dati e non sui book … studia tutto").
Preparazione: modello dell'app (cards_model.py v3) rifatto walk-forward come in produzione (pesi stimati ogni mese con le sole
partite precedenti al mese, possesso nella ripartizione casa/ospite), su tutte le partite API-Football del ramo storico.
Per ogni partita: cartellini attesi totali, di casa e d'ospite, alpha, reali, più le caratteristiche pre-partita per le varianti.
Uscita: ricerca/cartellini/base.pkl"""
import os, sys, json, glob, math, collections, datetime
import numpy as np, pandas as pd
from scipy.special import gammaln
REPO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
RIC = os.path.join(REPO, "ricerca"); OUT = os.path.join(RIC, "cartellini"); os.makedirs(OUT, exist_ok=True)
sys.path.insert(0, REPO)
import cards_model as CM
log = lambda *a: print(*a, flush=True)
SX = {}
for f in glob.glob(os.path.join(RIC, "sx", "*.json")):
    for fid, r in json.load(open(f)).items():
        if r[3] and r[4] and len(r[3]) > 11 and len(r[4]) > 11: SX[fid] = (r[3][11], r[4][11])
M, FID = [], []
for f in glob.glob(os.path.join(RIC, "storico", "*_20*.json")):
    D = json.load(open(f)); lg = D.get("lega") or os.path.basename(f).split("_")[0]
    for fid, v in D["partite"].items():
        sh, sa = v[6], v[7]
        ok = bool(sh and sa and sh[4] is not None and sa[4] is not None)
        M.append(dict(lg=lg, d=v[0], h=v[1], a=v[2], ref=v[5], hc=(sh[4] + (sh[5] or 0)) if ok else None, ac=(sa[4] + (sa[5] or 0)) if ok else None,
                      hf=sh[3] if ok else None, af=sa[3] if ok else None, gh=v[3], ga=v[4])); FID.append(fid)
log("partite", len(M))
F = CM.features(M)
poss = {(m["lg"], m["d"], m["h"], m["a"]): SX[fid] for m, fid in zip(M, FID) if fid in SX and SX[fid][0] is not None and SX[fid][1] is not None}
PX = CM.possession_x(M, poss)
def fit_np(rows, lam=1e-2):   # stessa stima di cards_model.fit (IRLS con penalità, poi alpha a sezione aurea), in numpy per la velocità
    Xm = np.array([[1.0] + f['x'] for f in rows]); off = np.log([f['lm'] for f in rows]); y = np.array([f['T'] for f in rows], float)
    b = np.zeros(Xm.shape[1]); b[0] = math.log(y.mean() / np.exp(off).mean()); P = np.eye(Xm.shape[1]) * lam; P[0, 0] = 0
    for _ in range(30):
        eta = Xm @ b + off; mu = np.exp(eta); z = eta - off + (y - mu) / mu
        nb = np.linalg.solve(Xm.T @ (Xm * mu[:, None]) + P, Xm.T @ (mu * z))
        if np.max(np.abs(nb - b)) < 1e-8: b = nb; break
        b = nb
    mu = np.exp(Xm @ b + off); ly = gammaln(y + 1)
    def nll(a):
        n = 1 / a; return -np.mean(gammaln(y + n) - gammaln(n) - ly + n * np.log(n / (n + mu)) + y * np.log(mu / (n + mu)))
    lo, hi = 1e-4, 0.5; g = (math.sqrt(5) - 1) / 2; c1, c2 = hi - g * (hi - lo), lo + g * (hi - lo); f1, f2 = nll(c1), nll(c2)
    for _ in range(30):
        if f1 < f2: hi, c2, f2 = c2, c1, f1; c1 = hi - g * (hi - lo); f1 = nll(c1)
        else: lo, c1, f1 = c1, c2, f2; c2 = lo + g * (hi - lo); f2 = nll(c2)
    return [float(v) for v in b], float((lo + hi) / 2)
played = [f for f in F if f and f["played"]]
# controllo: la stima in numpy coincide con cards_model.fit
tr = [f for f in played if f["d"] < "2024-01-01"][:4000]; b1, a1 = CM.fit(tr); b2, a2 = fit_np(tr)
log("controllo fit: max diff pesi", max(abs(x - y) for x, y in zip(b1, b2)), "alpha", a1, a2)
months = sorted({f["d"][:7] for f in played if f["d"] >= "2023-01"}); W = {}
for mo in months:
    tr = [f for f in played if f["d"] < mo + "-01"]
    if len(tr) >= 2000: W[mo] = fit_np(tr)
log("mesi stimati", len(W))
R = []
for m, f, px in zip(M, F, PX):
    if not f or not f["played"] or f["d"][:7] not in W: continue
    b, a = W[f["d"][:7]]; p = CM.predict(f, b)
    mh, ma = CM.split_possession(p, px) if px is not None else (p["mh"], p["ma"])
    R.append(dict(lg=f["lg"], d=f["d"][:10], h=m["h"], a=m["a"], ref=m["ref"], mu=p["mu"], mh=mh, ma=ma, alpha=a, yh=m["hc"], ya=m["ac"], T=f["T"],
                  lm=f["lm"], nmin=f["nmin"], derby=f["x"][CM.FEATS.index("DB")], gh=m["gh"], ga=m["ga"]))
B = pd.DataFrame(R).sort_values(["d", "lg", "h"]).reset_index(drop=True)
B.to_pickle(os.path.join(OUT, "base.pkl")); json.dump({k: v for k, v in W.items()}, open(os.path.join(OUT, "pesi_mensili.json"), "w"))
log("righe", len(B), B.d.min(), B.d.max())
