"""Fase 2 · la media gol del campionato si adatta abbastanza in fretta? (dalla fotografia: da luglio 2025 Over 2,5 dichiarato 50,3%,
uscito 52,8%; Over 1,5 74,6% contro 76,5%). Correzione: gol attesi × (media gol del campionato negli ultimi D giorni / ultimi 365)^β,
medie con le sole partite dei giorni precedenti, β stimato mese per mese sulle sole partite precedenti (Poisson sui gol per squadra).
Giudizio con l'harness su Over/Under 2,5 (esito binario) e 1X2 gol."""
import json, glob, sys, math, collections, datetime, numpy as np, pandas as pd
from scipy.stats import poisson
from scipy.optimize import minimize_scalar
sys.path.insert(0, "/home/claude/statistiche-previste-v1/tools"); import harness as H
B = []
for fn in glob.glob("/home/claude/research/p2/base/*.json"):
    lg = fn.split("/")[-1][:-5]
    for r in json.load(open(fn)):
        if r.get("g") and r["y"]["g"][0] is not None: r["lg"] = lg; B.append(r)
B.sort(key=lambda r: r["d"])
def feats(D):
    hist = collections.defaultdict(list); out = []
    for r in B:
        d0 = datetime.date.fromisoformat(r["d"]); L = hist[r["lg"]]
        g365 = [t for dd, t in L if 0 < (d0 - dd).days <= 365]; gD = [t for dd, t in L if 0 < (d0 - dd).days <= D]
        out.append(math.log((sum(gD) / len(gD)) / (sum(g365) / len(g365))) if len(gD) >= 30 and len(g365) >= 150 else 0.0)
        L.append((d0, r["y"]["g"][0] + r["y"]["g"][1]))
    return np.array(out)
def dc(lh, la, rho, N=10):
    M = np.outer(poisson.pmf(np.arange(N + 1), lh), poisson.pmf(np.arange(N + 1), la))
    if rho: M[0, 0] *= 1 - lh * la * rho; M[0, 1] *= 1 + lh * rho; M[1, 0] *= 1 + la * rho; M[1, 1] *= 1 - rho
    return M / M.sum()
lh = np.array([r["g"][0] for r in B]); la = np.array([r["g"][1] for r in B]); rho = np.array([r["g"][2] or 0 for r in B])
yh = np.array([r["y"]["g"][0] for r in B]); ya = np.array([r["y"]["g"][1] for r in B]); mon = np.array([r["d"][:7] for r in B])
tot = np.add.outer(np.arange(11), np.arange(11))
for D in (60, 120):
    x = feats(D); beta = np.zeros(len(B)); mons = sorted(set(mon))
    for mo in mons:
        tr = (mon < mo) & (x != 0)
        if tr.sum() < 5000: continue
        f = lambda b: -(poisson.logpmf(yh[tr], lh[tr] * np.exp(b * x[tr])).sum() + poisson.logpmf(ya[tr], la[tr] * np.exp(b * x[tr])).sum())
        b = minimize_scalar(f, bounds=(-1, 2), method="bounded").x; beta[mon == mo] = b
    rows = []
    for i, r in enumerate(B):
        if beta[i] == 0 and x[i] == 0: pass
        M0 = dc(lh[i], la[i], rho[i]); m = math.exp(beta[i] * x[i]); M1 = dc(lh[i] * m, la[i] * m, rho[i])
        o0, o1 = M0[tot > 2.5].sum(), M1[tot > 2.5].sum(); y = int(yh[i] + ya[i] > 2.5)
        rows.append(dict(date=r["d"], lg=r["lg"], season=r["se"], y=0 if y else 1, p_old=np.array([o0, 1 - o0, 0]), p_new=np.array([o1, 1 - o1, 0])))
    res = H.confronta(pd.DataFrame(rows))
    print(H.riepilogo(f"Over/Under 2,5 · media gol recente {D} giorni · β ultimo {beta[-1]:.2f}", res), flush=True)
