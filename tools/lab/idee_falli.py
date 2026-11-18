"""Laboratorio · idee sui FALLI (18/11/2026, Denny: "vorrei partire dai falli"). Formule fissate prima di vedere i risultati.
Il modello falli dell'app ha già: media del campionato, rating falli fatti × subiti (2 anni), falli delle ultime 5, quota di partite in
vantaggio/svantaggio all'intervallo, tiri delle ultime 15, arbitro (tetto +4%), formazioni ufficiali. Le idee aggiungono SOLO cose che non ci sono:
  F1 derby          derby (lista di derby.py, nomi API-Football): 1 coefficiente, uguale per le due squadre
  F2 forza          differenza di gol attesi nella partita (λ gol squadra − λ gol avversaria, dall'app): la sfavorita insegue e fa più falli?
  F3 classifica     partita che conta (classifica prima della partita, dalla 10ª giornata): entrambe nelle ultime 4, entrambe nelle prime 4,
                    distanza in punti ≤ 3; ultime 6 giornate. 4 coefficienti uguali per le due squadre
  F4 riposo         giorni dall'ultima partita (campionato + coppe europee, al massimo 14): ln(giorni/7) della squadra e dell'avversaria
  F5 avvio          prime 5 giornate della stagione"""
import os, sys, numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
from comune import *
import derby

def classifica(S):
    """per ogni partita di campionato: posizione, punti, giocate delle due squadre PRIMA della partita, numero squadre"""
    out = {}
    L = S[~S.lg.isin(EUROPA)].sort_values("dt")
    for (lg, se), g in L.groupby(["lg", "se"]):
        teams = sorted(set(g.h) | set(g.a)); n = len(teams)
        P = {t: [0, 0, 0] for t in teams}   # punti, differenza reti, giocate
        for day, gd in g.groupby("d", sort=True):
            rank = sorted(teams, key=lambda t: (-P[t][0], -P[t][1]))
            pos = {t: i + 1 for i, t in enumerate(rank)}
            for r in gd.itertuples():
                out[r.fid] = (pos[r.h], pos[r.a], P[r.h][0], P[r.a][0], P[r.h][2], P[r.a][2], n)
            for r in gd.itertuples():
                ph, pa = (3, 0) if r.hg > r.ag else (1, 1) if r.hg == r.ag else (0, 3)
                P[r.h][0] += ph; P[r.a][0] += pa; P[r.h][1] += r.hg - r.ag; P[r.a][1] += r.ag - r.hg; P[r.h][2] += 1; P[r.a][2] += 1
    return out

def riposo(S):
    """giorni dall'ultima partita della squadra (stesso campionato o coppe europee, nomi API), per partita"""
    out, last = {}, {}
    for r in S.sort_values("dt").itertuples():
        d = pd.Timestamp(r.d); scope = "EU" if r.lg in EUROPA else r.lg
        def rest(t):
            xs = [x for x in (last.get((scope, t)), last.get(("EU", t)) if scope != "EU" else None) if x is not None]
            return (d - max(xs)).days if xs else None
        out[r.fid] = (rest(r.h), rest(r.a))
        last[(scope, r.h)] = d; last[(scope, r.a)] = d
    return out

def features(J, S):
    C = classifica(S); RP = riposo(S)
    F = pd.DataFrame(index=J.index)
    F["derby"] = [1.0 if derby.is_derby(lg, h, a) else 0.0 for lg, h, a in zip(J.lg, J.h, J.a)]
    F["forza_h"] = (J.gh - J.ga).fillna(0).values; F["forza_a"] = -F["forza_h"]
    z = np.zeros((len(J), 4))
    for i, fid in enumerate(J.fid):
        c = C.get(fid)
        if not c: continue
        ph, pa, qh, qa, gh, ga, n = c; rnd = min(gh, ga) + 1
        if rnd >= 10:
            z[i, 0] = 1.0 if ph > n - 4 and pa > n - 4 else 0.0
            z[i, 1] = 1.0 if ph <= 4 and pa <= 4 else 0.0
            z[i, 2] = 1.0 if abs(qh - qa) <= 3 else 0.0
        z[i, 3] = 1.0 if max(gh, ga) >= 2 * (n - 1) - 6 else 0.0
    F[["salvezza", "vertice", "vicine", "fine"]] = z
    rh = np.array([RP.get(f, (None, None))[0] or 14 for f in J.fid], float); ra = np.array([RP.get(f, (None, None))[1] or 14 for f in J.fid], float)
    F["rip_h"] = np.log(np.clip(rh, 2, 14) / 7); F["rip_a"] = np.log(np.clip(ra, 2, 14) / 7)
    av = np.array([1.0 if (C.get(f) and max(C[f][4], C[f][5]) < 5) else 0.0 for f in J.fid])
    F["avvio"] = av
    return F

IDEE = {
    "F1": ("Derby", lambda F: (F[["derby"]].values, F[["derby"]].values, ["derby"])),
    "F2": ("Differenza di forza (gol attesi)", lambda F: (F[["forza_h"]].values, F[["forza_a"]].values, ["forza"])),
    "F3": ("Partita che conta (classifica)", lambda F: (F[["salvezza", "vertice", "vicine", "fine"]].values, F[["salvezza", "vertice", "vicine", "fine"]].values, ["salvezza", "vertice", "vicine", "fine"])),
    "F4": ("Riposo (giorni dall'ultima partita)", lambda F: (F[["rip_h", "rip_a"]].values, F[["rip_a", "rip_h"]].values, ["riposo squadra", "riposo avversaria"])),
    "F5": ("Avvio di stagione (prime 5 giornate)", lambda F: (F[["avvio"]].values, F[["avvio"]].values, ["avvio"])),
}

def prepare():
    S = load_storico(); B = load_base("f"); J = join(B, S, ("hf", "af"))
    return J, features(J, S)

def run(idea_id, J=None, F=None):
    if J is None: J, F = prepare()
    nome, fn = IDEE[idea_id]; Xh, Xa, names = fn(F)
    b, se, lh, la = fit_apply(J, Xh, Xa)
    res = evaluate(J, b, se, lh, la, names); res["nome"] = nome; res["statistica"] = "falli"; res["partite"] = int(len(J))
    if idea_id == "F1": res["derby_nel_campione"] = int(F.derby.sum())
    return res
