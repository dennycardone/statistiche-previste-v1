"""Corner V2 · prova IN OMBRA sulle partite nuove (18/11/2026, Denny: "approvo la validazione Shadow Mode, non l'attivazione").
Ogni notte (lab.yml): legge data/corner_v2.json (scritto da precalc.js: corner UFFICIALI dell'app e Corner V2 sulla stessa partita, allo stesso
momento) e registra le partite da giocare; per le partite già giocate la registrazione resta l'ultima fatta prima del giorno della partita
(nessun ricalcolo dopo). Coefficienti CONGELATI in index.html (CORNER_V2): qui non si stima né si ricalibra nulla.
Con i corner reali (data/bundle.json) confronta i due modelli sugli STESSI eventi: log-loss per squadra (NB r = 12), totale (NB r = 60), 1X2 con
copula gaussiana −0,20 (stessa formula di h2hCop), Over/Under totale (linea vicina all'atteso ufficiale e linee fisse 7,5-12,5), per squadra
(linea vicina all'atteso ufficiale e 3,5-6,5), Brier, MAE, RMSE; per campionato, fascia di corner attesi, periodo; intervallo al 99% con
bootstrap per settimana e per campionato. Uscita: ombra_corner.json (registro) e CORNER_V2.md (report) nella cartella del laboratorio.
Uso: python tools/lab/ombra_corner.py CARTELLA_PAGINE/data CARTELLA_STATO"""
import os, sys, json, csv, io, math, datetime, numpy as np, pandas as pd
from scipy.stats import nbinom, norm
DATA, OUT = sys.argv[1], sys.argv[2]
oggi = os.environ.get("OMBRA_OGGI") or datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")   # OMBRA_OGGI solo per le prove
OP = os.path.join(OUT, "ombra_corner.json")
REG = json.load(open(OP)) if os.path.exists(OP) else {"dal": oggi, "partite": {}}
RT, RTOT, COP = 12.0, 60.0, -0.20
CV = json.load(open(os.path.join(DATA, "corner_v2.json"))) if os.path.exists(os.path.join(DATA, "corner_v2.json")) else {"partite": {}}
REG.setdefault("coef", CV.get("coef"))
if CV.get("coef") and REG["coef"] != CV["coef"]: REG.setdefault("avvisi", []).append(f"{oggi}: coefficienti in corner_v2.json diversi da quelli registrati all'inizio")
for key, v in CV["partite"].items():
    lg, d, h, a, lh, la, mh, ma, vh, va, on, muH, muA = v
    if d < oggi: continue                     # le partite di giorni passati restano con l'ultima registrazione
    REG["partite"][key] = dict(lg=lg, d=d, h=h, a=a, app=[lh, la], v2=[vh, va], on=on, mu=[muH, muA], reg=CV.get("updated"))
# ---------------- corner reali
Y = {}
for fl in json.load(open(os.path.join(DATA, "bundle.json")))["files"]:
    stem = fl["name"].rsplit(".", 1)[0].split("_")[0]
    for r in csv.DictReader(io.StringIO(fl["text"])):
        try:
            dd, mm, yy = r["Date"].split("/"); yy = ("20" + yy) if len(yy) == 2 else yy
            if r.get("HC") not in (None, "") and r.get("AC") not in (None, ""):
                Y[f"{r.get('Div') or stem}|{yy}-{mm}-{dd}|{r.get('HomeTeam') or r.get('Home')}|{r.get('AwayTeam') or r.get('Away')}"] = (int(float(r["HC"])), int(float(r["AC"])))
        except Exception: pass
for k, p in REG["partite"].items():
    if k in Y and p["d"] < oggi: p["y"] = list(Y[k])
# ---------------- metriche (stesse formule dell'app)
BX = np.array([.9815606342467191, .9041172563704750, .7699026741943050, .5873179542866171, .3678314989981802, .1252334085114692])
BW = np.array([.04717533638651177, .1069393259953183, .1600783285433464, .2031674267230659, .2334925365383547, .2491470458134029])
KM = 31; KK = np.arange(KM)
def nbp(mu, r): return nbinom.pmf(KK[None, :], r, r / (r + np.asarray(mu, float)[:, None]))
def x12(lh, la):
    ph, pa = nbp(lh, RT), nbp(la, RT)
    Fh, Fa = np.clip(np.cumsum(ph, 1), 1e-13, 1 - 1e-13), np.clip(np.cumsum(pa, 1), 1e-13, 1 - 1e-13); zh, za = norm.ppf(Fh), norm.ppf(Fa)
    asr = math.asin(COP) / 2; xs = np.r_[1 - BX, 1 + BX]; ws = np.r_[BW, BW]; sn = np.sin(asr * xs); iv = 1 / (1 - sn ** 2)
    hk = zh[:, :, None] * za[:, None, :]; hs = (zh[:, :, None] ** 2 + za[:, None, :] ** 2) / 2; t = np.zeros_like(hk)
    for q in range(12): t += ws[q] * np.exp((sn[q] * hk - hs) * iv[q])
    C = np.pad(t * asr / (2 * math.pi) + Fh[:, :, None] * Fa[:, None, :], ((0, 0), (1, 0), (1, 0)))
    P = np.clip(C[:, 1:, 1:] - C[:, :-1, 1:] - C[:, 1:, :-1] + C[:, :-1, :-1], 0, None); P /= P.sum((1, 2), keepdims=True)
    i, j = np.meshgrid(KK, KK, indexing="ij"); return (P * (i > j)).sum((1, 2)), (P * (i == j)).sum((1, 2))
lp = lambda y, mu, r: nbinom.logpmf(y, r, r / (r + mu))
ovr = lambda L, mu, r: 1 - nbinom.cdf(np.floor(L), r, r / (r + mu))
bll = lambda p, o: -np.log(np.clip(np.where(o == 1, p, 1 - p), 1e-12, 1))
TL, SL = (7.5, 8.5, 9.5, 10.5, 11.5, 12.5), (3.5, 4.5, 5.5, 6.5)
def metrics(G, lh, la):
    yh, ya = G.yh.values, G.ya.values; yt = yh + ya; tot = lh + la; o = pd.DataFrame(index=G.index)
    o["ll_squadra"] = -(lp(yh, lh, RT) + lp(ya, la, RT)) / 2; o["ll_totale"] = -lp(yt, tot, RTOT)
    p1, px = x12(lh, la); p2 = np.clip(1 - p1 - px, 1e-12, 1); o1, ox = (yh > ya).astype(float), (yh == ya).astype(float)
    o["ll_1x2"] = -np.log(np.clip(np.where(o1 == 1, p1, np.where(ox == 1, px, p2)), 1e-12, 1)); o["brier_1x2"] = (p1 - o1) ** 2 + (px - ox) ** 2 + (p2 - (1 - o1 - ox)) ** 2
    o["p1"], o["px"], o["p2"] = p1, px, p2
    L = np.floor(G.ah.values + G.aa.values) + 0.5; p = ovr(L, tot, RTOT); oo = (yt > L).astype(float)   # stessa linea per i due modelli
    o["linea"], o["p_over"], o["brier_ou"], o["ll_ou"] = L, p, (p - oo) ** 2, bll(p, oo)
    o["brier_ou_fisse"] = np.mean([(ovr(L_, tot, RTOT) - (yt > L_)) ** 2 for L_ in TL], 0)
    o["ll_ou_fisse"] = np.mean([bll(ovr(L_, tot, RTOT), (yt > L_).astype(float)) for L_ in TL], 0)
    bs = []; ls = []
    for mu, y, ref in ((lh, yh, G.ah.values), (la, ya, G.aa.values)):
        L = np.floor(ref) + 0.5; p = ovr(L, mu, RT); oo = (y > L).astype(float); bs.append((p - oo) ** 2); ls.append(bll(p, oo))
    o["brier_ou_squadra"], o["ll_ou_squadra"] = (bs[0] + bs[1]) / 2, (ls[0] + ls[1]) / 2
    o["mae_totale"], o["se_totale"] = np.abs(yt - tot), (yt - tot) ** 2
    o["mae_squadra"], o["se_squadra"] = (np.abs(yh - lh) + np.abs(ya - la)) / 2, ((yh - lh) ** 2 + (ya - la) ** 2) / 2
    return o
def boot(d, g, B=2000, q=(0.5, 99.5)):
    s = pd.Series(d).groupby(g); S_ = s.sum().values; C = s.count().values
    if len(S_) < 2: return [None, None]
    idx = np.random.default_rng(7).integers(0, len(S_), (B, len(S_))); bs = S_[idx].sum(1) / C[idx].sum(1)
    return [round(float(np.percentile(bs, q[0])), 6), round(float(np.percentile(bs, q[1])), 6)]
rows = [dict(key=k, lg=p["lg"], d=p["d"], ah=p["app"][0], aa=p["app"][1], vh=p["v2"][0], va=p["v2"][1], on=p["on"], yh=p["y"][0], ya=p["y"][1])
        for k, p in REG["partite"].items() if "y" in p and p["app"][0] and p["v2"][0]]
REP = {"aggiornato": oggi, "dal": REG["dal"], "registrate": len(REG["partite"]), "con_risultato": len(rows)}
MD = [f"# Corner V2 · prova in ombra (dal {REG['dal']})", "", f"Aggiornato {oggi}. Partite registrate {len(REG['partite'])}, con corner reali {len(rows)}.",
      "Confronto sugli stessi eventi: app (ufficiale) contro Corner V2, coefficienti congelati. Negativo = V2 meglio. Nessuna ricalibrazione.", ""]
KEYS = ["ll_squadra", "ll_totale", "ll_1x2", "brier_1x2", "ll_ou", "brier_ou", "ll_ou_fisse", "brier_ou_fisse", "ll_ou_squadra", "brier_ou_squadra", "mae_totale", "se_totale", "mae_squadra", "se_squadra"]
if rows:
    G = pd.DataFrame(rows).sort_values(["d", "key"]).reset_index(drop=True); G["wk"] = (pd.to_datetime(G.d) - pd.Timestamp("1970-01-01")).dt.days // 7
    XA, XV = metrics(G, G.ah.values, G.aa.values), metrics(G, G.vh.values, G.va.values)
    agg = {}
    for k in KEYS:
        d = (XV[k] - XA[k]).values; agg[k] = dict(app=round(float(XA[k].mean()), 6), v2=round(float(XV[k].mean()), 6), diff=round(float(d.mean()), 6),
                                                  ic99_settimana=boot(d, G.wk.values), ic99_campionato=boot(d, G.lg.values),
                                                  campionati_meglio=f"{int((pd.Series(d).groupby(G.lg.values).mean() < 0).sum())}/{G.lg.nunique()}")
    for k in ("se_totale", "se_squadra"): agg[k]["rmse_app"] = round(math.sqrt(XA[k].mean()), 4); agg[k]["rmse_v2"] = round(math.sqrt(XV[k].mean()), 4)
    REP["aggregato"] = agg; REP["attive"] = int(G.on.sum())
    REP["livello"] = dict(reali=round(float((G.yh + G.ya).mean()), 3), app=round(float((G.ah + G.aa).mean()), 3), v2=round(float((G.vh + G.va).mean()), 3),
                          over_reale=round(float((XA.p_over * 0 + ((G.yh + G.ya) > XA.linea)).mean() * 100), 1), over_app=round(float(XA.p_over.mean() * 100), 1), over_v2=round(float(XV.p_over.mean() * 100), 1))
    dd = G.assign(d_sq=XV.ll_squadra - XA.ll_squadra, d_tot=XV.ll_totale - XA.ll_totale, d_12=XV.ll_1x2 - XA.ll_1x2, d_ou=XV.brier_ou - XA.brier_ou)
    REP["campionati"] = dd.groupby("lg").agg(n=("d", "size"), d_squadra=("d_sq", "mean"), d_totale=("d_tot", "mean"), d_1x2=("d_12", "mean"), d_brier_ou=("d_ou", "mean")).round(5).to_dict("index")
    fas = pd.cut(G.ah + G.aa, [0, 8.5, 9.5, 10.5, 11.5, 99])
    REP["fasce"] = {str(f): dict(n=int(len(g)), reali=round(float((g.yh + g.ya).mean()), 3), app=round(float((g.ah + g.aa).mean()), 3), v2=round(float((g.vh + g.va).mean()), 3),
                            d_squadra=round(float(g.d_sq.mean()), 5), d_totale=round(float(g.d_tot.mean()), 5), d_1x2=round(float(g.d_12.mean()), 5)) for f, g in dd.groupby(fas, observed=True)}
    REP["linee_fisse"] = {str(L_): dict(brier_app=round(float(((ovr(L_, G.ah + G.aa, RTOT) - ((G.yh + G.ya) > L_)) ** 2).mean()), 5), brier_v2=round(float(((ovr(L_, G.vh + G.va, RTOT) - ((G.yh + G.ya) > L_)) ** 2).mean()), 5)) for L_ in TL}
    sp = G.vh / G.ah; REP["spostamento_casa"] = [round(float(x), 4) for x in np.percentile(sp, [5, 50, 95])]
    MD += ["## Aggregato", "", "| metrica | app | V2 | V2 − app | IC 99% (settimane) | IC 99% (campionati) | campionati meglio |", "|---|---|---|---|---|---|---|"]
    MD += [f"| {k} | {v['app']} | {v['v2']} | {v['diff']:+.6f} | {v['ic99_settimana']} | {v['ic99_campionato']} | {v['campionati_meglio']} |" for k, v in agg.items()]
    MD += ["", f"Livello: reali {REP['livello']['reali']} · app {REP['livello']['app']} · V2 {REP['livello']['v2']}; Over sulla linea: reale {REP['livello']['over_reale']}% · app {REP['livello']['over_app']}% · V2 {REP['livello']['over_v2']}%",
           f"V2 attivo in {REP['attive']} partite su {len(G)} (le altre: dati insufficienti, uguale all'ufficiale).", "", "## Fasce di corner attesi (ufficiali)", "",
           "| fascia | n | reali | app | V2 | Δ squadra | Δ totale | Δ 1X2 |", "|---|---|---|---|---|---|---|---|"]
    MD += [f"| {f} | {v['n']} | {v['reali']} | {v['app']} | {v['v2']} | {v['d_squadra']:+.5f} | {v['d_totale']:+.5f} | {v['d_1x2']:+.5f} |" for f, v in REP["fasce"].items()]
    MD += ["", "## Campionati", "", "| campionato | n | Δ squadra | Δ totale | Δ 1X2 | Δ Brier O/U |", "|---|---|---|---|---|---|"]
    MD += [f"| {lg} | {v['n']} | {v['d_squadra']:+.5f} | {v['d_totale']:+.5f} | {v['d_1x2']:+.5f} | {v['d_brier_ou']:+.5f} |" for lg, v in REP["campionati"].items()]
    MD += ["", "## Over/Under sulle linee fisse (Brier)", "", "| linea | app | V2 |", "|---|---|---|"] + [f"| {L_} | {v['brier_app']} | {v['brier_v2']} |" for L_, v in REP["linee_fisse"].items()]
    worse = [lg for lg, v in REP["campionati"].items() if v["n"] >= 30 and v["d_squadra"] > 0 and v["d_totale"] > 0 and v["d_1x2"] > 0]
    MD += ["", "Campionati con almeno 30 partite peggiorati su tutte e tre le verosimiglianze: " + (", ".join(worse) if worse else "nessuno")]
else:
    MD += ["Nessuna partita con risultato ancora."]
REG["riepilogo"] = REP
json.dump(REG, open(OP, "w"), ensure_ascii=False, separators=(",", ":"))
open(os.path.join(OUT, "CORNER_V2.md"), "w").write("\n".join(MD) + "\n")
riga = f"Corner V2 in ombra: {REP['registrate']} partite registrate, {REP['con_risultato']} con risultato" + (f" · log-loss squadra V2 − app {REP['aggregato']['ll_squadra']['diff']:+.5f}, 1X2 {REP['aggregato']['ll_1x2']['diff']:+.5f}" if rows else "")
with open(os.path.join(OUT, "RIEPILOGO.md"), "a") as fh: fh.write("\n\n## Corner V2 (prova in ombra, dettaglio in CORNER_V2.md)\n- " + riga + "\n")
print("::notice title=Corner V2 · in ombra::" + riga)
