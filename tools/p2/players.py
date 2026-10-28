"""Prevista 2.0 · fase 1-A: chi gioca davvero. Variabili dai giocatori, calcolate con le sole partite precedenti (point-in-time).

Per ogni giocatore e statistica (tiri, tiri in porta, falli fatti, falli subiti, fuorigioco, cartellini): valore ogni 90 minuti,
media mobile per presenza (peso DP), ristretto verso la media del suo ruolo (portiere/difensore/centrocampista/attaccante) con K
partite fittizie. Per ogni squadra e partita:
  - xi_<k>:  log(somma dei valori dei titolari di oggi / somma abituale dei titolari della squadra)   [formazione ufficiale]
  - pr_<k>:  lo stesso con la formazione PROBABILE: gli 11 con più presenze da titolare nelle ultime partite (peso DT a partita),
             tolti gli assenti noti (infortuni/squalifiche di API-Football)                              [giorni prima]
  - ab_<k>:  peso degli assenti noti rispetto ai titolari abituali
Unione con la baseline dell'app (base/<lg>.json, nomi dell'app) per data ±1 e risultato, come apif_extra.learn_map.
Uscita: feat.pkl = {(lg, data, casa, ospite): {"h": {...}, "a": {...}}}."""
import os as _os
P2 = _os.environ.get("RICERCA", _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", "..", "ricerca"))   # 28/10/2026: archivio di ricerca (ramo ricerca)
REPO = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", "..")
import json, glob, math, collections, pickle, sys, os
import numpy as np
FORM = sys.argv[1] if len(sys.argv) > 1 else P2 + "/form2"
DP, DT, K = 0.97, 0.85, 5.0
STAT = ["sh", "sot", "fc", "fd", "off", "crd", "tk", "duel", "drib"]          # colonne: tiri, tiri in porta, falli fatti, falli subiti, fuorigioco, cartellini
IDX = {"sh": 9, "sot": 10, "fc": 7, "fd": 8, "off": 12}
POS = {"G": 0, "D": 1, "M": 2, "F": 3}
log = lambda *a: print(*a, flush=True)

FX, INJ = [], collections.defaultdict(list)
for fn in glob.glob(FORM + "/*.json"):
    D = json.load(open(fn))
    if "partite" not in D: continue
    for fid, v in D["partite"].items(): FX.append((v[0], D["lega"], fid, v))
    for x in D.get("infortuni") or []:
        if x[3] == "Missing Fixture": INJ[str(x[0])].append((x[1], x[2]))
FX.sort()
has_off = sum(1 for *_, v in FX if v[9] and len(v[9][0]) > 12)
log("partite con formazioni", len(FX), "· con fuorigioco per giocatore", has_off)

def prow(r):
    """statistiche di una riga giocatore → vettore minuti + STAT (fuorigioco NaN se il formato è vecchio)"""
    nn = lambda j: r[j] if len(r) > j and r[j] is not None else np.nan
    return r[2], np.array([r[9], r[10], r[7], r[8], nn(12), r[5] + r[6], nn(13), nn(16), nn(18)], float)

pl = {}                                              # giocatore → [minuti decaduti, somme decadute (6)], ruolo
role = {}
NS = len(STAT); G = np.zeros((4, 2 * NS)); G[:, :NS] = 1e-9               # per ruolo: minuti per statistica (6), somme (6): prior
def rates(pid):
    r = POS.get(role.get(pid, "M"), 2); g = G[r, NS:] / np.maximum(G[r, :NS], 1e-9) * 90
    p = pl.get(pid)
    if p is None: return g
    return (p[NS:] + K * g) / (p[:NS] / 90 + K)
team_typ = {}                                        # squadra → [somme decadute dei titolari (6), peso]
team_starts = collections.defaultdict(dict)          # squadra → giocatore → presenze da titolare decadute
FEAT = {}
for d, lg, fid, v in FX:
    _, hid, aid, hn, an, hg, ag, xh, xa, P = v
    if len(xh) >= 10 and len(xa) >= 10 and G[:, 0].sum() > 1e6:
        f = {}
        for side, tid, xi in (("h", hid, xh), ("a", aid, xa)):
            T = team_typ.get(tid); ok = T is not None and T[NS] >= 3
            if not ok: f[side] = None; continue
            typ = T[:NS] / T[NS]
            agg = np.sum([rates(p) for p in xi], axis=0)
            miss = {p for t, p in INJ.get(fid, []) if t == tid}
            st = team_starts[tid]; prob = [p for p, _ in sorted(st.items(), key=lambda z: -z[1]) if p not in miss][:11]
            pagg = np.sum([rates(p) for p in prob], axis=0) if len(prob) >= 10 else None
            mag = np.sum([rates(p) for p in miss], axis=0) if miss else np.zeros(NS)
            g_ = {}
            for i, k in enumerate(STAT):
                if not (typ[i] > 0): continue
                g_["xi_" + k] = math.log(max(agg[i], 1e-6) / typ[i])
                if pagg is not None: g_["pr_" + k] = math.log(max(pagg[i], 1e-6) / typ[i])
                g_["ab_" + k] = mag[i] / typ[i]
            g_["n_ab"] = len(miss)
            f[side] = g_
        FEAT[(lg, d[:10], hn, an, hg, ag)] = f
    # aggiornamento dopo la partita
    for side, tid, xi in ((0, hid, xh), (1, aid, xa)):
        if len(xi) >= 10:
            agg = np.sum([rates(p) for p in xi], axis=0); T = team_typ.setdefault(tid, np.zeros(NS + 1)); T[:NS] = T[:NS] * DT + agg; T[NS] = T[NS] * DT + 1
            st = team_starts[tid]
            for p in list(st): st[p] *= DT
            for p in xi: st[p] = st.get(p, 0) + 1
    for r in P:
        pid = r[0]; mi, x = prow(r)
        if r[11]: role[pid] = r[11]
        ok_ = np.isfinite(x); a = pl.setdefault(pid, np.zeros(2 * NS)); a *= DP
        a[:NS] += np.where(ok_, mi, 0); a[NS:] += np.where(ok_, x, 0)
        rr = POS.get(role.get(pid, "M"), 2); G[rr] *= 0.9999; G[rr, :NS] += np.where(ok_, mi, 0); G[rr, NS:] += np.where(ok_, x, 0)
log("partite con variabili", len(FEAT))
pickle.dump(FEAT, open(sys.argv[2] if len(sys.argv) > 2 else os.path.join(os.path.dirname(__file__), "feat.pkl"), "wb"))
