"""Verifica sul campo delle modifiche del 15/10/2026 (controllo programmato del 17/10). Legge verifica_15ott.json (tools/verifica_15ott.js),
esiti.json (tools/esiti_extra.py con ESITI_DA=2024-07-01: corner, tiri, tiri in porta del 1° tempo e a 90' dai dati API reali) e pub/tempi.json.
1) corner per squadra con e senza i tiri non in porta: log-loss della Binomiale Negativa per squadra sul conteggio reale;
2) 1X2 corner e tiri con la correlazione (−0,20 / −0,24) contro l'indipendenza: log-loss, pareggi previsti/reali, calibrazione del favorito;
3) 1X2 per tempo (corner, tiri, tiri in porta; 1° tempo reale, 2° tempo = 90' − 1° tempo reale) contro le frequenze di lega (partite precedenti).
IC 95% da bootstrap a blocchi per settimana. Stampa solo numeri aggregati."""
import json, math, collections, random, sys, os
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from harness import nb_pmf, h2h
R = json.load(open("verifica_15ott.json")); ES = json.load(open("esiti.json")); HT = json.load(open("pub/tempi.json"))
def week(d): import datetime; return datetime.date.fromisoformat(d).isocalendar()[:2]
def boot(diffs, weeks, n=2000):
    diffs = np.array(diffs); W = collections.defaultdict(list)
    for d, w in zip(diffs, weeks): W[w].append(d)
    ks = list(W); rng = random.Random(7); ms = []
    for _ in range(n):
        s = []; [s.extend(W[rng.choice(ks)]) for _ in ks]; ms.append(np.mean(s))
    return float(diffs.mean()), float(np.percentile(ms, 2.5)), float(np.percentile(ms, 97.5))
def fmt(x): m, lo, hi = x; return f"{m:+.4f} (IC 95% {lo:+.4f} / {hi:+.4f})"
out = {"partite": len(R)}
# 1) corner per squadra
d1, w1 = [], []
for lg, d, h, a, v in R:
    c = v["corner"]; rc = v["reali"]
    if c[2] is None: continue
    rt = c[5]
    for mu, mu0, y in ((c[0], c[2], rc[0]), (c[1], c[3], rc[1])):
        K = max(60, y + 5); p1, p0 = nb_pmf(mu, rt, K)[y], nb_pmf(mu0, rt, K)[y]
        d1.append(-math.log(max(p1, 1e-12)) + math.log(max(p0, 1e-12))); w1.append(week(d))
out["1) corner per squadra, con tiri non in porta − senza (log-loss)"] = fmt(boot(d1, w1)) + f" · {len(d1)} squadre-partita · test −0,0019"
# 2) 1X2 corner e tiri: correlazione contro indipendenza
for nm, key, idx, cop, test in (("corner", "corner", (0, 1), -0.20, "−0,0018"), ("tiri", "tiri", (2, 3), -0.24, "−0,0012")):
    dd, ww, pd1, pd0, xr, fav = [], [], [], [], [], collections.defaultdict(lambda: [0, 0.0, 0])
    for lg, d, h, a, v in R:
        x = v.get(key)
        if not x: continue
        r, rt = (v["corner"][4], v["corner"][5]) if key == "corner" else (x[2], x[3])
        yh, ya = v["reali"][idx[0]], v["reali"][idx[1]]
        if yh is None or ya is None: continue
        P1, P0 = h2h(x[0], x[1], r, rt, cop), h2h(x[0], x[1], r, rt, 0.0)
        o = 0 if yh > ya else 1 if yh == ya else 2
        dd.append(-math.log(max(P1[o], 1e-12)) + math.log(max(P0[o], 1e-12))); ww.append(week(d))
        pd1.append(P1[1]); pd0.append(P0[1]); xr.append(o == 1)
        f = 0 if P1[0] >= P1[2] else 2; b = min(9, int(P1[f] * 10)); c = fav[b]; c[0] += 1; c[1] += P1[f]; c[2] += (o == f)
    out[f"2) 1X2 {nm}, correlazione − indipendenza (log-loss)"] = fmt(boot(dd, ww)) + f" · {len(dd)} partite · test {test}"
    out[f"2) 1X2 {nm}, pareggi previsti (correlazione / indipendenza) e reali"] = f"{np.mean(pd1):.3f} / {np.mean(pd0):.3f} · reali {np.mean(xr):.3f}"
    out[f"2) 1X2 {nm}, favorito previsto/uscito per fascia"] = " · ".join(f"{c[1]/c[0]:.2f}/{c[2]/c[0]:.2f} ({c[0]})" for _, c in sorted(fav.items()) if c[0] >= 15)
# 3) per tempo contro le frequenze di lega
hist = collections.defaultdict(list)   # (lega, stat, tempo) → [(data, esito)]
for key, e in ES.items():
    lg, d = key.split("|")[:2]
    for i, k in enumerate(("c", "s", "st")):
        h1 = e.get(k + "1")
        if not h1: continue
        o1 = 0 if h1[0] > h1[1] else 1 if h1[0] == h1[1] else 2; hist[(lg, k, 1)].append((d, o1))
        if e.get("tot"):
            th, ta = e["tot"][0][i], e["tot"][1][i]; h2, a2 = th - h1[0], ta - h1[1]
            if h2 >= 0 and a2 >= 0: hist[(lg, k, 2)].append((d, 0 if h2 > a2 else 1 if h2 == a2 else 2))
for v in hist.values(): v.sort()
mk = {"c": ("corner", "corner"), "s": ("tiri", "tiri"), "st": ("tiri in porta", "tip")}
for k, (nm, key) in mk.items():
    for half in (1, 2):
        dd, ww = [], []
        for lg, d, h, a, v in R:
            e = ES.get(f"{lg}|{d}|{h}|{a}"); x = v.get(key); H = (HT.get("campionati") or {}).get(lg, {}).get(k)
            if not e or not x or not H or not e.get(k + "1"): continue
            h1 = e[k + "1"]
            if half == 1: yh, ya = h1
            else:
                if not e.get("tot"): continue
                i = ("c", "s", "st").index(k); yh, ya = e["tot"][0][i] - h1[0], e["tot"][1][i] - h1[1]
                if yh < 0 or ya < 0: continue
            sh = (H[0], H[1]) if half == 1 else (1 - H[0], 1 - H[1])
            P = h2h(x[0] * sh[0], x[1] * sh[1], None, HT["r"][k][0], 0.0)
            prev = [o for dd_, o in hist[(lg, k, half)] if dd_ < d]
            if len(prev) < 50: continue
            fr = np.bincount(prev, minlength=3) / len(prev)
            o = 0 if yh > ya else 1 if yh == ya else 2
            dd.append(-math.log(max(P[o], 1e-12)) + math.log(max(fr[o], 1e-12))); ww.append(week(d))
        if dd: out[f"3) 1X2 {nm} {half}° tempo, Prevista − frequenze di lega (log-loss)"] = fmt(boot(dd, ww)) + f" · {len(dd)} partite"
json.dump(out, open("verifica_15ott_esito.json", "w"), indent=1, ensure_ascii=False)
for k, v in out.items(): print(f"::notice title=Verifica 15/10 · {k[:60]}::{v}")
print(json.dumps(out, indent=1, ensure_ascii=False))
