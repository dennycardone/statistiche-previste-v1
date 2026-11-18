"""Falli · audit e backtest (18/11/2026, Denny). Solo analisi: nessuna modifica all'app.
Ingressi: ricerca/falli/<lg>.json (falli_dump.js: falli attesi dell'app senza arbitro = M0 e con l'arbitro come in produzione, partite dal 2023,
soli dati precedenti) + ricerca/storico (API-Football: nomi API, arbitro, giornata) per arbitro, derby, classifica, forma.
Periodi: sviluppo (stima) fino al 30/6/2024, verifica 2024-25, holdout da luglio 2025 (mai usato per stimare o scegliere).
Uscita: ricerca/falli/audit.json + stampa delle tabelle."""
import os, sys, json, glob, math, collections, numpy as np, pandas as pd
from scipy.stats import nbinom
from scipy.optimize import minimize_scalar
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lab")); sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
from comune import load_storico, per, pois_fit, boot, EUROPA
import derby, apif_extra
REPO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."); R = {}
log = lambda *a: print(*a, flush=True)
# ---------------- dati
rows = []
for f in glob.glob(os.path.join(REPO, "ricerca", "falli", "*.json")):
    lg = os.path.basename(f)[:-5]
    if lg in ("audit",): continue
    for r in json.load(open(f)):
        d, h, a, hf, af, lhB, laB, lhR, laR, rt, rT, xff, xref, hg, ag = r
        if lhB is None or hg is None: continue
        rows.append(dict(lg=lg, d=d, h_app=h, a_app=a, yh=hf, ya=af, l0h=lhB, l0a=laB, lrh=lhR, lra=laR, r_tot=rt, r_team=rT, xff=xff, hg=hg, ag=ag))
J = pd.DataFrame(rows)
S = load_storico(); S = S[S.hf.notna() & S.af.notna()]
k = lambda df, a, b, c, e, f_, g: df.lg + "|" + df.d + "|" + df[a].astype(int).astype(str) + "-" + df[b].astype(int).astype(str) + "|" + df[c].astype(int).astype(str) + "-" + df[e].astype(int).astype(str)
S["k"] = k(S, "hg", "ag", "hf", "af", 0, 0); J["k"] = k(J, "hg", "ag", "yh", "ya", 0, 0)
S1 = S[~S.k.duplicated(keep=False)]; J = J[~J.k.duplicated(keep=False)]
J = J.merge(S1[["k", "fid", "dt", "h", "a", "ref", "rnd", "se"]], on="k", how="inner").sort_values(["d", "lg"]).reset_index(drop=True)
J["per"] = J.d.map(per); J["wk"] = (pd.to_datetime(J.d) - pd.Timestamp("1970-01-01")).dt.days // 7
J["yt"] = J.yh + J.ya
log("partite dell'app con falli dal 2023:", len(rows), "· unite all'archivio API:", len(J), J.per.value_counts().to_dict())
R["dati"] = {"app_dal_2023": len(rows), "unite": len(J), "per_periodo": J.per.value_counts().to_dict(), "con_arbitro": float(J.ref.notna().mean())}
# ---------------- metriche (Binomiale Negativa come l'app: r squadra 200, r totale 150)
KK = np.arange(0, 91)
def nbp(mu, r): return nbinom.pmf(KK[None, :], r, r / (r + np.asarray(mu)[:, None]))
def metrics(lh, la, rT=200.0, rt=150.0, sub=None):
    D = J if sub is None else J[sub]; lh = np.asarray(lh) if sub is None else np.asarray(lh)[sub]; la = np.asarray(la) if sub is None else np.asarray(la)[sub]
    yh, ya = D.yh.values.astype(int), D.ya.values.astype(int); yt = yh + ya; tot = lh + la
    o = pd.DataFrame(index=D.index)
    lp = lambda y, mu, r: nbinom.logpmf(y, r, r / (r + mu))
    o["ll_team"] = -(lp(yh, lh, rT) + lp(ya, la, rT)); o["ll_tot"] = -lp(yt, tot, rt)
    Ph, Pa = nbp(lh, rT), nbp(la, rT); cA = np.cumsum(Pa, 1)
    p1 = (Ph[:, 1:] * cA[:, :-1]).sum(1); px = (Ph * Pa).sum(1); p2 = np.clip(1 - p1 - px, 1e-12, 1)
    o1, ox = (yh > ya).astype(float), (yh == ya).astype(float); o2 = 1 - o1 - ox
    o["ll_1x2"] = -np.log(np.clip(np.where(o1 == 1, p1, np.where(ox == 1, px, p2)), 1e-12, 1)); o["br_1x2"] = (p1 - o1) ** 2 + (px - ox) ** 2 + (p2 - o2) ** 2
    for j, off in enumerate((-3, 0, 3)):
        L = np.round(tot) + 0.5 + off; pov = 1 - nbinom.cdf(np.floor(L), rt, rt / (rt + tot)); oo = (yt > L).astype(float)
        o[f"br_ou{j}"] = (pov - oo) ** 2; o[f"ll_ou{j}"] = -np.log(np.clip(np.where(oo == 1, pov, 1 - pov), 1e-12, 1)); o[f"p_ou{j}"] = pov; o[f"o_ou{j}"] = oo
    o["ae_t"] = np.abs(yt - tot); o["se_t"] = (yt - tot) ** 2; o["ae_h"] = np.abs(yh - lh); o["ae_a"] = np.abs(ya - la)
    o["p1"], o["o1"], o["px"], o["ox"], o["tot"] = p1, o1, px, ox, tot
    return o
def ece(p, y, b=10):
    q = np.clip((p * b).astype(int), 0, b - 1); return float(sum(abs(p[q == i].mean() - y[q == i].mean()) * (q == i).sum() for i in range(b) if (q == i).any()) / len(p))
def summary(X):
    out = {}
    for p in ("scelta", "verifica", "holdout"):
        m = (J.per == p).values; x = X[m]
        out[p] = dict(n=int(m.sum()), mae_tot=round(x.ae_t.mean(), 4), rmse_tot=round(math.sqrt(x.se_t.mean()), 4), mae_squadra=round((x.ae_h.mean() + x.ae_a.mean()) / 2, 4),
                      ll_squadra=round(x.ll_team.mean(), 5), ll_tot=round(x.ll_tot.mean(), 5), ll_1x2=round(x.ll_1x2.mean(), 5), br_1x2=round(x.br_1x2.mean(), 5),
                      br_ou=round(x.br_ou1.mean(), 5), ll_ou=round(x.ll_ou1.mean(), 5), ece_ou=round(ece(x.p_ou1.values, x.o_ou1.values) * 100, 2),
                      ece_1=round(ece(x.p1.values, x.o1.values) * 100, 2), ece_x=round(ece(x.px.values, x.ox.values) * 100, 2),
                      atteso_reale=f"{x.tot.mean():.2f}/{J.yt.values[m].mean():.2f}", over_lin=f"{x.p_ou1.mean()*100:.1f}/{x.o_ou1.mean()*100:.1f}")
    return out
def cmp(XA, XB, key):
    out = {}
    for p in ("scelta", "verifica", "holdout"):
        m = (J.per == p).values; d = (XB[key] - XA[key]).values[m]
        mu, lo, hi = boot(d, J.wk.values[m]); _, lo95, hi95 = boot(d, J.wk.values[m], q=(2.5, 97.5))
        lg = pd.Series(d).groupby(J.lg.values[m]).mean()
        out[p] = dict(diff=round(mu, 6), lo95=round(lo95, 6), hi95=round(hi95, 6), lo99=round(lo, 6), hi99=round(hi, 6), pct=round(100 * mu / XA[key].values[m].mean(), 4), camp=f"{int((lg < 0).sum())}/{len(lg)}")
    return out
def passes(c):   # regola dell'harness (95%) e del laboratorio (99%)
    v, h = c["verifica"], c["holdout"]; a, b = map(int, v["camp"].split("/"))
    return dict(harness=bool(v["hi95"] < 0 and h["diff"] < 0 and a > b / 2), lab99=bool(v["hi99"] < 0 and h["diff"] < 0 and a > b / 2))
sc = (J.per == "scelta").values
def fit_offset(Xh, Xa, base_h=None, base_a=None):
    bh = J.l0h.values if base_h is None else base_h; ba = J.l0a.values if base_a is None else base_a
    one = np.ones((len(J), 1)); XH = np.hstack([one, Xh]); XA = np.hstack([one, Xa])
    b, se = pois_fit(np.vstack([XH[sc], XA[sc]]), np.r_[J.yh.values[sc], J.ya.values[sc]], np.log(np.r_[bh[sc], ba[sc]]))
    return b, se, bh * np.exp(XH @ b), ba * np.exp(XA @ b)
# ---------------- 1. modello attuale e riferimenti
X0 = metrics(J.l0h, J.l0a); MODELS = {"M0 app (senza arbitro)": (J.l0h.values, J.l0a.values)}
z = np.zeros((len(J), 0)); b0, _, lch, lca = fit_offset(z, z); MODELS["M0 + costante (riferimento alla pari)"] = (lch, lca)
# media del campionato per sede (365 giorni, archivio API, solo partite precedenti) e medie squadra ristrette
Sl = S[~S.lg.isin(EUROPA)].sort_values("dt")
LM = {}; TA = {}
for lg, g in Sl.groupby("lg"):
    dd = pd.to_datetime(g.d).values.astype("datetime64[D]").astype(int); hf = g.hf.values; af = g.af.values
    ch, ca = np.r_[0, np.cumsum(hf)], np.r_[0, np.cumsum(af)]
    lo = np.searchsorted(dd, dd - 365, "left"); hi = np.searchsorted(dd, dd, "left"); n = hi - lo
    for fid, nn, a_, b_ in zip(g.fid.values, n, (ch[hi] - ch[lo]), (ca[hi] - ca[lo])): LM[fid] = (a_ / nn, b_ / nn) if nn >= 50 else (np.nan, np.nan)
J["muH"] = [LM.get(f, (np.nan, np.nan))[0] for f in J.fid]; J["muA"] = [LM.get(f, (np.nan, np.nan))[1] for f in J.fid]
okm = J.muH.notna().values
J.loc[~okm, "muH"] = J.l0h[~okm]; J.loc[~okm, "muA"] = J.l0a[~okm]
MODELS["Media del campionato (365 gg, per sede)"] = (J.muH.values, J.muA.values)
# medie squadra (falli fatti e subiti, media mobile peso 0,95 a partita, ristrette verso la lega con K partite) — riferimento semplice
team = collections.defaultdict(lambda: [0.0, 0.0, 0.0]); TS = {}
for r in Sl.itertuples():
    TS[r.fid] = (tuple(team[(r.lg, r.h)]), tuple(team[(r.lg, r.a)]))
    for t, of, pf in (((r.lg, r.h), r.hf, r.af), ((r.lg, r.a), r.af, r.hf)):
        x = team[t]; x[0] = x[0] * 0.95 + of; x[1] = x[1] * 0.95 + pf; x[2] = x[2] * 0.95 + 1
def simple(Kp):
    lh, la = np.empty(len(J)), np.empty(len(J))
    for i, (fid, mh, ma) in enumerate(zip(J.fid, J.muH, J.muA)):
        th, ta = TS.get(fid, ((0, 0, 0), (0, 0, 0))); m = (mh + ma) / 2
        rc = lambda x: (x[0] + Kp * m) / (x[2] + Kp) / m; rd = lambda x: (x[1] + Kp * m) / (x[2] + Kp) / m
        lh[i] = mh * rc(th) * rd(ta); la[i] = ma * rc(ta) * rd(th)
    return lh, la
best = min(((metrics(*simple(Kp), sub=sc).ll_team.mean(), Kp) for Kp in (3, 5, 10, 20)))
MODELS[f"Medie squadra ristrette (K {best[1]})"] = simple(best[1])
# ---------------- 2. distribuzione
res = (J.yh - J.l0h); resa = (J.ya - J.l0a)
disp = lambda y, l: float(((y - l) ** 2).sum() / l.sum())
def r_ml(y, l):
    f = lambda lr: -nbinom.logpmf(y, math.exp(lr), math.exp(lr) / (math.exp(lr) + l)).sum()
    return math.exp(minimize_scalar(f, bounds=(math.log(5), math.log(5000)), method="bounded").x)
R["distribuzione"] = {"grezza (tutti i campionati)": {"media_tot": round(J.yt.mean(), 2), "varianza_tot": round(J.yt.var(), 2), "asimmetria": round(J.yt.skew(), 2), "corr_casa_ospite": round(np.corrcoef(J.yh, J.ya)[0, 1], 3)},
    "condizionata al modello (sviluppo)": {"dispersione_squadra": round(disp(np.r_[J.yh[sc], J.ya[sc]], np.r_[J.l0h[sc], J.l0a[sc]]), 3),
        "dispersione_totale": round(disp(J.yt[sc], (J.l0h + J.l0a)[sc]), 3), "r_squadra_ML": round(r_ml(np.r_[J.yh[sc], J.ya[sc]], np.r_[J.l0h[sc], J.l0a[sc]]), 1),
        "r_totale_ML": round(r_ml(J.yt.values[sc], (J.l0h + J.l0a).values[sc]), 1), "corr_residui_casa_ospite": round(np.corrcoef(res[sc], resa[sc])[0, 1], 3)},
    "per campionato (tutti i periodi)": {lg: {"disp_squadra": round(disp(np.r_[g.yh, g.ya], np.r_[g.l0h, g.l0a]), 2), "corr_residui": round(np.corrcoef(g.yh - g.l0h, g.ya - g.l0a)[0, 1], 3)} for lg, g in J.groupby("lg")}}
log("distribuzione:", json.dumps({k: v for k, v in R["distribuzione"].items() if k != "per campionato (tutti i periodi)"}, ensure_ascii=False))
# ---------------- 3. arbitro (solo partite precedenti, stesso campionato, nome normalizzato come l'app)
J["rk"] = J.ref.map(lambda x: apif_extra.refkey(x) if isinstance(x, str) else None)
def ref_factor(K, cap=None, last=None):
    acc = collections.defaultdict(list); f = np.ones(len(J)); n = np.zeros(len(J))
    mbar = (J.l0h + J.l0a).groupby(J.lg).transform("mean").values
    for day, idx in J.groupby("d").groups.items():
        idx = np.asarray(idx)
        for i in idx:
            rk = J.rk.values[i]
            if not rk: continue
            H = acc.get((J.lg.values[i], rk))
            if H:
                Hs = H[-last:] if last else H; Y = sum(x[0] for x in Hs); L = sum(x[1] for x in Hs)
                f[i] = (Y + K * mbar[i]) / (L + K * mbar[i]); n[i] = len(Hs)
        for i in idx:
            rk = J.rk.values[i]
            if rk: acc[(J.lg.values[i], rk)].append((J.yt.values[i], J.l0h.values[i] + J.l0a.values[i]))
    if cap: f = np.minimum(f, cap)
    return f, n
grid = {}
for Kr in (5, 10, 20, 40, 80):
    for cap in (None, 1.04):
        fR, nR = ref_factor(Kr, cap); grid[(Kr, cap)] = fR
        v = metrics(J.l0h * fR, J.l0a * fR, sub=sc).ll_team.mean(); log(f"arbitro K {Kr} tetto {cap}: sviluppo ll {v:.5f}")
bestR = min(grid, key=lambda kk: metrics(J.l0h * grid[kk], J.l0a * grid[kk], sub=sc).ll_team.mean())
fR = grid[bestR]; _, nR = ref_factor(bestR[0])
MODELS[f"M0 × arbitro (residui del modello, K {bestR[0]}, tetto {bestR[1]})"] = (J.l0h.values * fR, J.l0a.values * fR)
# arbitro come in produzione: fattore di apif_extra (medie mobili semplici, K 20) con tetto +4%, ricostruito per tutti i periodi
app_ff = {}
for lg, g in S[~S.lg.isin(EUROPA)].sort_values("dt").groupby("lg"):
    out = apif_extra.compute([dict(d=r.d, h=r.h, a=r.a, ref=(r.ref if isinstance(r.ref, str) else None), hc=(r.hy if r.hy == r.hy else None), ac=(r.ay if r.ay == r.ay else None), hf=r.hf, af=r.af) for r in g.itertuples()])
    for fid, o in zip(g.fid.values, out): app_ff[fid] = o["ff"] or 1.0
fA = np.array([min(app_ff.get(f, 1.0), 1.04) for f in J.fid]); fA0 = np.array([app_ff.get(f, 1.0) for f in J.fid])
MODELS["M0 × arbitro come in app (K 20, tetto +4%)"] = (J.l0h.values * fA, J.l0a.values * fA)
MODELS["M0 × arbitro come in app senza tetto"] = (J.l0h.values * fA0, J.l0a.values * fA0)
# stabilità dell'arbitro: rapporto reale/atteso in metà pari e dispari delle sue partite, per numero di partite
G = J[J.rk.notna()].assign(ry=J.yt, rl=J.l0h + J.l0a).groupby(["lg", "rk"])
stab = []
for (lg, rk), g in G:
    if len(g) < 10: continue
    e, o = g.iloc[::2], g.iloc[1::2]; stab.append((len(g), e.ry.sum() / e.rl.sum(), o.ry.sum() / o.rl.sum()))
st = np.array(stab)
def rel(lo, hi): m = (st[:, 0] >= lo) & (st[:, 0] < hi); return (int(m.sum()), round(float(np.corrcoef(st[m, 1], st[m, 2])[0, 1]), 3)) if m.sum() > 10 else None
R["arbitro"] = {"griglia (sviluppo, ll squadra)": {f"K{a}_tetto{b}": round(metrics(J.l0h * v, J.l0a * v, sub=sc).ll_team.mean(), 6) for (a, b), v in grid.items()},
    "scelto": list(bestR), "sd del fattore (scelto)": round(float(np.std(fR)), 4), "sd fattore app": round(float(np.std(fA0)), 4),
    "affidabilità metà pari/dispari (arbitri, correlazione) per partite 10-20 / 20-40 / 40+": [rel(10, 20), rel(20, 40), rel(40, 999)],
    "arbitri con almeno 10 partite": int(len(st)), "sd del rapporto reale/atteso per arbitro (40+ partite)": round(float(st[st[:, 0] >= 40, 1:].mean(1).std()), 4)}
# ---------------- 4. forma recente, casa/fuori, derby, classifica (aggiunti a M0 con l'offset, coefficienti stimati nello sviluppo)
hist = collections.defaultdict(list)
for r in Sl.itertuples(): hist[(r.lg, r.h)].append((r.d, r.hf, r.af, 1)); hist[(r.lg, r.a)].append((r.d, r.af, r.hf, 0))
def form(N, Kf):
    fh, fa, ch, ca = (np.zeros(len(J)) for _ in range(4))
    idx = {}
    for t, L in hist.items(): idx[t] = ([x[0] for x in L], L)
    for i, r in enumerate(J.itertuples()):
        m = (r.muH + r.muA) / 2
        for side, t, opp in ((0, r.h, r.a), (1, r.a, r.h)):
            ds, L = idx.get((r.lg, t), ([], [])); j = np.searchsorted(ds, r.d, "left"); Z = L[max(0, j - N):j]
            dO, LO = idx.get((r.lg, opp), ([], [])); jo = np.searchsorted(dO, r.d, "left"); ZO = LO[max(0, jo - N):jo]
            f_ = math.log((sum(x[1] for x in Z) + Kf * m) / (len(Z) + Kf) / m); c_ = math.log((sum(x[2] for x in ZO) + Kf * m) / (len(ZO) + Kf) / m)
            if side == 0: fh[i], ca[i] = f_, c_
            else: fa[i], ch[i] = f_, c_
    return fh, fa, ch, ca
EXTRA = {}
for N in (5, 10):
    bestF = None
    for Kf in (2, 5, 10, 20):
        fh, fa, ch, ca = form(N, Kf); b, se, lh, la = fit_offset(np.c_[fh, ca], np.c_[fa, ch]); v = metrics(lh, la, sub=sc).ll_team.mean()
        if bestF is None or v < bestF[0]: bestF = (v, Kf, b, se, lh, la, (fh, fa, ch, ca))
    _, Kf, b, se, lh, la, FF = bestF; MODELS[f"M0 + forma ultime {N} (K {Kf})"] = (lh, la); EXTRA[f"forma{N}"] = dict(K=Kf, coef=[round(x, 4) for x in b], se=[round(x, 4) for x in se]); EXTRA[f"_F{N}"] = FF
# casa/fuori: falli fatti dalla squadra nella stessa sede rispetto a tutti (ristretto), ultime 20 partite di quella sede
def venue(Kv=10, N=20):
    vh, va = np.zeros(len(J)), np.zeros(len(J))
    for i, r in enumerate(J.itertuples()):
        for side, t in ((0, r.h), (1, r.a)):
            L = [x for x in hist.get((r.lg, t), []) if x[0] < r.d][-2 * N:]
            if not L: continue
            S_ = [x for x in L if x[3] == (1 if side == 0 else 0)][-N:]; allm = sum(x[1] for x in L) / len(L)
            v = math.log((sum(x[1] for x in S_) + Kv * allm) / (len(S_) + Kv) / allm) if allm > 0 else 0
            if side == 0: vh[i] = v
            else: va[i] = v
    return vh, va
vh, va = venue(); b, se, lh, la = fit_offset(vh[:, None], va[:, None]); MODELS["M0 + casa/fuori della squadra"] = (lh, la); EXTRA["casa_fuori"] = dict(coef=[round(x, 4) for x in b], se=[round(x, 4) for x in se])
db = np.array([1.0 if derby.is_derby(lg, h, a) else 0.0 for lg, h, a in zip(J.lg, J.h, J.a)])
b, se, lh, la = fit_offset(db[:, None], db[:, None]); MODELS["M0 + derby"] = (lh, la); EXTRA["derby"] = dict(coef=[round(x, 4) for x in b], se=[round(x, 4) for x in se], n=int(db.sum()))
lfR = np.log(fR); b, se, lh, la = fit_offset(lfR[:, None], lfR[:, None]); MODELS["M0 + arbitro con peso stimato"] = (lh, la); EXTRA["arbitro_peso"] = dict(coef=[round(x, 4) for x in b], se=[round(x, 4) for x in se])
# forza relativa (gol attesi) e differenza di falli tra le squadre: dal dump gol non disponibile qui → forza dall'Elo implicito: non usata (vedi laboratorio F2)
# ---------------- 5. confronto
XS = {nm: metrics(*v) for nm, v in MODELS.items()}
XC = XS["M0 + costante (riferimento alla pari)"]
R["modelli"] = {}
for nm, X in XS.items():
    c = {key: cmp(XC, X, key) for key in ("ll_team", "ll_tot", "ll_1x2", "br_1x2", "br_ou1", "ll_ou1", "se_t", "ae_t")}
    c0 = {key: cmp(X0, X, key) for key in ("ll_team", "ll_1x2", "br_ou1")}
    R["modelli"][nm] = {"riepilogo": summary(X), "contro_riferimento": c, "contro_M0": c0, "regola_ll_squadra": passes(c["ll_team"]), "regola_1x2": passes(c["ll_1x2"])}
    v = c["ll_team"]["verifica"]; h = c["ll_team"]["holdout"]
    log(f"{nm[:52]:52} ll sq. ver {v['diff']:+.5f} [{v['lo95']:+.5f},{v['hi95']:+.5f}] {v['camp']} · hol {h['diff']:+.5f} {h['camp']} · 1X2 ver {c['ll_1x2']['verifica']['diff']:+.5f} hol {c['ll_1x2']['holdout']['diff']:+.5f} · {passes(c['ll_team'])}")
R["coefficienti_extra"] = {k: v for k, v in EXTRA.items() if not k.startswith("_")}
json.dump(R, open(os.path.join(REPO, "ricerca", "falli", "audit.json"), "w"), indent=1, ensure_ascii=False, default=float)
pd.to_pickle({"J": J, "MODELS": MODELS, "fR": fR, "fA": fA, "db": db, "F10": EXTRA.get("_F10"), "F5": EXTRA.get("_F5"), "vh": vh, "va": va}, os.path.join(REPO, "ricerca", "falli", "audit.pkl"))
log(json.dumps(R["arbitro"], ensure_ascii=False)); log(json.dumps(R["coefficienti_extra"], ensure_ascii=False))
