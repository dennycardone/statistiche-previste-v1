"""Fuorigioco 0-0: la regola dei doppi vuoti, controllo e alternative più severe (26/10/2026).
Confronto, campionato per campionato, tra quota di doppi vuoti e 0-0 "atteso" (P(casa 0 | ospite >0) × P(ospite 0 | casa >0), dati espliciti).
Varianti dei dati che entrano nel modello (le previsioni si valutano sempre sulle STESSE partite con valori scritti e non 0-0, più gli 0-0 di tutte
le varianti dove sono accettati in tutte, quindi stesso bersaglio):
  R0  regola attuale (doppio vuoto = 0-0 se copertura ≥15/20 e 0-0 scritti <1% nelle ultime 200)
  R1  R0 + il doppio vuoto è 0-0 solo se, nelle partite precedenti del campionato, la quota di doppi vuoti non supera lo 0-0 atteso di oltre 2 punti
  R2  R1 + nei campionati dove la quota di 0-0 SCRITTI supera di oltre 2 punti quella attesa, anche lo 0-0 scritto è un dato mancante
Modello: lo stesso fuorigioco dell'app (OFFC, rating 365/90 giorni, prudenza 20/5, Binomiale Negativa r = 10,68)."""
import os as _os
P2 = _os.environ.get("RICERCA", _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", "..", "ricerca"))   # 28/10/2026: archivio di ricerca (ramo ricerca)
REPO = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", "..")
import json, glob, math, collections, datetime, sys, numpy as np, pandas as pd
sys.path.insert(0, REPO + "/tools"); import harness as H
from scipy.stats import nbinom
OFFC = dict(b0=0.1354244, lmu=0.7332036, att=0.9284822, de=1.1294708); TA, PA, TD, PD, RT = 365, 20, 90, 5, 10.68
def load(lg):
    d = json.load(open(f"{P2}/sx/{lg}.json")); L = []
    for fid, r in d.items():
        Hs, As = r[3], r[4]
        if not Hs or not As or len(Hs) < 14: continue
        adv = Hs[7] is not None or Hs[11] is not None
        L.append((r[0][:10], r[1], r[2], Hs[13], As[13], adv))
    return sorted(L)
def variant(L, rule):
    out = []; l20 = collections.deque(maxlen=20); l200 = collections.deque(maxlen=200); stats = collections.Counter()
    for d, h, a, oh, oa, adv in L:
        val = None
        if oh is not None and oa is not None:
            val = (oh, oa)
            if rule == "R2" and oh == 0 and oa == 0:
                exp = (stats["h0"] / max(stats["apos"], 1)) * (stats["a0"] / max(stats["hpos"], 1)); share = stats["e00"] / max(stats["n"], 1)
                if stats["n"] >= 100 and share - exp > 0.02: val = None
        elif oh is None and oa is None and adv:
            cov = len(l20) >= 15 and sum(l20) >= 15; expl = len(l200) >= 50 and sum(l200) / len(l200) >= 0.01
            ok = cov and not expl
            if ok and rule in ("R1", "R2"):
                exp = (stats["h0"] / max(stats["apos"], 1)) * (stats["a0"] / max(stats["hpos"], 1)); share = stats["dn"] / max(stats["n"], 1)
                if stats["n"] >= 100 and share - exp > 0.02: ok = False
            if ok: val = (0.0, 0.0)
        out.append((d, h, a, val, oh, oa))
        if adv:
            has = oh is not None and oa is not None; l20.append(1 if has else 0)
            if has: l200.append(1 if (oh == 0 and oa == 0) else 0)
            stats["n"] += 1
            if oh is None and oa is None: stats["dn"] += 1
            elif has:
                if oh == 0 and oa == 0: stats["e00"] += 1
                if oa > 0: stats["apos"] += 1; stats["h0"] += oh == 0
                if oh > 0: stats["hpos"] += 1; stats["a0"] += oa == 0
    return out
def predict(V):
    """previsioni walk-forward: per ogni partita, solo le partite (valorizzate nella variante) dei giorni precedenti"""
    res = []; hist = []
    for i, (d, h, a, val, oh, oa) in enumerate(V):
        D0 = datetime.date.fromisoformat(d); sH = sA = n = 0.0; T = collections.defaultdict(lambda: [0.0, 0.0, 0.0, 0.0])
        for (dd, hh, aa, vh, va) in reversed(hist):
            days = (D0 - dd).days
            if days < 1: continue
            if days > 1500: break
            w, wd = math.exp(-days / TA), math.exp(-days / TD); sH += w * vh; sA += w * va; n += w
            for t, f, c in ((hh, vh, va), (aa, va, vh)): x = T[t]; x[0] += w * f; x[1] += w; x[2] += wd * c; x[3] += wd
        if n > 20:
            muH, muA = sH / n, sA / n; m = (muH + muA) / 2
            att = lambda t: (T[t][0] + PA * m) / (T[t][1] + PA) / m; de = lambda t: (T[t][2] + PD * m) / (T[t][3] + PD) / m
            lh = math.exp(OFFC["b0"] + OFFC["lmu"] * math.log(muH) + OFFC["att"] * math.log(att(h)) + OFFC["de"] * math.log(de(a)))
            la = math.exp(OFFC["b0"] + OFFC["lmu"] * math.log(muA) + OFFC["att"] * math.log(att(a)) + OFFC["de"] * math.log(de(h)))
            res.append((i, lh, la))
        if val is not None: hist.append((D0, h, a, val[0], val[1]))
    return {i: (lh, la) for i, lh, la in res}
REP = []
for lg in ("HUN", "BUL", "N1", "AUT", "E0"):
    L = load(lg); V = {r: variant(L, r) for r in ("R0", "R1", "R2")}; P = {r: predict(V[r]) for r in V}
    rows = []
    for i, (d, h, a, val, oh, oa) in enumerate(V["R0"]):
        if d < "2024-07-01" or oh is None or oa is None or (oh == 0 and oa == 0): continue   # bersaglio comune: valori scritti, non 0-0
        if not all(i in P[r] for r in P): continue
        y = 0 if oh > oa else 1 if oh == oa else 2
        rows.append(dict(date=d, lg=lg, season=int(d[:4]), y=y, **{r: H.h2h(*P[r][i], None, RT, 0.0) for r in P},
                         **{"ll_" + r: -(nbinom.logpmf(int(oh), RT, RT / (RT + P[r][i][0])) + nbinom.logpmf(int(oa), RT, RT / (RT + P[r][i][1]))) for r in P}))
    df = pd.DataFrame(rows)
    acc = {r: sum(1 for x in V[r] if x[3] == (0.0, 0.0)) for r in V}
    line = f"{lg}: partite valutate {len(df)} · 0-0 accettati R0 {acc['R0']} R1 {acc['R1']} R2 {acc['R2']}"
    for r in ("R1", "R2"):
        d1 = df.copy(); d1["p_old"] = d1["R0"]; d1["p_new"] = d1[r]
        x = H.confronta(d1); v = x.get("verifica", {}); ho = x.get("holdout", {})
        line += f" · {r}: 1X2 verifica {v.get('diff', float('nan')):+.4f} holdout {ho.get('diff', float('nan')):+.4f} · conteggi per squadra {(df['ll_' + r] - df['ll_R0']).mean():+.4f}"
    print(line, flush=True)
