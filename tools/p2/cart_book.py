"""Cartellini · tabellone finale sulle linee dei book archiviate (20/11/2026). Il book non entra nei modelli: qui si guarda solo come
si comportano le giocate dell'app e delle varianti (stesse regole del Mercato: lato della lettura, probabilità ≥ 65%, valore ≥ 5%).
Ingresso: ricerca/cartellini/feat.pkl + varianti.pkl (cart_studio.py), pagine pubblicate data/linee.json ed extra.json (abbinamento delle
partite per campionato, data, cartellini reali e arbitro). Uso: python cart_book.py CARTELLA_DATI_PAGINE"""
import os, sys, json, numpy as np, pandas as pd
from scipy.stats import nbinom, poisson
REPO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."); OUT = os.path.join(REPO, "ricerca", "cartellini"); DATA = sys.argv[1]
B = pd.read_pickle(os.path.join(OUT, "feat.pkl")); V = pd.read_pickle(os.path.join(OUT, "varianti.pkl"))
E = json.load(open(os.path.join(DATA, "extra.json")))["partite"]; L = json.load(open(os.path.join(DATA, "linee.json")))["partite"]
ex = {}
for k, x in E.items():
    if x[5] is None: continue
    lg, d = k.split("|")[:2]; ex.setdefault((lg, d, int(x[5]), (x[0] or "").split(" ")[-1].lower()), []).append(k)
idx, keys = [], []
for i, r in enumerate(B.itertuples(index=False)):
    ref = (r.ref if isinstance(r.ref, str) else "").split(",")[0].split(" ")[-1].lower(); v = ex.get((r.lg, r.d, int(r.T), ref))
    if v and len(v) == 1 and v[0] in L: idx.append(i); keys.append(v[0])
idx = np.array(idx); print("partite con linee e risultato:", len(idx))
def plays(name, mu, mh, ma, rT):
    out = []
    r_tot = 1 / B.alpha.values
    for j, (i, k) in enumerate(zip(idx, keys)):
        b = L[k].get("mb") or L[k]
        for mk, m_, rr, y in (("k", mu[i], r_tot[i], B["T"].values[i]), ("hk", mh[i], rT[i], B.yh.values[i]), ("ak", ma[i], rT[i], B.ya.values[i])):
            c = b.get(mk)
            if not c: continue
            Lk, o, u = c[0], c[1], c[2]; po = 1 - (nbinom.cdf(np.floor(Lk), rr, rr / (rr + m_)) if np.isfinite(rr) else poisson.cdf(np.floor(Lk), m_))
            side = "O" if po >= 0.5 else "U"; p = po if side == "O" else 1 - po; q = o if side == "O" else u; ev = p * q - 1
            hit = (y > Lk) if side == "O" else (y < Lk)
            out.append(dict(mk=mk, side=side, p=p, q=q, ev=ev, hit=hit, d=B.d.values[i]))
    P = pd.DataFrame(out); S = P[(P.p >= 0.65) & (P.ev >= 0.05)]
    res = dict(linee=len(P), giocate=len(S), under=round(float((S.side == "U").mean() * 100), 1) if len(S) else None, presa=round(float(S.hit.mean() * 100), 1) if len(S) else None,
               dichiarata=round(float(S.p.mean() * 100), 1) if len(S) else None, rendimento=round(float(np.where(S.hit, S.q - 1, -1).mean() * 100), 1) if len(S) else None,
               per_mercato={mk: dict(n=int(len(g)), presa=round(float(g.hit.mean() * 100), 1), dichiarata=round(float(g.p.mean() * 100), 1), rendimento=round(float(np.where(g.hit, g.q - 1, -1).mean() * 100), 1)) for mk, g in S.groupby("mk")},
               tutte_le_linee=dict(lettura_presa=round(float(P.hit.mean() * 100), 1), dichiarata=round(float(P.p.mean() * 100), 1)))
    print(name, json.dumps(res, ensure_ascii=False)); return res
rA = 1 / B.alpha.values; INF = np.full(len(B), np.inf)
R = {"app": plays("app", B.mu.values, B.mh.values, B.ma.values, rA)}
for nm in ("A rec30", "D sede"):
    v = V[nm]; R[nm] = plays(nm, v["mu"], v["mh"], v["ma"], rA)
for nm in ("F contrazione",):
    v = V[nm]; R[nm] = plays(nm, v["mu"], v["mh"], v["ma"], rA)
for nm in ("F + E", "F + A30 + E"):
    v = V[nm]; R[nm] = plays(nm, v["mu"], v["mh"], v["ma"], INF)
R["E r squadra (Poisson)"] = plays("E Poisson squadre", B.mu.values, B.mh.values, B.ma.values, INF)
v = V["A rec30"]; R["A rec30 + E"] = plays("A rec30 + E", v["mu"], v["mh"], v["ma"], INF)
G = B.iloc[idx]; R["livello"] = dict(atteso=round(float(G.mu.mean()), 3), reale=round(float(G["T"].mean()), 3), campionati=G.lg.value_counts().head(12).to_dict())
print(R["livello"]); json.dump(R, open(os.path.join(OUT, "tabellone_book.json"), "w"), indent=1, ensure_ascii=False, default=float)
