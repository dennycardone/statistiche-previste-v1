"""Riallineamento del LIVELLO (10/11/2026, punto 5 dell'audit): negli ultimi mesi gli Over di gol e tiri escono più del dichiarato perché il
livello medio del modello si adegua tardi. Prova walk-forward: atteso × f, con f = reale / atteso delle partite dei W giorni precedenti
(globale, oppure per campionato ritirato verso il globale). Legge calib_full_*.json (attesi dell'app con i soli dati precedenti + reali).
Confronto alla pari: Over/Under con la stessa distribuzione (Poisson per i gol, Binomiale Negativa con la r dell'app per le statistiche)
calcolati con l'atteso originale e con quello riallineato, sulle linee round(atteso) ± 0,5 e ± 1,5 (gol: 1,5 · 2,5 · 3,5).
La variante (W, globale/campionato) si sceglie nel periodo "scelta"; regola: verifica significativa (IC 95% a blocchi settimanali), holdout
nello stesso verso, più della metà dei campionati. Stampa SOLO numeri aggregati."""
import json, glob, math, collections, datetime, sys, traceback
import numpy as np
from scipy.stats import nbinom, poisson
sys.excepthook = lambda t, v, tb: print("::error title=Livello::" + " | ".join(traceback.format_exception(t, v, tb)).replace("\n", " ")[-1500:])
note = lambda t, m: print(f"::notice title=Livello · {t}::" + m.replace("%", "%25").replace("\n", " "))
X = []
for f in sorted(glob.glob("calib_full_*.json")): X += json.load(open(f))["X"]
per = lambda d: "scelta" if d <= "2024-06-30" else "verifica" if d <= "2025-06-30" else "holdout"
LAST120 = (datetime.date.today() - datetime.timedelta(days=120)).isoformat()
D0 = datetime.date(2023, 1, 1); dn = lambda d: (datetime.date.fromisoformat(d) - D0).days
def pov(mu, r, L):
    k = math.floor(L)
    return float(poisson.sf(k, mu)) if not r else float(nbinom.sf(k, r, r / (r + mu)))
def boot(dl, wk, n=1500):
    G = collections.defaultdict(float); C = collections.Counter()
    for v, w in zip(dl, wk): G[w] += v; C[w] += 1
    ks = list(G); s = np.array([G[k] for k in ks]); c = np.array([C[k] for k in ks]); rng = np.random.default_rng(5)
    bs = [(lambda i: s[i].sum() / c[i].sum())(rng.integers(0, len(ks), len(ks))) for _ in range(n)]
    return s.sum() / c.sum(), np.percentile(bs, 2.5), np.percentile(bs, 97.5)
OUT = {}
for st, nm in (("g", "Gol"), ("Tiri", "Tiri"), ("Tiri in porta", "Tiri in porta"), ("Falli", "Falli"), ("Corner", "Corner (controllo)")):
    R = sorted([(dn(x[1]), x[1], x[0], x[4][st]) for x in X if st in x[4] and len(x[4][st]) >= 5 and x[4][st][2] >= 0 and x[4][st][3] >= 0], key=lambda r: r[0])
    if len(R) < 5000: continue
    days = np.array([r[0] for r in R]); ex = np.array([r[3][0] + r[3][1] for r in R]); re_ = np.array([r[3][2] + r[3][3] for r in R]); lgs = [r[2] for r in R]
    cE, cR = np.r_[0, np.cumsum(ex)], np.r_[0, np.cumsum(re_)]
    lgi = collections.defaultdict(list)
    for i, l in enumerate(lgs): lgi[l].append(i)
    lgc = {l: (np.array(ix), np.r_[0, np.cumsum(ex[ix])], np.r_[0, np.cumsum(re_[ix])]) for l, ix in ((l, np.array(v)) for l, v in lgi.items())}
    def factors(W, mode, K=40):
        f = np.ones(len(R)); mt = ex.mean()
        for i in range(len(R)):
            a, b = np.searchsorted(days, days[i] - W, "left"), np.searchsorted(days, days[i], "left")
            if b - a < 300: continue
            g = (cR[b] - cR[a]) / (cE[b] - cE[a])
            if mode == "globale": f[i] = g; continue
            ix, e_, r_ = lgc[lgs[i]]; a2, b2 = np.searchsorted(days[ix], days[i] - W, "left"), np.searchsorted(days[ix], days[i], "left")
            f[i] = (r_[b2] - r_[a2] + K * mt * g) / (e_[b2] - e_[a2] + K * mt)
        return f
    def evalv(f):
        rows = []
        for i, (dd, d, lg, v) in enumerate(R):
            if f[i] == 1.0: continue
            mu = v[0] + v[1]; real = v[2] + v[3]; r = v[4] or None
            for L in ((1.5, 2.5, 3.5) if st == "g" else [round(mu) + o for o in (-1.5, -0.5, 0.5, 1.5)]):
                if L <= 0: continue
                p, q = pov(mu, r, L), pov(mu * f[i], r, L); y = real > L
                p, q = min(max(p, 1e-4), 1 - 1e-4), min(max(q, 1e-4), 1 - 1e-4)
                rows.append((d, lg, -math.log(q if y else 1 - q) + math.log(p if y else 1 - p), p, q, y))
        return rows
    best = None; VAR = {}
    for W in (60, 120, 240):
        for mode in ("globale", "campionato"):
            rows = evalv(factors(W, mode)); VAR[(W, mode)] = rows
            sc = [r[2] for r in rows if per(r[0]) == "scelta"]
            m = np.mean(sc) if sc else 0
            if best is None or m < best[0]: best = (m, W, mode)
    _, W, mode = best; rows = VAR[(W, mode)]; res = {}
    for pn in ("scelta", "verifica", "holdout", "120 giorni"):
        S = [r for r in rows if (r[0] >= LAST120 if pn == "120 giorni" else per(r[0]) == pn)]
        if len(S) < 500: continue
        m, lo, hi = boot([r[2] for r in S], [datetime.date.fromisoformat(r[0]).isocalendar()[:2] for r in S])
        res[pn] = (m, lo, hi, np.mean([r[5] for r in S]) - np.mean([r[3] for r in S]), np.mean([r[5] for r in S]) - np.mean([r[4] for r in S]), len(S))
    lg = collections.defaultdict(list)
    for r in rows:
        if per(r[0]) != "scelta": lg[r[1]].append(r[2])
    share = np.mean([np.mean(v) < 0 for v in lg.values() if len(v) >= 200])
    ok = "verifica" in res and "holdout" in res and res["verifica"][2] < 0 and res["holdout"][0] < 0 and share > 0.5
    OUT[st] = dict(W=W, mode=mode, ok=bool(ok))
    note(f"{nm} · {'PASSA' if ok else 'non passa'} · variante scelta: ultimi {W} giorni, {mode}",
         " ‖ ".join(f"{pn}: log-loss {v[0]:+.5f} [{v[1]:+.5f}, {v[2]:+.5f}] · scarto Over {100 * v[3]:+.1f} → {100 * v[4]:+.1f} ({v[5]})" for pn, v in res.items()) + f" ‖ campionati migliorati {100 * share:.0f}%"
         + " ‖ altre varianti in verifica: " + " · ".join(f"{w}g {md[:4]} {np.mean([r[2] for r in rw if per(r[0]) == 'verifica']):+.5f}" for (w, md), rw in VAR.items()))
    ff = factors(W, mode); note(f"{nm} · fattore", f"oggi (ultime 300 partite): mediana {np.median(ff[-300:]):.3f} · minimo-massimo {ff[-300:].min():.3f}-{ff[-300:].max():.3f}")
json.dump(OUT, open("livello_esito.json", "w"))
