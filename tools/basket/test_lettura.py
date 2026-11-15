"""Basket · test della Lettura arricchita (15/11/2026, Denny). Harness walk-forward come il calcio: coefficienti scelti fino al 30/6/2024,
verifica 2024-25, holdout da luglio 2025; si adotta solo ciò che migliora in verifica, ha lo stesso segno in holdout e migliora la maggior parte dei campionati.
1) Riposo (giorni dall'ultima partita della squadra in qualsiasi competizione dell'archivio: back-to-back NBA, doppio turno in Europa) su Totale e Handicap.
2) Chiavi tattiche (rimbalzi, assist, dipendenza dal tiro da 3, tiri liberi, falli): dicono qualcosa oltre attacco/difesa?
3) 1° tempo e 1° quarto: quota del totale propria della squadra contro quella del campionato.
4) Rimbalzi totali e vincente dei rimbalzi: c'è un segnale (modello di squadra contro media del campionato)?
Uso: python tools/basket/test_lettura.py CARTELLA_ARCHIVIO [USCITA.json]"""
import sys, os, json, math, collections, datetime
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from bk_lib import load, team_model, per, Phi, rob, ll, SCELTA
DIR = sys.argv[1]; OUT = sys.argv[2] if len(sys.argv) > 2 else "basket_lettura.json"
rows = team_model(load(DIR))
EU = lambda lg: "NBA" if lg == "NBA" else "EU"
# ---------- riposo ----------
last = {}
for r in rows:
    d = datetime.date.fromisoformat(r["d"])
    for side, t in (("h", r["h"]), ("a", r["a"])):
        r["r" + side] = min(5, (d - last[t]).days) if t in last else 5
        last[t] = d
ok = [r for r in rows if r["eh"] is not None and r["nh"] >= 5 and r["na"] >= 5]
for r in ok:
    r["tres"] = r["ph"] + r["pa"] - r["eh"] - r["ea"]; r["mres"] = r["ph"] - r["pa"] - (r["eh"] - r["ea"])
res = {"partite": len(ok)}
# residui medi per categoria di riposo
cat = lambda x: "1 (back-to-back)" if x <= 1 else "2" if x == 2 else "3" if x == 3 else "4+"
tab = collections.defaultdict(lambda: [0, 0.0, 0.0])
for r in ok:
    if per(r["d"]) != "scelta": continue
    for side, sg in (("h", 1), ("a", -1)):
        k = (EU(r["lg"]), cat(r["r" + side])); t = tab[k]; t[0] += 1; t[1] += r["tres"] / 2; t[2] += sg * r["mres"]
res["riposo_scelta"] = {f"{g} riposo {c}": {"n": n, "totale_metà": round(a / n, 2), "scarto_squadra": round(b / n, 2)} for (g, c), (n, a, b) in sorted(tab.items())}
# coefficienti (scelta) per gruppo: effetto sul totale e sullo scarto di ogni categoria rispetto a 3+ giorni
def feats(r):
    f = lambda x: [1.0 if x <= 1 else 0.0, 1.0 if x == 2 else 0.0]
    return f(r["rh"]), f(r["ra"])
coef = {}
for g in ("NBA", "EU"):
    S = [r for r in ok if EU(r["lg"]) == g and per(r["d"]) == "scelta"]
    Xt = np.array([[fh[0] + fa[0], fh[1] + fa[1]] for r in S for fh, fa in [feats(r)]]); yt = np.array([r["tres"] for r in S])
    Xm = np.array([[fh[0] - fa[0], fh[1] - fa[1]] for r in S for fh, fa in [feats(r)]]); ym = np.array([r["mres"] for r in S])
    ct = np.linalg.lstsq(Xt, yt - yt.mean(), rcond=None)[0]; cm = np.linalg.lstsq(Xm, ym - ym.mean(), rcond=None)[0]
    coef[g] = (ct.tolist(), cm.tolist())
res["riposo_coefficienti"] = {g: {"totale: per squadra in back-to-back": round(c[0][0], 2), "totale: riposo 2 giorni": round(c[0][1], 2),
                                  "scarto: squadra in back-to-back": round(c[1][0], 2), "scarto: riposo 2 giorni": round(c[1][1], 2)} for g, c in coef.items()}
sig = {}
for lg in set(r["lg"] for r in ok):
    S = [r for r in ok if r["lg"] == lg and r["d"] <= SCELTA]; sig[lg] = (rob([r["mres"] for r in S]), rob([r["tres"] for r in S]))
def eval_rest(use):
    R = collections.defaultdict(list)
    for r in ok:
        p = per(r["d"])
        if p == "scelta": continue
        ss, st = sig[r["lg"]]; mt, ms = r["eh"] + r["ea"], r["eh"] - r["ea"]
        if use:
            ct, cm = coef[EU(r["lg"])]; fh, fa = feats(r)
            mt += ct[0] * (fh[0] + fa[0]) + ct[1] * (fh[1] + fa[1]); ms += cm[0] * (fh[0] - fa[0]) + cm[1] * (fh[1] - fa[1])
        Lt = round(r["eh"] + r["ea"]) + 0.5
        for off in (-10, -5, 0, 5, 10):
            L_ = Lt + off; R[(p, "totale", r["lg"])].append(ll(1 - Phi((L_ - mt) / st), 1 if r["ph"] + r["pa"] > L_ else 0))
        Ls = round(r["eh"] - r["ea"]) - 0.5
        R[(p, "handicap", r["lg"])].append(ll(1 - Phi((Ls - ms) / ss), 1 if r["ph"] - r["pa"] > Ls else 0))
        R[(p, "vittoria", r["lg"])].append(ll(Phi(ms / ss), 1 if r["ph"] > r["pa"] else 0))
    return R
def compare(R0, R1, label):
    out = {}
    for p in ("verifica", "holdout"):
        for mk in ("totale", "handicap", "vittoria"):
            keys = [k for k in R0 if k[0] == p and k[1] == mk]
            d = [np.mean(R1[k]) - np.mean(R0[k]) for k in keys]
            a0 = np.concatenate([R0[k] for k in keys]); a1 = np.concatenate([R1[k] for k in keys])
            diff = a1 - a0; se = diff.std() / math.sqrt(len(diff))
            out[f"{p} · {mk}"] = {"diff_logloss": round(float(diff.mean()), 5), "z": round(float(diff.mean() / se), 2) if se else 0,
                                  "campionati_migliorati": f"{sum(x < 0 for x in d)}/{len(d)}", "per_campionato": {k[2]: round(float(x), 4) for k, x in zip(keys, d)}}
    res[label] = out
R0 = eval_rest(False); compare(R0, eval_rest(True), "riposo_test")
# ---------- chiavi tattiche: correlazione delle medie mobili pre-partita con i residui ----------
TS = collections.defaultdict(lambda: collections.defaultdict(float)); DP = 0.97
def tf(s, o):   # s, o = statistiche squadra e avversario
    fga, fta = s[1] or 1, s[5] or 0
    return {"reb_quota": s[6] / max(1, s[6] + o[6]), "oreb_pct": s[7] / max(1, s[7] + o[8]), "ast_fg": s[9] / max(1, s[0]), "tre_quota": s[3] / fga,
            "tl_quota": fta / fga, "falli": s[13] or 0, "palle_perse": s[12] / max(1, fga)}
corr = collections.defaultdict(lambda: collections.defaultdict(list))
for r in rows:
    pre = {}
    for side, t in (("h", r["h"]), ("a", r["a"])):
        st_ = TS[(r["lg"], t)]
        pre[side] = {k: st_[k] / st_["n"] for k in st_ if k != "n"} if st_["n"] >= 5 else None
    if r in ok or (r["eh"] is not None and r["nh"] >= 5 and r["na"] >= 5):
        if pre["h"] and pre["a"] and "tres" in r:
            for k in pre["h"]:
                corr[per(r["d"])][("totale", k)].append((pre["h"][k] + pre["a"][k], r["tres"]))
                corr[per(r["d"])][("scarto", k)].append((pre["h"][k] - pre["a"][k], r["mres"]))
    if r["sh"] and r["sa"] and None not in r["sh"] and None not in r["sa"]:
        for side, s, o, t in (("h", r["sh"], r["sa"], r["h"]), ("a", r["sa"], r["sh"], r["a"])):
            st_ = TS[(r["lg"], t)]
            for k in list(st_): st_[k] *= DP
            st_["n"] += 1
            for k, v in tf(s, o).items(): st_[k] += v
res["tattiche_correlazione_con_residuo"] = {f"{mk} · {k}": {p: round(float(np.corrcoef(np.array(corr[p][(mk, k)]).T)[0, 1]), 3) for p in ("scelta", "verifica", "holdout")}
                                           for (mk, k) in sorted(corr["scelta"])}
# ---------- 1° tempo e 1° quarto ----------
H = collections.defaultdict(lambda: [0.0, 0.0]); Lq = collections.defaultdict(lambda: [0.0, 0.0])
hres = collections.defaultdict(list); hsig = collections.defaultdict(list)
for r in rows:
    tot = r["ph"] + r["pa"] - (r["qh"][4] or 0) - (r["qa"][4] or 0)   # regolamentari
    h1 = r["qh"][0] + r["qh"][1] + r["qa"][0] + r["qa"][1]; q1 = r["qh"][0] + r["qa"][0]
    if r in ok or "tres" in r:
        lg = r["lg"]; L_ = Lq[lg]
        if L_[0] > 20:
            lsh, lq1 = L_[1] / L_[0], Lq[lg + "q"][1] / Lq[lg + "q"][0]
            def tsh(t, key, base):
                x = H[(lg, t, key)]; return (x[1] + 8 * base) / (x[0] + 8)
            mt = r["eh"] + r["ea"]
            m_lg = mt * lsh; m_tm = mt * (tsh(r["h"], "h1", lsh) + tsh(r["a"], "h1", lsh)) / 2
            q_lg = mt * lq1; q_tm = mt * (tsh(r["h"], "q1", lq1) + tsh(r["a"], "q1", lq1)) / 2
            hres[per(r["d"])].append((lg, h1, m_lg, m_tm, q1, q_lg, q_tm))
    lg = r["lg"]
    for k, v in ((lg, h1 / tot), (lg + "q", q1 / tot)):
        x = Lq[k]; x[0] = x[0] * 0.998 + 1; x[1] = x[1] * 0.998 + v
    for t in (r["h"], r["a"]):
        for key, v in (("h1", h1 / tot), ("q1", q1 / tot)):
            x = H[(lg, t, key)]; x[0] = x[0] * 0.97 + 1; x[1] = x[1] * 0.97 + v
sg1 = {}
for lg in set(x[0] for x in hres["scelta"]):
    S = [x for x in hres["scelta"] if x[0] == lg]; sg1[lg] = (rob([x[1] - x[2] for x in S]), rob([x[4] - x[5] for x in S]))
out = {}
for p in ("verifica", "holdout"):
    for nm, iy, i0, i1, sidx, offs in (("1° tempo", 1, 2, 3, 0, (-6, -3, 0, 3, 6)), ("1° quarto", 4, 5, 6, 1, (-4, -2, 0, 2, 4))):
        d = collections.defaultdict(list)
        for x in hres[p]:
            s = sg1[x[0]][sidx]; L0 = round(x[i0]) + 0.5
            for o in offs:
                L_ = L0 + o; y = 1 if x[iy] > L_ else 0
                d[x[0]].append(ll(1 - Phi((L_ - x[i1]) / s), y) - ll(1 - Phi((L_ - x[i0]) / s), y))
        allv = np.concatenate(list(d.values()))
        out[f"{p} · {nm}"] = {"diff_logloss (squadra − campionato)": round(float(allv.mean()), 5), "z": round(float(allv.mean() / (allv.std() / math.sqrt(len(allv)))), 2),
                              "campionati_migliorati": f"{sum(np.mean(v) < 0 for v in d.values())}/{len(d)}"}
res["primo_tempo_quota_squadra"] = out
# ---------- rimbalzi ----------
RB = collections.defaultdict(lambda: [0.0, 0.0, 0.0]); LR = collections.defaultdict(lambda: [0.0, 0.0])
rb = collections.defaultdict(list)
for r in rows:
    have = r["sh"] and r["sa"] and r["sh"][6] and r["sa"][6] and r["P"]
    lg = r["lg"]
    if have and "tres" in r and LR[lg][0] > 30:
        lrate = LR[lg][1] / LR[lg][0]   # rimbalzi di una squadra per 100 possessi nel campionato
        def g_(t, i):
            x = RB[(lg, t)]; return (x[i] + 6 * lrate) / (x[0] + 6)
        eh_ = r["pace"] * (g_(r["h"], 1) + g_(r["a"], 2)) / 2 / 100; ea_ = r["pace"] * (g_(r["a"], 1) + g_(r["h"], 2)) / 2 / 100
        base = r["pace"] * lrate / 100
        rb[per(r["d"])].append((lg, r["sh"][6] + r["sa"][6], eh_ + ea_, 2 * base, r["sh"][6] - r["sa"][6], eh_ - ea_))
    if have:
        for t, f_, a_ in ((r["h"], r["sh"][6], r["sa"][6]), (r["a"], r["sa"][6], r["sh"][6])):
            x = RB[(lg, t)]; x[0] = x[0] * 0.97 + 1; x[1] = x[1] * 0.97 + 100 * f_ / r["P"]; x[2] = x[2] * 0.97 + 100 * a_ / r["P"]
        x = LR[lg]; x[0] = x[0] * 0.998 + 2; x[1] = x[1] * 0.998 + 100 * (r["sh"][6] + r["sa"][6]) / r["P"]
srb = {}
for lg in set(x[0] for x in rb["scelta"]):
    S = [x for x in rb["scelta"] if x[0] == lg]; srb[lg] = (rob([x[1] - x[2] for x in S]), rob([x[4] - x[5] for x in S]))
out = {}
for p in ("verifica", "holdout"):
    d = collections.defaultdict(list); dw = collections.defaultdict(list); mae = [0, 0, 0]
    for x in rb[p]:
        st, ss = srb[x[0]]; L0 = round(x[3]) + 0.5
        for o in (-4, -2, 0, 2, 4):
            L_ = L0 + o; y = 1 if x[1] > L_ else 0
            d[x[0]].append(ll(1 - Phi((L_ - x[2]) / st), y) - ll(1 - Phi((L_ - x[3]) / st), y))
        if x[4] != 0: dw[x[0]].append(ll(Phi(x[5] / ss), 1 if x[4] > 0 else 0) - ll(0.5, 1 if x[4] > 0 else 0))
        mae[0] += abs(x[1] - x[2]); mae[1] += abs(x[1] - x[3]); mae[2] += 1
    a, b = np.concatenate(list(d.values())), np.concatenate(list(dw.values()))
    out[p] = {"totale rimbalzi: diff logloss (squadre − campionato)": round(float(a.mean()), 5), "z": round(float(a.mean() / (a.std() / math.sqrt(len(a)))), 2),
              "campionati_migliorati": f"{sum(np.mean(v) < 0 for v in d.values())}/{len(d)}", "errore medio squadre / campionato": f"{mae[0]/mae[2]:.2f} / {mae[1]/mae[2]:.2f}",
              "chi prende più rimbalzi: diff logloss (modello − 50%)": round(float(b.mean()), 5), "z_vincente": round(float(b.mean() / (b.std() / math.sqrt(len(b)))), 2),
              "campionati_migliorati_vincente": f"{sum(np.mean(v) < 0 for v in dw.values())}/{len(dw)}", "casi": len(rb[p])}
res["rimbalzi"] = out
json.dump(res, open(OUT, "w"), indent=1, ensure_ascii=False)
print(json.dumps(res, indent=1, ensure_ascii=False))
