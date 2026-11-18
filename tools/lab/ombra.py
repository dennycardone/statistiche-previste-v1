"""Laboratorio di Prevista · prova IN OMBRA sulle partite nuove (18/11/2026, Denny). Le idee che passano il laboratorio non entrano nell'app:
ogni giorno si registrano le loro previsioni sulle partite da giocare (coefficienti congelati alla stima del laboratorio) accanto a quelle
dell'app, poi si confrontano con i risultati veri. Tre bracci: app (M0), app + costante (riferimento alla pari), app + idea.
Dati: pagine pubblicate (data/precalc.json: falli attesi dell'app per le partite da giocare; data/extra.json: derby; data/bundle.json: falli reali).
Uso: python tools/lab/ombra.py CARTELLA_PAGINE/data CARTELLA_STATO"""
import os, sys, json, csv, io, datetime, numpy as np
from scipy.stats import nbinom
DATA, OUT = sys.argv[1], sys.argv[2]
ST = json.load(open(os.path.join(OUT, "stato.json")))
OP = os.path.join(OUT, "ombra.json"); OM = json.load(open(OP)) if os.path.exists(OP) else {}
oggi = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
PC = json.load(open(os.path.join(DATA, "precalc.json")))["rows"]
EX = json.load(open(os.path.join(DATA, "extra.json"))).get("partite", {})
# moltiplicatori delle idee in ombra (solo idee sui falli per ora; ogni idea dice quale caratteristica le serve)
def feat_derby(key): x = EX.get(key); return 1.0 if x and len(x) > 8 and x[8] and len(x[8]) > 5 and x[8][5] and x[8][5] > 1.0 else 0.0
FEAT = {"F1": lambda key: {"derby": feat_derby(key)}}
INTEG = {x["id"] for x in json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "idee.json")))["idee"] if x.get("integrata")}
for iid in INTEG:
    if iid in ST["idee"]: ST["idee"][iid]["esito"] = "integrata nell'app"
json.dump(ST, open(os.path.join(OUT, "stato.json"), "w"), indent=1, ensure_ascii=False, default=float)
for iid, v in ST["idee"].items():
    if v["esito"] != "in ombra" or iid not in FEAT: continue
    co = {k: a[0] for k, a in v["risultato"]["coefficienti"].items()}
    c0 = float(v["risultato"]["riferimento"].split("(")[1].split(")")[0])
    O = OM.setdefault(iid, {"dal": oggi, "partite": {}})
    for k, row in PC.items():
        if not k.endswith("|dyn") or len(row) < 7 or not isinstance(row[6], dict) or "f" not in row[6]: continue
        key = k[:-4]; d = key.split("|")[1]
        if d < oggi: continue                     # le partite già cominciate restano con l'ultima previsione registrata
        f = row[6]["f"]; lh, la = f[0], f[1]
        x = FEAT[iid](key); eta = co["costante"] + sum(co[n] * x[n] for n in x if n in co)
        O["partite"][key] = {"d": d, "app": [lh, la], "rif": [lh * np.exp(c0), la * np.exp(c0)], "idea": [lh * np.exp(eta), la * np.exp(eta)], "x": x}
# risultati veri (falli) dal bundle
Y = {}
for fl in json.load(open(os.path.join(DATA, "bundle.json")))["files"]:
    for r in csv.DictReader(io.StringIO(fl["text"])):
        try:
            dd, mm, yy = r["Date"].split("/"); yy = ("20" + yy) if len(yy) == 2 else yy
            if r.get("HF") not in (None, "") and r.get("AF") not in (None, ""): Y[f"{r['Div']}|{yy}-{mm}-{dd}|{r['HomeTeam']}|{r['AwayTeam']}"] = (int(float(r["HF"])), int(float(r["AF"])))
        except Exception: pass
def ll(y, mu, r=200.0): return -nbinom.logpmf(y, r, r / (r + mu))
REP = []
for iid, O in OM.items():
    if iid in INTEG: REP.append(f"{iid}: integrata nell'app, prova in ombra chiusa ({len(O['partite'])} partite registrate)"); continue
    G = [(k, p, Y[k]) for k, p in O["partite"].items() if k in Y and p["d"] < oggi]
    for k, p, y in G: p["y"] = list(y)
    if not G: REP.append(f"{iid}: in ombra dal {O['dal']}, nessuna partita con risultato ancora"); continue
    A = np.array([[ll(y[0], p["app"][0]) + ll(y[1], p["app"][1]), ll(y[0], p["rif"][0]) + ll(y[1], p["rif"][1]), ll(y[0], p["idea"][0]) + ll(y[1], p["idea"][1])] for k, p, y in G])
    ch = np.array([abs(p["idea"][0] / p["rif"][0] - 1) > 0.01 for k, p, y in G])   # partite in cui l'idea cambia davvero la previsione
    d = A[:, 2] - A[:, 1]; se = d.std(ddof=1) / np.sqrt(len(d)) if len(d) > 1 else float("nan")
    O["riepilogo"] = {"partite": len(G), "cambiate": int(ch.sum()), "idea_meno_rif": float(d.mean()), "errore_std": float(se), "idea_meno_app": float((A[:, 2] - A[:, 0]).mean()),
                      "sulle_cambiate": float(d[ch].mean()) if ch.any() else None}
    REP.append(f"{iid}: {len(G)} partite ({int(ch.sum())} in cui l'idea cambia la previsione) · idea − riferimento {d.mean():+.5f} ± {se:.5f} · idea − app {(A[:, 2] - A[:, 0]).mean():+.5f}"
               + (f" · sulle cambiate {d[ch].mean():+.4f}" if ch.any() else ""))
json.dump(OM, open(OP, "w"), ensure_ascii=False, separators=(",", ":"))
with open(os.path.join(OUT, "RIEPILOGO.md"), "a") as fh: fh.write("\n\n## In ombra (partite nuove, negativo = idea meglio)\n" + "\n".join("- " + x for x in REP) + "\n")
print("::notice title=Laboratorio · in ombra::" + (" · ".join(REP) if REP else "nessuna idea in ombra"))
