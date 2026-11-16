"""Basket · audit di calibrazione voce per voce (16/11/2026, Denny). Motore come in produzione (pubblica.py): possessi con il formato nuovo e
statistiche rotte scartate, preseason NBA dentro, DP 0,97, K 6, LD 0,998; σ robuste stimate nel periodo scelta per campionato.
Voci con una probabilità nella pagina basket: Vincente (supplementari compresi), Handicap e Totale punti (lato della lettura) sulle linee
attorno all'atteso (le linee dei book in archivio partono dal 15/11: troppo poche), Grado ("uscite X su 100", Segnali ≥ 72).
Per periodo (scelta / verifica / holdout): fasce 50-60, 60-65, 65-72, 72-80, 80+ (dichiarata / uscita / casi), ECE, log-loss.
Ricalibrazione provata solo dove serve: fattore sulla σ per campionato (scelto nel periodo scelta), poi verifica e holdout.
Uso: python tools/basket/audit_calibrazione.py ARCHIVIO [USCITA.json]"""
import sys, os, json, math, collections
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from bk_lib import load, team_model, per, Phi, rob, SCELTA
DIR = sys.argv[1]; OUT = sys.argv[2] if len(sys.argv) > 2 else "basket_audit.json"
rows = [r for r in team_model(load(DIR, preseason=True, fix=True)) if r["eh"] is not None and r["nh"] >= 5 and r["na"] >= 5]
SIG = {}
for lg in set(r["lg"] for r in rows):
    S = [r for r in rows if r["lg"] == lg and r["d"] <= SCELTA]
    SIG[lg] = (rob([r["ph"] - r["pa"] - r["eh"] + r["ea"] for r in S]), rob([r["ph"] + r["pa"] - r["eh"] - r["ea"] for r in S]))
BANDS = [(0.5, 0.6), (0.6, 0.65), (0.65, 0.72), (0.72, 0.8), (0.8, 1.01)]
def events(kf=None, only=None):
    """eventi (voce, periodo, campionato, p lato lettura, esito, info) con fattore k sulla σ per campionato (kf[lg] = (k_scarto, k_totale))"""
    E = []
    for r in rows:
        if only and r["lg"] != only: continue
        ss, st = SIG[r["lg"]]
        if kf: ss, st = ss * kf[r["lg"]][0], st * kf[r["lg"]][1]
        ms, mt, p = r["eh"] - r["ea"], r["eh"] + r["ea"], per(r["d"])
        d, t = r["ph"] - r["pa"], r["ph"] + r["pa"]; ot = (r["qh"][4] or 0) + (r["qa"][4] or 0) > 0
        pw = Phi(ms / ss); E.append(("vittoria", p, r["lg"], max(pw, 1 - pw), int((d > 0) == (pw >= 0.5)), abs(ms)))
        for off in (-12, -8, -4, 0, 4, 8, 12):
            Lt = round(mt) + 0.5 + off; po = 1 - Phi((Lt - mt) / st)
            E.append(("totale", p, r["lg"], max(po, 1 - po), int((t > Lt) == (po >= 0.5)), (off, po >= 0.5, abs(ms) < 4, ot)))
            Ls = round(ms) + 0.5 + off / 2; pc = 1 - Phi((Ls - ms) / ss)
            E.append(("handicap", p, r["lg"], max(pc, 1 - pc), int((d > Ls) == (pc >= 0.5)), off))
    return E
def table(E):
    p = np.array([e[3] for e in E]); y = np.array([e[4] for e in E]); out = {}
    for lo, hi in BANDS:
        m = (p >= lo) & (p < hi)
        if m.sum() >= 20: out[f"{int(lo*100)}-{min(100, int(hi*100))}"] = f"{p[m].mean()*100:.1f} / {y[m].mean()*100:.1f} ({int(m.sum())})"
    bins = np.minimum(((p - 0.5) * 20).astype(int), 9); ece = sum(abs(p[bins == b].mean() - y[bins == b].mean()) * (bins == b).sum() for b in set(bins)) / len(p)
    ll = -np.mean(y * np.log(np.clip(p, 1e-9, 1)) + (1 - y) * np.log(np.clip(1 - p, 1e-9, 1)))
    return out, round(float(ece) * 100, 2), round(float(ll), 4), round(float((p - y).mean()) * 100, 2)
res = {"sigma (scarto, totale) dal periodo scelta": {lg: [round(a, 2), round(b, 2)] for lg, (a, b) in sorted(SIG.items())}}
E0 = events()
def report(E, tag):
    R = {}
    for voce in ("vittoria", "handicap", "totale"):
        for p in ("scelta", "verifica", "holdout"):
            sub = [e for e in E if e[0] == voce and e[1] == p]
            t, ece, ll, bias = table(sub)
            R[f"{voce} · {p}"] = {"fasce dichiarata / uscita (casi)": t, "ECE punti": ece, "log-loss": ll, "dichiarata − uscita (punti)": bias}
    res[tag] = R
report(E0, "prima")
# per campionato (holdout): dichiarata − uscita
res["per campionato holdout (dichiarata − uscita, punti)"] = {voce: {lg: table([e for e in E0 if e[0] == voce and e[1] == "holdout" and e[2] == lg])[3] for lg in sorted(SIG)} for voce in ("vittoria", "handicap", "totale")}
# Over/Under e supplementari (totale, holdout+verifica): Over in partite equilibrate (scarto atteso < 4) contro le altre
ou = collections.defaultdict(list)
for e in E0:
    if e[0] != "totale" or e[1] == "scelta": continue
    off, over, eq, ot = e[5]
    ou[("Over" if over else "Under", "equilibrate" if eq else "non equilibrate")].append(e)
res["totale: Over/Under e partite equilibrate (verifica+holdout)"] = {f"{a} · {b}": f"dichiarata {np.mean([e[3] for e in v])*100:.1f} / uscita {np.mean([e[4] for e in v])*100:.1f} ({len(v)})" for (a, b), v in sorted(ou.items())}
res["partite con supplementari (verifica+holdout)"] = f"{np.mean([e[5][3] for e in E0 if e[0] == 'totale' and e[1] != 'scelta' and e[5][0] == 0])*100:.1f}%"
# Grado: tabelle stimate sulla verifica, provate sull'holdout (le "uscite" che vede l'app, Segnali ≥ 72)
G = {v: collections.defaultdict(lambda: [0, 0]) for v in ("vittoria", "totale", "handicap")}
for e in E0:
    if e[1] == "verifica": b = G[e[0]][int(e[3] * 20)]; b[0] += 1; b[1] += e[4]
gr = collections.defaultdict(lambda: [0, 0.0, 0])
for e in E0:
    if e[1] != "holdout": continue
    b = G[e[0]].get(int(e[3] * 20))
    if not b or b[0] < 30: continue
    u = b[1] / b[0]; band = "A+ (≥80)" if u >= 0.8 else "A (72-80)" if u >= 0.72 else "B (64-72)" if u >= 0.64 else "C (56-64)" if u >= 0.56 else "senza grado"
    for key in (f"{e[0]} · {band}", f"tutte · {band}"):
        c = gr[key]; c[0] += 1; c[1] += u; c[2] += e[4]
res["Grado: uscite dichiarate (stimate sulla verifica) / uscite reali nell'holdout"] = {k: f"{c[1]/c[0]*100:.1f} / {c[2]/c[0]*100:.1f} ({c[0]})" for k, c in sorted(gr.items())}
# Ricalibrazione: fattore sulla σ per campionato scelto nel periodo scelta (log-loss di vittoria+handicap per lo scarto, totale per il totale)
def ll_of(E): p = np.array([e[3] for e in E]); y = np.array([e[4] for e in E]); return -np.mean(y * np.log(np.clip(p, 1e-9, 1)) + (1 - y) * np.log(np.clip(1 - p, 1e-9, 1)))
KS = (0.85, 0.9, 0.95, 1.0, 1.05, 1.1, 1.15, 1.2, 1.25)
best = {lg: [1.0, 1.0] for lg in SIG}
def events_lg(lg, ks, kt):
    return events({lg: (ks, kt)}, only=lg)
for lg in SIG:
    for j, voci in ((0, ("vittoria", "handicap")), (1, ("totale",))):
        sc = []
        for k in KS:
            E = events_lg(lg, k if j == 0 else 1.0, k if j == 1 else 1.0)
            sc.append((ll_of([e for e in E if e[0] in voci and e[1] == "scelta"]), k))
        best[lg][j] = min(sc)[1]
res["fattori σ scelti nel periodo scelta (scarto, totale)"] = {lg: best[lg] for lg in sorted(best)}
E1 = events({lg: tuple(best[lg]) for lg in SIG})
report(E1, "dopo (σ × fattore)")
cmp = {}
for voce in ("vittoria", "handicap", "totale"):
    for p in ("verifica", "holdout"):
        a = [e for e in E0 if e[0] == voce and e[1] == p]; b = [e for e in E1 if e[0] == voce and e[1] == p]
        ya = np.array([e[4] for e in a]); pa_ = np.array([e[3] for e in a]); yb = np.array([e[4] for e in b]); pb_ = np.array([e[3] for e in b])
        la = -(ya * np.log(pa_) + (1 - ya) * np.log(1 - pa_)); lb = -(yb * np.log(pb_) + (1 - yb) * np.log(1 - pb_)); dd = lb - la
        per_lg = {lg: float(np.mean(dd[[e[2] == lg for e in a]])) for lg in SIG}
        cmp[f"{voce} · {p}"] = {"diff log-loss (dopo − prima)": round(float(dd.mean()), 5), "z": round(float(dd.mean() / (dd.std() / math.sqrt(len(dd)))), 2),
                                "campionati migliorati": f"{sum(v < 0 for v in per_lg.values())}/{len(per_lg)}", "ECE prima → dopo": f"{table(a)[1]} → {table(b)[1]}"}
res["confronto ricalibrazione"] = cmp
json.dump(res, open(OUT, "w"), indent=1, ensure_ascii=False)
print(json.dumps(res, indent=1, ensure_ascii=False))
