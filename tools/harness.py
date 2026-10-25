"""Prevista 2.0 · harness di backtest unificato (25/10/2026).

Un solo protocollo per tutti i test, quelli fatti finora a mano con script diversi (corner, cartellini, derby, possesso, fuorigioco):
  1. previsioni calcolate SOLO con i dati dei giorni precedenti (le produce chi fa il test: app via node, oppure walk_forward() qui sotto);
  2. tre periodi fissi: "scelta" (fino al 30/6/2024: qui si scelgono variabili e parametri), "verifica" (luglio 2024 – giugno 2025),
     "holdout" (da luglio 2025, si guarda solo alla fine);
  3. metriche: log-loss e Brier (1X2 o Over/Under), calibrazione per fasce del lato favorito;
  4. confronto con il modello attuale partita per partita: differenza media con intervallo al 95% da bootstrap a blocchi per settimana
     (le partite della stessa giornata non sono indipendenti), quota di campionati migliorati, segno per stagione;
  5. regola di adozione (la stessa usata da Denny dal 5/10): migliora in modo significativo nella verifica, nello stesso verso
     nell'holdout e nella maggior parte dei campionati; altrimenti non si tocca nulla.

Strumenti per i modelli di conteggio dell'app: pmf Binomiale Negativa, 1X2 "chi ne fa di più" con la copula gaussiana come
headToHeadProb dell'app, correzione moltiplicativa e^(b·x) stimata mese per mese sulle sole partite precedenti."""
import math, json, numpy as np, pandas as pd
from scipy.special import gammaln, ndtri, ndtr
from scipy.optimize import minimize

PERIODI = {"scelta": ("2000-01-01", "2024-06-30"), "verifica": ("2024-07-01", "2025-06-30"), "holdout": ("2025-07-01", "2100-01-01")}

# ---------------------------------------------------------------- distribuzioni (come l'app)
def nb_pmf(mu, r, K):
    k = np.arange(K + 1)
    if mu <= 0: p = np.zeros(K + 1); p[0] = 1; return p
    if r is None or not np.isfinite(r) or r <= 0:
        return np.exp(-mu + k * np.log(mu) - gammaln(k + 1))
    q = r / (r + mu)
    return np.exp(gammaln(k + r) - gammaln(r) - gammaln(k + 1) + r * np.log(q) + k * np.log1p(-q))


def _bvn_grid(zh, za, rho):
    """C(F(x), G(y)) su tutta la griglia, copula gaussiana (Drezner-Wesolowsky, 12 punti di Gauss come l'app)."""
    Fh, Fa = ndtr(zh), ndtr(za)
    if rho == 0: return np.outer(Fh, Fa)
    # stessi 6 nodi e pesi dell'app (BVN_X, BVN_W), ognuno usato come 1 − x e 1 + x
    BX = np.array([0.9815606342467192, 0.9041172563704749, 0.7699026741943047, 0.5873179542866175, 0.3678314989981802, 0.1252334085114689])
    BW = np.array([0.04717533638651183, 0.1069393259953184, 0.1600783285433462, 0.2031674267230659, 0.2334925365383548, 0.2491470458134028])
    asr = math.asin(rho) / 2
    xs = np.concatenate([1 - BX, 1 + BX]); ws = np.concatenate([BW, BW]); sn = np.sin(asr * xs); iv = 1 / (1 - sn * sn)
    H, Kk = np.meshgrid(zh, za, indexing="ij")
    fin = np.isfinite(H) & np.isfinite(Kk)
    Hf, Kf = np.where(fin, H, 0), np.where(fin, Kk, 0)
    hk, hs = Hf * Kf, (Hf * Hf + Kf * Kf) / 2
    t = np.zeros_like(hk)
    for s_, w_, i_ in zip(sn, ws, iv): t += w_ * np.exp((s_ * hk - hs) * i_)
    C = t * asr / (2 * math.pi) + np.outer(Fh, Fa)
    C = np.where(np.isneginf(H) | np.isneginf(Kk), 0, C)
    C = np.where(np.isposinf(H) & np.isfinite(Kk), Fa[None, :] * np.ones_like(C), C)
    C = np.where(np.isposinf(Kk) & np.isfinite(H), Fh[:, None] * np.ones_like(C), C)
    C = np.where(np.isposinf(H) & np.isposinf(Kk), 1, C)
    return C

def h2h(lh, la, r=None, rTeam=None, cop=0.0):
    """P(casa ne fa di più), P(pari), P(ospite ne fa di più): come headToHeadProb dell'app."""
    m = lh + la; K = max(40, int(math.ceil(m * 3)))
    if not m > 0: return np.array([0.0, 1.0, 0.0])
    rt = r if (r is not None and np.isfinite(r) and r > 0) else None
    if rTeam is not None and rTeam > 0 and np.isfinite(rTeam): ph, pa = nb_pmf(lh, rTeam, K), nb_pmf(la, rTeam, K)
    elif rTeam is not None and (rTeam == -1 or rTeam == float("inf")): ph, pa = nb_pmf(lh, None, K), nb_pmf(la, None, K)
    else: ph, pa = nb_pmf(lh, rt * lh / m if rt else None, K), nb_pmf(la, rt * la / m if rt else None, K)
    if cop:
        cz = lambda p: np.where(np.cumsum(p) >= 1 - 1e-13, np.inf, np.where(np.cumsum(p) < 1e-13, -np.inf, ndtri(np.clip(np.cumsum(p), 1e-300, 1 - 1e-16))))
        C = _bvn_grid(cz(ph), cz(pa), cop)
        C = np.pad(C, ((1, 0), (1, 0)))
        P = np.maximum(0, C[1:, 1:] - C[:-1, 1:] - C[1:, :-1] + C[:-1, :-1]); tot = P.sum()
        home = np.tril(P, -1).sum() / tot; draw = np.trace(P) / tot
        return np.array([home, draw, max(0.0, 1 - home - draw)])
    J = np.outer(ph, pa); home = np.tril(J, -1).sum(); draw = np.trace(J)
    s = home + draw + np.triu(J, 1).sum()
    return np.array([home / s, draw / s, 1 - (home + draw) / s])

# ---------------------------------------------------------------- correzione walk-forward e^(b·x) sui valori attesi
def nb_team_nll(b, X, y, mu0, r):
    mu = mu0 * np.exp(np.clip(X @ b, -3, 3))
    if r is None or not np.isfinite(r): return -(y * np.log(mu) - mu - gammaln(y + 1)).sum() + 1e-3 * (b @ b)
    return -(gammaln(y + r) - gammaln(r) - gammaln(y + 1) + r * np.log(r / (r + mu)) + y * np.log(mu / (r + mu))).sum() + 1e-3 * (b @ b)

def walk_forward(T, feats, r=None, min_train=3000, step="M"):
    """T: una riga per squadra e partita con colonne date, mu0 (valore atteso dell'app), y (valore reale) e le variabili feats.
    Restituisce mu corretto per ogni riga, con i pesi stimati sulle sole righe dei mesi precedenti (None finché non bastano)."""
    T = T.sort_values("date").copy(); T["mu"] = np.nan; T["per"] = pd.to_datetime(T.date).dt.to_period(step)
    coefs = {}
    for per in sorted(T.per.unique()):
        tr = T[(T.per < per) & T.y.notna() & T.mu0.notna()]
        if len(tr) < min_train: continue
        X, y, m0 = tr[feats].fillna(0).values, tr.y.values.astype(float), tr.mu0.values
        b = minimize(nb_team_nll, np.zeros(len(feats)), args=(X, y, m0, r), method="L-BFGS-B").x
        coefs[str(per)] = b
        idx = T.per == per
        T.loc[idx, "mu"] = T.loc[idx, "mu0"] * np.exp(np.clip(T.loc[idx, feats].fillna(0).values @ b, -3, 3))
    return T, coefs

# ---------------------------------------------------------------- valutazione
def logloss(P, y): return -np.log(np.clip(P[np.arange(len(y)), y], 1e-9, 1))
def brier(P, y): Y = np.zeros_like(P); Y[np.arange(len(y)), y] = 1; return ((P - Y) ** 2).sum(1)

def _boot(diff, week, B=2000, seed=7):
    rng = np.random.default_rng(seed); W = pd.Series(diff).groupby(week).agg(["sum", "count"]); s, c = W["sum"].values, W["count"].values
    if len(s) < 5: return (np.nan, np.nan)
    idx = rng.integers(0, len(s), (B, len(s))); m = s[idx].sum(1) / c[idx].sum(1)
    return tuple(np.percentile(m, [2.5, 97.5]))

def confronta(df, p_old="p_old", p_new="p_new", y="y"):
    """df: date, lg, season, y (0 casa, 1 pari, 2 ospite) e due colonne con le probabilità [p1, pX, p2] (vecchio e nuovo modello).
    Restituisce un dict per periodo con n, log-loss e Brier di entrambi, differenza con IC 95%, quota di campionati migliorati,
    differenza per stagione, calibrazione del lato favorito, e la decisione."""
    out = {}
    for name, (a, b) in PERIODI.items():
        d = df[(df.date >= a) & (df.date <= b)]
        d = d[d[p_old].notna() & d[p_new].notna()]
        if not len(d): continue
        Po, Pn, yy = np.vstack(d[p_old].values), np.vstack(d[p_new].values), d[y].values.astype(int)
        lo, ln_ = logloss(Po, yy), logloss(Pn, yy); diff = ln_ - lo
        wk = pd.to_datetime(d.date).dt.strftime("%G-%V").values
        ci = _boot(diff, wk)
        lg = pd.Series(diff).groupby(d.lg.values).mean()
        se = pd.Series(diff).groupby(d.season.values).mean().round(4).to_dict()
        fav = Pn[:, [0, 2]].max(1); hit = np.where(Pn[:, 0] >= Pn[:, 2], yy == 0, yy == 2)
        cal = {}
        for lo_ in np.arange(0.4, 0.95, 0.05):
            m = (fav >= lo_) & (fav < lo_ + 0.05)
            if m.sum() >= 30: cal[f"{lo_:.2f}"] = [int(m.sum()), round(float(hit[m].mean()), 3), round(float(fav[m].mean()), 3)]
        out[name] = dict(n=int(len(d)), ll_old=round(float(lo.mean()), 5), ll_new=round(float(ln_.mean()), 5), diff=round(float(diff.mean()), 5),
                         ci95=[round(float(ci[0]), 5), round(float(ci[1]), 5)], brier_old=round(float(brier(Po, yy).mean()), 5), brier_new=round(float(brier(Pn, yy).mean()), 5),
                         campionati_migliorati=f"{int((lg < 0).sum())}/{len(lg)}", stagioni=se, calibrazione=cal)
    v, h = out.get("verifica"), out.get("holdout")
    ok = bool(v and h and v["ci95"][1] < 0 and h["diff"] < 0 and int(v["campionati_migliorati"].split("/")[0]) > int(v["campionati_migliorati"].split("/")[1]) / 2)
    out["decisione"] = "ADOTTARE (significativo nella verifica, stesso verso nell'holdout, maggioranza dei campionati)" if ok else "NON ADOTTARE (non supera la regola)"
    return out

def riepilogo(nome, res):
    r = [f"== {nome} · {res['decisione']}"]
    for k in PERIODI:
        x = res.get(k)
        if x: r.append(f"  {k:9s} n={x['n']:6d} log-loss {x['ll_old']:.4f} → {x['ll_new']:.4f} (diff {x['diff']:+.4f}, IC95 {x['ci95'][0]:+.4f} / {x['ci95'][1]:+.4f}) · campionati migliorati {x['campionati_migliorati']} · stagioni {x['stagioni']}")
    return "\n".join(r)
