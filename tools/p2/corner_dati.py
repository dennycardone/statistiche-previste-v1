"""Corner · preparazione dei dati per l'audit (18/11/2026, Denny). Solo analisi: nessuna modifica all'app.
Ingressi: ricerca/base (corner attesi dell'app con i soli dati precedenti, partite dal 2023), ricerca/storico (API-Football: tutte le partite
di campionato dal 2022 con tiri, tiri in porta, corner, xG), ricerca/sx (statistiche in più per partita: tiri bloccati, in area, possesso).
Per ogni partita dell'app costruisce caratteristiche SOLO dalle partite precedenti (giorno prima o prima ancora), con le medie del campionato
per sede degli ultimi 365 giorni come riferimento. Uscita: ricerca/corner/feat.pkl + copertura.json."""
import os, sys, json, glob, collections, numpy as np, pandas as pd
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lab"))
from comune import RIC, per
OUT = os.path.join(RIC, "corner"); os.makedirs(OUT, exist_ok=True)
log = lambda *a: print(*a, flush=True)
# indici delle statistiche in più (tools/extra_stats_apifootball.py, KS)
SX = {"bl": 9, "ib": 7, "po": 11, "xg": 6}
sx = {}
for f in glob.glob(os.path.join(RIC, "sx", "*.json")):
    for fid, r in json.load(open(f)).items():
        if r[3] and r[4]: sx[fid] = (r[3], r[4])
# ---------------- archivio API (tutte le partite di campionato dal 2022)
S, COV = [], []
for f in glob.glob(os.path.join(RIC, "storico", "*_20*.json")):
    D = json.load(open(f)); lg = D.get("lega") or os.path.basename(f).split("_")[0]
    if lg in ("UCL", "UEL", "UECL", "ucl", "uel"): continue
    n = nc = 0
    for fid, v in D["partite"].items():
        if v[3] is None or v[4] is None: continue
        n += 1; sh, sa = v[6], v[7]
        ok = bool(sh and sa and sh[2] is not None and sa[2] is not None)
        nc += ok
        if not ok: continue
        e = sx.get(fid)
        g = lambda t, i: (None if t is None or len(t) <= i else t[i])
        row = dict(lg=lg, se=D.get("stagione"), fid=fid, dt=v[0], d=v[0][:10], h=v[1], a=v[2], hg=v[3], ag=v[4],
                   hc=sh[2], ac=sa[2], hs=sh[0], as_=sa[0], hst=sh[1], ast=sa[1], hxg=sh[6] if len(sh) > 6 else None, axg=sa[6] if len(sa) > 6 else None)
        for k, i in SX.items():
            row["h" + k] = g(e[0], i) if e else None; row["a" + k] = g(e[1], i) if e else None
        if e and row["hxg"] is None: row["hxg"], row["axg"] = g(e[0], 6), g(e[1], 6)
        S.append(row)
    COV.append(dict(lg=lg, se=D.get("stagione"), partite=n, con_corner=nc))
S = pd.DataFrame(S); S = S[~S.fid.duplicated()].sort_values(["dt", "fid"]).reset_index(drop=True)
for c in ["hc", "ac", "hs", "as_", "hst", "ast", "hxg", "axg"] + ["h" + k for k in SX] + ["a" + k for k in SX]: S[c] = pd.to_numeric(S[c], errors="coerce")
log("archivio API: partite con corner", len(S))
# ---------------- medie del campionato per sede, ultimi 365 giorni (solo partite di giorni precedenti)
S["t"] = (pd.to_datetime(S.d) - pd.Timestamp("1970-01-01")).dt.days.astype(int)
STATS = {"c": ("hc", "ac"), "s": ("hs", "as_"), "st": ("hst", "ast"), "xg": ("hxg", "axg"), "bl": ("hbl", "abl"), "ib": ("hib", "aib"), "po": ("hpo", "apo")}
for k, (a, b) in STATS.items():
    S["mH_" + k] = np.nan; S["mA_" + k] = np.nan
for lg, G in S.groupby("lg"):
    t = G.t.values
    for k, (a, b) in STATS.items():
        for col, src in (("mH_" + k, a), ("mA_" + k, b)):
            v = G[src].values.astype(float); ok = ~np.isnan(v)
            cs = np.r_[0, np.cumsum(np.where(ok, v, 0))]; cn = np.r_[0, np.cumsum(ok)]
            lo = np.searchsorted(t, t - 365, "left"); hi = np.searchsorted(t, t, "left")   # [t-365, t): giorni precedenti
            n = cn[hi] - cn[lo]; s = cs[hi] - cs[lo]
            S.loc[G.index, col] = np.where(n >= 30, s / np.maximum(n, 1), np.nan)
# ---------------- storia di ogni squadra (partite di campionato precedenti)
KEYS = ["c", "s", "st", "xg", "bl", "ib", "po"]
H = collections.defaultdict(list)    # (lg, squadra) -> lista di record
feat = {}
def ratio(rec, k, side, n=None, days=None, t=None, venue=None, K=3.0, hl=None):
    """rapporto con shrinkage: (Σ valore + K·ē) / (Σ atteso + K·ē); side 'f' fatti, 'a' concessi"""
    R = rec
    if venue is not None: R = [r for r in R if r["v"] == venue]
    if days is not None: R = [r for r in R if t - r["t"] <= days]
    if n is not None: R = R[-n:]
    R = [r for r in R if r[k + side] is not None and r["e" + k + side] is not None and not np.isnan(r[k + side]) and not np.isnan(r["e" + k + side])]
    if not R: return 0.0, 0
    w = np.array([0.5 ** ((t - r["t"]) / hl) for r in R]) if hl else np.ones(len(R))
    y = np.array([r[k + side] for r in R]); e = np.array([r["e" + k + side] for r in R]); eb = (w * e).sum() / w.sum()
    return float(np.log(((w * y).sum() + K * eb) / ((w * e).sum() + K * eb))), len(R)
def poss(rec, n=10, K=3.0):
    R = [r for r in rec[-n:] if r["pof"] is not None and r["epof"] is not None and not np.isnan(r["pof"]) and not np.isnan(r["epof"])]
    if not R: return 0.0, 0
    return float(sum(r["pof"] - r["epof"] for r in R) / (len(R) + K) / 100.0), len(R)
for i, m in enumerate(S.itertuples(index=False)):
    ht, at = (m.lg, m.h), (m.lg, m.a)
    F = {}
    for side_team, key, opp, ven in (("h", ht, at, "H"), ("a", at, ht, "A")):
        T, O = H[key], H[opp]; t = m.t
        x = {}
        x["n"] = len([r for r in T if t - r["t"] <= 365])
        x["att365"], _ = ratio(T, "c", "f", days=365, t=t, K=5); x["def365"], _ = ratio(O, "c", "a", days=365, t=t, K=5)
        x["att5"], _ = ratio(T, "c", "f", n=5, t=t, K=3); x["def5"], _ = ratio(O, "c", "a", n=5, t=t, K=3)
        x["att10"], _ = ratio(T, "c", "f", n=10, t=t, K=3); x["def10"], _ = ratio(O, "c", "a", n=10, t=t, K=3)
        x["attE"], _ = ratio(T, "c", "f", days=365, t=t, K=3, hl=60); x["defE"], _ = ratio(O, "c", "a", days=365, t=t, K=3, hl=60)
        # sede: rapporto nella stessa sede meno rapporto in tutte le sedi (positivo = squadra che in quella sede ne batte di più del suo solito)
        oven = "A" if ven == "H" else "H"
        a_v, _ = ratio(T, "c", "f", days=365, t=t, venue=ven, K=5); d_v, _ = ratio(O, "c", "a", days=365, t=t, venue=oven, K=5)
        x["attV"] = a_v - x["att365"]; x["defV"] = d_v - x["def365"]
        for k in ("s", "st", "xg", "bl", "ib"):
            x["att_" + k], _ = ratio(T, k, "f", n=10, t=t, K=3); x["def_" + k], _ = ratio(O, k, "a", n=10, t=t, K=3)
        pT, npT = poss(T); pO, npO = poss(O); x["poss"] = (pT - pO) / 2; x["n_po"] = min(npT, npO)
        F[side_team] = x
    feat[m.fid] = F
    # aggiunge la partita alla storia delle due squadre (dopo aver calcolato le caratteristiche)
    for key, v, fs, ag in ((ht, "H", "h", "a"), (at, "A", "a", "h")):
        r = {"t": m.t, "v": v}
        for k, (a, b) in STATS.items():
            cf, ca = (getattr(m, a), getattr(m, b)) if fs == "h" else (getattr(m, b), getattr(m, a))
            ef, ea = (getattr(m, "mH_" + k), getattr(m, "mA_" + k)) if fs == "h" else (getattr(m, "mA_" + k), getattr(m, "mH_" + k))
            r[k + "f"], r[k + "a"], r["e" + k + "f"], r["e" + k + "a"] = cf, ca, ef, ea
        H[key].append(r)
        if len(H[key]) > 80: H[key] = H[key][-80:]
    if i % 20000 == 0: log("caratteristiche", i, "/", len(S))
# ---------------- previsioni dell'app (base) unite all'archivio: stessa lega, data, gol, corner e tiri
B = []
for f in glob.glob(os.path.join(RIC, "base", "*.json")):
    lg = os.path.basename(f)[:-5]
    for m in json.load(open(f)):
        y = m.get("y") or {}; c = m.get("c"); yc = y.get("c"); yg = y.get("g"); ys = y.get("s") or [None, None]
        B.append(dict(lg=lg, d=m["d"], se_app=m.get("se"), h_app=m["h"], a_app=m["a"], has_c=bool(c and c[0] is not None), has_y=bool(yc and yc[0] is not None and yc[1] is not None),
                      l0h=c[0] if c else np.nan, l0a=c[1] if c else np.nan, yh=yc[0] if yc else np.nan, ya=yc[1] if yc else np.nan,
                      ygh=yg[0] if yg else np.nan, yga=yg[1] if yg else np.nan, ysh=ys[0], ysa=ys[1],
                      gh=(m.get("g") or [np.nan, np.nan])[0], ga=(m.get("g") or [np.nan, np.nan])[1]))
B = pd.DataFrame(B)
cov_app = B.groupby("lg").agg(partite=("d", "size"), con_previsione=("has_c", "sum"), con_reale=("has_y", "sum")).reset_index()
B = B[B.has_c & B.has_y & B.ygh.notna()].copy()
for c in ("yh", "ya", "ygh", "yga"): B[c] = B[c].astype(int)
key = lambda lg, d, a, b, c, e: lg + "|" + d + "|" + a.astype(int).astype(str) + "-" + b.astype(int).astype(str) + "|" + c.astype(int).astype(str) + "-" + e.astype(int).astype(str)
S["k"] = key(S.lg, S.d, S.hg, S.ag, S.hc, S.ac); B["k"] = key(B.lg, B.d, B.ygh, B.yga, B.yh, B.ya)
S1 = S[~S.k.duplicated(keep=False)]; B1 = B[~B.k.duplicated(keep=False)]
J = B1.merge(S1[["k", "fid", "dt", "h", "a", "se", "t"] + [c for c in S.columns if c.startswith("mH_") or c.startswith("mA_")]], on="k", how="inner")
rows = []
for r in J.itertuples(index=False):
    F = feat[r.fid]; o = {"fid": r.fid}
    for s in ("h", "a"):
        for k, v in F[s].items(): o[s + "_" + k] = v
    rows.append(o)
J = J.merge(pd.DataFrame(rows), on="fid").sort_values(["d", "lg", "fid"]).reset_index(drop=True)
J["per"] = J.d.map(per); J["wk"] = (pd.to_datetime(J.d) - pd.Timestamp("1970-01-01")).dt.days // 7
log("app con corner (previsione e reale):", len(B), "· unite all'archivio:", len(J), J.per.value_counts().to_dict())
# ---------------- copertura e anomalie
C = pd.DataFrame(COV).groupby(["lg", "se"]).sum().reset_index()
an = dict(squadra_0=int(((S.hc == 0) | (S.ac == 0)).sum()), squadra_ge20=int(((S.hc >= 20) | (S.ac >= 20)).sum()), totale_0=int(((S.hc + S.ac) == 0).sum()),
          totale_ge25=int(((S.hc + S.ac) >= 25).sum()), max_squadra=int(max(S.hc.max(), S.ac.max())), max_totale=int((S.hc + S.ac).max()),
          con_tiri_bloccati=int(S.hbl.notna().sum()), con_possesso=int(S.hpo.notna().sum()), con_xg=int(S.hxg.notna().sum()),
          corner_senza_tiri=int(((S.hs.isna()) | (S.as_.isna())).sum()), corner_maggiori_tiri_0=int((((S.hs == 0) & (S.hc > 5)) | ((S.as_ == 0) & (S.ac > 5))).sum()))
# confronto fonte: corner dell'app (base, spesso football-data) e API sulla stessa partita (lega, data, gol e tiri uguali)
kk = lambda lg, d, a, b: lg + "|" + d + "|" + a.astype(int).astype(str) + "-" + b.astype(int).astype(str)
S2 = S.copy(); S2["k2"] = kk(S2.lg, S2.d, S2.hg, S2.ag) + "|" + S2.h.str[:0]
B2 = B.copy(); B2["k2"] = kk(B2.lg, B2.d, B2.ygh, B2.yga) + "|"
S2 = S2[~S2.k2.duplicated(keep=False)]; B2 = B2[~B2.k2.duplicated(keep=False)]
X = B2.merge(S2[["k2", "hc", "ac"]], on="k2")
an["coerenza_fonti"] = dict(partite_confrontate=len(X), corner_uguali=round(float(((X.yh == X.hc) & (X.ya == X.ac)).mean()) * 100, 2),
                            diff_media_assoluta=round(float((abs(X.yh - X.hc) + abs(X.ya - X.ac)).mean() / 2), 3))
json.dump({"archivio": C.to_dict("records"), "app": cov_app.to_dict("records"), "anomalie": an, "unite": len(J), "per_periodo": J.per.value_counts().to_dict(),
           "archivio_partite": int(C.partite.sum()), "archivio_con_corner": int(C.con_corner.sum())}, open(os.path.join(OUT, "copertura.json"), "w"), indent=1, default=int)
J.to_pickle(os.path.join(OUT, "feat.pkl")); S.to_pickle(os.path.join(OUT, "storico.pkl"))
log("anomalie", an)
