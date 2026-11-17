"""Gol attesi V2 (17/11/2026, Denny, fase 4): versione candidata CONGELATA e verifiche prima dell'integrazione.
V2 = M0 × e^(C0 + C1·FS_squadra + C2·FC_avversaria), poi matrice dei risultati con Dixon-Coles (rho unico del mese).
  FS = ln[(tiri in porta FATTI dalla squadra nelle sue ultime 10 partite di campionato + K·m) / (partite con il dato + K) / m]
  FC = ln[(tiri in porta CONCESSI dall'avversaria nelle sue ultime 10 partite di campionato + K·m) / (partite con il dato + K) / m]
  m = tiri in porta per squadra a partita nel campionato (365 giorni) = (gol medi casa + fuori) / 2 / (gol per tiro in porta), come M0
  ultime 10 = ultime 10 partite giocate nello stesso campionato (anche stagioni precedenti), di qualunque sede, con data precedente al giorno
  della partita; si contano solo quelle con i tiri in porta; con meno partite pesa di più la media (K = 320 partite fittizie).
  rho del mese = massima verosimiglianza Dixon-Coles su tutte le partite (31 campionati) giocate PRIMA del mese, con i λ della V2.
Uso: python tools/p2/gol_v2.py → verifiche a schermo, tools/p2/gol_v2_congelata.json (formula, coefficienti, rho per mese)."""
import sys, os, json, math, numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(__file__)); from gol_eval import *
REPO = os.path.join(os.path.dirname(__file__), "..", "..")
C0, C1, C2, KF, NF = 0.0084, 6.4771, 2.5448, 320, 10
def form_terms(d):
    m = (d.muH + d.muA) / 2 / d.conv
    f = lambda s, n: np.log((s + KF * m) / (n + KF) / m)
    return f(d.sf10H, d.ns10H), f(d.sa10A, d.ns10A), f(d.sf10A, d.ns10A), f(d.sa10H, d.ns10H)
def v2(d):
    fsH, fcA, fsA, fcH = form_terms(d)
    return d.lh0 * np.exp(C0 + C1 * fsH + C2 * fcA), d.la0 * np.exp(C0 + C1 * fsA + C2 * fcH)
def rho_table(d, lh, la):
    d = d.assign(mese=d.date.dt.to_period("M"), lh=lh, la=la); T = {}
    for mo in sorted(d.mese.unique()) + [d.mese.max() + 1]:
        p = d[d.mese < mo]; T[str(mo)] = round(float(fit_rho(p.lh, p.la, p.yh, p.ya)), 4) if len(p) >= 1000 else 0.0
    return T
if __name__ == "__main__":
    df = pd.read_pickle(os.path.join(REPO, "ricerca", "gol", "feat.pkl")).sort_values(["d", "lg"]).reset_index(drop=True)
    lh, la = v2(df)
    fsH, fcA, fsA, fcH = form_terms(df)
    print("== Forma: partite disponibili tra le ultime 10 (con i tiri in porta)")
    n = np.r_[df.ns10H, df.ns10A]; print("  quota con 10:", round((n == 10).mean() * 100, 1), "% · con 0:", round((n == 0).mean() * 100, 2), "% · media", round(n.mean(), 2))
    mult = np.r_[np.exp(C0 + C1 * fsH + C2 * fcA), np.exp(C0 + C1 * fsA + C2 * fcH)]
    print("== Fattore V2/M0 su λ: percentili 0,1/1/5/50/95/99/99,9 e min/max:", np.round(np.percentile(mult, [0.1, 1, 5, 50, 95, 99, 99.9]), 3), round(mult.min(), 3), round(mult.max(), 3))
    L0, L2 = np.r_[df.lh0, df.la0], np.r_[lh, la]
    print("== λ M0 min/max", round(L0.min(), 3), round(L0.max(), 3), "· λ V2 min/max", round(L2.min(), 3), round(L2.max(), 3), "· λ V2 > 4:", int((L2 > 4).sum()), "· < 0,2:", int((L2 < 0.2).sum()))
    # doppio uso dell'informazione: correlazione con il rating strutturale (log tiri in porta attesi di M0) e con l'Elo
    ltp = np.r_[np.log(df.tpH), np.log(df.tpA)]; fs = np.r_[fsH, fsA]; fc = np.r_[fcA, fcH]; ed = np.r_[df.ed, -df.ed]
    print("== Correlazioni: FS~log(tiri in porta attesi M0)", round(np.corrcoef(fs, ltp)[0, 1], 3), "· FC~log tp", round(np.corrcoef(fc, ltp)[0, 1], 3),
          "· FS~FC", round(np.corrcoef(fs, fc)[0, 1], 3), "· FS~Elo", round(np.corrcoef(fs, ed)[0, 1], 3))
    X = np.column_stack([ltp, ed, fs, fc]); R2 = []
    for j in range(4):
        A = np.column_stack([np.ones(len(X)), np.delete(X, j, 1)]); b = np.linalg.lstsq(A, X[:, j], rcond=None)[0]; r = X[:, j] - A @ b
        R2.append(1 - r.var() / X[:, j].var())
    print("== VIF (log tp, Elo, FS, FC):", [round(1 / (1 - r), 2) for r in R2])
    # stima di controllo dei coefficienti con l'offset (scelta) e intervalli
    sc = (df.per == "scelta").values
    A = np.vstack([np.column_stack([np.ones(sc.sum()), fsH[sc], fcA[sc]]), np.column_stack([np.ones(sc.sum()), fsA[sc], fcH[sc]])])
    y = np.r_[df.yh[sc], df.ya[sc]]; off = np.r_[np.log(df.lh0[sc]), np.log(df.la0[sc])]; b = pois_fit(A, y, offset=off)
    mu = np.exp(off + A @ b); cov = np.linalg.inv((A.T * mu) @ A); se = np.sqrt(np.diag(cov))
    print("== Coefficienti (scelta):", np.round(b, 4), "errore standard", np.round(se, 4), "· congelati", (C0, C1, C2))
    # stessa stima nei soli dati di verifica (stabilità, non usata per scegliere)
    vf = (df.per == "verifica").values
    A2 = np.vstack([np.column_stack([np.ones(vf.sum()), fsH[vf], fcA[vf]]), np.column_stack([np.ones(vf.sum()), fsA[vf], fcH[vf]])])
    b2 = pois_fit(A2, np.r_[df.yh[vf], df.ya[vf]], offset=np.r_[np.log(df.lh0[vf]), np.log(df.la0[vf])])
    print("== Coefficienti stimati sulla sola verifica (controllo di stabilità):", np.round(b2, 4))
    # rho per mese con i λ V2 (solo partite precedenti al mese)
    T = rho_table(df, lh, la)
    print("== rho per mese (ultimi 8):", list(T.items())[-8:])
    rho = df.date.dt.to_period("M").astype(str).map(T).values
    # Dixon-Coles: controlli matematici sulla matrice
    M = matrices(lh.values[:2000], la.values[:2000], rho[:2000]); M0 = matrices(lh.values[:2000], la.values[:2000])
    print("== DC: somma matrice", float(np.abs(M.sum((1, 2)) - 1).max()), "· marginali casa uguali alla Poisson (max diff)", float(np.abs(M.sum(2) - M0.sum(2)).max()),
          "· marginali ospite", float(np.abs(M.sum(1) - M0.sum(1)).max()), "· celle negative", int((M < 0).sum()))
    X0 = metrics(df, df.lh0, df.la0); X2 = metrics(df, lh, la, rho)
    for key in ("ll_score", "ll_1x2", "br_1x2", "ll_o25"):
        R = compare(df, X0, X2, key); print(f"  V2 congelata contro M0 {key:8}", " | ".join(f"{p[:3]} {R[p]['diff']:+.5f} [{R[p]['lo']:+.5f},{R[p]['hi']:+.5f}] {R[p]['camp']}" for p in R))
    json.dump({"congelata": "2026-11-17", "formula": "λ = λ_M0 · exp(C0 + C1·FS_squadra + C2·FC_avversaria); FS/FC = ln[(tiri in porta fatti/concessi nelle ultime 10 + K·m)/(partite con il dato + K)/m]; Dixon-Coles con rho del mese",
               "C0": C0, "C1": C1, "C2": C2, "K": KF, "N": NF, "rho_per_mese": T,
               "stima": "coefficienti stimati sul periodo scelta (fino al 30/6/2024), offset log λ_M0, 25.678 partite; rho per mese su tutte le partite precedenti al mese"},
              open(os.path.join(os.path.dirname(__file__), "gol_v2_congelata.json"), "w"), indent=1, ensure_ascii=False)
