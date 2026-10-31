"""Probabilità corretta per l'app (30/10/2026, vista Operatività): stessi pesi dello studio Quota 2/3 (tools/quota23.py), stimati su
TUTTI i giorni già giocati dell'archivio 1xBet (quota ultima prima del fischio). Pubblica SOLO i coefficienti (numeri aggregati):
  p_corretta = 1 / (1 + e^-(b0 + b1·logit(p Prevista) + b2·logit(p 1xBet senza margine)))
Gruppi: "statistiche" (1X2 corner, tiri, tiri in porta, falli, fuorigioco, gialli e Over/Under cartellini) e "gol" (solo riferimento).
Più un controllo fuori campione (pesi stimati sui giorni precedenti, come nello studio): log-loss di Prevista, 1xBet e corretta."""
import json, math, collections, datetime, statistics, sys, traceback
import numpy as np
sys.excepthook = lambda t, v, tb: print("::error title=Probabilità corretta::" + " | ".join(traceback.format_exception(t, v, tb)).replace("\n", " ")[-1500:])
C = json.load(open("q23_candidati.json"))
GOL = {"1X2 gol", "Over/Under 1.5", "Over/Under 2.5", "Over/Under 3.5", "Gol/No gol"}
grp = collections.defaultdict(list)
for c in C: grp[(c["key"], c["mk"])].append(c)
for L in grp.values():
    s_ = sum(1 / c["q1"] for c in L if c.get("q1"))
    full = all(c.get("q1") for c in L)
    for c in L: c["m"] = (1 / c["q1"]) / s_ if full and s_ > 0 else None
lg_ = lambda p: math.log(min(max(p, 1e-4), 1 - 1e-4) / (1 - min(max(p, 1e-4), 1 - 1e-4)))
def fit_lr(X, y, l2=1.0):   # identica a tools/quota23.py
    X = np.hstack([np.ones((len(X), 1)), np.array(X)]); y = np.array(y, float); b = np.zeros(X.shape[1])
    for _ in range(50):
        p = 1 / (1 + np.exp(-X @ b)); W = p * (1 - p); g = X.T @ (y - p) - l2 * np.r_[0, b[1:] - 1 * (np.arange(1, len(b)) == 1)]
        H = X.T @ (X * W[:, None]) + l2 * np.diag(np.r_[0, np.ones(len(b) - 1)]); b = b + np.linalg.solve(H, g)
    return b
OUT = {"agg": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M"), "quota": "ultima prima del fischio", "gruppi": {}}
for name, test in (("statistiche", lambda c: c["mk"] not in GOL), ("gol", lambda c: c["mk"] in GOL)):
    E = [c for c in C if test(c) and c["m"] is not None]
    if len(E) < 300: continue
    b = fit_lr([[lg_(c["p"]), lg_(c["m"])] for c in E], [c["y"] for c in E])
    days = sorted({c["d"] for c in E}); ev = collections.defaultdict(list)
    for c in E: ev[c["d"]].append(c)
    om, ob, op, ys = [], [], [], []
    for i, d in enumerate(days):
        tr = [c for dd in days[:i] for c in ev[dd]]
        if i < 7 or len(tr) < 300: continue
        bb = fit_lr([[lg_(c["p"]), lg_(c["m"])] for c in tr], [c["y"] for c in tr])
        for c in ev[d]:
            om.append(c["p"]); ob.append(c["m"]); op.append(1 / (1 + math.exp(-(bb[0] + bb[1] * lg_(c["p"]) + bb[2] * lg_(c["m"]))))); ys.append(c["y"])
    if name == "statistiche":   # 31/10/2026: coefficienti stimati sui soli giorni precedenti, per la ricostruzione dello storico di Operatività
        OUT["per_giorno"] = {}
        for i, d in enumerate(days[-10:], start=len(days) - 10):
            tr = [c for dd in days[:i] for c in ev[dd]]
            if i >= 7 and len(tr) >= 300: OUT["per_giorno"][d] = [round(float(x), 4) for x in fit_lr([[lg_(c["p"]), lg_(c["m"])] for c in tr], [c["y"] for c in tr])]
    L_ = lambda P: round(-statistics.mean(math.log(max(1e-6, p if y else 1 - p)) for p, y in zip(P, ys)), 4) if ys else None
    OUT["gruppi"][name] = {"b": [round(float(x), 4) for x in b], "esiti": len(E), "giorni": len(days), "dal": days[0], "al": days[-1],
                           "fuori_campione": {"esiti": len(ys), "logloss_prevista": L_(om), "logloss_1xbet": L_(ob), "logloss_corretta": L_(op)}}
json.dump(OUT, open("corretta.json", "w"), separators=(",", ":"))
print("::notice title=Probabilità corretta::" + " ‖ ".join(f"{k}: pesi {v['b']} · {v['esiti']} esiti in {v['giorni']} giorni · fuori campione {v['fuori_campione']}" for k, v in OUT["gruppi"].items()))
