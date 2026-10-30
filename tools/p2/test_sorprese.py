"""Prevista 2.0 · SORPRESE sull'archivio lungo (30/10/2026, studio di Denny, passo 2). Senza quote: la "favorita sulla carta" è quella
che il modello gol di Prevista dà più forte (1X2 gol), cioè il "blasone"; la sorpresa è che vinca il mercato la sfavorita sulla carta.
Previsioni di Prevista walk-forward (ricerca/base, solo dati precedenti), regola dell'harness per qualsiasi aggiunta.

Parte 1 · Prevista vede le sorprese dei mercati statistici? Per ogni mercato (corner, tiri, tiri in porta, falli, fuorigioco), partite
con una favorita sulla carta netta (vittoria nei gol ≥ 50% e almeno 25 punti sopra l'altra):
  - quante volte vince il mercato la sfavorita sulla carta (frequenza reale);
  - "blasone": probabilità che la sfavorita vinca il mercato secondo un modello che conosce SOLO la forza nei gol (logistica walk-forward
    sulla differenza dei gol attesi) — è il prezzo di chi trascina il blasone sulle statistiche;
  - Prevista: probabilità del modello del mercato; casi di inversione (Prevista dà la sfavorita sulla carta avanti nel mercato) e
    forbice ≥ +10 punti sopra il blasone: presa reale contro dichiarata.
Parte 2 · fattori scatenanti, aggiunti a Prevista (logit(p) + fattore, pesi mese per mese, harness su "vince la sfavorita sulla carta"):
  fuorigioco · linea alta della favorita: fuorigioco provocati dalla favorita negli ultimi 90 giorni / media del campionato
  corner, tiri · piccola in casa: volume casalingo della sfavorita (ultime 8 in casa) contro quello in trasferta della favorita
                 (ultime 8 fuori), rispetto al campionato
  falli         · la formazione ufficiale è già nel modello dal 25/10 (fase 1-B): qui nessun fattore nuovo (manca il possesso storico)
  gol           · favorita "fragile" (vittoria ≥ 60%, quota equa < 1,65): (a) gol segnati contro tiri in porta delle ultime 8
                  (sovra-rendimento → regressione), (b) gol subiti contro tiri in porta concessi, (c) calo di punti: ultime 5 contro ultime 20."""
import os, sys, json, glob, math, collections, datetime
import numpy as np, pandas as pd
from scipy.stats import poisson
REPO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
P2 = os.environ.get("RICERCA", os.path.join(REPO, "ricerca"))
sys.path.insert(0, os.path.join(REPO, "tools")); import harness as H
log = lambda *a: print(*a, flush=True)
B = []
for fn in glob.glob(P2 + "/base/*.json"):
    lg = os.path.basename(fn)[:-5]
    for r in json.load(open(fn)):
        if r["y"]["g"][0] is None or not r.get("g"): continue
        r["lg"] = lg; B.append(r)
B.sort(key=lambda r: r["d"]); log("partite", len(B))
KK = np.arange(11)
def g1x2(lh, la):
    M = np.outer(poisson.pmf(KK, lh), poisson.pmf(KK, la)); M /= M.sum()
    return np.array([np.tril(M, -1).sum(), np.trace(M), np.triu(M, 1).sum()])
for r in B: r["G"] = g1x2(r["g"][0], r["g"][1])
MK = {"c": "Corner", "s": "Tiri", "st": "Tiri in porta", "f": "Falli", "o": "Fuorigioco"}
# --- stato "solo partite precedenti" per i fattori
hist = collections.defaultdict(list)    # (lg, squadra) -> [(data, casa?, per: dict mercato -> (fatti, subiti), gol fatti, gol subiti, tiri in porta fatti, concessi, punti)]
lgavg = collections.defaultdict(lambda: collections.defaultdict(lambda: [0.0, 0]))
def lgm(lg, k): a = lgavg[lg][k]; return a[0] / a[1] if a[1] else None
rows = []
for r in B:
    lg, d0 = r["lg"], datetime.date.fromisoformat(r["d"])
    G = r["G"]; fav = 0 if G[0] >= G[2] else 1; pf, pu = (G[0], G[2]) if fav == 0 else (G[2], G[0])
    hh, ha = hist[(lg, r["h"])], hist[(lg, r["a"])]
    feats = {}
    if pf >= 0.5 and pf - pu >= 0.25:
        F, U = (hh, ha) if fav == 0 else (ha, hh)
        # fuorigioco provocati dalla favorita (offside degli avversari) negli ultimi 90 giorni
        o_prov = [x["per"]["o"][1] for x in F if (d0 - x["d"]).days <= 90 and x["per"].get("o") and x["per"]["o"][1] is not None]
        if len(o_prov) >= 4 and lgm(lg, "o"): feats["x_linea"] = math.log((sum(o_prov) + 3 * lgm(lg, "o")) / ((len(o_prov) + 3) * lgm(lg, "o")))
        for k in ("c", "s"):
            if fav == 1:   # sfavorita in casa
                uh = [x["per"][k][0] for x in U if x["casa"] and x["per"].get(k) and x["per"][k][0] is not None][-8:]
                fa = [x["per"][k][0] for x in F if not x["casa"] and x["per"].get(k) and x["per"][k][0] is not None][-8:]
                if len(uh) >= 4 and len(fa) >= 4 and lgm(lg, k): feats["x_casa_" + k] = math.log((np.mean(uh) + 0.1) / (np.mean(fa) + 0.1))
        if pf >= 0.6:
            L8 = [x for x in F if x["st"] is not None][-8:]
            if len(L8) >= 6 and lgm(lg, "conv"):
                feats["x_conv"] = math.log((sum(x["gf"] for x in L8) + 4) / (sum(x["st"] for x in L8) * lgm(lg, "conv") + 4))
                feats["x_dif"] = math.log((sum(x["ga"] for x in L8) + 4) / (sum(x["sta"] for x in L8) * lgm(lg, "conv") + 4)) if all(x["sta"] is not None for x in L8) else 0.0
            P20 = [x["pt"] for x in F][-20:]
            if len(P20) >= 10: feats["x_calo"] = np.mean(P20[-5:]) - np.mean(P20)
    rows.append(dict(r=r, fav=fav, pf=pf, pu=pu, **feats))
    # aggiornamento dopo la partita
    y = r["y"]; gh, ga = y["g"]
    for side, team, casa in ((0, r["h"], True), (1, r["a"], False)):
        per = {k: ((y[k][side], y[k][1 - side]) if y.get(k) and y[k][0] is not None else None) for k in ("c", "s", "st", "f", "o")}
        st_ = y["st"][side] if y.get("st") and y["st"][0] is not None else None; sta = y["st"][1 - side] if st_ is not None else None
        gf, gaa = (gh, ga) if side == 0 else (ga, gh)
        hist[(lg, team)].append(dict(d=d0, casa=casa, per=per, gf=gf, ga=gaa, st=st_, sta=sta, pt=3 if gf > gaa else 1 if gf == gaa else 0))
    for k in ("c", "s", "o"):
        if y.get(k) and y[k][0] is not None:
            a = lgavg[lg][k]; a[0] = a[0] * 0.999 + (y[k][0] + y[k][1]) / 2; a[1] = a[1] * 0.999 + 1
    if y.get("st") and y["st"][0] is not None and y["st"][0] + y["st"][1] > 0:
        a = lgavg[lg]["conv"]; a[0] = a[0] * 0.999 + (gh + ga); a[1] = a[1] * 0.999 + (y["st"][0] + y["st"][1])
R = [x for x in rows if x["pf"] >= 0.5 and x["pf"] - x["pu"] >= 0.25]
log("partite con favorita netta sulla carta", len(R))
season = lambda d: int(d[:4]) if d[5:7] >= "07" else int(d[:4]) - 1
def lr_wf(df, cols, min_train=800):
    """logistica walk-forward mese per mese: P(sfavorita vince) da logit(Prevista) + fattori"""
    df = df.sort_values("date").copy(); df["p_new"] = np.nan; df["mo"] = df.date.str[:7]
    for mo in sorted(df.mo.unique()):
        tr = df[df.mo < mo]
        if len(tr) < min_train: continue
        X = np.c_[np.ones(len(tr)), tr[cols].values]; y = tr.y.values; b = np.zeros(X.shape[1])
        for _ in range(25):
            p = 1 / (1 + np.exp(-X @ b)); W = p * (1 - p) + 1e-9
            b += np.linalg.solve(X.T @ (X * W[:, None]) + 1e-3 * np.eye(len(b)), X.T @ (y - p) - 1e-3 * b)
        te = df.mo == mo; Xt = np.c_[np.ones(te.sum()), df.loc[te, cols].values]; df.loc[te, "p_new"] = 1 / (1 + np.exp(-Xt @ b))
    return df
lgt = lambda p: np.log(np.clip(p, 1e-4, 1 - 1e-4) / (1 - np.clip(p, 1e-4, 1 - 1e-4)))
REP = {}
# ---------------- Parte 1
for k, nm in MK.items():
    D = []
    for x in R:
        r = x["r"]; y = r["y"].get(k)
        if not r.get(k) or not y or y[0] is None: continue
        P = H.h2h(*r[k][:2], r[k][2] if r[k][2] and r[k][2] > 0 else None, r[k][3], r[k][4])
        pu = P[2] if x["fav"] == 0 else P[0]; pfv = P[0] if x["fav"] == 0 else P[2]
        yu = y[1] > y[0] if x["fav"] == 0 else y[0] > y[1]
        gd = math.log(r["g"][1 - x["fav"]] / r["g"][x["fav"]])   # forza nei gol della sfavorita rispetto alla favorita
        D.append(dict(date=r["d"], lg=r["lg"], season=season(r["d"]), y=1.0 if yu else 0.0, pu=pu, pfv=pfv, gd=gd, lpu=lgt(pu), **{f: x.get(f, np.nan) for f in ("x_linea", "x_casa_c", "x_casa_s")}))
    D = pd.DataFrame(D)
    Dg = lr_wf(D, ["gd"]).rename(columns={"p_new": "p_bl"})
    V = Dg[Dg.date >= "2024-07-01"].dropna(subset=["p_bl"])
    inv = V[V.pu > V.pfv]; gap = V[V.pu - V.p_bl >= 0.10]
    f = lambda S: f"n {len(S)} · vince la sfavorita {100 * S.y.mean():.1f}% · Prevista {100 * S.pu.mean():.1f}% · blasone {100 * S.p_bl.mean():.1f}%" if len(S) else "n 0"
    ll = lambda p: float(-np.mean(np.where(V.y == 1, np.log(np.clip(p, 1e-6, 1)), np.log(np.clip(1 - p, 1e-6, 1)))))
    log(f"\n== {nm} · sfavorita sulla carta (dal luglio 2024)\n  tutte: {f(V)} · log-loss Prevista {ll(V.pu):.4f} contro blasone {ll(V.p_bl):.4f}\n  inversione (Prevista dà avanti la sfavorita): {f(inv)}\n  forbice ≥ +10 punti sopra il blasone: {f(gap)}")
    REP[nm] = dict(tutte=len(V), inversione=dict(n=len(inv), reale=float(inv.y.mean()) if len(inv) else None, prevista=float(inv.pu.mean()) if len(inv) else None))
    # Parte 2 · fattori
    fac = {"o": ["x_linea"], "c": ["x_casa_c"], "s": ["x_casa_s"], "st": ["x_casa_s"]}.get(k)
    if fac:
        E = D.dropna(subset=fac).copy()
        log(f"  righe con il fattore {fac}: {len(E)}")
        if len(E) > 1200:
            E2 = lr_wf(E, ["lpu"] + fac).rename(columns={"p_new": "pn"}); E1 = lr_wf(E, ["lpu"]).rename(columns={"p_new": "p0"})
            E2["p0"] = E1["p0"]; E2 = E2.dropna(subset=["p0", "pn"])
            E2["p_old"] = [np.array([p, 0, 1 - p]) for p in E2.p0]; E2["p_new"] = [np.array([p, 0, 1 - p]) for p in E2.pn]; E2["y"] = np.where(E2.y == 1, 0, 2)
            log(H.riepilogo(f"{nm} · fattore {fac} su 'vince la sfavorita' (Prevista ricalibrata contro + fattore)", H.confronta(E2)))
# ---------------- Parte 2 · gol: favorita fragile (vittoria ≥ 60%)
D = []
for x in R:
    if x["pf"] < 0.6 or "x_conv" not in x: continue
    r = x["r"]; gh, ga = r["y"]["g"]; yu = (ga > gh) if x["fav"] == 0 else (gh > ga); nofav = not ((gh > ga) if x["fav"] == 0 else (ga > gh))
    D.append(dict(date=r["d"], lg=r["lg"], season=season(r["d"]), y=1.0 if nofav else 0.0, yu=yu, pu=1 - x["pf"], lpu=lgt(1 - x["pf"]), x_conv=x["x_conv"], x_dif=x.get("x_dif", 0.0), x_calo=x.get("x_calo", 0.0)))
D = pd.DataFrame(D); log(f"\n== Gol · favorita netta (vittoria ≥ 60%): {len(D)} partite · la favorita NON vince {100 * D.y.mean():.1f}% contro {100 * D.pu.mean():.1f}% previsto")
E1 = lr_wf(D, ["lpu"]).rename(columns={"p_new": "p0"})
for fac in (["x_conv"], ["x_dif"], ["x_calo"], ["x_conv", "x_dif", "x_calo"]):
    E2 = lr_wf(D, ["lpu"] + fac).rename(columns={"p_new": "pn"}); E2["p0"] = E1["p0"]; E2 = E2.dropna(subset=["p0", "pn"])
    E2["p_old"] = [np.array([p, 0, 1 - p]) for p in E2.p0]; E2["p_new"] = [np.array([p, 0, 1 - p]) for p in E2.pn]; E2["y"] = np.where(E2.y == 1, 0, 2)
    log(H.riepilogo(f"Gol · favorita fragile · fattore {fac} su 'la favorita non vince'", H.confronta(E2)))
    # le favorite più "fragili" secondo il fattore: decile più alto della probabilità di non vincere rispetto alla base
    V = E2[E2.date >= "2024-07-01"]; d_ = V.pn - V.p0; top = V[d_ >= d_.quantile(0.9)]
    log(f"  10% più fragili (dal luglio 2024): n {len(top)} · la favorita non vince {100 * (top.y == 0).mean():.1f}% · base {100 * top.p0.mean():.1f}% · con il fattore {100 * top.pn.mean():.1f}%")
