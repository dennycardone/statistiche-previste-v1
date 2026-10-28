"""Prevista 2.0 · cartellini del 1° tempo con arbitro e propensione di 1° tempo delle squadre (28/10/2026, punto 4 di Denny).
Dati: ramo eventi (cartellini con il minuto, API-Football, dal 2022) + arbitro dal ramo storico (stesso id partita).
Gialli del 1° tempo = cartellini gialli con minuto ≤ 45 (recupero del 1° tempo compreso).
Valore atteso a 90' per squadra (uguale nei due modelli, con le sole partite precedenti): media gialli a squadra del campionato ×
fattore della squadra (gialli presi) × fattore dell'avversario (gialli fatti prendere) × fattore arbitro, ogni fattore ristretto verso 1.
Baseline = come l'app (halfSplit): valore a 90' × quota di 1° tempo del campionato per sede (casa/ospite), con le sole partite precedenti.
Modello: baseline × e^(c + a·x_sq + b·x_avv + r·x_arb), con
  x_sq  = ln(quota di 1° tempo dei gialli della squadra / quota del campionato)
  x_avv = ln(quota di 1° tempo dei gialli presi dagli avversari di quella squadra / quota del campionato)
  x_arb = ln(quota di 1° tempo dei gialli dati dall'arbitro / quota del campionato)
  quote ristrette verso il campionato con K = 10 partite fittizie (fissato prima del test, come per tiri e corner del 1° tempo).
Pesi mese per mese sulle sole partite precedenti (harness.walk_forward), varianti "solo c" (frazione ricalibrata), "solo arbitro",
"solo squadre", "tutto". Giudizio: 1X2 gialli del 1° tempo (il mercato 1xBet) e Over/Under 0,5 · 1,5 · 2,5 gialli totali del 1° tempo."""
import os, sys, json, glob, math, collections
import numpy as np, pandas as pd
REPO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
P2 = os.environ.get("RICERCA", os.path.join(REPO, "ricerca"))
sys.path.insert(0, os.path.join(REPO, "tools")); import harness as H
log = lambda *a: print(*a, flush=True)
K = 10.0; DEC = 0.97; KF = 8.0
REF = {}
for f in glob.glob(P2 + "/storico/*_20*.json"):
    for k, v in json.load(open(f))["partite"].items():
        if v[5]: REF[k] = v[5].split(",")[0].strip()
EV = []
for f in glob.glob(P2 + "/eventi/*.json"):
    lg = os.path.basename(f)[:-5]
    for fid, v in json.load(open(f)).items():
        c = v[5]; y = [[0, 0], [0, 0]]   # [lato][1°T, 2°T]
        for mi, ex, side, kd in c:
            if kd != "G" or mi is None: continue
            y[side][0 if mi <= 45 else 1] += 1
        EV.append((v[0][:10], lg, v[1], v[2], REF.get(fid), y))
EV.sort(); log("partite", len(EV), "con arbitro", sum(1 for e in EV if e[4]))
lgS = collections.defaultdict(lambda: np.array([1e-9, 1e-9, 1e-9, 1e-9, 0.0]))   # gialli 1°T casa, tot casa, 1°T ospite, tot ospite, partite
own = collections.defaultdict(lambda: np.zeros(3)); opp = collections.defaultdict(lambda: np.zeros(3)); ref = collections.defaultdict(lambda: np.zeros(3))   # [1°T, tot, partite]
rows, pairs = [], []
def season(d): return int(d[:4]) if d[5:7] >= "07" else int(d[:4]) - 1
for d, lg, h, a, rf, y in EV:
    L = lgS[lg]
    if L[4] > 150:
        sH, sA = L[0] / L[1], L[2] / L[3]; mT = (L[1] + L[3]) / (2 * L[4])
        fac = lambda S, m: (S[1] + KF * m) / (S[2] * m + KF * m)            # gialli per partita / media, ristretto verso 1
        shr = lambda S, s, m: (S[0] + K * m * s) / (S[1] + K * m)
        R = ref[rf] if rf else np.zeros(3)
        fr = fac(R, 2 * mT)
        mh = mT * fac(own[(lg, h)], mT) * fac(opp[(lg, a)], mT) * fr; ma = mT * fac(own[(lg, a)], mT) * fac(opp[(lg, h)], mT) * fr
        i = len(pairs); pairs.append(dict(d=d, lg=lg, y=(y[0][0], y[1][0])))
        for side, t, o, mu, s in ((0, h, a, mh, sH), (1, a, h, ma, sA)):
            rows.append(dict(i=i, side=side, date=d, lg=lg, season=season(d), mu0=mu * s, y=y[side][0], one=1.0,
                             x_sq=math.log(shr(own[(lg, t)], s, mT) / s), x_avv=math.log(shr(opp[(lg, o)], s, mT) / s),
                             x_arb=math.log(shr(R, s, 2 * mT) / s) if rf else 0.0))
    L *= 0.999; L += [y[0][0], sum(y[0]), y[1][0], sum(y[1]), 1]
    for t, side in ((h, 0), (a, 1)):
        S = own[(lg, t)]; S *= DEC; S += [y[side][0], sum(y[side]), 1]
        S = opp[(lg, a if side == 0 else h)]; S *= DEC; S += [y[side][0], sum(y[side]), 1]
    if rf:
        S = ref[rf]; S *= DEC; S += [y[0][0] + y[1][0], sum(y[0]) + sum(y[1]), 1]
T = pd.DataFrame(rows); log("righe", len(T))
def po(m1, m2, L):
    k = np.arange(15); p1 = np.exp(-m1) * m1 ** k / np.array([math.factorial(int(x)) for x in k]); p2 = np.exp(-m2) * m2 ** k / np.array([math.factorial(int(x)) for x in k])
    return float(np.convolve(p1, p2)[:int(L) + 1].sum())
REP = {}
for lab, feats in (("frazione ricalibrata (solo c)", ["one"]), ("solo arbitro", ["one", "x_arb"]), ("solo squadre", ["one", "x_sq", "x_avv"]), ("arbitro e squadre", ["one", "x_sq", "x_avv", "x_arb"])):
    T2, coefs = H.walk_forward(T.copy(), feats, r=None)
    G = T2.dropna(subset=["mu"]).groupby("i")
    P = {"1X2": [], 0.5: [], 1.5: [], 2.5: []}
    for i, g in G:
        if len(g) != 2: continue
        gh, ga = g[g.side == 0].iloc[0], g[g.side == 1].iloc[0]; p = pairs[i]; yh, ya = p["y"]; se = int(gh.season)
        base = dict(date=p["d"], lg=p["lg"], season=se)
        P["1X2"].append(dict(base, y=0 if yh > ya else 1 if yh == ya else 2, p_old=H.h2h(gh.mu0, ga.mu0, None, -1, 0.0), p_new=H.h2h(gh.mu, ga.mu, None, -1, 0.0)))
        for Lx in (0.5, 1.5, 2.5):
            uo, un = po(gh.mu0, ga.mu0, Lx), po(gh.mu, ga.mu, Lx)
            P[Lx].append(dict(base, y=0 if yh + ya > Lx else 2, p_old=np.array([1 - uo, 0, uo]), p_new=np.array([1 - un, 0, un])))
    last = [round(float(x), 3) for x in list(coefs.values())[-1]] if coefs else None
    res = {"pesi": dict(zip(feats, last)) if last else None}
    for mk, L_ in P.items():
        R = H.confronta(pd.DataFrame(L_)); res[str(mk)] = R
        log(H.riepilogo(f"Gialli 1° tempo {'1X2' if mk == '1X2' else 'Over ' + str(mk)} · {lab} · pesi ultimi {res['pesi']}", R))
    REP[lab] = res
json.dump(REP, open(os.path.join(P2, "res_cartellini_1t.json"), "w"), indent=1, default=float)
