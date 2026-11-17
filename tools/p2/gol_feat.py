"""Gol attesi · fase 3: tabella delle caratteristiche walk-forward (solo dati dei giorni precedenti a ogni partita) per tutti gli esperimenti.
Una riga per partita giocata con il rating dei tiri in porta disponibile (M0 "gdyn"): parti di M0 e caratteristiche candidate.
  M0: muH, muA (gol medi di lega 365 gg), tpH, tpA (gol dai tiri in porta), ed (Elo/100), we (Elo presente), qxh, qxa (qualità tiri), lh0/la0 = λ app
  M1 (volume e precisione): tiri attesi (rating tiri totali att × dif, 4 anni, τ 365, P 4) e tiri in porta attesi (stesso rating di M0, senza conversione);
      tiri in area attesi (rating 365 gg come la qualità dei tiri); conversione della squadra (gol / tiri in porta, pesata τ 365) con i totali grezzi
  M2 (difesa): conversione concessa (gol subiti / tiri in porta concessi), totali grezzi; i tiri concessi sono già nei rating att × dif
  M3 (forma): gol, tiri in porta, tiri fatti e concessi nelle ultime 5 e 10 partite (somme grezze e numero di partite)
  M4 (livello): gol medi di lega 120 gg, della stagione in corso (partite e somma), della stessa giornata dello scorso anno no.
Le prudenze (shrinkage) si applicano negli esperimenti, scelte nel periodo "scelta". Uscita: ricerca/gol/feat.pkl"""
import sys, os, math, numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(__file__)); from gol_lib import *

TA = load_tarea(); rows = []
codes = sorted(f[:-5] for f in os.listdir(os.path.join(REPO, "ricerca", "gol")) if f.endswith(".json"))
for c in codes:
    L = League(c, TA)
    order = np.argsort(L.d, kind="stable")
    hasS = ~np.isnan(L.hst) & ~np.isnan(L.ast); hasT = ~np.isnan(L.hs) & ~np.isnan(L.as_)
    # storico per squadra (partite giocate, in ordine): data, gol fatti, subiti, tiri in porta fatti, concessi, tiri fatti, concessi
    TH = {}
    for i in order:
        if not L.played[i]: continue
        for t, gf, ga, sf, sa, tf, ta in ((L.h[i], L.hg[i], L.ag[i], L.hst[i], L.ast[i], L.hs[i], L.as_[i]), (L.a[i], L.ag[i], L.hg[i], L.ast[i], L.hst[i], L.as_[i], L.hs[i])):
            TH.setdefault(t, []).append((L.d[i], gf, ga, sf, sa, tf, ta))
    TH = {t: np.array(v, float) for t, v in TH.items()}
    shot_cache = {}
    def shots_fit(D):
        if D not in shot_cache:
            m = hasT & L.played & (L.d < D) & (L.d >= D - GD_LOOK)
            if m.sum() < 50: shot_cache[D] = None
            else:
                vh = np.where(hasT, L.hs, 0.0); va = np.where(hasT, L.as_, 0.0)
                # stesso rating di M0 sui tiri totali (solo partite con i tiri)
                sav = L.played.copy(); L.played = L.played & hasT
                try: shot_cache[D] = L.rating(D, vh, va, GD_TAU, GD_P, GD_LOOK, False)
                finally: L.played = sav
        return shot_cache[D]
    for i in order:
        if not L.played[i]: continue
        D = L.d[i]; h, a = L.h[i], L.a[i]
        r = L.m0(D, h, a, parts=True)
        if r is None or r[2]["src"] != "gdyn": continue
        lh0, la0, P = r
        F = L.gdyn_fit(D); ih, ia = L.tid[h], L.tid[a]
        row = dict(lg=c, d=int(D), se=int(L.se[i]), h=h, a=a, yh=L.hg[i], ya=L.ag[i], ysh=L.hst[i], ysa=L.ast[i],
                   lh0=lh0, la0=la0, muH=P["muH"], muA=P["muA"], tpH=P["tpH"], tpA=P["tpA"], ed=P["ed"], we=P["we"], conv=P["conv"],
                   qxh=P["qx"][0] if P["qx"] else np.nan, qxa=P["qx"][1] if P["qx"] else np.nan,
                   esH=F["sH"] * F["att"][ih] * F["de"][ia], esA=F["sA"] * F["att"][ia] * F["de"][ih])
        S = shots_fit(D)
        if S: row.update(etH=S["sH"] * S["att"][ih] * S["de"][ia], etA=S["sA"] * S["att"][ia] * S["de"][ih])
        Q = L.qual_fit(D)
        if Q:
            z = np.zeros(5); g = lambda t: Q["acc"][L.qid[t]] if t in L.qid else z
            rr = lambda v, w, mm: (v + Q_P * mm) / (w + Q_P) / mm
            gh, ga_ = g(h), g(a)
            row.update(eiH=Q["mi"] * rr(gh[0], gh[4], Q["mi"]) * rr(ga_[1], ga_[4], Q["mi"]), eiA=Q["mi"] * rr(ga_[0], ga_[4], Q["mi"]) * rr(gh[1], gh[4], Q["mi"]))
        # conversione pesata (τ 365, 4 anni) fatta e concessa, totali grezzi
        for side, t in (("H", h), ("A", a)):
            X = TH.get(t)
            if X is None: continue
            pm = X[:, 0] < D
            Xp = X[pm]
            ok = ~np.isnan(Xp[:, 3]) & (Xp[:, 0] >= D - GD_LOOK)
            w = np.exp(-np.round(D - Xp[ok, 0]) / GD_TAU)
            row["cg" + side] = (w * Xp[ok, 1]).sum(); row["cs" + side] = (w * Xp[ok, 3]).sum()          # gol fatti, tiri in porta fatti
            row["kg" + side] = (w * Xp[ok, 2]).sum(); row["ks" + side] = (w * Xp[ok, 4]).sum()          # gol subiti, tiri in porta concessi
            for N in (5, 10):
                Z = Xp[-N:]
                row[f"n{N}{side}"] = len(Z)
                row[f"gf{N}{side}"] = np.nansum(Z[:, 1]); row[f"ga{N}{side}"] = np.nansum(Z[:, 2])
                zs = Z[~np.isnan(Z[:, 3])]; row[f"ns{N}{side}"] = len(zs)
                row[f"sf{N}{side}"] = zs[:, 3].sum(); row[f"sa{N}{side}"] = zs[:, 4].sum()
        # livello del campionato
        m120 = L.played & (L.d < D) & (L.d >= D - 120)
        row["n120"] = int(m120.sum()); row["g120"] = float(L.hg[m120].sum() + L.ag[m120].sum())
        msea = L.played & (L.d < D) & (L.se == L.se[i])
        row["nse"] = int(msea.sum()); row["gse"] = float(L.hg[msea].sum() + L.ag[msea].sum())
        rows.append(row)
    print(c, len(rows), flush=True)
df = pd.DataFrame(rows)
df["date"] = pd.to_datetime(df.d, unit="D")
df["per"] = np.where(df.date <= "2024-06-30", "scelta", np.where(df.date <= "2025-06-30", "verifica", "holdout"))
df.to_pickle(os.path.join(REPO, "ricerca", "gol", "feat.pkl"))
print(df.groupby("per").size(), df.date.min(), df.date.max())
