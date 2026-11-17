"""Gol attesi V2 · verifica prospettica (Denny, 17/11/2026): solo partite giocate DOPO il congelamento (dal 18/11/2026), V2 contro M0,
coefficienti e formule fissi (nessuna riottimizzazione). Legge ricerca/base (base.js: g = [λ V2 casa, ospite, rho, λ M0 casa, ospite]).
Stampa log-loss del risultato esatto e dell'1X2, Brier 1X2, Over 2,5, pareggi, con intervallo al 95% e campionati migliorati."""
import sys, os, json, glob, warnings, numpy as np, pandas as pd
warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.dirname(__file__)); from gol_eval import *
DA = os.environ.get("GOL_V2_DA", "2026-11-18"); B = sys.argv[1] if len(sys.argv) > 1 else "ricerca/base"
R = []
for f in glob.glob(os.path.join(B, "*.json")):
    for m in json.load(open(f)):
        g = m.get("g"); y = (m.get("y") or {}).get("g")
        if m["d"] < DA or not g or len(g) < 5 or g[3] is None or not y or y[0] is None: continue
        R.append(dict(lg=os.path.basename(f)[:-5], d=int(np.datetime64(m["d"], "D").astype(int)), yh=y[0], ya=y[1], lh=g[0], la=g[1], rho=g[2], lh0=g[3], la0=g[4]))
if not R: print(f"::notice title=Gol V2 · verifica prospettica::nessuna partita giocata dal {DA}"); sys.exit()
df = pd.DataFrame(R); df["per"] = "holdout"
X0 = metrics(df, df.lh0, df.la0); X2 = metrics(df, df.lh, df.la, df.rho.values)
out = [f"partite {len(df)} dal {DA}"]
for k, nm in (("ll_score", "risultato esatto"), ("ll_1x2", "1X2"), ("br_1x2", "Brier 1X2"), ("ll_o25", "Over 2,5")):
    r = compare(df, X0, X2, k)["holdout"]; out.append(f"{nm} {r['diff']:+.5f} [{r['lo']:+.5f}, {r['hi']:+.5f}] ({r['pct']:+.2f}%, campionati {r['camp']})")
out.append(f"pareggi previsti M0 {X0.p_x.mean()*100:.1f}% · V2 {X2.p_x.mean()*100:.1f}% · reali {X0.o_x.mean()*100:.1f}%")
print("::notice title=Gol V2 · verifica prospettica (negativo = V2 meglio di M0)::" + " · ".join(out))
