"""Player props · punto 1 (14/11/2026, Denny): copertura e qualità dei dati per giocatore nei Top 5 contro il resto.
Somma delle statistiche dei giocatori (ramo formazioni) contro il totale di squadra della stessa partita (ramo storico, stesso id API-Football).
Uso: python tools/props/copertura.py ricerca"""
import json, glob, os, sys, collections
R = sys.argv[1] if len(sys.argv) > 1 else "ricerca"
TOP = {"I1", "E0", "SP1", "D1", "F1"}
ST = {}
for fn in glob.glob(R + "/storico/*.json"):
    D = json.load(open(fn)); P = D.get("partite") or {}
    for fid, v in (P.items() if isinstance(P, dict) else P): ST[str(fid)] = v
acc = collections.defaultdict(lambda: collections.defaultdict(float)); cnt = collections.Counter()
lgacc = collections.defaultdict(lambda: collections.defaultdict(float))
for fn in glob.glob(R + "/form2/*.json"):
    D = json.load(open(fn))
    if "lega" not in D or not isinstance(D.get("partite"), dict): continue
    lg = D["lega"]; grp = "TOP5" if lg in TOP else "resto"
    for fid, v in D["partite"].items():
        cnt[grp, "partite"] += 1
        P = v[9]
        if not P: continue
        cnt[grp, "con giocatori"] += 1
        s = ST.get(fid)
        if not s or len(s) < 8: continue
        for side, tv in ((0, s[6]), (1, s[7])):
            rows = [r for r in P if r[1] == side]
            if not rows or tv is None or tv[0] is None: continue
            starters = [r for r in rows if len(r) > 23 and r[23] == 0]
            cnt[grp, "squadre"] += 1; cnt[grp, "titolari 11"] += len(starters) == 11
            a = acc[grp]; L = lgacc[lg]
            for j, (k, col) in enumerate((("tiri", 9), ("tiri in porta", 10), ("falli", 7))):
                ps = sum(r[col] or 0 for r in rows); tt = tv[[0, 1, 3][j]]
                if tt is None: continue
                a[k + " gioc"] += ps; a[k + " squadra"] += tt; a[k + " uguali"] += abs(ps - tt) < 0.5; a[k + " n"] += 1
                L[k + " gioc"] += ps; L[k + " squadra"] += tt; L[k + " n"] += 1
            a["minuti"] += sum(r[2] or 0 for r in rows); a["min n"] += 1
            a["gialli gioc"] += sum(r[5] or 0 for r in rows)
for grp in ("TOP5", "resto"):
    a = acc[grp]
    print(f"== {grp}: partite {cnt[grp,'partite']}, con giocatori {cnt[grp,'con giocatori']} ({cnt[grp,'con giocatori']/max(1,cnt[grp,'partite'])*100:.1f}%), "
          f"squadre confrontate {cnt[grp,'squadre']}, con 11 titolari {cnt[grp,'titolari 11']/max(1,cnt[grp,'squadre'])*100:.1f}%, minuti per squadra {a['minuti']/max(1,a['min n']):.0f}")
    for k in ("tiri", "tiri in porta", "falli"):
        n = a[k + " n"]
        if n: print(f"   {k}: somma giocatori / squadra {a[k+' gioc']/a[k+' squadra']*100-100:+.1f}% · partite con somma identica {a[k+' uguali']/n*100:.1f}%")
print("== per campionato (somma giocatori / squadra − 1): tiri · tiri in porta · falli")
for lg in sorted(lgacc, key=lambda l: (l not in TOP, l)):
    L = lgacc[lg]
    if L["tiri n"] < 50: continue
    print(f"   {lg:4s} {int(L['tiri n']):5d} squadre · " + " · ".join(f"{(L[k+' gioc']/L[k+' squadra']-1)*100:+.1f}%" if L[k+' squadra'] else "n/d" for k in ("tiri", "tiri in porta", "falli")))
