"""Audit completo di calibrazione e test di ricalibrazione (9/11/2026, richiesta di Denny). Legge calib_full_*.json (tools/calib_full.js),
l'archivio privato data/apif.json e il ramo tempi (statistiche per tempo). Stampa SOLO numeri aggregati.
1. Per mercato e periodo (scelta ≤ 30/6/2024 · verifica 2024-25 · holdout dal 1/7/2025 · ultimi 120 giorni): scarto (uscita − dichiarata),
   ECE per fasce del lato favorito (50-60, 60-70, 70-80, 80+), log-loss, Brier. Over/Under: scarto per distanza della linea dall'atteso (code).
2. Ricalibrazione walk-forward per mercato: Platt (a + b·logit p) stimato ogni mese sulle sole righe dei mesi precedenti (almeno 3.000);
   per gli Over/Under anche con la distanza linea − atteso come seconda variabile (corregge la dispersione sulle code).
   Regola di adozione: log-loss migliore in modo significativo nella verifica (IC 95% bootstrap a blocchi settimanali sotto zero), stesso verso
   nell'holdout, più della metà dei campionati migliorati (verifica + holdout).
3. 1° tempo (dati per tempo dal 2024-25: verifica e holdout): attesi a 90' dell'app × quota del 1° tempo del campionato per sede (solo partite
   precedenti); gol e cartellini Poisson, corner/tiri/tiri in porta Binomiale Negativa con r di squadra di data/tempi.json, fuorigioco r 10,68."""
import json, glob, os, sys, math, collections, datetime, csv, io, traceback
import numpy as np
from scipy.special import gammaln, expit, logit
from scipy.optimize import minimize
sys.excepthook = lambda t, v, tb: print("::error title=Calibrazione completa::" + " | ".join(traceback.format_exception(t, v, tb)).replace("\n", " ")[-1500:])
OUT = []
def note(t, m): OUT.append((t, m)); print(f"::notice title=Calibrazione · {t}::" + m.replace("%", "%25").replace("\n", " "))
E, X = [], []
for f in sorted(glob.glob("calib_full_*.json")):
    d = json.load(open(f)); E += d["E"]; X += d["X"]
LAST120 = (datetime.date.today() - datetime.timedelta(days=120)).isoformat()
per = lambda d: "scelta" if d <= "2024-06-30" else "verifica" if d <= "2025-06-30" else "holdout"
PERS = ("scelta", "verifica", "holdout", "120 giorni")
def metrics(P, Y):
    P = np.clip(np.array(P, float), 1e-4, 1 - 1e-4); Y = np.array(Y, float); n = len(P)
    fav = np.where(P >= 0.5, P, 1 - P); yf = np.where(P >= 0.5, Y, 1 - Y)
    bands = [(0.5, 0.6), (0.6, 0.7), (0.7, 0.8), (0.8, 1.01)]; ece = 0; bt = []
    for lo, hi in bands:
        s = (fav >= lo) & (fav < hi)
        if s.sum(): ece += s.sum() * abs(yf[s].mean() - fav[s].mean()); bt.append(f"{int(lo * 100)}+: {100 * fav[s].mean():.0f}→{100 * yf[s].mean():.0f} ({s.sum()})")
    ll = -np.mean(Y * np.log(P) + (1 - Y) * np.log(1 - P)); br = np.mean((P - Y) ** 2)
    return dict(n=n, p=P.mean(), y=Y.mean(), bias=Y.mean() - P.mean(), se=math.sqrt(max(Y.mean() * (1 - Y.mean()), 1e-9) / n), ece=ece / n, ll=ll, br=br, bands=" · ".join(bt))
def fmt(m): return f"{m['n']} · dich. {100 * m['p']:.1f}% usc. {100 * m['y']:.1f}% (scarto {100 * m['bias']:+.1f} ±{196 * m['se']:.1f}) · ECE {100 * m['ece']:.1f} · LL {m['ll']:.4f} · Brier {m['br']:.4f}"
# ---------------- 1 · audit 90' ----------------
byM = collections.defaultdict(list)
for e in E: byM[e[2]].append(e)
SUMMARY = {}
for mk in sorted(byM):
    L = byM[mk]; txt = []
    for pn in PERS:
        S = [e for e in L if (e[1] >= LAST120 if pn == "120 giorni" else per(e[1]) == pn)]
        if len(S) < 200: continue
        m = metrics([e[3] for e in S], [e[4] for e in S]); SUMMARY[(mk, pn)] = m; txt.append(f"{pn}: {fmt(m)}")
    if txt: note(f"audit · {mk}", " ‖ ".join(txt) + (f" ‖ fasce (holdout): {SUMMARY[(mk, 'holdout')]['bands']}" if (mk, "holdout") in SUMMARY else ""))
# code degli Over/Under: scarto per distanza linea − atteso (verifica + holdout)
tails = []
for mk in sorted(byM):
    if "Over" not in mk or mk.startswith("Gol"): continue
    L = [e for e in byM[mk] if e[5] is not None and per(e[1]) != "scelta"]
    bins = collections.defaultdict(list)
    for e in L: bins[max(-4, min(4, round(e[5])))].append(e)
    t = []
    for b in sorted(bins):
        S = bins[b]
        if len(S) < 300: continue
        p, y = np.mean([e[3] for e in S]), np.mean([e[4] for e in S]); t.append(f"{b:+d}: {100 * p:.0f}→{100 * y:.0f} ({100 * (y - p):+.1f})")
    if t: tails.append(f"{mk}: " + " · ".join(t))
note("code degli Over/Under (linea − atteso: dichiarata → uscita, verifica + holdout)", " ‖ ".join(tails))
# ---------------- 2 · ricalibrazione walk-forward ----------------
def fit(Z, Y, l2=1.0):
    Z = np.column_stack([np.ones(len(Z)), Z]); Y = np.array(Y, float)
    def f(b):
        q = Z @ b; return np.sum(np.logaddexp(0, q) - Y * q) + l2 * np.sum((b[1:] - np.r_[1, np.zeros(len(b) - 2)]) ** 2)
    def g(b):
        q = expit(Z @ b); gr = Z.T @ (q - Y); gr[1:] += 2 * l2 * (b[1:] - np.r_[1, np.zeros(len(b) - 2)]); return gr
    b0 = np.r_[0, 1, np.zeros(Z.shape[1] - 2)]
    return minimize(f, b0, jac=g, method="L-BFGS-B").x
def week(d): return datetime.date.fromisoformat(d).isocalendar()[:2]
def boot(dl, wk, n=2000):
    G = collections.defaultdict(float); C = collections.Counter()
    for v, w in zip(dl, wk): G[w] += v; C[w] += 1
    keys = list(G); s = np.array([G[k] for k in keys]); c = np.array([C[k] for k in keys]); rng = np.random.default_rng(3)
    bs = []
    for _ in range(n):
        i = rng.integers(0, len(keys), len(keys)); bs.append(s[i].sum() / c[i].sum())
    return s.sum() / c.sum(), np.percentile(bs, 2.5), np.percentile(bs, 97.5)
RESULTS = {}
def recal(mk, L, use_off):
    L = sorted(L, key=lambda e: e[1]); months = sorted({e[1][:7] for e in L}); rows = []
    for mo in months:
        prev = [e for e in L if e[1][:7] < mo]; cur = [e for e in L if e[1][:7] == mo]
        if len(prev) < 3000 or not cur: continue
        if len(prev) > 60000: prev = prev[-60000:]
        Zp = np.column_stack([logit(np.clip([e[3] for e in prev], 1e-4, 1 - 1e-4))] + ([np.array([e[5] or 0 for e in prev])] if use_off else []))
        b = fit(Zp, [e[4] for e in prev])
        for e in cur:
            z = [logit(min(max(e[3], 1e-4), 1 - 1e-4))] + ([e[5] or 0] if use_off else [])
            q = expit(b[0] + np.dot(b[1:], z)); rows.append((e, q))
    if not rows: return None
    out = {}
    for pn in ("verifica", "holdout"):
        R = [(e, q) for e, q in rows if per(e[1]) == pn]
        if len(R) < 300: continue
        P = np.clip([e[3] for e, _ in R], 1e-4, 1 - 1e-4); Q = np.clip([q for _, q in R], 1e-4, 1 - 1e-4); Y = np.array([e[4] for e, _ in R])
        llp = -(Y * np.log(P) + (1 - Y) * np.log(1 - P)); llq = -(Y * np.log(Q) + (1 - Y) * np.log(1 - Q))
        mean, lo, hi = boot(llq - llp, [week(e[1]) for e, _ in R])
        lgd = collections.defaultdict(list)
        for (e, _), v in zip(R, llq - llp): lgd[e[0]].append(v)
        out[pn] = dict(n=len(R), d=mean, lo=lo, hi=hi, lg=lgd, before=metrics(P, Y), after=metrics(Q, Y))
    if "verifica" not in out or "holdout" not in out: return None
    lgs = collections.defaultdict(list)
    for pn in ("verifica", "holdout"):
        for k, v in out[pn]["lg"].items(): lgs[k] += v
    share = np.mean([np.mean(v) < 0 for v in lgs.values() if len(v) >= 30]) if lgs else 0
    ok = out["verifica"]["hi"] < 0 and out["holdout"]["d"] < 0 and share > 0.5
    return dict(out=out, share=share, ok=ok)
for mk in sorted(byM):
    for use_off in ((False, True) if "Over" in mk and not mk.startswith("Gol") else (False,)):
        r = recal(mk, byM[mk], use_off)
        if not r: continue
        RESULTS[(mk, use_off)] = r; v, h = r["out"]["verifica"], r["out"]["holdout"]
        note(f"ricalibrazione · {mk}{' (con distanza dalla linea)' if use_off else ''} · {'PASSA' if r['ok'] else 'non passa'}",
             f"verifica: log-loss {v['d']:+.5f} [{v['lo']:+.5f}, {v['hi']:+.5f}] · scarto {100 * v['before']['bias']:+.1f} → {100 * v['after']['bias']:+.1f} · ECE {100 * v['before']['ece']:.1f} → {100 * v['after']['ece']:.1f} ‖ "
             f"holdout: log-loss {h['d']:+.5f} [{h['lo']:+.5f}, {h['hi']:+.5f}] · scarto {100 * h['before']['bias']:+.1f} → {100 * h['after']['bias']:+.1f} · ECE {100 * h['before']['ece']:.1f} → {100 * h['after']['ece']:.1f} ‖ campionati migliorati {100 * r['share']:.0f}%")
# coefficienti finali (tutte le righe) per i mercati che passano → calib_coef.json (numeri aggregati, pubblicabili)
COEF = {}
for (mk, use_off), r in RESULTS.items():
    if not r["ok"]: continue
    L = byM[mk][-80000:]
    Z = np.column_stack([logit(np.clip([e[3] for e in L], 1e-4, 1 - 1e-4))] + ([np.array([e[5] or 0 for e in L])] if use_off else []))
    b = fit(Z, [e[4] for e in L]); key = mk + (" · distanza" if use_off else "")
    if mk in {k.split(" · distanza")[0] for k in COEF}:   # tiene la versione con la log-loss migliore in verifica
        old = [k for k in COEF if k.split(" · distanza")[0] == mk][0]
        if RESULTS[(mk, " · distanza" in old)]["out"]["verifica"]["d"] <= r["out"]["verifica"]["d"]: continue
        del COEF[old]
    COEF[key] = [round(float(x), 4) for x in b]
json.dump({"agg": datetime.date.today().isoformat(), "coef": COEF}, open("calib_coef.json", "w"))
note("coefficienti dei mercati che passano", json.dumps(COEF) if COEF else "nessuno")

# ---------------- 3 · 1° tempo ----------------
try:
    AP = json.load(open("data/apif.json"))["partite"]
    RES = collections.defaultdict(list)
    for bf in ("pub/bundle_storico.json", "pub/bundle.json"):
        for f in json.load(open(bf))["files"]:
            for r in csv.DictReader(io.StringIO(f["text"])):
                try: d = datetime.datetime.strptime(r["Date"], "%d/%m/%Y").date(); RES[(r["Div"], int(r["FTHG"]), int(r["FTAG"]))].append((d, r["HomeTeam"], r["AwayTeam"]))
                except Exception: pass
    votes = collections.defaultdict(collections.Counter)
    for fid, v in AP.items():
        try: d0 = datetime.date.fromisoformat(v[0][:10]); hg, ag = int(v[4]), int(v[5])
        except Exception: continue
        for d, h, a in RES.get((v[1], hg, ag), []):
            if abs((d - d0).days) <= 1: votes[(v[1], v[2])][h] += 1; votes[(v[1], v[3])][a] += 1
    MAP = {k: c.most_common(1)[0][0] for k, c in votes.items() if c.most_common(1)[0][1] >= 3}
    XI = {}
    for x in X:
        for dd in (0, -1, 1): XI[(x[0], (datetime.date.fromisoformat(x[1]) + datetime.timedelta(days=dd)).isoformat(), x[2], x[3])] = x
    HSTAT = {"Corner": 0, "Tiri": 1, "Tiri in porta": 2, "Fuorigioco": 4, "Cartellini": (5, 6)}
    TR = json.load(open("pub/tempi.json"))["r"] if os.path.exists("pub/tempi.json") else {}
    RTEAM = {"Corner": TR.get("c", [0, 3.37])[1], "Tiri": TR.get("s", [0, 8.79])[1], "Tiri in porta": TR.get("st", [0, 7.34])[1], "Fuorigioco": 10.68, "Cartellini": None, "g": None}
    def nbp(mu, r, K=40):
        k = np.arange(K + 1)
        if not r: return np.exp(-mu + k * np.log(mu) - gammaln(k + 1))
        q = r / (r + mu); return np.exp(gammaln(k + r) - gammaln(r) - gammaln(k + 1) + r * np.log(q) + k * np.log1p(-q))
    H1 = []
    rows = []
    for fn in glob.glob("tempi/*.json"):
        lg = os.path.basename(fn)[:-5]
        for fid, v in json.load(open(fn)).items():
            if not (v[3] and v[4] and v[5] and v[6]): continue
            h, a = MAP.get((lg, v[1])), MAP.get((lg, v[2]))
            if h and a: rows.append((v[0][:10], lg, h, a, v))
    rows.sort(key=lambda r: r[0])
    acc = collections.defaultdict(lambda: [0.0, 0.0, 0.0, 0.0])   # (lg, stat): 1°T casa, tot casa, 1°T ospite, tot ospite
    for d, lg, h, a, v in rows:
        x = XI.get((lg, d, h, a))
        for st, ix in list(HSTAT.items()) + [("g", None)]:
            if st == "g":
                if not x or not x[5]: continue
                # gol del 1° tempo dal risultato all'intervallo; totale dai gol attesi
                h1, a1 = x[5]; ht = hf = None
                tot = None
            else:
                ii = ix if isinstance(ix, tuple) else (ix,)
                try:
                    h1 = sum(v[3][j] for j in ii); a1 = sum(v[4][j] for j in ii); h2 = sum(v[5][j] for j in ii); a2 = sum(v[6][j] for j in ii)
                except Exception: continue
                if None in (h1, a1, h2, a2): continue
                tot = (h1 + h2, a1 + a2)
            A_ = acc[(lg, st)]
            xs = x[4] if x else {}
            key90 = "g" if st == "g" else st
            if x and key90 in xs and A_[1] > 300 and A_[3] > 300:
                sh, sa = A_[0] / A_[1], A_[2] / A_[3]; mh, ma = xs[key90][0] * sh, xs[key90][1] * sa; r_ = RTEAM.get(st)
                ph, pa = nbp(mh, r_), nbp(ma, r_); M = np.outer(ph, pa); M /= M.sum()
                rr = 0 if h1 > a1 else 1 if h1 == a1 else 2
                for lab, p, y in (("1", np.tril(M, -1).sum(), rr == 0), ("X", np.trace(M), rr == 1), ("2", np.triu(M, 1).sum(), rr == 2)):
                    H1.append((lg, d, f"1°T {st} 1X2 · {lab}", float(p), int(y), None))
                tt = np.convolve(ph, pa)
                for o in (-1.5, -0.5, 0.5, 1.5):
                    Lx = round(mh + ma) + o
                    if Lx > 0: H1.append((lg, d, f"1°T {st} totale Over", float(tt[int(math.floor(Lx)) + 1:].sum() / tt.sum()), int(h1 + a1 > Lx), Lx - mh - ma))
            if st == "g":
                if x and "g" in xs:   # quota del 1° tempo dei gol: gol del 1° tempo / gol attesi a 90' (accumulata)
                    A_[0] += h1; A_[1] += xs["g"][0]; A_[2] += a1; A_[3] += xs["g"][1]
            else:
                A_[0] += h1; A_[1] += tot[0]; A_[2] += a1; A_[3] += tot[1]
    byH = collections.defaultdict(list)
    for e in H1: byH[e[2]].append(e)
    for mk in sorted(byH):
        L = byH[mk]; txt = []
        for pn in ("verifica", "holdout", "120 giorni"):
            S_ = [e for e in L if (e[1] >= LAST120 if pn == "120 giorni" else per(e[1]) == pn)]
            if len(S_) < 200: continue
            txt.append(f"{pn}: {fmt(metrics([e[3] for e in S_], [e[4] for e in S_]))}")
        if txt: note(f"audit 1° tempo · {mk}", " ‖ ".join(txt))
    for mk in sorted(byH):
        L = [list(e) for e in byH[mk]]
        for use_off in ((False, True) if "Over" in mk else (False,)):
            r = recal(mk, L, use_off)
            if not r: continue
            v, h = r["out"]["verifica"], r["out"]["holdout"]
            note(f"ricalibrazione 1° tempo · {mk}{' (con distanza)' if use_off else ''} · {'PASSA' if r['ok'] else 'non passa'}",
                 f"verifica: log-loss {v['d']:+.5f} [{v['lo']:+.5f}, {v['hi']:+.5f}] · scarto {100 * v['before']['bias']:+.1f} → {100 * v['after']['bias']:+.1f} ‖ holdout: {h['d']:+.5f} · scarto {100 * h['before']['bias']:+.1f} → {100 * h['after']['bias']:+.1f} ‖ campionati {100 * r['share']:.0f}%")
except Exception as e_:
    note("1° tempo", "non calcolato: " + " | ".join(traceback.format_exception(type(e_), e_, e_.__traceback__))[-600:])
json.dump(OUT, open("calib_report.json", "w"), ensure_ascii=False)
