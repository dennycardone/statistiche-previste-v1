"""Cartellini V2 · prova IN OMBRA sulle partite nuove (20/11/2026, Denny: "1. ok 2. togliamo e lo analizziamo in ombra assieme al resto").
Due cose, senza toccare le previsioni ufficiali:
  1) Cartellini V2 = app × e^(0,0007 + 0,752 · L30), L30 = ln[(cartellini reali + 50·ē) / (attesi dall'app + 50·ē)] delle partite dello stesso
     campionato nei 30 giorni precedenti (ē = attesi medi); per squadra distribuzione di Poisson (l'app usa la NB del totale, r = 1/alpha).
     Coefficienti CONGELATI (studio del 20/11, stima fino al 30/6/2024, tools/p2/cart_studio.py "A rec30" + "E"): nessuna ricalibrazione.
  2) Giocate del Mercato sui cartellini PER SQUADRA, tolte dall'app il 20/11: le registra qui con la regola del Mercato (lato della lettura,
     riuscita ≥ 65%, valore ≥ 5%), sia con l'app sia con V2, insieme a quelle sui cartellini totali (che restano nell'app).
Ogni notte (lab.yml) registra le partite da giocare (data/extra.json: attesi dell'app; data/linee.json: linee del book in quel momento); le
partite di giorni passati restano con l'ultima registrazione. Risultati: cartellini totali da extra.json, per squadra da bundle.json (HK/AK).
Uscita nella cartella del laboratorio: ombra_cartellini.json (registro) e CARTELLINI_V2.md (report).
Uso: python tools/lab/ombra_cartellini.py CARTELLA_PAGINE/data CARTELLA_STATO"""
import os, sys, json, csv, io, math, datetime, collections, numpy as np, pandas as pd
from scipy.stats import nbinom, poisson
DATA, OUT = sys.argv[1], sys.argv[2]
oggi = os.environ.get("OMBRA_OGGI") or datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")   # OMBRA_OGGI solo per le prove
COEF = {"c": 0.0007, "l30": 0.752, "giorni": 30, "K": 50, "squadra": "Poisson", "regola_mercato": "lato della lettura, riuscita >= 65%, valore >= 5%"}
OP = os.path.join(OUT, "ombra_cartellini.json")
REG = json.load(open(OP)) if os.path.exists(OP) else {"dal": oggi, "coef": COEF, "partite": {}}
if REG.get("coef") != COEF: REG.setdefault("avvisi", []).append(f"{oggi}: coefficienti dello script diversi da quelli registrati all'inizio")
EXJ = json.load(open(os.path.join(DATA, "extra.json"))); E = EXJ["partite"]; ALPHA = EXJ.get("alpha"); R_TOT = 1 / ALPHA if ALPHA and ALPHA > 2e-4 else float("inf")
LJ = json.load(open(os.path.join(DATA, "linee.json"))) if os.path.exists(os.path.join(DATA, "linee.json")) else {"partite": {}}
# ---------------- livello recente del campionato (solo partite di giorni precedenti, attesi dell'app ed esito reale)
by_lg = collections.defaultdict(list)
for k, x in E.items():
    if len(x) > 7 and x[4] is not None and x[5] is not None: by_lg[k.split("|")[0]].append((k.split("|")[1], x[5], x[4]))
for v in by_lg.values(): v.sort()
def l30(lg, d):
    d0 = (datetime.date.fromisoformat(d) - datetime.timedelta(days=COEF["giorni"])).isoformat()
    R = [z for z in by_lg.get(lg, []) if d0 <= z[0] < d]
    if not R: return 0.0, 0
    sy, sm = sum(z[1] for z in R), sum(z[2] for z in R); eb = sm / len(R); return math.log((sy + COEF["K"] * eb) / (sm + COEF["K"] * eb)), len(R)
for k, x in E.items():
    lg, d = k.split("|")[:2]
    if d < oggi or len(x) < 8 or x[4] is None or x[6] is None or x[7] is None: continue
    L, n = l30(lg, d); f = math.exp(COEF["c"] + COEF["l30"] * L)
    b = (LJ["partite"].get(k) or {}); b = b.get("mb") and {**b, **b["mb"]} or b
    REG["partite"][k] = dict(lg=lg, d=d, app=[x[4], x[6], x[7]], v2=[x[4] * f, x[6] * f, x[7] * f], l30=[round(L, 5), n], r_tot=R_TOT,
                             linee={m: b[m][:3] for m in ("k", "hk", "ak") if b.get(m)}, reg=oggi)
# ---------------- risultati
Y = {}
for fl in json.load(open(os.path.join(DATA, "bundle.json")))["files"]:
    stem = fl["name"].rsplit(".", 1)[0].split("_")[0]
    for r in csv.DictReader(io.StringIO(fl["text"])):
        try:
            dd, mm, yy = r["Date"].split("/"); yy = ("20" + yy) if len(yy) == 2 else yy
            if r.get("HK") not in (None, "") and r.get("AK") not in (None, ""):
                Y[f"{r.get('Div') or stem}|{yy}-{mm}-{dd}|{r.get('HomeTeam') or r.get('Home')}|{r.get('AwayTeam') or r.get('Away')}"] = (int(float(r["HK"])), int(float(r["AK"])))
        except Exception: pass
for k, p in REG["partite"].items():
    if p["d"] >= oggi: continue
    x = E.get(k)
    if x and len(x) > 5 and x[5] is not None: p["yt"] = x[5]
    if k in Y: p["ys"] = list(Y[k])
# ---------------- metriche
lpn = lambda y, mu, r: nbinom.logpmf(y, r, r / (r + mu)) if np.isfinite(r) else poisson.logpmf(y, mu)
def pov(L, mu, r): return 1 - (nbinom.cdf(math.floor(L), r, r / (r + mu)) if np.isfinite(r) else poisson.cdf(math.floor(L), mu))
def plays(p, arm):
    mu = p[arm]; out = []
    for mk, m_, r_ in (("k", mu[0], p["r_tot"]), ("hk", mu[1], p["r_tot"] if arm == "app" else float("inf")), ("ak", mu[2], p["r_tot"] if arm == "app" else float("inf"))):
        c = p["linee"].get(mk)
        if not c: continue
        Lk, o, u = c; po = pov(Lk, m_, r_); side = "O" if po >= 0.5 else "U"; pr = po if side == "O" else 1 - po; q = o if side == "O" else u
        if pr >= 0.65 and pr * q - 1 >= 0.05:
            y = p.get("yt") if mk == "k" else (p["ys"][0] if mk == "hk" else p["ys"][1]) if p.get("ys") else None
            out.append(dict(mk=mk, side=side, p=pr, q=q, ev=pr * q - 1, hit=None if y is None else bool(y > Lk if side == "O" else y < Lk)))
    return out
reg = REG["partite"]; conc = {k: p for k, p in reg.items() if p["d"] < oggi}
util = {k: p for k, p in conc.items() if p.get("yt") is not None}
util_sq = {k: p for k, p in conc.items() if p.get("ys")}
REP = dict(aggiornato=oggi, dal=REG["dal"], registrate=len(reg), concluse=len(conc), utilizzabili_totale=len(util), utilizzabili_squadra=len(util_sq))
MD = [f"# Cartellini V2 · prova in ombra (dal {REG['dal']})", "", f"Aggiornato {oggi}. Partite registrate {len(reg)} · concluse {len(conc)} · con cartellini reali: totali {len(util)}, per squadra {len(util_sq)}.",
      "V2 = livello del campionato negli ultimi 30 giorni + Poisson per squadra (coefficienti congelati). Le previsioni ufficiali non cambiano. Negativo = V2 meglio.", ""]
def boot(d, g, B=2000):
    s = pd.Series(d).groupby(g); S_ = s.sum().values; C = s.count().values
    if len(S_) < 2: return [None, None]
    idx = np.random.default_rng(7).integers(0, len(S_), (B, len(S_))); bs = S_[idx].sum(1) / C[idx].sum(1)
    return [round(float(np.percentile(bs, 0.5)), 6), round(float(np.percentile(bs, 99.5)), 6)]
if util:
    T = pd.DataFrame([dict(k=k, lg=p["lg"], d=p["d"], y=p["yt"], a=p["app"][0], v=p["v2"][0], r=p["r_tot"]) for k, p in util.items()])
    T["wk"] = (pd.to_datetime(T.d) - pd.Timestamp("1970-01-01")).dt.days // 7
    rr = T.r.values
    la = -np.array([lpn(y, m, r) for y, m, r in zip(T.y, T.a, rr)]); lv = -np.array([lpn(y, m, r) for y, m, r in zip(T.y, T.v, rr)])
    agg = {"ll_totale": (la, lv), "mae_totale": (abs(T.y - T.a).values, abs(T.y - T.v).values)}
    for L in (3.5, 4.5, 5.5):
        pa = np.array([pov(L, m, r) for m, r in zip(T.a, rr)]); pv = np.array([pov(L, m, r) for m, r in zip(T.v, rr)]); o = (T.y > L).values.astype(float)
        agg[f"brier_over{L}"] = ((pa - o) ** 2, (pv - o) ** 2)
    LN = np.floor(T.a.values) + 0.5; o = (T.y.values > LN).astype(float)
    agg["brier_linea_vicina"] = ((np.array([pov(L, m, r) for L, m, r in zip(LN, T.a, rr)]) - o) ** 2, (np.array([pov(L, m, r) for L, m, r in zip(LN, T.v, rr)]) - o) ** 2)
    REP["totale"] = {k: dict(app=round(float(a.mean()), 5), v2=round(float(b.mean()), 5), diff=round(float((b - a).mean()), 6), ic99_settimana=boot(b - a, T.wk.values), ic99_campionato=boot(b - a, T.lg.values)) for k, (a, b) in agg.items()}
    REP["livello"] = dict(reali=round(float(T.y.mean()), 3), app=round(float(T.a.mean()), 3), v2=round(float(T.v.mean()), 3))
    dd = pd.Series(lv - la).groupby(T.lg.values); REP["campionati_totale"] = {g: dict(n=int(s.size), d_ll=round(float(s.mean()), 5)) for g, s in dd}
    fas = pd.cut(T.a, [0, 3.5, 4.0, 4.5, 5.0, 99]); REP["fasce_totale"] = {str(f): dict(n=int(len(g)), reali=round(float(g.y.mean()), 3), app=round(float(g.a.mean()), 3), v2=round(float(g.v.mean()), 3)) for f, g in T.groupby(fas, observed=True)}
    MD += ["## Cartellini totali", "", "| metrica | app | V2 | V2 − app | IC 99% settimane | IC 99% campionati |", "|---|---|---|---|---|---|"]
    MD += [f"| {k} | {v['app']} | {v['v2']} | {v['diff']:+.6f} | {v['ic99_settimana']} | {v['ic99_campionato']} |" for k, v in REP["totale"].items()]
    MD += ["", f"Livello: reali {REP['livello']['reali']} · app {REP['livello']['app']} · V2 {REP['livello']['v2']}", "", "| fascia attesi app | n | reali | app | V2 |", "|---|---|---|---|---|"]
    MD += [f"| {f} | {v['n']} | {v['reali']} | {v['app']} | {v['v2']} |" for f, v in REP["fasce_totale"].items()]
if util_sq:
    S = pd.DataFrame([dict(lg=p["lg"], d=p["d"], yh=p["ys"][0], ya=p["ys"][1], ah=p["app"][1], aa=p["app"][2], vh=p["v2"][1], va=p["v2"][2], r=p["r_tot"]) for p in util_sq.values()])
    S["wk"] = (pd.to_datetime(S.d) - pd.Timestamp("1970-01-01")).dt.days // 7
    la = -np.array([(lpn(a, b, r) + lpn(c, d_, r)) / 2 for a, b, c, d_, r in zip(S.yh, S.ah, S.ya, S.aa, S.r)])
    lv = -np.array([(lpn(a, b, np.inf) + lpn(c, d_, np.inf)) / 2 for a, b, c, d_ in zip(S.yh, S.vh, S.ya, S.va)])
    agg = {"ll_squadra": (la, lv)}
    for L in (0.5, 1.5, 2.5):
        ba = np.mean([[(pov(L, m, r) - (y > L)) ** 2 for m, y, r in zip(S[mc], S[yc], S.r)] for mc, yc in (("ah", "yh"), ("aa", "ya"))], 0)
        bv = np.mean([[(pov(L, m, np.inf) - (y > L)) ** 2 for m, y in zip(S[mc], S[yc])] for mc, yc in (("vh", "yh"), ("va", "ya"))], 0)
        agg[f"brier_squadra_over{L}"] = (ba, bv)
    REP["squadra"] = {k: dict(app=round(float(a.mean()), 5), v2=round(float(b.mean()), 5), diff=round(float((b - a).mean()), 6), ic99_settimana=boot(b - a, S.wk.values), ic99_campionato=boot(b - a, S.lg.values)) for k, (a, b) in agg.items()}
    MD += ["", "## Cartellini per squadra", "", "| metrica | app | V2 | V2 − app | IC 99% settimane | IC 99% campionati |", "|---|---|---|---|---|---|"]
    MD += [f"| {k} | {v['app']} | {v['v2']} | {v['diff']:+.6f} | {v['ic99_settimana']} | {v['ic99_campionato']} |" for k, v in REP["squadra"].items()]
# ---------------- giocate del Mercato (totali: nell'app; per squadra: tolte dall'app il 20/11, solo qui)
G = []
for k, p in conc.items():
    for arm in ("app", "v2"):
        for g in plays(p, arm): G.append(dict(arm=arm, lg=p["lg"], **g))
G = pd.DataFrame(G)
REP["giocate"] = {}
if len(G):
    for (arm, grp), g in G.groupby([G.arm, np.where(G.mk == "k", "totali", "per squadra")]):
        h = g[g.hit.notna()]
        REP["giocate"][f"{arm} · {grp}"] = dict(giocate=int(len(g)), con_esito=int(len(h)), under=round(float((g.side == "U").mean() * 100), 1),
                                                presa=round(float(h.hit.mean() * 100), 1) if len(h) else None, dichiarata=round(float(h.p.mean() * 100), 1) if len(h) else None,
                                                rendimento=round(float(np.where(h.hit.astype(bool), h.q - 1, -1).mean() * 100), 1) if len(h) else None)
    MD += ["", "## Giocate del Mercato (riuscita ≥ 65%, valore ≥ 5%)", "", "Per squadra: tolte dall'app il 20/11/2026, seguite solo qui.", "",
           "| braccio · mercato | giocate | con esito | Under % | presa % | dichiarata % | rendimento % |", "|---|---|---|---|---|---|---|"]
    MD += [f"| {k} | {v['giocate']} | {v['con_esito']} | {v['under']} | {v['presa']} | {v['dichiarata']} | {v['rendimento']} |" for k, v in REP["giocate"].items()]
if not util and not util_sq: MD += ["Nessuna partita conclusa con cartellini reali ancora."]
REG["riepilogo"] = REP
json.dump(REG, open(OP, "w"), ensure_ascii=False, separators=(",", ":"))
open(os.path.join(OUT, "CARTELLINI_V2.md"), "w").write("\n".join(MD) + "\n")
riga = f"Cartellini V2 in ombra: registrate {REP['registrate']}, concluse {REP['concluse']}, utilizzabili {REP['utilizzabili_totale']} (totali) / {REP['utilizzabili_squadra']} (per squadra)"
with open(os.path.join(OUT, "RIEPILOGO.md"), "a") as fh: fh.write("\n\n## Cartellini V2 (prova in ombra, dettaglio in CARTELLINI_V2.md)\n- " + riga + "\n")
print("::notice title=Cartellini V2 · in ombra::" + riga)
