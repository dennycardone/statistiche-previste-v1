"""Corner V2 · controlli statistici chiesti da Denny prima della prova in ombra (18/11/2026). Solo analisi.
1) intervalli al 99% con bootstrap a grappoli diversi: settimana (quello dell'audit), campionato-stagione (dipendenza tra partite della stessa
   squadra, campionato e periodo: le squadre stanno dentro il campionato-stagione), campionato intero (il più prudente);
2) correzione per la scelta tra 3 varianti (Bonferroni: intervallo al 99,67%);
3) copertura di tiri e tiri in porta per campionato e stagione (archivio API) e quota di partite dell'app con storia sufficiente.
Uscita: ricerca/corner/controlli.json"""
import os
src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "corner_audit.py")).read()
exec(src[:src.index("# ================= 1. modello attuale")])
J["h_contrH"] = np.log(J.l0h / J.mH_c); J["a_contrH"] = 0.0; J["h_contrA"] = 0.0; J["a_contrA"] = np.log(J.l0a / J.mA_c)
VARS = {"tiri_porta+contrazione": ["att_st", "def_st", "contrH", "contrA"], "tiri+contrazione": ["att_s", "def_s", "contrH", "contrA"],
        "tiri+tiri_porta+contrazione (candidato)": ["att_s", "def_s", "att_st", "def_st", "contrH", "contrA"]}
b0, _, lhC, laC = fit(np.zeros((len(J), 0)), np.zeros((len(J), 0)), J.l0h.values, J.l0a.values); XC = metrics(lhC, laC)
def cboot(d, g, B=2000, q=(0.5, 99.5), seed=11):
    s = pd.Series(d).groupby(g); S_ = s.sum().values; C = s.count().values; rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(S_), (B, len(S_))); bs = S_[idx].sum(1) / C[idx].sum(1); return [round(float(np.percentile(bs, q[0])), 6), round(float(np.percentile(bs, q[1])), 6)]
OUTR = {"metodo": "differenza per partita (candidato − app con costante), media; bootstrap percentile su grappoli ricampionati con reinserimento (2.000 repliche)"}
for nm, ff in VARS.items():
    b, se, lh, la = fit(*fx(ff), J.l0h.values, J.l0a.values); X = metrics(lh, la); OUTR[nm] = {}
    for key in ("ll_team", "ll_tot", "ll_1x2", "br_ou"):
        OUTR[nm][key] = {}
        for p in PER:
            m = M[p]; d = (X[key] - XC[key]).values[m]; G = J[m]
            OUTR[nm][key][p] = dict(diff=round(float(d.mean()), 6),
                                    settimana_99=cboot(d, G.wk.values), settimana_99_67=cboot(d, G.wk.values, q=(0.1667, 99.8333)),
                                    camp_stagione_99=cboot(d, (G.lg + "|" + G.se.astype(str)).values), camp_stagione_99_67=cboot(d, (G.lg + "|" + G.se.astype(str)).values, q=(0.1667, 99.8333)),
                                    campionato_99=cboot(d, G.lg.values), n_grappoli=dict(settimane=int(G.wk.nunique()), camp_stagione=int((G.lg + G.se.astype(str)).nunique()), campionati=int(G.lg.nunique())))
        log(nm, key, json.dumps(OUTR[nm][key]))
# copertura
S = pd.read_pickle(os.path.join(OUT, "storico.pkl")); S = S[S.lg.isin(J.lg.unique())]
cov = S.groupby(["lg", "se"]).apply(lambda g: pd.Series(dict(partite=len(g), tiri=round(float(g.hs.notna().mean() * 100), 1), tiri_porta=round(float(g.hst.notna().mean() * 100), 1))), include_groups=False).reset_index()
OUTR["copertura_archivio"] = cov.to_dict("records")
OUTR["copertura_campionato"] = S.groupby("lg").apply(lambda g: dict(partite=len(g), tiri=round(float(g.hs.notna().mean() * 100), 1), tiri_porta=round(float(g.hst.notna().mean() * 100), 1)), include_groups=False).to_dict()
json.dump(OUTR, open(os.path.join(OUT, "controlli.json"), "w"), indent=1, ensure_ascii=False, default=float)
log("fatto")
