"""Studio del sistema di gioco (3/11/2026, richiesta di Denny). Gira nel runner sull'archivio privato delle quote 1xBet; stampa SOLO numeri
aggregati. Input (prodotti nello stesso runner, solo dati precedenti a ogni partita):
  q23_candidati.json (tools/quota23.js): 1X2 corner, tiri, tiri in porta, falli (anche con le formazioni ufficiali), fuorigioco, gialli
  rm_all.json (tools/radar_mercato.js): Over/Under 1xBet sulla linea più equilibrata di corner, tiri, tiri in porta, falli, cartellini
  pub/extra.json: arbitro (effetto sui cartellini) e derby, per i filtri sui cartellini
Probabilità corretta: logistica su logit(Prevista) e logit(1xBet senza margine), un solo gruppo "statistiche" come l'app, stimata giorno
per giorno sui soli giorni precedenti (almeno 7 giorni e 300 esiti). Quota: ultima vista prima del fischio. Puntata fissa 1 unità.
Passi:
  1  mercato per mercato (valore atteso corretto > 0): giocate, presa, yield, profitto, calo massimo, rendimento/rischio, IC 95% e p-value
     (bootstrap per giorno, 10.000)
  2  griglia di filtri (EV minimo × fascia di quota × concordanza × mercati tenuti) scelta SOLO sulla prima metà dei giorni, verificata sulla
     seconda; quante combinazioni provate e posizione della scelta nella seconda metà (contro la selezione fortunata)
  3  portafogli con la cassa (100, Kelly 1/8, tetto 3% e 10% al giorno): sole singole, sola doppia (quota 1,85-2,20), 80/20; Monte Carlo
     10.000 (giorni ricampionati e ordine rimescolato): probabilità di profitto, calo massimo al 95° percentile, giocate a settimana."""
import json, math, os, sys, collections, random, itertools, traceback
import numpy as np
sys.excepthook = lambda t, v, tb: print("::error title=Sistema::" + " | ".join(traceback.format_exception(t, v, tb)).replace("\n", " ")[-1500:])
note = lambda t, m: print(f"::notice title=Sistema · {t}::" + m.replace("%", "%25").replace("\n", " "))
rng = np.random.default_rng(11)
EX = json.load(open("pub/extra.json"))["partite"] if os.path.exists("pub/extra.json") else {}
lg_ = lambda p: math.log(min(max(p, 1e-4), 1 - 1e-4) / (1 - min(max(p, 1e-4), 1 - 1e-4)))
O = []   # esiti: key, d, mkt, side, p, q, y, m (1xBet senza margine), conc (concordanza), extra
# 1X2 delle statistiche
C = json.load(open("q23_candidati.json"))
G = collections.defaultdict(dict)
for c in C:
    if c["mk"].startswith("1X2") and c["mk"] != "1X2 gol" and c.get("q1"): G[(c["key"], c["mk"])][c["side"]] = c
for (key, mk), S in G.items():
    if not all(s in S for s in "1X2"): continue
    inv = {s: 1 / S[s]["q1"] for s in S}; t = sum(inv.values())
    bfav = "1" if S["1"]["q1"] <= S["2"]["q1"] else "2"; pfav = "1" if S["1"]["p"] >= S["2"]["p"] else "2"
    for s in "1X2":
        conc = "pareggio" if s == "X" else ("concorde" if s == bfav == pfav else "inversione" if s == pfav != bfav else "contro Prevista")
        O.append(dict(key=key, d=key.split("|")[1], mkt=mk, side=s, p=S[s]["p"], q=S[s]["q1"], y=S[s]["y"], m=inv[s] / t, conc=conc,
                      qm=S[s].get("q1m") if all(S[x].get("q1m") for x in "1X2") else None,   # 6/11/2026: media dei book, in parallelo
                      mm=(1 / S[s]["q1m"]) / sum(1 / S[x]["q1m"] for x in "1X2") if all(S[x].get("q1m") for x in "1X2") else None))
        if mk == "1X2 falli" and S[s].get("pxi") is not None:
            O.append(dict(key=key, d=key.split("|")[1], mkt="1X2 falli · formazioni", side=s, p=S[s]["pxi"], q=S[s]["q1"], y=S[s]["y"], m=inv[s] / t, conc=conc))
# Over/Under (linea più equilibrata)
FAM = {"c": "O/U corner totali", "hc": "O/U corner squadra", "ac": "O/U corner squadra", "k": "O/U cartellini totali", "hk": "O/U cartellini squadra", "ak": "O/U cartellini squadra",
       "st": "O/U tiri in porta totali", "hst": "O/U tiri in porta squadra", "ast": "O/U tiri in porta squadra", "s": "O/U tiri totali", "f": "O/U falli totali", "hf": "O/U falli squadra", "af": "O/U falli squadra"}
if os.path.exists("rm_all.json"):
    for r in json.load(open("rm_all.json")):
        mo = (1 / r["o"]) / (1 / r["o"] + 1 / r["u"])
        for side, p, q, y, m in (("Over", r["po"], r["o"], r["over"], mo), ("Under", 1 - r["po"], r["u"], 1 - r["over"], 1 - mo)):
            conc = "concorde" if (p > 0.5 and m > 0.5) else "inversione" if (p > 0.5 and m <= 0.5) else "contro Prevista"
            O.append(dict(key=r["key"], d=r["d"], mkt=FAM.get(r["k"], r["k"]), side=side, p=p, q=q, y=y, m=m, conc=conc, L=r["L"]))
# filtri arbitro / derby per i cartellini (extra.json: [3] effetto arbitro sui cartellini, [8][5] derby)
for o in O:
    x = EX.get(o["key"])
    o["arb"] = (x[3] or 1.0) if x and len(x) > 3 and x[3] else 1.0
    o["derby"] = 1 if x and len(x) > 8 and x[8] and len(x[8]) > 5 and x[8][5] and x[8][5] > 1.0 else 0
# probabilità corretta walk-forward (gruppo unico, come l'app)
def fit_lr(X, y, l2=1.0):
    X = np.hstack([np.ones((len(X), 1)), np.array(X)]); y = np.array(y, float); b = np.zeros(X.shape[1])
    for _ in range(50):
        p = 1 / (1 + np.exp(-X @ b)); W = p * (1 - p); g = X.T @ (y - p) - l2 * np.r_[0, b[1:] - 1 * (np.arange(1, len(b)) == 1)]
        H = X.T @ (X * W[:, None]) + l2 * np.diag(np.r_[0, np.ones(len(b) - 1)]); b = b + np.linalg.solve(H, g)
    return b
days = sorted({o["d"] for o in O}); byd = collections.defaultdict(list)
for o in O: byd[o["d"]].append(o)
for i, d in enumerate(days):
    tr = [o for dd in days[:i] for o in byd[dd] if "formazioni" not in o["mkt"]]
    if i < 7 or len(tr) < 300: continue
    b = fit_lr([[lg_(o["p"]), lg_(o["m"])] for o in tr], [o["y"] for o in tr])
    for o in byd[d]:
        o["pc"] = 1 / (1 + math.exp(-(b[0] + b[1] * lg_(o["p"]) + b[2] * lg_(o["m"])))); o["ev"] = o["pc"] * o["q"] - 1
        if o.get("qm"): o["pcm"] = 1 / (1 + math.exp(-(b[0] + b[1] * lg_(o["p"]) + b[2] * lg_(o["mm"])))); o["evm"] = o["pcm"] * o["qm"] - 1
E = [o for o in O if o.get("pc") is not None]
ED = sorted({o["d"] for o in E}); half = ED[len(ED) // 2]
marg = np.mean([1 / o["m"] * 0 + 1 for o in []]) if False else None
mg = collections.defaultdict(float)
for (key, mk), S in G.items():
    if all(s in S for s in "1X2"): mg["1X2"] += 1
note("archivio", f"giorni con quote e risultato {len(days)} (dal {days[0]} al {days[-1]}), con probabilità corretta {len(ED)} (dal {ED[0]}) · esiti valutabili {len(E)} · prima metà fino al {half} (scelta), seconda metà dal {half} (verifica)")

def stats(B, unit=1.0):
    """B: giocate (dict con d, q, y). Puntata fissa: yield, profitto, calo massimo, rendimento/rischio, IC 95% e p-value (bootstrap per giorno)"""
    if not B: return None
    pl = np.array([(b["q"] - 1) if b["y"] else -1.0 for b in B]); n = len(B)
    per = collections.defaultdict(float); cnt = collections.Counter()
    for b, v in zip(B, pl): per[b["d"]] += v; cnt[b["d"]] += 1
    ds = sorted(per); dv = np.array([per[d] for d in ds]); dn = np.array([cnt[d] for d in ds])
    eq = np.cumsum(dv); dd = float(np.max(np.maximum.accumulate(np.r_[0, eq]) - np.r_[0, eq]))
    idx = rng.integers(0, len(ds), (10000, len(ds))); boot = dv[idx].sum(1) / dn[idx].sum(1)
    lo, hi = np.percentile(boot, [2.5, 97.5]); pv = float((boot <= 0).mean())
    sd = dv.std() if len(dv) > 1 else 0
    return dict(n=n, hit=float(np.mean([b["y"] for b in B])), q=float(np.mean([b["q"] for b in B])), y=float(pl.mean()), pr=float(pl.sum()), dd=dd,
                rr=float(dv.mean() / sd * math.sqrt(7)) if sd > 0 else 0.0, lo=float(lo), hi=float(hi), pv=pv, nd=len(ds))
def fmt(s):
    if not s: return "nessuna giocata"
    return (f"{s['n']} giocate in {s['nd']} giorni · presa {100 * s['hit']:.0f}% · quota {s['q']:.2f} · yield {100 * s['y']:+.1f}% (IC95 {100 * s['lo']:+.1f} / {100 * s['hi']:+.1f}, p {s['pv']:.3f})"
            f" · profitto {s['pr']:+.1f} u · calo max {s['dd']:.1f} u · rend/rischio {s['rr']:+.2f}")
# ---------------- 1 · mercato per mercato (EV corretto > 0, tutte le giocate a valore)
MK = sorted({o["mkt"] for o in E})
lines = []
for mk in MK:
    B = [o for o in E if o["mkt"] == mk and o["ev"] > 0]
    s = stats(B); lines.append((mk, s))
note("1 · mercato per mercato (valore atteso corretto > 0, puntata fissa)", " ‖ ".join(f"{mk}: {fmt(s)}" for mk, s in lines))
# riferimento: tutte le quote alla cieca (margine) e cartellini con arbitro severo / derby
note("1 · riferimenti", " ‖ ".join([
    "tutti gli esiti alla cieca: " + fmt(stats(E)),
    "O/U cartellini a valore con arbitro severo (effetto ≥ +10%): " + fmt(stats([o for o in E if o["mkt"].startswith("O/U cartellini") and o["ev"] > 0 and o["arb"] >= 1.10])),
    "… con arbitro non severo: " + fmt(stats([o for o in E if o["mkt"].startswith("O/U cartellini") and o["ev"] > 0 and o["arb"] < 1.10])),
    "O/U cartellini a valore nei derby: " + fmt(stats([o for o in E if o["mkt"].startswith("O/U cartellini") and o["ev"] > 0 and o["derby"]])),
    "Over cartellini a valore con arbitro severo: " + fmt(stats([o for o in E if o["mkt"].startswith("O/U cartellini") and o["side"] == "Over" and o["ev"] > 0 and o["arb"] >= 1.10])),
    "Under cartellini a valore: " + fmt(stats([o for o in E if o["mkt"].startswith("O/U cartellini") and o["side"] == "Under" and o["ev"] > 0])),
]))
# ---------------- 2 · griglia di filtri: scelta sulla prima metà, verifica sulla seconda
EVS = [0.0, 0.02, 0.03, 0.05, 0.08]
BANDS = [("tutte", 1.0, 99), ("1,45-1,85", 1.45, 1.85), ("1,85-2,40", 1.85, 2.40), ("oltre 2,40", 2.40, 99), ("fino a 2,40", 1.0, 2.40)]
CONC = ["tutte", "concorde", "inversione", "concorde o inversione"]
# insiemi di mercati: tutti; i mercati con yield > 0 nella PRIMA metà (scelti senza guardare la seconda); famiglie
first = {mk: stats([o for o in E if o["mkt"] == mk and o["ev"] > 0 and o["d"] < half]) for mk in MK}
pos1 = sorted(mk for mk, s in first.items() if s and s["y"] > 0 and s["n"] >= 20)
SETS = {"tutti i mercati": set(MK), "positivi nella prima metà": set(pos1), "solo 1X2": {m for m in MK if m.startswith("1X2")}, "solo Over/Under": {m for m in MK if m.startswith("O/U")},
        "solo cartellini": {m for m in MK if "cartellini" in m or "gialli" in m}, "solo corner": {m for m in MK if "corner" in m}}
def sel(o, ev, band, conc, ms):
    if o["mkt"] not in ms or o["ev"] < ev or not (band[1] <= o["q"] < band[2]): return False
    if conc == "tutte": return True
    if conc == "concorde o inversione": return o["conc"] in ("concorde", "inversione")
    return o["conc"] == conc
def one_per_match(B):   # come l'app: al massimo una singola per partita, la più a valore
    best = {}
    for o in B:
        k = o["key"]
        if k not in best or o["ev"] > best[k]["ev"]: best[k] = o
    return list(best.values())
grid = []
for (sn, ms), ev, band, conc in itertools.product(SETS.items(), EVS, BANDS, CONC):
    B = one_per_match([o for o in E if sel(o, ev, band, conc, ms)])
    a = stats([o for o in B if o["d"] < half]); b = stats([o for o in B if o["d"] >= half])
    if a and a["n"] >= 30: grid.append((sn, ev, band[0], conc, a, b))
grid.sort(key=lambda g: -g[4]["y"])
top = grid[0]
rank_b = sorted([g for g in grid if g[5]], key=lambda g: -g[5]["y"])
pos = next((i for i, g in enumerate(rank_b) if g[:4] == top[:4]), None)
by_b = [g[5]["y"] for g in grid if g[5]]
note("2 · griglia (scelta sulla prima metà, verifica sulla seconda)",
     f"combinazioni provate {len(grid)} (almeno 30 giocate nella prima metà) · mercati positivi nella prima metà: {', '.join(pos1) or 'nessuno'} ‖ "
     + " ‖ ".join(f"#{i + 1} {g[0]} · EV ≥ {int(g[1] * 100)}% · quota {g[2]} · {g[3]}: PRIMA {100 * g[4]['y']:+.1f}% su {g[4]['n']} → SECONDA {(100 * g[5]['y']) if g[5] else float('nan'):+.1f}% su {g[5]['n'] if g[5] else 0} (IC95 {100 * g[5]['lo'] if g[5] else 0:+.1f} / {100 * g[5]['hi'] if g[5] else 0:+.1f})" for i, g in enumerate(grid[:8]))
     + f" ‖ la migliore della prima metà nella seconda è {pos + 1 if pos is not None else '-'}ª su {len(rank_b)}; yield mediano di tutte le combinazioni nella seconda metà {100 * np.median(by_b):+.1f}%")
# effetto di ogni filtro da solo (tutto il periodo con probabilità corretta, una per partita)
eff = []
for ev in EVS: eff.append(f"EV ≥ {int(ev * 100)}%: {fmt(stats(one_per_match([o for o in E if o['ev'] >= ev and o['ev'] > 0])))}")
for band in BANDS[1:4]: eff.append(f"quota {band[0]}: {fmt(stats(one_per_match([o for o in E if o['ev'] > 0 and band[1] <= o['q'] < band[2]])))}")
for conc in ("concorde", "inversione", "contro Prevista"): eff.append(f"{conc}: {fmt(stats(one_per_match([o for o in E if o['ev'] > 0 and o['conc'] == conc])))}")
note("2 · un filtro alla volta (tutti i mercati, valore > 0, una per partita)", " ‖ ".join(eff))
# ---------------- 3 · portafogli con la cassa e Monte Carlo (regole della migliore combinazione della PRIMA metà)
sn, ev0, bname, conc0 = top[:4]; band0 = next(b for b in BANDS if b[0] == bname); ms0 = SETS[sn]
def day_bets(d, rule):
    return one_per_match([o for o in byd[d] if o.get("pc") is not None and rule(o)])
def best_double(L):
    L = sorted([o for o in L if 1.2 <= o["q"] <= 1.9], key=lambda o: -o["ev"])[:40]; best = None
    for a, b in itertools.combinations(L, 2):
        if a["key"] == b["key"]: continue
        q = a["q"] * b["q"]
        if 1.85 <= q <= 2.20:
            p = a["pc"] * b["pc"]; e = p * q - 1
            if e >= 0 and (best is None or e > best[2]): best = (a, b, e, p, q)
    return best
kel = lambda p, q: min(0.03, max(0.0, (p * q - 1) / (q - 1)) / 8)
def simulate(daylist, mode, rule):
    cash, peak, mdd, nb, rets = 100.0, 100.0, 0.0, 0, []
    for d in daylist:
        S = day_bets(d, rule) if mode in ("singole", "mix") else []
        allv = [o for o in byd[d] if o.get("pc") is not None and o["mkt"] in ms0 and o["ev"] > 0]
        D = best_double(allv) if mode in ("doppia", "mix") else None
        W = [(kel(o["pc"], o["q"]), o["q"], o["y"]) for o in S]
        if D: W.append((kel(D[3], D[4]), D[4], D[0]["y"] and D[1]["y"]))
        if mode == "mix" and W:   # 80% del tetto alle singole, 20% alla doppia
            ws = sum(w for w, _, _ in W[:len(S)]); wd = W[-1][0] if D else 0
            sc_s = min(1, 0.08 / ws) if ws > 0 else 1; sc_d = min(1, 0.02 / wd) if wd > 0 else 1
            W = [(w * sc_s, q, y) for w, q, y in W[:len(S)]] + ([(W[-1][0] * sc_d, W[-1][1], W[-1][2])] if D else [])
        tot = sum(w for w, _, _ in W); sc = min(1, 0.10 / tot) if tot > 0 else 1
        pl = sum(w * sc * ((q - 1) if y else -1) for w, q, y in W)
        rets.append(pl); cash *= 1 + pl; nb += len(W); peak = max(peak, cash); mdd = max(mdd, (peak - cash) / peak)
    return cash, mdd, nb, np.array(rets)
rule0 = lambda o: sel(o, ev0, band0, conc0, ms0)
rule_all = lambda o: o["ev"] > 0 and o["mkt"] in SETS["tutti i mercati"]
out = []
for lab, mode, rule in (("singole · regola scelta", "singole", rule0), ("singole · tutte a valore", "singole", rule_all), ("sola doppia", "doppia", rule0), ("mix 80/20", "mix", rule0)):
    for per, dl in (("seconda metà", [d for d in ED if d >= half]), ("tutto", ED)):
        cash, mdd, nb, r = simulate(dl, mode, rule)
        sd = r.std() if len(r) > 1 else 0
        out.append(f"{lab} · {per}: cassa 100 → {cash:.1f} · calo max {100 * mdd:.1f}% · {nb} giocate ({7 * nb / len(dl):.1f} a settimana) · rend/rischio {r.mean() / sd * math.sqrt(7) if sd > 0 else 0:+.2f}")
note(f"3 · portafogli (regola scelta: {sn} · EV ≥ {int(ev0 * 100)}% · quota {bname} · {conc0})", " ‖ ".join(out))
# Monte Carlo sul sistema migliore tra i portafogli (giorni ricampionati con reinserimento e ordine rimescolato)
mc = []
for lab, mode, rule in (("singole · regola scelta", "singole", rule0), ("mix 80/20", "mix", rule0), ("singole · tutte a valore", "singole", rule_all)):
    _, _, nb, r = simulate(ED, mode, rule)
    fin, dds = [], []
    for _ in range(10000):
        x = r[rng.integers(0, len(r), len(r))]; eq = 100 * np.cumprod(1 + x); pk = np.maximum.accumulate(np.r_[100, eq])
        fin.append(eq[-1]); dds.append(float(np.max((pk[1:] - eq) / pk[1:])))
    fin, dds = np.array(fin), np.array(dds)
    mc.append(f"{lab}: probabilità di chiudere in profitto {100 * (fin > 100).mean():.0f}% · cassa finale mediana {np.median(fin):.1f} (5°-95° percentile {np.percentile(fin, 5):.1f} – {np.percentile(fin, 95):.1f}) · calo massimo al 95° percentile {100 * np.percentile(dds, 95):.1f}% · {7 * nb / len(ED):.1f} giocate a settimana (orizzonte {len(ED)} giorni)")
note("3 · Monte Carlo 10.000", " ‖ ".join(mc))
# ---------------- 4 · stabilità delle regole candidate nelle due metà (nessuna scelta: confronto descrittivo)
CAND = [("tutti i mercati, valore > 0", lambda o: o["ev"] > 0),
        ("Under cartellini totali, valore > 0", lambda o: o["mkt"] == "O/U cartellini totali" and o["side"] == "Under" and o["ev"] > 0),
        ("Over cartellini totali, valore > 0", lambda o: o["mkt"] == "O/U cartellini totali" and o["side"] == "Over" and o["ev"] > 0),
        ("quota oltre 2,40, valore > 0", lambda o: o["q"] >= 2.40 and o["ev"] > 0),
        ("quota 1,45-1,85, valore > 0", lambda o: 1.45 <= o["q"] < 1.85 and o["ev"] > 0),
        ("1X2 corner, valore > 0", lambda o: o["mkt"] == "1X2 corner" and o["ev"] > 0),
        ("O/U corner squadra, valore > 0", lambda o: o["mkt"] == "O/U corner squadra" and o["ev"] > 0),
        ("senza 1X2 tiri, O/U corner squadra, O/U tiri in porta, valore > 0", lambda o: o["ev"] > 0 and o["mkt"] not in ("1X2 tiri", "O/U corner squadra", "O/U tiri in porta totali", "O/U tiri in porta squadra"))]
note("4 · stabilità nelle due metà (una giocata per partita)", " ‖ ".join(
    f"{lab}: PRIMA {fmt(stats(one_per_match([o for o in E if rule(o) and o['d'] < half])))} → SECONDA {fmt(stats(one_per_match([o for o in E if rule(o) and o['d'] >= half])))}" for lab, rule in CAND))
mc = []
for lab, rule in CAND[:2] + CAND[-1:]:
    for per, dl in (("tutto", ED), ("solo seconda metà", [d for d in ED if d >= half])):
        _, _, nb, r = simulate(dl, "singole", rule)
        fin, dds = [], []
        for _ in range(10000):
            x = r[rng.integers(0, len(r), len(r))]; eq = 100 * np.cumprod(1 + x); pk = np.maximum.accumulate(np.r_[100, eq])
            fin.append(eq[-1]); dds.append(float(np.max((pk[1:] - eq) / pk[1:])))
        fin, dds = np.array(fin), np.array(dds)
        mc.append(f"{lab} · {per} ({len(dl)} giorni): profitto nel {100 * (fin > 100).mean():.0f}% delle simulazioni · cassa mediana {np.median(fin):.1f} (5°-95° {np.percentile(fin, 5):.1f} – {np.percentile(fin, 95):.1f}) · calo massimo al 95° percentile {100 * np.percentile(dds, 95):.1f}% · {7 * nb / len(dl):.1f} giocate a settimana")
note("4 · Monte Carlo 10.000 delle regole candidate (Kelly 1/8, tetti 3% e 10%)", " ‖ ".join(mc))

# ---------------- 5 · verifica in avanti dal 4/11/2026 (regole fissate il 3/11): puntata fissa 1% contro Kelly 1/8, tre perimetri
FWD = "2026-11-04"
SPENTI = ("O/U corner squadra", "1X2 tiri", "O/U tiri in porta totali", "O/U tiri in porta squadra")
PERIM = [("Under cartellini totali", lambda o: o["mkt"] == "O/U cartellini totali" and o["side"] == "Under" and o["ev"] > 0),
         ("Nucleo pulito (senza i 3 mercati spenti)", lambda o: o["ev"] > 0 and o["mkt"] not in SPENTI),
         ("Perimetro di Operatività", lambda o: o["ev"] > 0 and o["mkt"] in ("1X2 corner", "1X2 falli", "1X2 fuorigioco", "1X2 gialli", "O/U cartellini totali", "O/U tiri totali"))]
def sim_flat(dl, rule):
    cash, peak, mdd, nb = 100.0, 100.0, 0.0, 0
    for d in dl:
        S = day_bets(d, rule); stake = min(0.01, 0.10 / len(S)) if S else 0
        cash *= 1 + sum(stake * ((o["q"] - 1) if o["y"] else -1) for o in S); nb += len(S); peak = max(peak, cash); mdd = max(mdd, (peak - cash) / peak)
    return cash, mdd, nb
FD = [d for d in ED if d >= FWD]
if FD:
    out = []
    for lab, rule in PERIM:
        cf, mf, nb = sim_flat(FD, rule); ck, mk_, nk, _ = simulate(FD, "singole", rule)
        s_ = stats(one_per_match([o for o in E if rule(o) and o["d"] >= FWD]))
        out.append(f"{lab}: {fmt(s_)} · cassa con fissa 1% {cf:.1f} (calo max {100 * mf:.1f}%) · con Kelly 1/8 {ck:.1f} (calo max {100 * mk_:.1f}%)")
    note(f"5 · verifica in avanti dal 4/11 ({len(FD)} giorni)", " ‖ ".join(out))
else:
    note("5 · verifica in avanti dal 4/11", "nessun giorno giocato dal 4/11 con probabilità corretta: si parte dal prossimo lunedì")

# ---------------- 6 · in parallelo (6/11/2026, Denny): media dei book contro 1xBet, sugli stessi 1X2 delle statistiche del perimetro di Operatività
# (le regole e gli studi restano fissati su 1xBet; qui solo il confronto: stesse partite, stessi pesi della corretta)
OPM = ("1X2 corner", "1X2 falli", "1X2 fuorigioco", "1X2 gialli")
MB = [o for o in E if o.get("pcm") is not None and o["mkt"] in OPM]
if MB:
    a = one_per_match([o for o in MB if o["ev"] > 0])
    bm = one_per_match([dict(o, q=o["qm"], ev=o["evm"], pc=o["pcm"]) for o in MB if o["evm"] > 0])
    note(f"6 · media dei book in parallelo ({len(MB)} esiti con le tre quote medie, dal {min(o['d'] for o in MB)})",
         f"1xBet: {fmt(stats(a))} ‖ media dei book: {fmt(stats(bm))} ‖ quota media 1xBet {np.mean([o['q'] for o in MB]):.3f} contro media dei book {np.mean([o['qm'] for o in MB]):.3f}")
else:
    note("6 · media dei book in parallelo", "ancora nessun esito con le quote medie (archivio dal 7/11/2026)")
