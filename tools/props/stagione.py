"""Scheda "Giocatori" della partita · statistiche della stagione in corso, solo campionato (21/11/2026, Denny).
Per ogni squadra con i nomi dei giocatori nell'archivio formazioni (oggi Serie A, Premier, Liga, Bundesliga, Ligue 1; dal 21/11 i nomi si
salvano per tutti i campionati e le squadre si aggiungono da sole quando sono abbinate in data/giocatori.json):
presenze, da titolare, minuti, gol, assist, tiri, tiri in porta, falli fatti, falli subiti, gialli, rossi, fuorigioco, contrasti, dribbling
riusciti; più le ultime 5 partite di campionato del giocatore. Dati API-Football (fixtures/players), nessuna richiesta in più.
Squadre API-Football → nomi dell'app come in tools/props/giocatori.py (stessa data ±1 e stesso risultato sulla base walk-forward, ramo ricerca).
Un file per campionato (gs_<lega>.json): l'app scarica solo quello della partita aperta.
Uso: python tools/props/stagione.py CARTELLA_FORMAZIONI CARTELLA_BASE giocatori.json CARTELLA_USCITA"""
import json, glob, sys, os, datetime, collections
FORM, BASE, GJ, OUT = sys.argv[1:5]
G = json.load(open(GJ)) if os.path.exists(GJ) else {"squadre": {}, "giocatori": {}}
os.makedirs(OUT, exist_ok=True)
NOMI = {}
files = collections.defaultdict(list)
for fn in glob.glob(os.path.join(FORM, "*_20*.json")):
    D = json.load(open(fn))
    if "lega" not in D or not isinstance(D.get("partite"), dict): continue
    NOMI.update({str(k): v for k, v in (D.get("nomi") or {}).items()})
    files[D["lega"]].append((int(D.get("stagione") or os.path.basename(fn).split("_")[1][:4]), D))
# nomi delle squadre: voti partita per partita (stessa data ±1, stesso risultato, una sola partita possibile nella base dell'app)
bidx = collections.defaultdict(list)
for fn in glob.glob(os.path.join(BASE, "*.json")):
    lg = os.path.basename(fn)[:-5]
    for r in json.load(open(fn)):
        g = (r.get("y") or {}).get("g")
        if g and g[0] is not None: bidx[(lg, r["d"], g[0], g[1])].append(r)
vote = collections.defaultdict(collections.Counter)
for lg, L in files.items():
    for _, D in L:
        for v in D["partite"].values():
            if v[5] is None: continue
            for dd in (0, -1, 1):
                k = (lg, str(datetime.date.fromisoformat(v[0][:10]) + datetime.timedelta(days=dd)), v[5], v[6])
                if len(bidx.get(k, [])) == 1:
                    b = bidx[k][0]; vote[(lg, v[1])][b["h"]] += 1; vote[(lg, v[2])][b["a"]] += 1; break
NAME = {k: c.most_common(1)[0][0] for k, c in vote.items() if c.most_common(1)[0][1] >= 3}
ID2APP_G = {t["id"]: n for n, t in G["squadre"].items() if t.get("id")}
RUOLO = {k: v[1] for k, v in G.get("giocatori", {}).items()}
out = {}
for lg, L in files.items():
    se, D = max(L, key=lambda z: z[0])            # stagione in corso del campionato
    ID2APP = {tid: n for (l_, tid), n in NAME.items() if l_ == lg}
    for tid, n in ID2APP_G.items():
        if G["squadre"][n].get("lg") == lg: ID2APP.setdefault(tid, n)
    T = collections.defaultdict(lambda: {"n": 0, "p": {}, "u": collections.defaultdict(list)})
    for fid, v in sorted(D["partite"].items(), key=lambda z: z[1][0]):
        dt, hid, aid, hn, an, hg, ag, xh, xa, P = v[:10]
        if hg is None or not P: continue
        for side, tid, oid, xi in ((0, hid, aid, set(xh or [])), (1, aid, hid, set(xa or []))):
            if tid not in ID2APP: continue
            S = T[ID2APP[tid]]; S["n"] += 1; opp = ID2APP.get(oid, an if side == 0 else hn)
            for r in P:
                if r[1] != side: continue
                pid = str(r[0]); x = S["p"].setdefault(pid, [0] * 15)
                tit = 1 if (r[0] in xi or (len(r) > 23 and r[23] == 0)) else 0
                vals = [1, tit, r[2], r[3], r[4], r[9], r[10], r[7], r[8], r[5], r[6], r[12], r[13], r[19]]
                for i, z in enumerate(vals): x[i] += (z or 0)
                if r[11] and pid not in RUOLO: RUOLO[pid] = r[11]
                S["u"][pid].append([dt[:10], opp, "C" if side == 0 else "T", r[2] or 0, r[3] or 0, r[4] or 0, r[9] or 0, r[10] or 0, r[7] or 0, r[8] or 0, (r[5] or 0) + (r[6] or 0)])
    for team, S in T.items():
        rows = [[pid, NOMI.get(pid), RUOLO.get(pid, "")] + x[:14] for pid, x in S["p"].items() if NOMI.get(pid)]
        tot = sum(x[2] for x in S["p"].values()); nom = sum(r[5] for r in rows)
        if not rows or tot <= 0 or nom / tot < 0.9: continue   # squadra solo se i nomi coprono almeno il 90% dei minuti giocati
        out.setdefault(lg, {})[team] = {"lg": lg, "stagione": se, "partite": S["n"], "g": sorted(rows, key=lambda r: -r[5]), "u5": {pid: S["u"][pid][-5:][::-1] for pid, *_ in rows}}
agg = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M")
for lg, sq in out.items():
    json.dump({"agg": agg, "lega": lg,
               "colonne": ["id", "nome", "ruolo", "presenze", "titolare", "minuti", "gol", "assist", "tiri", "tiri_porta", "falli_fatti", "falli_subiti", "gialli", "rossi", "fuorigioco", "contrasti", "dribbling"],
               "u5": ["data", "avversario", "sede", "minuti", "gol", "assist", "tiri", "tiri_porta", "falli_fatti", "falli_subiti", "cartellini"],
               "squadre": sq}, open(os.path.join(OUT, f"gs_{lg}.json"), "w"), ensure_ascii=False, separators=(",", ":"))
print("stagione giocatori:", {lg: len(sq) for lg, sq in out.items()}, sum(len(t["g"]) for sq in out.values() for t in sq.values()), "giocatori")
