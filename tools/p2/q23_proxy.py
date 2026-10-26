"""Quota 2 / Quota 3 · studio sul lungo periodo con quote storiche di football-data (OK di Denny 26/10/2026: SOLO per il test, mai nell'app).
Mercati: 1X2 gol e Over/Under 2,5 (gli unici con quote storiche). Quota "prima" = Bet365 (raccolta prima della giornata),
quota "ultima" = media di chiusura (AvgC). Probabilità di Prevista dai file base (soli dati precedenti). Scrive q23_candidati.json
nello stesso formato del flusso GitHub, così lo studio (tools/quota23.py) è identico."""
import json, glob, csv, io, numpy as np
from scipy.stats import poisson
B = {}
for fn in glob.glob("/home/claude/research/p2/base/*.json"):
    lg = fn.split("/")[-1][:-5]
    for r in json.load(open(fn)): B[(lg, r["d"], r["h"], r["a"])] = r
def dc(lh, la, rho, N=10):
    M = np.outer(poisson.pmf(np.arange(N + 1), lh), poisson.pmf(np.arange(N + 1), la))
    if rho: M[0, 0] *= 1 - lh * la * rho; M[0, 1] *= 1 + lh * rho; M[1, 0] *= 1 + la * rho; M[1, 1] *= 1 - rho
    return M / M.sum()
f = lambda x: float(x) if x not in (None, "") else None
out = []; n = 0
for fl in json.load(open("/tmp/claude-0/audit/live7/data/bundle_storico.json"))["files"] + json.load(open("/tmp/claude-0/audit/live7/data/bundle.json"))["files"]:
    for r in csv.DictReader(io.StringIO(fl["text"])):
        try: dd = r["Date"].split("/"); d = f"{dd[2] if len(dd[2]) == 4 else '20' + dd[2]}-{dd[1]}-{dd[0]}"
        except Exception: continue
        b = B.get((r.get("Div"), d, r.get("HomeTeam"), r.get("AwayTeam")))
        if not b or not b.get("g") or b["y"]["g"][0] is None: continue
        hg, ag = b["y"]["g"]; M = dc(*b["g"]); tot = np.add.outer(np.arange(11), np.arange(11))
        p1, px = float(np.tril(M, -1).sum()), float(np.trace(M)); p2 = 1 - p1 - px; po = float(M[tot > 2.5].sum())
        key = f"{b['lg'] if 'lg' in b else r['Div']}|{d}|{r['HomeTeam']}|{r['AwayTeam']}"
        def add(mk, side, p, y, q0, q1):
            if (q0 and q0 > 1) or (q1 and q1 > 1): out.append(dict(key=key, d=d, lg=r["Div"], t=r.get("Time", ""), mk=mk, side=side, p=round(p, 4), y=int(y), q0=q0 if q0 and q0 > 1 else None, q1=q1 if q1 and q1 > 1 else None))
        add("1X2 gol", "1", p1, hg > ag, f(r.get("B365H")), f(r.get("AvgCH")))
        add("1X2 gol", "X", px, hg == ag, f(r.get("B365D")), f(r.get("AvgCD")))
        add("1X2 gol", "2", p2, ag > hg, f(r.get("B365A")), f(r.get("AvgCA")))
        add("Over/Under 2.5", "Over", po, hg + ag > 2.5, f(r.get("B365>2.5")), f(r.get("AvgC>2.5")))
        add("Over/Under 2.5", "Under", 1 - po, hg + ag < 2.5, f(r.get("B365<2.5")), f(r.get("AvgC<2.5")))
        n += 1
json.dump(out, open("/home/claude/research/p2/q23proxy/q23_candidati.json", "w"))
print("partite", n, "esiti", len(out), "giorni", len({c["d"] for c in out}))
