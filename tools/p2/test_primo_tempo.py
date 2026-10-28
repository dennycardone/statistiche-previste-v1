"""Prevista 2.0 · 1° tempo (28/10/2026, richiesta di Denny): un modello di 1° tempo per squadra batte la frazione fissa del campionato?

Baseline = quello che fa l'app (halfSplit): valore atteso a 90' (previsioni walk-forward dell'app, ricerca/base) × quota del 1° tempo
del campionato per sede (casa/ospite), qui calcolata con le sole partite precedenti.
Modello di 1° tempo: baseline × e^(c + a·x_att + d·x_dif), con
  x_att = ln(quota di 1° tempo della squadra su quello che PRODUCE / quota del campionato)
  x_dif = ln(quota di 1° tempo dell'avversario su quello che CONCEDE / quota del campionato)
  quote di squadra con le sole partite precedenti, decadute (peso 0,97 a partita) e ristrette verso il campionato con K = 10 partite
  fittizie (fissato prima del test: per corner, tiri e tiri in porta i dati per tempo partono dal 2024-25, il periodo "scelta" è vuoto).
Pesi stimati mese per mese sulle sole partite precedenti (harness.walk_forward). Variante "solo c" = frazione fissa ricalibrata (per
separare l'effetto delle squadre da una semplice correzione della frazione). Giudizio: 1X2 del 1° tempo (chi ne fa di più), log-loss su
verifica (lug 2024 – giu 2025) e holdout (da lug 2025), regola di adozione dell'harness.
Mercati: corner, tiri, tiri in porta (ricerca/tempi, API-Football per tempo) e gol (risultato del 1° tempo dei file football-data).
Dispersione per tempo: Binomiale Negativa per squadra con r di data/tempi.json (corner 3,37 · tiri 8,79 · tiri in porta 7,34); gol: Poisson."""
import os, sys, json, glob, math, collections, datetime, csv, io
import numpy as np, pandas as pd
REPO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
P2 = os.environ.get("RICERCA", os.path.join(REPO, "ricerca"))
PUB = os.environ.get("P2_DATA", os.path.join(REPO, "pub"))
sys.path.insert(0, os.path.join(REPO, "tools")); import harness as H
log = lambda *a: print(*a, flush=True)
K, DEC = 10.0, 0.97
RHALF = {"c": 3.37, "s": 8.79, "st": 7.34, "g": None}

B = []
for fn in glob.glob(P2 + "/base/*.json"):
    lg = os.path.basename(fn)[:-5]
    for r in json.load(open(fn)): r["lg"] = lg; B.append(r)
BI = {(r["lg"], r["d"], r["h"], r["a"]): r for r in B}
log("previsioni dell'app (base)", len(B))
def base_of(lg, d, h, a):
    for dd in (0, -1, 1):
        r = BI.get((lg, (datetime.date.fromisoformat(d) + datetime.timedelta(days=dd)).isoformat(), h, a))
        if r: return r
    return None

# nomi API-Football → nomi dell'app (archivio formazioni: stessa data ±1 e stesso risultato, voto a maggioranza)
FK = []
for fn in glob.glob(P2 + "/form2/*.json"):
    D = json.load(open(fn))
    if not isinstance(D.get("partite"), dict) or "lega" not in D: continue
    for fid, v in D["partite"].items(): FK.append((D["lega"], v[0][:10], v[3], v[4], v[5], v[6]))
byk = collections.defaultdict(list)
for k in FK: byk[(k[0], k[4], k[5])].append(k)
votes = collections.defaultdict(collections.Counter)
for r in B:
    if r["y"]["g"][0] is None: continue
    d0 = datetime.date.fromisoformat(r["d"])
    for k in byk.get((r["lg"], r["y"]["g"][0], r["y"]["g"][1]), []):
        if abs((datetime.date.fromisoformat(k[1]) - d0).days) <= 1: votes[(r["lg"], k[2])][r["h"]] += 1; votes[(r["lg"], k[3])][r["a"]] += 1
MAP = {key: c.most_common(1)[0][0] for key, c in votes.items() if c.most_common(1)[0][1] >= 3}
log("nomi abbinati", len(MAP))

# eventi per mercato: (lg, data, casa, ospite, casa 1°T, ospite 1°T, casa totale, ospite totale), nomi dell'app
EV = collections.defaultdict(list)
for fn in glob.glob(P2 + "/tempi/*.json"):
    lg = os.path.basename(fn)[:-5]
    for fid, v in json.load(open(fn)).items():
        if not (v[3] and v[4] and v[5] and v[6]): continue
        h, a = MAP.get((lg, v[1])), MAP.get((lg, v[2]))
        if not h or not a: continue
        for k, i in (("c", 0), ("s", 1), ("st", 2)):
            x = (v[3][i], v[4][i], v[5][i], v[6][i])
            if None in x: continue
            EV[k].append((lg, v[0][:10], h, a, x[0], x[1], x[0] + x[2], x[1] + x[3]))
for bf in ("bundle_storico.json", "bundle.json"):
    p = os.path.join(PUB, bf)
    if not os.path.exists(p): continue
    for f in json.load(open(p))["files"]:
        rows = list(csv.DictReader(io.StringIO(f["text"])))
        for r in rows:
            try:
                d = datetime.datetime.strptime(r["Date"], "%d/%m/%Y" if len(r["Date"]) == 10 else "%d/%m/%y").date().isoformat()
                h1, a1, ht, at = int(r["HTHG"]), int(r["HTAG"]), int(r["FTHG"]), int(r["FTAG"])
            except Exception: continue
            EV["g"].append((r.get("Div"), d, r["HomeTeam"], r["AwayTeam"], h1, a1, ht, at))
for k in EV: EV[k] = sorted(set(EV[k]), key=lambda e: e[1]); log(k, "partite con il 1° tempo", len(EV[k]))

def table(k):
    """righe per squadra e partita con baseline e variabili, tutte con le sole partite precedenti"""
    lgS = collections.defaultdict(lambda: np.array([1e-9, 1e-9, 1e-9, 1e-9]))   # campionato: 1°T casa, tot casa, 1°T ospite, tot ospite (decaduti)
    att = collections.defaultdict(lambda: np.zeros(2)); dif = collections.defaultdict(lambda: np.zeros(2))   # squadra: [1°T, totale]
    out, pairs = [], []
    for (lg, d, h, a, h1, a1, ht, at) in EV[k]:
        L = lgS[(lg,)]
        if L[1] > 200 and L[3] > 200:
            sH, sA = L[0] / L[1], L[2] / L[3]
            r = base_of(lg, d, h, a); m = r and r.get(k) if k != "g" else (r and r.get("g"))
            if m and m[0] and m[1] and m[0] > 0 and m[1] > 0:
                def share(S, s_lg, scale):   # quota ristretta verso il campionato con K partite fittizie (scale = totale medio a partita)
                    return (S[0] + K * scale * s_lg) / (S[1] + K * scale)
                scale_h = m[0]; scale_a = m[1]
                xa_h = math.log(share(att[(lg, h)], sH, scale_h) / sH); xd_h = math.log(share(dif[(lg, a)], sH, scale_h) / sH)
                xa_a = math.log(share(att[(lg, a)], sA, scale_a) / sA); xd_a = math.log(share(dif[(lg, h)], sA, scale_a) / sA)
                i = len(pairs)
                pairs.append(dict(d=d, lg=lg, se=r["se"], m=m, y=(h1, a1)))
                out.append(dict(i=i, side=0, date=d, lg=lg, season=r["se"], mu0=m[0] * sH, y=h1, x_att=xa_h, x_dif=xd_h, one=1.0))
                out.append(dict(i=i, side=1, date=d, lg=lg, season=r["se"], mu0=m[1] * sA, y=a1, x_att=xa_a, x_dif=xd_a, one=1.0))
        # aggiornamento dopo la partita
        L *= 0.999; L += [h1, ht, a1, at]
        for key, S, v1, vt in (((lg, h), att, h1, ht), ((lg, a), att, a1, at), ((lg, a), dif, h1, ht), ((lg, h), dif, a1, at)):
            S[key] *= DEC; S[key] += [v1, vt]
    return pd.DataFrame(out), pairs

def probs(T2, pairs, k, col):
    P = []
    rT = RHALF[k]
    for i, g in T2.groupby("i"):
        if len(g) != 2 or g[col].isna().any(): continue
        p = pairs[i]; y = p["y"]
        gh, ga = g[g.side == 0].iloc[0], g[g.side == 1].iloc[0]
        P.append(dict(date=p["d"], lg=p["lg"], season=p["se"], y=0 if y[0] > y[1] else 1 if y[0] == y[1] else 2,
                      p_old=H.h2h(gh.mu0, ga.mu0, None, rT if rT else -1, 0.0), p_new=H.h2h(gh[col], ga[col], None, rT if rT else -1, 0.0)))
    return pd.DataFrame(P)

REP = {}
NAME = {"c": "Corner 1° tempo", "s": "Tiri 1° tempo", "st": "Tiri in porta 1° tempo", "g": "Gol 1° tempo (1X2 del primo tempo)"}
for k in ("c", "s", "st", "g"):
    T, pairs = table(k)
    if not len(T): log(k, "nessuna riga"); continue
    log(NAME[k], "righe", len(T))
    rT = RHALF[k]
    res = {}
    for lab, feats in (("frazione ricalibrata (solo c)", ["one"]), ("quote di 1° tempo delle squadre", ["one", "x_att", "x_dif"])):
        T2, coefs = H.walk_forward(T.copy(), feats, r=rT)
        T2 = T2.rename(columns={"mu": "mu_n"})
        PP = probs(T2, pairs, k, "mu_n")
        R = H.confronta(PP)
        last = [round(float(x), 3) for x in list(coefs.values())[-1]] if coefs else None
        log(H.riepilogo(f"{NAME[k]} · {lab} · pesi ultimi {dict(zip(feats, last)) if last else None}", R))
        res[lab] = dict(pesi=last, **R)
    REP[NAME[k]] = res
json.dump(REP, open(os.path.join(P2, "res_primo_tempo.json"), "w"), indent=1, default=float)
