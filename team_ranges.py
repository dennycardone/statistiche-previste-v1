"""Range della MEDIA attesa per squadra (gol e cartellini, casa e ospite), solo livello aggiuntivo: le previsioni non cambiano.
Ogni settimana, per campionato: modello attacco×difesa (gol) o cartellini presi×provocati + arbitro (cartellini), regressione di
Poisson sulle partite dei 365 giorni precedenti. Errore standard di log(media) di ciascuna squadra in ciascuna partita dalla
matrice di informazione, corretto con il fattore di taratura K misurato nel backtest (due stime indipendenti della stessa partita
da due metà dei dati: K gol 0,884, cartellini 0,900). Range 80% = media prevista dall'app × exp(±1,2816 × errore standard).
Settimane già passate conservate in data/team_ranges.json (non cambiano)."""
import math, datetime, collections
import numpy as np
K_GOL, K_CART = 0.884, 0.900
VERSION = "range-squadre-v1 (2026-10-05)"
def _design(rows, ti, ri):
    T = len(ti); P = 2 + 2 * T + len(ri); X = np.zeros((2 * len(rows), P)); y = np.zeros(2 * len(rows))
    for k, r in enumerate(rows):
        for j, (s, o, v, h) in enumerate(((r[0], r[1], r[2], 1), (r[1], r[0], r[3], 0))):
            X[2 * k + j, 0] = 1; X[2 * k + j, 1] = h
            if s in ti: X[2 * k + j, 2 + ti[s]] = 1
            if o in ti: X[2 * k + j, 2 + T + ti[o]] = 1
            if r[4] in ri: X[2 * k + j, 2 + 2 * T + ri[r[4]]] = 1
            y[2 * k + j] = v if v is not None else 0
    return X, y
def _fit(X, y):
    P = X.shape[1]; pen = np.ones(P) * 2.0; pen[:2] = 0; b = np.zeros(P); b[0] = math.log(max(y.mean(), .05))
    for _ in range(30):
        mu = np.exp(X @ b); z = X @ b + (y - mu) / mu; A = X.T @ (X * mu[:, None]) + np.diag(pen)
        nb = np.linalg.solve(A, X.T @ (mu * z))
        if np.max(np.abs(nb - b)) < 1e-7: b = nb; break
        b = nb
    mu = np.exp(X @ b); A = X.T @ (X * mu[:, None]) + np.diag(pen)
    phi = max(1.0, float(np.sum((y - mu) ** 2 / mu) / max(1, len(y) - P)))
    return np.linalg.inv(A) * phi
def _se(window, targets, kind):
    teams = sorted({r[0] for r in window} | {r[1] for r in window}); ti = {t: i for i, t in enumerate(teams)}
    refs = sorted({r[4] for r in window if r[4]}) if kind == "cart" else []; ri = {x: i for i, x in enumerate(refs)}
    X, y = _design(window, ti, ri); C = _fit(X, y)
    Xt, _ = _design([(t[0], t[1], 0, 0, t[2] if kind == "cart" else None) for t in targets], ti, ri)
    s = np.sqrt(np.einsum("ij,jk,ik->i", Xt, C, Xt)) * (K_GOL if kind == "gol" else K_CART)
    return [(float(s[2 * k]), float(s[2 * k + 1])) for k in range(len(targets))]
def run(by_lg, refkey, today, since, cache):
    """by_lg: {lg: [v, ...]} archivio API-Football. → {(lg, data16, casa, ospite): [se gol casa, se gol ospite, se cart casa, se cart ospite]}"""
    if cache.get("version") != VERSION: cache.clear(); cache.update(version=VERSION, settimane={})
    wk_now = today - datetime.timedelta(days=today.weekday()); out = {}
    for lg, L in by_lg.items():
        played = []
        for v in L:
            if v[9] in ("FT", "AET", "PEN") and v[4] is not None:
                H, A = v[7], v[8]; cards = H[4] is not None and A[4] is not None
                played.append((datetime.date.fromisoformat(v[0][:10]), v[2], v[3], v[4], v[5], (H[4] + (H[5] or 0)) if cards else None, (A[4] + (A[5] or 0)) if cards else None, refkey(v[6])))
        bywk = collections.defaultdict(list)
        for v in L:
            d = datetime.date.fromisoformat(v[0][:10])
            if d < since: continue
            wk = d - datetime.timedelta(days=d.weekday()); bywk[min(wk, wk_now)].append(v)
        for wk, vs in bywk.items():
            key = f"{lg}|{wk}"
            if wk < wk_now and key in cache["settimane"]:
                for v in vs:
                    x = cache["settimane"][key].get(f"{v[0]}|{v[2]}|{v[3]}")
                    if x: out[(lg, v[0], v[2], v[3])] = x
                continue
            win = [p for p in played if wk - datetime.timedelta(days=365) <= p[0] < wk]
            if len(win) < 80: continue
            tg = [(v[2], v[3], refkey(v[6])) for v in vs]
            g = _se([(p[1], p[2], p[3], p[4], None) for p in win], tg, "gol")
            wc = [(p[1], p[2], p[5], p[6], p[7]) for p in win if p[5] is not None]
            c = _se(wc, tg, "cart") if len(wc) >= 80 else [(None, None)] * len(tg)
            res = {}
            for v, (a, b), (e, f) in zip(vs, g, c):
                x = [round(a, 4), round(b, 4), round(e, 4) if e else None, round(f, 4) if f else None]
                out[(lg, v[0], v[2], v[3])] = x; res[f"{v[0]}|{v[2]}|{v[3]}"] = x
            if wk < wk_now: cache["settimane"][key] = res
    return out
