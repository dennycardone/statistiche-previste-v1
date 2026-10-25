import sys, numpy as np, pandas as pd
sys.argv = ["x", "feat2.pkl"]
src = open("test1a.py").read().split("REP = {}")[0]
exec(src)
POLD = {}
feats = ["own:xi_fc", "opp:xi_fd", "own:xi_crd"]
T = team_table("f", feats, "xi"); T2, co = H.walk_forward(T, feats, r=200)
PP = probs("f", T2)
for per, (a, b) in H.PERIODI.items():
    d = PP[(PP.date >= a) & (PP.date <= b)]
    for lab, col in (("app", "p_old"), ("con formazioni", "p_new")):
        P = np.vstack(d[col].values); y = d.y.values
        fav = np.where(P[:, 0] >= P[:, 2], 0, 2); pf = P[np.arange(len(P)), fav]
        for th in (0.65, 0.70, 0.75):
            m = pf >= th
            print(f"{per:9s} {lab:15s} soglia {th:.2f}: {m.sum():5d} segnali, presi {(y[m] == fav[m]).mean()*100:5.1f}% (attesi {pf[m].mean()*100:5.1f}%)")
