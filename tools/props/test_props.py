"""Player props · punto 3 (14/11/2026, Denny): previsione diretta dei mercati sul SINGOLO giocatore, solo titolari, Top 5 campionati.
Mercati: tiri in porta Over 0,5 / 1,5 · tiri Over 1,5 / 2,5 · falli commessi Over 0,5 / 1,5 · ammonito Sì.

Tutto point-in-time (per ogni partita solo le partite precedenti), periodi dell'harness (scelta fino al 30/6/2024, verifica 2024-25, holdout
da luglio 2025). Storia dei giocatori da TUTTE le competizioni dell'archivio formazioni (chi cambia campionato si porta i suoi numeri),
valutazione solo sui titolari di Serie A, Premier, Liga, Bundesliga, Ligue 1.

  Modello 0 (riferimento): media del ruolo ogni 90' × minuti medi del ruolo da titolare (nessuna informazione sul giocatore).
  Modello A: valore ogni 90' del giocatore (media mobile per presenza, peso DP) ristretto verso la media del ruolo con K partite fittizie
             × minuti attesi da titolare (media mobile dei minuti nelle sue partite da titolare, ristretta verso il ruolo).
  Modello B: A × (statistica attesa oggi per la squadra da Prevista / media abituale delle attese della squadra): tiri, tiri in porta,
             falli dalla base walk-forward dell'app (ramo ricerca, base/<lg>.json, già con l'arbitro sui falli); cartellini: rapporto dei
             falli × severità dell'arbitro (cartellini a partita dell'arbitro / media del campionato, ristretta con 10 partite fittizie).
  Distribuzione: Binomiale Negativa con α per statistica scelto nel periodo "scelta" (lo stesso per A e B); ammonito: P(almeno 1).
  DP e K scelti nel periodo "scelta" sul Modello A, poi fissi.
Bonus assenze: quando il "tiratore principale" abituale della squadra non è tra i titolari, rapporto tiri reali / attesi (Modello A)
degli altri titolari centrocampisti e attaccanti, contro le partite in cui c'è.

Uso: python tools/props/test_props.py ricerca   (dopo bash tools/ricerca_locale.sh)"""
import json, glob, sys, os, math, collections, datetime
import numpy as np, pandas as pd
from scipy.special import gammaln
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import harness as H

R = sys.argv[1] if len(sys.argv) > 1 else "ricerca"
TOP = ["I1", "E0", "SP1", "D1", "F1"]
POS = {"G": 0, "D": 1, "M": 2, "F": 3}
STATS = ["sh", "sot", "fc", "yc"]                       # tiri (API: senza i respinti), tiri in porta, falli commessi, cartellini (gialli + rossi)
COL = {"sh": 9, "sot": 10, "fc": 7}
MARKETS = [("sot", 0.5), ("sot", 1.5), ("sh", 1.5), ("sh", 2.5), ("fc", 0.5), ("fc", 1.5), ("yc", 0.5)]
LAB = {("sot", 0.5): "Tiri in porta Over 0,5", ("sot", 1.5): "Tiri in porta Over 1,5", ("sh", 1.5): "Tiri Over 1,5", ("sh", 2.5): "Tiri Over 2,5",
       ("fc", 0.5): "Falli Over 0,5", ("fc", 1.5): "Falli Over 1,5", ("yc", 0.5): "Ammonito Sì"}
DPS = [0.95, 0.97, 0.99]; KS = [2.0, 5.0, 10.0, 20.0]
log = lambda *a: print(*a, flush=True)

# ---------------------------------------------------------------- dati
FX = []
for fn in glob.glob(R + "/form2/*.json"):
    D = json.load(open(fn))
    if "lega" not in D or not isinstance(D.get("partite"), dict): continue
    for fid, v in D["partite"].items():
        if v[9]: FX.append((v[0], D["lega"], fid, v))
FX.sort()
REF = {}
for fn in glob.glob(R + "/storico/*.json"):
    P = json.load(open(fn)).get("partite") or {}
    for fid, v in (P.items() if isinstance(P, dict) else P):
        if len(v) > 5 and v[5]: REF[str(fid)] = str(v[5]).split(",")[0].strip()
BASE = {}
for lg in TOP:
    for r in json.load(open(f"{R}/base/{lg}.json")): BASE.setdefault(lg, []).append(r)
log("partite con giocatori", len(FX), "· Top 5 in base", {lg: len(v) for lg, v in BASE.items()})

# nomi API-Football → nomi dell'app: partite con la stessa data (±1) e lo stesso risultato
def day(s): return datetime.date.fromisoformat(s[:10])
bidx = collections.defaultdict(list)
for lg, rows in BASE.items():
    for r in rows: bidx[(lg, r["d"], r["y"]["g"][0], r["y"]["g"][1])].append(r)
vote = collections.defaultdict(collections.Counter)
for d, lg, fid, v in FX:
    if lg not in BASE: continue
    for dd in (0, -1, 1):
        k = (lg, str(day(d) + datetime.timedelta(days=dd)), v[5], v[6])
        if len(bidx.get(k, [])) == 1:
            b = bidx[k][0]; vote[(lg, v[1])][b["h"]] += 1; vote[(lg, v[2])][b["a"]] += 1
NAME = {k: c.most_common(1)[0][0] for k, c in vote.items() if c.most_common(1)[0][1] >= 3}
def base_row(lg, d, v):
    h, a = NAME.get((lg, v[1])), NAME.get((lg, v[2]))
    if not h or not a: return None
    for dd in (0, -1, 1):
        for b in bidx.get((lg, str(day(d) + datetime.timedelta(days=dd)), v[5], v[6]), []):
            if b["h"] == h and b["a"] == a: return b
    return None

# ---------------------------------------------------------------- passaggio unico point-in-time
NS = len(STATS); ND = len(DPS)
pl = {}                      # giocatore → array (ND, 2, NS): [minuti decaduti, somme decadute] per ogni DP
pmin = {}                    # giocatore → [minuti decaduti da titolare, partite decadute da titolare]
role = {}
G = np.zeros((4, 2, NS)); G[:, 0] = 1e-9                         # per ruolo: minuti, somme (prior)
GM = np.zeros((4, 2)); GM[:, 1] = 1e-9                           # per ruolo: minuti da titolare, partite da titolare
team_exp = {}                # (lg, squadra app, stat) → [somma decadute delle attese, peso]
ref_st = {}                  # arbitro → [cartellini decaduti, partite decadute]
lg_cards = collections.defaultdict(lambda: [0.0, 1e-9])
team_starts = collections.defaultdict(dict)
DT = 0.90
rows_out = []
abs_out = []
def vec(r):
    return np.array([r[9] or 0, r[10] or 0, r[7] or 0, (r[5] or 0) + (r[6] or 0)], float)

for d, lg, fid, v in FX:
    _, hid, aid, hn, an, hg, ag, xh, xa, P = v
    byp = {r[0]: r for r in P}
    ev = lg in BASE and d[:10] >= "2023-07-01" and len(xh) >= 10 and len(xa) >= 10 and GM[:, 1].sum() > 2000
    b = base_row(lg, d, v) if ev else None
    if b is not None:
        ref = REF.get(fid); rs = ref_st.get(ref) if ref else None; lc = lg_cards[lg]; lgm = lc[0] / lc[1]
        reff = ((rs[0] + 10 * lgm) / (rs[1] + 10)) / lgm if rs and lgm > 0 else 1.0
        for side, tid, xi, tname, sk in ((0, hid, xh, b["h"], 0), (1, aid, xa, b["a"], 1)):
            ratio = {}
            for st, bk in (("sh", "s"), ("sot", "st"), ("fc", "f")):
                e = (b.get(bk) or [None, None])[sk]; T = team_exp.get((lg, tname, st))
                ratio[st] = e / (T[0] / T[1]) if e and T and T[1] >= 3 else None
            ratio["yc"] = ratio["fc"] * reff if ratio["fc"] is not None else None
            # tiratore principale abituale (bonus assenze)
            stt = team_starts[(lg, tid)]; habit = [p for p, _ in sorted(stt.items(), key=lambda z: -z[1])][:11]
            def expA(p, j=1, K=5.0):
                rr = POS.get(role.get(p, "M"), 2); g = G[rr, 1] / np.maximum(G[rr, 0], 1e-9) * 90; a = pl.get(p)
                rate = g if a is None else (a[j, 1] + K * g) / (a[j, 0] / 90 + K)
                gm = GM[rr, 0] / GM[rr, 1]; m = pmin.get(p); mins = gm if m is None else (m[0] + 3 * gm) / (m[1] + 3)
                return rate, mins
            top = None
            if len(habit) >= 11 and min(stt[p] for p in habit) > 0.3:
                top = max(habit, key=lambda p: expA(p)[0][0] * expA(p)[1])
            for p in xi:
                r = byp.get(p)
                if r is None or r[1] != side: continue
                rr = POS.get(role.get(p, r[11] or "M"), 2)
                y = vec(r)
                gm = GM[rr, 0] / GM[rr, 1]; m = pmin.get(p); mins = gm if m is None else (m[0] + 3 * gm) / (m[1] + 3)
                g = G[rr, 1] / np.maximum(G[rr, 0], 1e-9) * 90
                a = pl.get(p)
                rec = {"date": d[:10], "lg": lg, "season": d[:4] if d[5:7] >= "07" else str(int(d[:4]) - 1), "fid": fid, "pid": p, "role": rr,
                       "mins": mins, "real_min": r[2], "base0": g * gm / 90, "n_app": 0 if a is None else a[1, 0, 0] / 90}
                for i in range(ND):
                    for K in KS:
                        rate = g if a is None else (a[i, 1] + K * g) / (a[i, 0] / 90 + K)
                        rec[f"A_{i}_{K}"] = rate * mins / 90
                for st in STATS: rec["y_" + st] = y[STATS.index(st)]; rec["r_" + st] = ratio[st]
                rows_out.append(rec)
                if top is not None and p != top and rr >= 2:
                    ra, mi = expA(p); abs_out.append((d[:10], lg, fid, side, top in xi, ra[0] * mi / 90, y[0], ra[1] * mi / 90, y[1]))
    # ---- aggiornamento dopo la partita
    if b is not None:
        for st, bk in (("sh", "s"), ("sot", "st"), ("fc", "f")):
            for tname, sk in ((b["h"], 0), (b["a"], 1)):
                e = (b.get(bk) or [None, None])[sk]
                if e:
                    T = team_exp.setdefault((lg, tname, st), [0.0, 0.0]); T[0] = T[0] * DT + e; T[1] = T[1] * DT + 1
    tc = sum((r[5] or 0) + (r[6] or 0) for r in P)
    ref = REF.get(fid)
    if ref:
        rs = ref_st.setdefault(ref, [0.0, 0.0]); rs[0] = rs[0] * 0.95 + tc; rs[1] = rs[1] * 0.95 + 1
    lc = lg_cards[lg]; lc[0] = lc[0] * 0.995 + tc; lc[1] = lc[1] * 0.995 + 1
    for tid, xi in ((hid, xh), (aid, xa)):
        stt = team_starts[(lg, tid)]
        for p in list(stt): stt[p] *= 0.85
        for p in xi: stt[p] = stt.get(p, 0) + 1
    xs = set(xh) | set(xa)
    for r in P:
        p = r[0]
        if r[11]: role[p] = r[11]
        rr = POS.get(role.get(p, "M"), 2); x = vec(r); mi = r[2] or 0
        a = pl.setdefault(p, np.zeros((ND, 2, NS)))
        for i, dp in enumerate(DPS): a[i] *= dp; a[i, 0] += mi; a[i, 1] += x
        G[rr] *= 0.9999; G[rr, 0] += mi; G[rr, 1] += x
        if p in xs:
            m = pmin.setdefault(p, [0.0, 0.0]); m[0] = m[0] * 0.9 + mi; m[1] = m[1] * 0.9 + 1
            GM[rr] *= 0.9999; GM[rr, 0] += mi; GM[rr, 1] += 1
log("titolari valutati", len(rows_out), "· nomi abbinati", len(NAME))
import pickle; pickle.dump((rows_out, abs_out), open(os.path.join(R, "props_rows.pkl"), "wb"))
df = pd.DataFrame(rows_out)
for i in range(ND):
    for K in KS:
        c = f"A_{i}_{K}"; df[c] = df[c].apply(lambda z: np.asarray(z, float))
df["base0"] = df["base0"].apply(lambda z: np.asarray(z, float))

# ---------------------------------------------------------------- probabilità
def p_over(mu, L, alpha):
    """P(X > L) con X Binomiale Negativa (media mu, varianza mu + alpha·mu²); alpha 0 = Poisson."""
    k = np.arange(int(L) + 1)[None, :]; mu = np.maximum(np.asarray(mu, float), 1e-9)[:, None]
    if alpha <= 1e-6: lp = -mu + k * np.log(mu) - gammaln(k + 1)
    else:
        r = 1 / alpha; q = r / (r + mu); lp = gammaln(k + r) - gammaln(r) - gammaln(k + 1) + r * np.log(q) + k * np.log1p(-q)
    return np.clip(1 - np.exp(lp).sum(1), 1e-6, 1 - 1e-6)
def ll(p, y): return -(y * np.log(p) + (1 - y) * np.log(1 - p))
sc = df.date <= H.PERIODI["scelta"][1]
j = {s: STATS.index(s) for s in STATS}
best = {}
for st in STATS:
    res = []
    for i in range(ND):
        for K in KS:
            mu = np.vstack(df.loc[sc, f"A_{i}_{K}"].values)[:, j[st]]
            for al in (0.0, 0.1, 0.2, 0.35, 0.5):
                tot = 0
                for (s2, L) in MARKETS:
                    if s2 != st: continue
                    y = (df.loc[sc, "y_" + st].values > L).astype(float); tot += ll(p_over(mu, L, al), y).mean()
                res.append((tot, i, K, al))
    res.sort(); best[st] = res[0]
    log(f"scelta · {st}: DP {DPS[res[0][1]]}, K {res[0][2]}, alpha {res[0][3]}")
out = {}
for (st, L) in MARKETS:
    _, i, K, al = best[st]
    muA = np.vstack(df[f"A_{i}_{K}"].values)[:, j[st]]; mu0 = np.vstack(df["base0"].values)[:, j[st]]
    rat = df["r_" + st].astype(float).values; muB = np.where(np.isfinite(rat), muA * rat, np.nan)
    y = (df["y_" + st].values > L).astype(int)
    d = pd.DataFrame({"date": df.date, "lg": df.lg, "season": df.season, "y": y, "p0": p_over(mu0, L, al), "pA": p_over(muA, L, al),
                      "pB": np.where(np.isfinite(muB), p_over(np.nan_to_num(muB, nan=1e-3), L, al), np.nan)})
    d = d[d.pB.notna()]
    two = lambda c: [np.array([1 - q, 0.0, q]) for q in d[c].values]     # formato 1X2 dell'harness: 0 = Under/No, 2 = Over/Sì
    d2 = pd.DataFrame({"date": d.date, "lg": d.lg, "season": d.season, "y": d.y * 2, "p0": two("p0"), "pA": two("pA"), "pB": two("pB")})
    rA0 = H.confronta(d2, "p0", "pA"); rBA = H.confronta(d2, "pA", "pB")
    cal = {}
    for nm in ("pA", "pB"):
        q = d[nm].values; yy = d.y.values; hold = (d.date >= H.PERIODI["holdout"][0]).values
        bins = np.quantile(q[hold], np.linspace(0, 1, 11)); idx = np.clip(np.searchsorted(bins, q[hold]) - 1, 0, 9)
        cal[nm] = [(round(float(q[hold][idx == b].mean()), 3), round(float(yy[hold][idx == b].mean()), 3), int((idx == b).sum())) for b in range(10)]
    out[LAB[(st, L)]] = {"A_vs_0": rA0, "B_vs_A": rBA, "cal": cal, "freq": round(float(d.y.mean()), 3)}
    log(f"\n######## {LAB[(st, L)]} · frequenza reale {d.y.mean():.3f}")
    log(H.riepilogo("Modello A contro riferimento di ruolo", rA0)); log(H.riepilogo("Modello B contro Modello A", rBA))
    for nm in ("pA", "pB"): log(f"  calibrazione holdout {nm} (prevista, reale, n) per decili: {cal[nm]}")
# ---------------------------------------------------------------- bonus assenze
A = pd.DataFrame(abs_out, columns=["date", "lg", "fid", "side", "top_in", "e_sh", "y_sh", "e_sot", "y_sot"])
for stn in ("sh", "sot"):
    g = A.groupby("top_in")[["e_" + stn, "y_" + stn]].sum(); rr = (g["y_" + stn] / g["e_" + stn]).to_dict()
    rng = np.random.default_rng(3); wk = pd.to_datetime(A.date).dt.strftime("%G-%V"); W = A.assign(wk=wk).groupby(["wk", "top_in"])[["e_" + stn, "y_" + stn]].sum().unstack()
    W = W.dropna(); bs = []
    for _ in range(2000):
        s = W.iloc[rng.integers(0, len(W), len(W))]
        bs.append(s[("y_" + stn, False)].sum() / s[("e_" + stn, False)].sum() - s[("y_" + stn, True)].sum() / s[("e_" + stn, True)].sum())
    lo, hi = np.percentile(bs, [2.5, 97.5])
    n_abs = int((~A.top_in).groupby(A.fid).any().sum())
    log(f"\nBonus assenze · {stn}: reali/attesi degli altri centrocampisti e attaccanti titolari · con il tiratore principale {rr.get(True, float('nan')):.3f} · senza {rr.get(False, float('nan')):.3f} "
        f"· differenza {rr.get(False, 0) - rr.get(True, 0):+.3f} (IC95 {lo:+.3f} / {hi:+.3f}) · partite-squadra senza: {A[~A.top_in].groupby(['fid','side']).ngroups}, con: {A[A.top_in].groupby(['fid','side']).ngroups}")
json.dump({"mercati": out, "parametri": {s: {"DP": DPS[best[s][1]], "K": best[s][2], "alpha": best[s][3]} for s in STATS}}, open(os.path.join(R, "props_esito.json"), "w"), default=str)
