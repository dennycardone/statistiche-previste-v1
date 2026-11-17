"""Gol attesi · fase 3 (17/11/2026, Denny): replica in Python del modello gol dell'app (M0) e mattoni per gli esperimenti.
Ingresso: ricerca/gol/<lg>.json (tools/p2/gol_dump.js: partite caricate dall'app e riferimento dell'app) + pub/tiri_area.json.
Tutto con i soli dati dei giorni precedenti alla partita, come l'app (goalDynParts, gdynFit, selfElo, qualFit, goalOnlyDynParts, modelGoals)."""
import json, math, os, numpy as np
from scipy.stats import poisson

GDYN = dict(b0=0.0014876, lmu=0.1603687, home=0.0706217, lst=0.6374843, elo=0.1075574)
GDYN0 = dict(b0=-0.0213109, lmu=-0.1741235, home=0.0469935, lst=1.1518468)
GONLY = dict(b0=0.0279083, lmu=0.2394232, home=0.0452138, lrg=0.5475475, elo=0.0977350)
GD_TAU, GD_P, GD_LOOK = 365, 4, 1460
GO_TAU, GO_P, GO_LOOK = 730, 12, 1460
QB, Q_TAU, Q_P = 0.295, 365, 4
SELO_K, SELO_H = 10, 70
REPO = os.path.join(os.path.dirname(__file__), "..", "..")

def day(s): return np.datetime64(s, "D").astype(np.int64)

class League:
    def __init__(self, code, tarea=None):
        J = json.load(open(os.path.join(REPO, "ricerca", "gol", code + ".json")))
        self.code = code
        M = J["M"]
        self.d = np.array([day(m[0]) for m in M]); self.se = np.array([m[1] for m in M])
        self.h = [m[2] for m in M]; self.a = [m[3] for m in M]
        f = lambda i: np.array([np.nan if m[i] is None else m[i] for m in M], float)
        self.hg, self.ag, self.hst, self.ast, self.hs, self.as_ = f(4), f(5), f(6), f(7), f(8), f(9)
        self.fx = J["fx"]; self.ref = J["ref"]
        teams = sorted(set(self.h) | set(self.a) | {x[2] for x in self.fx} | {x[3] for x in self.fx})
        self.tid = {t: i for i, t in enumerate(teams)}; self.T = len(teams)
        self.H = np.array([self.tid[t] for t in self.h]); self.A = np.array([self.tid[t] for t in self.a])
        self.played = ~np.isnan(self.hg) & ~np.isnan(self.ag)
        self.elo_hist = self._self_elo()
        self.tarea = (tarea or {}).get(code)
        if self.tarea:
            R = self.tarea
            self.q_d = np.array([day(r[0]) for r in R]); self.q_h = [r[1] for r in R]; self.q_a = [r[2] for r in R]
            self.q_v = np.array([[r[3], r[4], r[5], r[6]] for r in R], float)
            qt = sorted(set(self.q_h) | set(self.q_a)); self.qid = {t: i for i, t in enumerate(qt)}
            self.q_H = np.array([self.qid[t] for t in self.q_h]); self.q_A = np.array([self.qid[t] for t in self.q_a])
        self._cache = {}

    # ---- Elo calcolato dall'app (selfElo): K 10, casa 70, aggiornamento a fine giornata, nuove squadre = media delle uscite
    def _self_elo(self):
        idx = np.where(self.played)[0]; idx = idx[np.argsort(self.d[idx], kind="stable")]
        seasons = sorted(set(self.se[idx].tolist()) | {x[1] for x in self.fx})
        hist, R = {}, {}
        def push(t, dd): hist.setdefault(t, []).append((dd, R[t]))
        prev, pend, dcur = None, {}, None
        def flush():
            nonlocal pend
            for t, v in pend.items(): R[t] += v; push(t, dcur + 1)
            pend = {}
        for y in seasons:
            flush()
            sy = [i for i in idx if self.se[i] == y]
            cur = {self.h[i] for i in sy} | {self.a[i] for i in sy} | {x[2] for x in self.fx if x[1] == y} | {x[3] for x in self.fx if x[1] == y}
            gone = [t for t in (prev or []) if t not in cur and t in R]
            vals = list(R.values())
            base = sum(R[t] for t in gone) / len(gone) if gone else (sum(vals) / len(vals) - 100 if vals else 1500)
            start = self.d[sy[0]] if sy else min(day(x[0]) for x in self.fx if x[1] == y)
            for t in sorted(cur):
                if t not in R: R[t] = base; push(t, start)
            for i in sy:
                if self.d[i] != dcur: flush(); dcur = self.d[i]
                rh, ra = R[self.h[i]], R[self.a[i]]; e = 1 / (1 + 10 ** (-(rh + SELO_H - ra) / 400))
                hg, ag = self.hg[i], self.ag[i]; res = 1 if hg > ag else 0.5 if hg == ag else 0
                g = abs(hg - ag); mult = 1 if g <= 1 else 1.5 if g == 2 else (11 + g) / 8
                dd = SELO_K * mult * (res - e); pend[self.h[i]] = pend.get(self.h[i], 0) + dd; pend[self.a[i]] = pend.get(self.a[i], 0) - dd
            flush(); prev = cur
        return hist

    def elo_at(self, team, D):
        s = self.elo_hist.get(team); r = None
        if not s: return None
        for x in s:
            if x[0] <= D: r = x
            else: break
        return r[1] if r else None

    # ---- rating attacco × difesa (gdynFit / gonlyFit)
    def rating(self, D, vh, va, tau, P, look, need_sot):
        m = self.played & (self.d < D) & (self.d >= D - look)
        y365 = m & (self.d >= D - 365)
        if need_sot:
            hasS = ~np.isnan(self.hst) & ~np.isnan(self.ast); L = m & hasS; s365 = y365 & hasS
            if not (y365.sum() > 100 and s365.sum() > 100 and L.sum() >= 50): return None
            conv = (self.hg[s365].sum() + self.ag[s365].sum()) / (self.hst[s365].sum() + self.ast[s365].sum())
        else:
            L = m
            if not (y365.sum() > 100 and L.sum() >= 50): return None
            conv = None
        muH, muA = self.hg[y365].mean(), self.ag[y365].mean()
        ii = np.where(L)[0]; w = np.exp(-np.round(D - self.d[ii]) / tau); W = w.sum()
        xh, xa = vh[ii], va[ii]; sH, sA = (w * xh).sum() / W, (w * xa).sum() / W; u = (sH + sA) / 2
        H, A = self.H[ii], self.A[ii]; T = self.T
        att, de = np.ones(T), np.ones(T)
        for _ in range(6):
            xa_ = np.bincount(H, w * xh, T) + np.bincount(A, w * xa, T)
            ea_ = np.bincount(H, w * sH * de[A], T) + np.bincount(A, w * sA * de[H], T)
            xd_ = np.bincount(H, w * xa, T) + np.bincount(A, w * xh, T)
            ed_ = np.bincount(H, w * sA * att[A], T) + np.bincount(A, w * sH * att[H], T)
            att, de = (xa_ + P * u) / (ea_ + P * u), (xd_ + P * u) / (ed_ + P * u)
        seen = np.zeros(T, bool); seen[H] = True; seen[A] = True
        att[~seen] = 1; de[~seen] = 1
        return dict(muH=muH, muA=muA, conv=conv, sH=sH, sA=sA, att=att, de=de, n=len(ii))

    def gdyn_fit(self, D):
        k = ("g", D)
        if k not in self._cache: self._cache[k] = self.rating(D, self.hst, self.ast, GD_TAU, GD_P, GD_LOOK, True)
        return self._cache[k]

    def gonly_fit(self, D):
        k = ("o", D)
        if k not in self._cache: self._cache[k] = self.rating(D, self.hg, self.ag, GO_TAU, GO_P, GO_LOOK, False)
        return self._cache[k]

    # ---- qualità dei tiri (qualFit / qualX)
    def qual_fit(self, D):
        k = ("q", D)
        if k in self._cache: return self._cache[k]
        res = None
        if self.tarea:
            days = np.round(D - self.q_d); ok = days >= 1
            w = np.exp(-days[ok] / Q_TAU); v = self.q_v[ok]; H, A = self.q_H[ok], self.q_A[ok]; Tq = len(self.qid)
            si = (w * (v[:, 0] + v[:, 1])).sum(); ss = (w * (v[:, 2] + v[:, 3])).sum(); n = 2 * w.sum()
            if n >= 40:
                acc = np.zeros((Tq, 5))
                for j, (c0, c1, c2, c3) in enumerate(((0, 1, 2, 3), (1, 0, 3, 2))):
                    TT = H if j == 0 else A
                    acc[:, 0] += np.bincount(TT, w * v[:, c0], Tq); acc[:, 1] += np.bincount(TT, w * v[:, c1], Tq)
                    acc[:, 2] += np.bincount(TT, w * v[:, c2], Tq); acc[:, 3] += np.bincount(TT, w * v[:, c3], Tq)
                    acc[:, 4] += np.bincount(TT, w, Tq)
                res = dict(mi=si / n, ms=ss / n, acc=acc)
        self._cache[k] = res; return res

    def qual_x(self, D, home, away):
        F = self.qual_fit(D)
        if not F: return None
        z = np.zeros(5)
        g = lambda t: F["acc"][self.qid[t]] if t in self.qid else z
        r = lambda v, w, m: (v + Q_P * m) / (w + Q_P) / m
        h, a = g(home), g(away)
        try:
            xh = math.log(r(h[0], h[4], F["mi"]) * r(a[1], a[4], F["mi"])) - math.log(r(h[2], h[4], F["ms"]) * r(a[3], a[4], F["ms"]))
            xa = math.log(r(a[0], a[4], F["mi"]) * r(h[1], h[4], F["mi"])) - math.log(r(a[2], a[4], F["ms"]) * r(h[3], h[4], F["ms"]))
        except (ValueError, ZeroDivisionError): return None
        return (xh, xa) if math.isfinite(xh) and math.isfinite(xa) else None

    # ---- M0: gol attesi dell'app
    def m0(self, D, home, away, parts=False):
        F = self.gdyn_fit(D)
        if F is not None:
            ih, ia = self.tid[home], self.tid[away]
            tpH = F["sH"] * F["att"][ih] * F["de"][ia] * F["conv"]; tpA = F["sA"] * F["att"][ia] * F["de"][ih] * F["conv"]
            eH, eA = self.elo_at(home, D), self.elo_at(away, D); we = eH is not None and eA is not None
            C = GDYN if we else GDYN0; ed = (eH - eA) / 100 if we else 0
            lh0 = math.exp(C["b0"] + C["lmu"] * math.log(F["muH"]) + C["home"] + C["lst"] * math.log(tpH) + (C["elo"] * ed if we else 0))
            la0 = math.exp(C["b0"] + C["lmu"] * math.log(F["muA"]) + C["lst"] * math.log(tpA) - (C["elo"] * ed if we else 0))
            QX = self.qual_x(D, home, away)
            lh, la = (lh0 * math.exp(QB * QX[0]), la0 * math.exp(QB * QX[1])) if QX else (lh0, la0)
            if parts: return lh, la, dict(src="gdyn", muH=F["muH"], muA=F["muA"], tpH=tpH, tpA=tpA, ed=ed, we=we, qx=QX, conv=F["conv"])
            return lh, la
        F = self.gonly_fit(D)
        if F is None: return None
        ih, ia = self.tid[home], self.tid[away]
        rgH = F["sH"] * F["att"][ih] * F["de"][ia]; rgA = F["sA"] * F["att"][ia] * F["de"][ih]
        eH, eA = self.elo_at(home, D), self.elo_at(away, D); ed = (eH - eA) / 100 if eH is not None and eA is not None else 0
        C = GONLY
        lh = math.exp(C["b0"] + C["lmu"] * math.log(F["muH"]) + C["home"] + C["lrg"] * math.log(rgH) + C["elo"] * ed)
        la = math.exp(C["b0"] + C["lmu"] * math.log(F["muA"]) + C["lrg"] * math.log(rgA) - C["elo"] * ed)
        if parts: return lh, la, dict(src="gonly", muH=F["muH"], muA=F["muA"], tpH=rgH, tpA=rgA, ed=ed, we=eH is not None and eA is not None, qx=None, conv=None)
        return lh, la

# ---- matrice dei risultati (modelGoals: N = 10, normalizzata, correzione Dixon-Coles)
K = np.arange(11)
def score_matrix(lh, la, rho=0.0):
    M = np.outer(poisson.pmf(K, lh), poisson.pmf(K, la))
    if rho:
        M[0, 0] *= max(0, 1 - lh * la * rho); M[0, 1] *= max(0, 1 + lh * rho); M[1, 0] *= max(0, 1 + la * rho); M[1, 1] *= max(0, 1 - rho)
    return M / M.sum()
def p1x2(M): return np.tril(M, -1).sum(), np.trace(M), np.triu(M, 1).sum()

def load_tarea():
    T = json.load(open(os.path.join(REPO, "pub", "tiri_area.json")))
    return T.get("campionati", {})
