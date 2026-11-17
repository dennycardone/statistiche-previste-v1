"""Gol attesi V2: rho Dixon-Coles per mese (massima verosimiglianza su tutte le partite giocate PRIMA del mese, λ della V2 congelata).
Gira ogni mese in gol_rho.yml dopo gol_dump.js e gol_feat.py; scrive gol_rho.json (pubblicato in data/ da update.yml). Coefficienti fissi."""
import sys, os, json, datetime
sys.path.insert(0, os.path.dirname(__file__)); from gol_v2 import *
df = pd.read_pickle(os.path.join(REPO, "ricerca", "gol", "feat.pkl")).sort_values(["d", "lg"]).reset_index(drop=True)
lh, la = v2(df); T = rho_table(df, lh, la)
out = sys.argv[1] if len(sys.argv) > 1 else "gol_rho.json"
json.dump({"agg": datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M"), "partite": len(df), "rho": T}, open(out, "w"))
print(f"::notice title=Gol V2 · rho del mese::{list(T.items())[-3:]} · partite {len(df)}")
