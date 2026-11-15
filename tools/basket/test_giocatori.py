"""Basket · test dei mercati giocatori (15/11/2026, Denny): Punti, Rimbalzi, Assist, Doppia doppia, Tripla doppia.
Harness come il calcio: parametri scelti fino al 30/6/2024, verifica 2024-25, holdout da luglio 2025. Solo partite precedenti.
Si valuta il giocatore che gioca (le giocate sui giocatori si annullano se non entra), quintetto noto (come la formazione ufficiale nel calcio).

Modello A (individuale): punti/rimbalzi/assist al minuto del giocatore (media mobile, peso DP a partita), ristretti verso la media del suo
  ruolo nel campionato (titolare / panchina) con K minuti fittizi, × minuti attesi (media mobile dei minuti da titolare o da panchina).
Modello B (ancorato a Prevista): A × (punti attesi oggi dalla squadra / punti abituali della squadra)^α per punti e assist,
  × (possessi attesi oggi / ritmo abituale della squadra)^α per i rimbalzi.
Bonus assenze: B × (1 + β · quota mancante), quota mancante = quanto producono di solito i giocatori abituali assenti oggi
  (≥15 minuti di media, visti negli ultimi 30 giorni) sul totale della squadra.
Distribuzione: binomiale negativa con varianza φ·media (φ scelto per voce nel periodo scelta).
Doppia/tripla doppia: P(≥10) delle tre voci, indipendenti oppure legate dai minuti (miscela sul fattore minuti).
Uso: python tools/basket/test_giocatori.py CARTELLA_ARCHIVIO [USCITA.json]"""
import sys, os, json, math, collections, datetime
import numpy as np
from scipy.stats import nbinom
sys.path.insert(0, os.path.dirname(__file__))
from bk_lib import load, team_model, per, SCELTA
DIR = sys.argv[1]; OUT = sys.argv[2] if len(sys.argv) > 2 else "basket_giocatori.json"
DP, KMIN, KGM = 0.97, 120.0, 3.0
rows = team_model(load(DIR))
ST = ("pts", "reb", "ast"); IX = {"pts": 4, "reb": 11, "ast": 12}
P = collections.defaultdict(lambda: {"w": 0.0, "m": 0.0, "pts": 0.0, "reb": 0.0, "ast": 0.0, "ws": 0.0, "ms": 0.0, "wb": 0.0, "mb": 0.0, "n": 0,
                                     "team": None, "last": None, "sn": 0, "ss": None, "s_pts": 0.0, "s_reb": 0.0, "s_ast": 0.0})
LR = collections.defaultdict(lambda: {"m": 0.0, "pts": 0.0, "reb": 0.0, "ast": 0.0, "w": 0.0, "mm": 0.0})
ROST = collections.defaultdict(set)
LASTP = {}   # giocatori presenti nell'ultima partita della squadra (per le assenze note prima: chi mancava l'ultima volta)
rec = []   # una riga per giocatore valutato
for r in rows:
    if not r["gi"] or r["eh"] is None or r["nh"] < 5 or r["na"] < 5: pass
    lg, d = r["lg"], datetime.date.fromisoformat(r["d"])
    gi = [p for p in (r["gi"] or []) if p[3] and p[3] > 0 and None not in (p[4], p[11], p[12])]
    ok_game = bool(gi) and r["eh"] is not None and r["nh"] >= 5 and r["na"] >= 5
    if ok_game:
        for side in (0, 1):
            team = r["h"] if side == 0 else r["a"]
            present = {p[0] for p in gi if p[1] == side}
            if len(present) < 5: continue
            # abituali della squadra (presenti e assenti) con la produzione abituale
            def typ(pid):
                s = P[(lg, pid)]; am = s["m"] / s["w"]
                return {k: (s[k] / s["m"]) * am for k in ST}, am
            regs = {}
            for pid in ROST[(lg, team)]:
                s = P[(lg, pid)]
                if s["team"] != team or s["w"] < 2 or s["last"] is None or (d - s["last"]).days > 30: continue
                t_, am = typ(pid)
                if am >= 15: regs[pid] = t_
            tot = {k: sum(v[k] for v in regs.values()) or 1 for k in ST}
            miss = {k: sum(v[k] for pid, v in regs.items() if pid not in present) / tot[k] for k in ST}
            top = {k: sorted(regs, key=lambda q: -regs[q][k])[:2] for k in ST}
            top_abs = {k: any(q not in present for q in top[k]) for k in ST}
            lp = LASTP.get((lg, team))
            mprev = {k: (sum(v[k] for pid, v in regs.items() if lp is not None and pid not in lp) / tot[k]) for k in ST}
            eh, hab = (r["eh"], r["habh"]) if side == 0 else (r["ea"], r["haba"])
            pc = r["pch"] if side == 0 else r["pca"]
            for p in gi:
                if p[1] != side: continue
                s = P[(lg, p[0])]
                if s["n"] < 5: continue
                stt = 1 if p[2] else 0
                Lr = LR[(lg, stt)]
                if Lr["m"] < 500: continue
                allm = s["m"] / s["w"]
                em = (s["ms"] + KGM * allm) / (s["ws"] + KGM) if stt else (s["mb"] + KGM * allm) / (s["wb"] + KGM)
                if em < 15: continue
                muA = [(s[k] + KMIN * Lr[k] / Lr["m"]) / (s["m"] + KMIN) * em for k in ST]
                base = [s["s_" + k] / s["sn"] if s["sn"] >= 3 else np.nan for k in ST]   # media semplice della stagione
                muAll = [(s[k] + KMIN * Lr[k] / Lr["m"]) / (s["m"] + KMIN) * allm for k in ST]   # senza sapere se parte titolare
                rec.append((lg, per(r["d"]), stt, em, p[3], p[4], p[11], p[12], *muA, eh / hab, r["pace"] / pc,
                            miss["pts"], miss["reb"], miss["ast"], top_abs["pts"], top_abs["reb"], top_abs["ast"], p[0] in top["pts"], *base, *muAll, mprev["pts"], mprev["reb"], mprev["ast"]))
    # aggiornamento
    for side in (0, 1):
        pres = {p[0] for p in gi if p[1] == side}
        if len(pres) >= 5: LASTP[(lg, r["h"] if side == 0 else r["a"])] = pres
    for p in (r["gi"] or []):
        if not p[3] or p[3] <= 0 or None in (p[4], p[11], p[12]): continue
        s = P[(lg, p[0])]; team = r["h"] if p[1] == 0 else r["a"]
        for k in ("w", "m", "pts", "reb", "ast", "ws", "ms", "wb", "mb"): s[k] *= DP
        s["w"] += 1; s["m"] += p[3]; s["pts"] += p[4]; s["reb"] += p[11]; s["ast"] += p[12]; s["n"] += 1
        if p[2]: s["ws"] += 1; s["ms"] += p[3]
        else: s["wb"] += 1; s["mb"] += p[3]
        if s["ss"] != r["ss"]: s["ss"] = r["ss"]; s["sn"] = 0; s["s_pts"] = s["s_reb"] = s["s_ast"] = 0.0
        s["sn"] += 1; s["s_pts"] += p[4]; s["s_reb"] += p[11]; s["s_ast"] += p[12]
        if s["team"] != team: s["team"] = team
        s["last"] = d; ROST[(lg, team)].add(p[0])
        Lr = LR[(lg, 1 if p[2] else 0)]
        for k in ("m", "pts", "reb", "ast", "w", "mm"): Lr[k] *= 0.999
        Lr["m"] += p[3]; Lr["pts"] += p[4]; Lr["reb"] += p[11]; Lr["ast"] += p[12]
cols = ["lg", "per", "stt", "em", "min", "pts", "reb", "ast", "Apts", "Areb", "Aast", "rp", "rr", "mpts", "mreb", "mast", "tpts", "treb", "tast", "istop", "Bpts", "Breb", "Bast", "Lpts", "Lreb", "Last", "ppts", "preb", "past"]
A = {c: np.array([x[i] for x in rec]) for i, c in enumerate(cols)}
print("giocatori-partita valutati", len(rec), collections.Counter(zip(A["lg"], A["per"])).most_common(30))
LINES = {"pts": (9.5, 14.5, 19.5, 24.5, 29.5), "reb": (3.5, 5.5, 7.5, 9.5, 11.5), "ast": (2.5, 4.5, 6.5, 8.5)}
def psf(mu, line, phi):
    """P(X > line) con binomiale negativa, varianza phi·mu (phi>1)"""
    mu = np.maximum(mu, 0.05); n = mu / (phi - 1); p = 1 / phi
    return nbinom.sf(np.floor(line), n, p)
def ll(p, y): p = np.clip(p, 1e-6, 1 - 1e-6); return -(y * np.log(p) + (1 - y) * np.log(1 - p))
S = A["per"] == "scelta"
res = {"casi": {f"{lg} {p}": int(((A['lg'] == lg) & (A['per'] == p)).sum()) for lg in sorted(set(A["lg"])) for p in ("scelta", "verifica", "holdout")}}
def mus(k, alpha, beta=0.0):
    sc = A["rp"] if k != "reb" else A["rr"]
    return A["A" + k] * sc ** alpha * (1 + beta * A["m" + k])
def score(k, mu, phi, mask):
    line = np.floor(A["A" + k][mask]) + 0.5    # linea del giocatore (dal modello A, comune a tutti i modelli)
    y = (A[k][mask] > line).astype(float)
    return ll(psf(mu[mask], line, phi), y)
# 1) φ per voce (scelta, modello A)
PHI = {}
for k in ST:
    best = min((float(np.mean(score(k, A["A" + k], ph, S))), ph) for ph in (1.1, 1.3, 1.6, 2.0, 2.5, 3.0, 3.5, 4.0, 5.0))
    PHI[k] = best[1]
res["phi"] = PHI
# 2) α (ancoraggio alla partita) e β (assenze), scelti nel periodo scelta
AL, BE = {}, {}
for k in ST:
    AL[k] = min((float(np.mean(score(k, mus(k, a), PHI[k], S))), a) for a in (0, 0.25, 0.5, 0.75, 1.0, 1.25, 1.5))[1]
    BE[k] = min((float(np.mean(score(k, mus(k, AL[k], b), PHI[k], S))), b) for b in (0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.7, 1.0))[1]
res["alpha"] = AL; res["beta_assenze"] = BE
# 3) confronto per periodo e campionato: media semplice, A, B, B+assenze (log-loss sulla linea del giocatore)
cmp = {}
for k in ST:
    for p in ("verifica", "holdout"):
        out = {}
        m = (A["per"] == p) & ~np.isnan(A["B" + k])
        base = score(k, np.nan_to_num(A["B" + k]), PHI[k], m); la = score(k, A["A" + k], PHI[k], m)
        lb = score(k, mus(k, AL[k]), PHI[k], m); lc = score(k, mus(k, AL[k], BE[k]), PHI[k], m)
        def z(x, y): d = x - y; return round(float(d.mean() / (d.std() / math.sqrt(len(d)))), 2)
        lgs = A["lg"][m]
        def by(x, y): return {lg: round(float((x - y)[lgs == lg].mean()), 4) for lg in sorted(set(lgs))}
        out["n"] = int(m.sum())
        out["logloss media semplice / A / B / B+assenze"] = [round(float(v.mean()), 4) for v in (base, la, lb, lc)]
        out["A − media semplice"] = [round(float((la - base).mean()), 4), z(la, base)]
        out["B − A"] = [round(float((lb - la).mean()), 4), z(lb, la), f"{sum(v < 0 for v in by(lb, la).values())}/{len(set(lgs))}"]
        out["B+assenze − B"] = [round(float((lc - lb).mean()), 4), z(lc, lb), f"{sum(v < 0 for v in by(lc, lb).values())}/{len(set(lgs))}"]
        out["per campionato B − A"] = by(lb, la); out["per campionato B+assenze − B"] = by(lc, lb)
        cmp[f"{k} · {p}"] = out
res["confronto"] = cmp
# 3b) versione possibile in app senza quintetto ufficiale: minuti medi (titolare o no non noto) e assenze = chi mancava nell'ultima partita
live = {}
for k in ST:
    sc = A["rp"] if k != "reb" else A["rr"]
    muL = A["L" + k] * sc ** AL[k]
    bl = min((float(np.mean(score(k, muL * (1 + b * A["p" + k]), PHI[k], S))), b) for b in (0, 0.1, 0.2, 0.3, 0.5, 0.7, 1.0))[1]
    for p in ("verifica", "holdout"):
        m = A["per"] == p; lgs = A["lg"][m]
        la = score(k, A["A" + k], PHI[k], m); lL = score(k, muL, PHI[k], m); lP = score(k, muL * (1 + bl * A["p" + k]), PHI[k], m); lfull = score(k, mus(k, AL[k], BE[k]), PHI[k], m)
        def z(x, y): d = x - y; return round(float(d.mean() / (d.std() / math.sqrt(len(d)))), 2)
        live[f"{k} · {p}"] = {"beta_ultima_partita": bl, "logloss B senza quintetto / + assenze ultima partita / completo (quintetto e assenze noti)": [round(float(v.mean()), 4) for v in (lL, lP, lfull)],
                              "assenze ultima partita − senza": [round(float((lP - lL).mean()), 4), z(lP, lL), f"{sum((lP - lL)[lgs == g].mean() < 0 for g in set(lgs))}/{len(set(lgs))}"],
                              "costo di non sapere il quintetto (completo − live)": round(float((lfull - lP).mean()), 4)}
res["versione_app_senza_quintetto"] = live
# 4) bonus assenze grezzo: scarto medio (reale − B) dei titolari presenti quando manca uno dei primi 2 della squadra in quella voce
raw = {}
for k in ST:
    for p in ("scelta", "verifica", "holdout"):
        mb = mus(k, AL[k]); base_m = (A["per"] == p) & (A["stt"] == 1)
        yes, no = base_m & A["t" + k].astype(bool), base_m & ~A["t" + k].astype(bool)
        raw[f"{k} · {p}"] = {"manca uno dei primi 2: reale − atteso B": round(float((A[k][yes] - mb[yes]).mean()), 2), "casi": int(yes.sum()),
                             "nessuno manca": round(float((A[k][no] - mb[no]).mean()), 2), "media voce titolari": round(float(A[k][base_m].mean()), 1)}
res["assenze_grezzo"] = raw
# 5) calibrazione (holdout, B+assenze) sulle soglie fisse
cal = {}
for k in ST:
    m = A["per"] == "holdout"; mu = mus(k, AL[k], BE[k])[m]
    for L_ in LINES[k]:
        pr = psf(mu, L_, PHI[k]); y = A[k][m] > L_
        bins = collections.defaultdict(lambda: [0, 0.0, 0])
        for a, b in zip(pr, y):
            if a < 0.03: continue
            bb = min(9, int(a * 10)); c = bins[bb]; c[0] += 1; c[1] += a; c[2] += b
        cal[f"{k} Over {L_}"] = {"previsto/uscito (n)": [f"{c[1]/c[0]:.2f}/{c[2]/c[0]:.2f} ({c[0]})" for _, c in sorted(bins.items()) if c[0] >= 30]}
res["calibrazione_holdout"] = cal
# 6) doppia e tripla doppia
def p10(k, f=1.0): return psf(mus(k, AL[k], BE[k]) * f, 9.5, PHI[k])
def dd_td(f=1.0):
    a, b, c = p10("pts", f), p10("reb", f), p10("ast", f)
    return a * b + a * c + b * c - 2 * a * b * c, a * b * c
ydd = ((A["pts"] >= 10).astype(int) + (A["reb"] >= 10) + (A["ast"] >= 10)) >= 2; ytd = (A["pts"] >= 10) & (A["reb"] >= 10) & (A["ast"] >= 10)
# legame dai minuti: deviazione robusta del rapporto minuti reali / attesi (scelta)
ratio = A["min"] / A["em"]; sdm = float(1.4826 * np.median(np.abs(ratio[S] - np.median(ratio[S]))))
nodes = np.array([-2.3344, -0.7420, 0.7420, 2.3344]); wts = np.array([0.0459, 0.4541, 0.4541, 0.0459])   # Gauss–Hermite (normale) a 4 punti
def dd_td_mix():
    dd = 0; td = 0
    for z_, w in zip(nodes, wts):
        f = max(0.3, 1 + z_ * sdm); a, b = dd_td(f); dd = dd + w * a; td = td + w * b
    return dd, td
dI, tI = dd_td(); dM, tM = dd_td_mix()
ddr = {"sd_minuti": round(sdm, 3)}
for p in ("verifica", "holdout"):
    m = A["per"] == p
    for nm, pd_, pt_ in (("indipendenti", dI, tI), ("legate dai minuti", dM, tM)):
        ddr[f"{p} · {nm}"] = {"doppia doppia prevista/uscita": f"{pd_[m].mean():.4f}/{ydd[m].mean():.4f}", "logloss dd": round(float(ll(pd_[m], ydd[m]).mean()), 5),
                              "tripla doppia prevista/uscita": f"{pt_[m].mean():.5f}/{ytd[m].mean():.5f}", "logloss td": round(float(ll(pt_[m], ytd[m]).mean()), 6)}
        bins = collections.defaultdict(lambda: [0, 0.0, 0])
        for a, b in zip(pd_[m], ydd[m]):
            if a < 0.05: continue
            bb = min(9, int(a * 10)); c = bins[bb]; c[0] += 1; c[1] += a; c[2] += b
        ddr[f"{p} · {nm}"]["calibrazione dd previsto/uscito (n)"] = [f"{c[1]/c[0]:.2f}/{c[2]/c[0]:.2f} ({c[0]})" for _, c in sorted(bins.items()) if c[0] >= 20]
res["doppia_tripla"] = ddr
json.dump(res, open(OUT, "w"), indent=1, ensure_ascii=False)
print(json.dumps(res, indent=1, ensure_ascii=False))
