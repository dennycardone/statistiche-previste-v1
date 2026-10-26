"""Agente di ricerca · ipotesi 3 (formazioni sui cartellini) e 1 (riposo sui cartellini). Modello cartellini v3 dell'app (cards_model.py,
con derby) più una variabile alla volta, pesi stimati sulle sole partite precedenti (come il test del derby del 24/10):
  XC  propensione ai cartellini dei titolari di oggi rispetto agli abituali (somma delle due squadre, log)
  XF  propensione ai falli commessi dei titolari (somma delle due squadre, log)
  RS  riposo: giorni dall'ultima partita (media delle due squadre, tetto 14)
Giudizio: log-loss della Binomiale Negativa sul totale, verifica (lug 2024 – giu 2025) e holdout (da lug 2025), IC al 95%."""
import sys, math, types, pickle, json, datetime
sys.path.insert(0, "/home/claude/statistiche-previste-v1"); sys.path.insert(0, "/tmp/claude-0/h2h")
from load import load
FEAT = pickle.load(open("/home/claude/research/p2/feat2.pkl", "rb")); REST = pickle.load(open("/home/claude/research/p2/feat_rest.pkl", "rb"))
IDX = {}
for src, D in (("xi", FEAT), ("rest", REST)):
    for k, f in D.items(): IDX[(src, k[0], k[1], k[2], k[3])] = f
def look(src, lg, d, h, a):
    for dd in (0, -1, 1):
        x = (datetime.date.fromisoformat(d) + datetime.timedelta(days=dd)).isoformat()
        f = IDX.get((src, lg, x, h, a))
        if f: return f
    return None
def XC(lg, d, h, a, key):
    f = look("xi", lg, d, h, a)
    if not f or not f.get("h") or not f.get("a"): return 0.0
    return (f["h"].get("xi_" + key, 0) + f["a"].get("xi_" + key, 0))
def RS(lg, d, h, a):
    f = look("rest", lg, d, h, a)
    if not f or not f.get("h") or not f.get("a"): return 0.0
    return (f["h"]["xi_rest"] + f["a"]["xi_rest"]) / 2 - 6.0
src = open("/home/claude/statistiche-previste-v1/cards_model.py").read()
def variant(extra):
    s = src
    if extra:
        s = s.replace('FEATS = ["E", "R", "FF", "H", "nlo", "R10", "DB"]', 'FEATS = ["E", "R", "FF", "H", "nlo", "R10", "DB", "' + extra + '"]')
        expr = {"XC": "XC_(lg, r['d'][:10], r['h'], r['a'], 'crd')", "XF": "XC_(lg, r['d'][:10], r['h'], r['a'], 'fc')", "RS": "RS_(lg, r['d'][:10], r['h'], r['a'])"}[extra]
        s = s.replace('''"DB": 1.0 if is_derby(lg, r['h'], r['a']) else 0.0}''', '''"DB": 1.0 if is_derby(lg, r['h'], r['a']) else 0.0, "''' + extra + '''": ''' + expr + "}")
    m = types.ModuleType("cmx"); m.__dict__.update(XC_=XC, RS_=RS); exec(compile(s, "cmx", "exec"), m.__dict__); return m
def nbll(y, mu, a):
    n = 1 / a; return -(math.lgamma(y + n) - math.lgamma(n) - math.lgamma(y + 1) + n * math.log(n / (n + mu)) + y * math.log(mu / (n + mu)))
ms = load(); res = {}
for name in ("base", "XC", "XF", "RS"):
    M = variant(None if name == "base" else name); F = M.features(ms)
    for cut, end in (("2024-07", "2025-07"), ("2025-07", "2026-11")):
        tr = [f for f in F if f and f["played"] and f["d"] < cut + "-01"]
        te = [(i, f) for i, f in enumerate(F) if f and f["played"] and cut + "-01" <= f["d"] < end + "-01"]
        b, a = M.fit(tr); res[(name, cut)] = ({i: nbll(f["T"], M.predict(f, b)["mu"], a) for i, f in te}, b)
    print(name, {c: [round(v, 3) for v in res[(name, c)][1]] for c in ("2024-07", "2025-07")}, flush=True)
for name in ("XC", "XF", "RS"):
    out = [name]
    for c in ("2024-07", "2025-07"):
        o, B = res[(name, c)][0], res[("base", c)][0]; d = [o[i] - B[i] for i in o if i in B]; n = len(d); m = sum(d) / n
        sd = math.sqrt(sum((x - m) ** 2 for x in d) / n / n); out.append(f"{c}: n={n} Δ log-loss {m:+.4f} ±{1.96 * sd:.4f}")
    print(" | ".join(out), flush=True)
