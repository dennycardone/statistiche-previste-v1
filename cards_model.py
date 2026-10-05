"""Modello cartellini v2 (gialli + rossi totali di una partita), scelto con il backtest walk-forward del 5/10/2026
(47.955 partite API-Football 2022-2026, scelte sul 2023, verifica sul 2024-2026: MAE 1,731 contro 1,741 del modello
precedente e 1,774 della media del campionato; Brier Over/Under 0,1914 contro 0,1928 e 0,1971).

Previsione: log(cartellini attesi) = log(media del campionato) + b0 + somma dei pesi per le variabili:
  E    squadre: media mobile (peso 0,95 a partita) dei cartellini presi e provocati dalle due squadre, rispetto al campionato
  R    arbitro: cartellini reali / attesi nelle sue partite precedenti (stesso paese, tutte le stagioni), ristretto verso 1 (K=10)
  R10  arbitro: lo stesso sulle sue ultime 10 partite
  FF   falli fatti e subiti dalle due squadre in stagione, rispetto al campionato (ristretti verso la media con 3 partite fittizie)
  H    scontri diretti degli ultimi 3 anni: cartellini reali / attesi, ristretti verso 1 (K=12)
  nlo  1 se una delle due squadre ha meno di 5 partite nella stagione
Distribuzione: Binomiale Negativa (Var = mu + alpha mu^2), alpha stimato sui dati.
Pesi stimati ogni mese con le sole partite precedenti al mese (data/cards_model.json li conserva): le previsioni delle
partite già giocate restano quelle che il modello avrebbe dato prima della partita; le partite da giocare usano i pesi
stimati su tutte le partite già giocate. Variabili calcolate solo con le partite precedenti."""
import math, collections, datetime
import apif_extra as X

VERSION = "cartellini-v2 (2026-10-05)"
COUNTRY = {'I1': 'ITA', 'I2': 'ITA', 'E0': 'ENG', 'E1': 'ENG', 'E2': 'ENG', 'E3': 'ENG', 'EC': 'ENG', 'SP1': 'ESP', 'SP2': 'ESP', 'F1': 'FRA', 'F2': 'FRA',
           'D1': 'GER', 'D2': 'GER', 'SC0': 'SCO', 'SC1': 'SCO', 'SC2': 'SCO', 'SC3': 'SCO'}
CALENDAR_YEAR = {'ARG', 'BRA', 'CHN', 'FIN', 'IRL', 'JPN', 'NOR', 'SWE', 'USA'}   # stagione = anno solare
FEATS = ["E", "R", "FF", "H", "nlo", "R10"]
K_TEAM, K_R, K_H, W, WL, MIN_LG = 3, 10, 12, 0.95, 0.995, 40

def season_of(lg, d):
    y, m = int(d[:4]), int(d[5:7])
    return y if lg in CALENDAR_YEAR else (y if m >= 7 else y - 1)

def features(matches):
    """matches: dict(lg, d 'YYYY-MM-DD...', h, a, ref (nome), hc, ac, hf, af); hc/ac None = non giocata o senza cartellini.
    Restituisce, nello stesso ordine, None (dati insufficienti) o dict(x, lm, eh, ea, rN, played, T)."""
    order = sorted(range(len(matches)), key=lambda i: (matches[i]['d'][:16], matches[i]['lg']))
    res = [None] * len(matches)
    lgs = collections.defaultdict(lambda: {'c': 0.0, 'f': 0.0, 'w': 0.0, 'wf': 0.0, 'n': 0})
    teams = collections.defaultdict(list); ewma = collections.defaultdict(lambda: [0.0, 0.0, 0.0, 0.0, 0.0])
    refs = collections.defaultdict(list); h2h = collections.defaultdict(list)
    shr = lambda s, n, prior, k=K_TEAM: (s + k * prior) / (n + k)
    for i in order:
        r = matches[i]; lg = r['lg']; s = season_of(lg, r['d']); L = lgs[lg]
        played = r.get('hc') is not None and r.get('ac') is not None and r['hc'] + r['ac'] <= 16
        fok = played and r.get('hf') is not None and r.get('af') is not None and r['hf'] >= 3 and r['af'] >= 3 and r['hf'] + r['af'] >= 10
        hf, af = (r['hf'], r['af']) if fok else (None, None)
        rk = X.refkey(r.get('ref'))
        E_ = None; feat = None
        if L['n'] >= MIN_LG:
            lm = L['c'] / L['w']; lf = L['f'] / L['wf'] if L['wf'] else None
            th, ta = teams[(lg, r['h'])], teams[(lg, r['a'])]
            thS = [x for x in th if x[0] == s]; taS = [x for x in ta if x[0] == s]
            eh_, ea_ = ewma[(lg, r['h'])], ewma[(lg, r['a'])]
            eh = ea = None
            if eh_[4] >= 3 and ea_[4] >= 3:
                eh = (eh_[0] / eh_[4] + ea_[1] / ea_[4]) / 2; ea = (ea_[0] / ea_[4] + eh_[1] / eh_[4]) / 2; E_ = eh + ea
            FF = None
            if lf:
                pf = lf / 2
                def mf(lst, j):
                    l2 = [x for x in lst if x[j] is not None]; return shr(sum(x[j] for x in l2), len(l2), pf)
                FF = (mf(thS, 4) + mf(taS, 5) + mf(taS, 4) + mf(thS, 5)) / 2 / lf
            R = refs.get((COUNTRY.get(lg, lg), rk), []) if rk else []
            R10 = R[-10:]
            d0 = datetime.date.fromisoformat(r['d'][:10])
            HH = [x for x in h2h.get(frozenset((r['h'], r['a'])), []) if (d0 - x[2]).days <= 3 * 365]
            ratio = lambda A, Ex, K: math.log((A + K * lm) / (Ex + K * lm))
            x = {"E": math.log((E_ or lm) / lm),
                 "R": ratio(sum(z[0] for z in R), sum(z[1] for z in R), K_R) if R else 0.0,
                 "R10": ratio(sum(z[0] for z in R10), sum(z[1] for z in R10), K_R) if R10 else 0.0,
                 "FF": math.log(FF) if FF else 0.0,
                 "H": ratio(sum(z[0] for z in HH), sum(z[1] for z in HH), K_H) if HH else 0.0,
                 "nlo": 1.0 if min(len(thS), len(taS)) < 5 else 0.0}
            feat = dict(x=[x[k] for k in FEATS], lm=lm, eh=eh, ea=ea, rN=len(R), nmin=min(len(thS), len(taS)), played=played, T=(r['hc'] + r['ac']) if played else None, d=r['d'][:10])
        res[i] = feat
        if not played: continue
        T = r['hc'] + r['ac']; F = hf + af if fok else None
        exp_team = E_ if E_ else (L['c'] / L['w'] if L['w'] else None)
        if rk and exp_team: refs[(COUNTRY.get(lg, lg), rk)].append((T, exp_team))
        if exp_team: h2h[frozenset((r['h'], r['a']))].append((T, exp_team, datetime.date.fromisoformat(r['d'][:10])))
        teams[(lg, r['h'])].append((s, 'H', r['hc'], r['ac'], hf, af)); teams[(lg, r['a'])].append((s, 'A', r['ac'], r['hc'], af, hf))
        for t, own, prov, fo, fs in ((r['h'], r['hc'], r['ac'], hf, af), (r['a'], r['ac'], r['hc'], af, hf)):
            z = ewma[(lg, t)]
            if fo is None: fo, fs = (z[2] / z[4], z[3] / z[4]) if z[4] else (0.0, 0.0)
            z[0] = z[0] * W + own; z[1] = z[1] * W + prov; z[2] = z[2] * W + fo; z[3] = z[3] * W + fs; z[4] = z[4] * W + 1
        L['c'] = L['c'] * WL + T; L['w'] = L['w'] * WL + 1; L['n'] += 1
        if F is not None: L['f'] = L['f'] * WL + F; L['wf'] = L['wf'] * WL + 1
    return res

def fit(rows, lam=1e-2):
    """Poisson con offset log(media campionato) (IRLS, leggera penalità sui pesi) + alpha della Binomiale Negativa."""
    import numpy as np
    Xm = np.array([[1.0] + f['x'] for f in rows]); off = np.log([f['lm'] for f in rows]); y = np.array([f['T'] for f in rows], float)
    b = np.zeros(Xm.shape[1]); b[0] = math.log(y.mean() / np.exp(off).mean())
    P = np.eye(Xm.shape[1]) * lam; P[0, 0] = 0
    for _ in range(30):
        eta = Xm @ b + off; mu = np.exp(eta); z = eta - off + (y - mu) / mu
        nb = np.linalg.solve(Xm.T @ (Xm * mu[:, None]) + P, Xm.T @ (mu * z))
        if np.max(np.abs(nb - b)) < 1e-8: b = nb; break
        b = nb
    mu = np.exp(Xm @ b + off)
    lg_y1 = [math.lgamma(v + 1) for v in y]
    def nll(a):
        n = 1 / a; c = math.lgamma(n)
        return -sum(math.lgamma(v + n) - c - l + n * math.log(n / (n + m)) + v * math.log(m / (n + m)) for v, m, l in zip(y, mu, lg_y1)) / len(y)
    lo, hi = 1e-4, 0.5; g = (math.sqrt(5) - 1) / 2
    c1, c2 = hi - g * (hi - lo), lo + g * (hi - lo); f1, f2 = nll(c1), nll(c2)
    for _ in range(30):
        if f1 < f2: hi, c2, f2 = c2, c1, f1; c1 = hi - g * (hi - lo); f1 = nll(c1)
        else: lo, c1, f1 = c1, c2, f2; c2 = lo + g * (hi - lo); f2 = nll(c2)
    return [float(v) for v in b], float((lo + hi) / 2)

def predict(f, b):
    eta = math.log(f['lm']) + b[0] + sum(w * v for w, v in zip(b[1:], f['x']))
    mu = math.exp(eta)
    mult = {k: math.exp(w * v) for k, w, v in zip(FEATS, b[1:], f['x'])}
    ref = mult["R"] * mult["R10"]
    if f['eh'] and f['ea']: mh = mu * f['eh'] / (f['eh'] + f['ea'])
    else: mh = mu / 2
    return dict(mu=mu, mh=mh, ma=mu - mh, ref=ref, team=mult["E"], fouls=mult["FF"], h2h=mult["H"], early=mult["nlo"])

def run(matches, cache, today, since):
    """Previsioni per le partite dal giorno `since` in poi. cache: {"version", "mesi": {YYYY-MM: [pesi, alpha]}} aggiornato qui.
    Restituisce (lista allineata a matches con dict o None, alpha attuale, pesi attuali)."""
    F = features(matches)
    if cache.get("version") != VERSION: cache.clear(); cache.update(version=VERSION, mesi={})
    played = [f for f in F if f and f['played']]
    cur_m = today.isoformat()[:7]
    need = sorted({f['d'][:7] for f in F if f and f['d'] >= since.isoformat() and f['d'][:7] <= cur_m})
    for m in need:
        if m in cache["mesi"]: continue
        tr = [f for f in played if f['d'] < m + "-01"]
        if len(tr) >= 2000: cache["mesi"][m] = list(fit(tr))
    b_now, a_now = fit(played)
    out = []
    for f in F:
        if not f or f['d'] < since.isoformat(): out.append(None); continue
        m = f['d'][:7]
        if f['played'] or f['d'] < today.isoformat():
            ba = cache["mesi"].get(m)
            if not ba: out.append(None); continue
            b, a = ba
        else: b, a = b_now, a_now
        p = predict(f, b); p['alpha'] = a; p['rN'] = f['rN']; out.append(p)
    return out, a_now, b_now
