"""Esiti reali che i file dell'app non hanno, per la verifica delle quote 1X2 (tools/analisi_1x2.js): gialli per squadra
(data/apif.json, statistiche API-Football) e corner, tiri e tiri in porta del 1° tempo (ramo tempi, scaricato da halves.yml).
Gira solo in GitHub Actions (archivio privato). Nomi API → nomi dell'app con apif_extra.learn_map (come update_data.py).
Scrive esiti.json: {"lg|data|casa|ospite": {"y": [casa, ospite], "c1": [...], "s1": [...], "st1": [...]}}. Nessuna richiesta API."""
import json, os, sys, glob, csv, io, datetime, collections
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__)))); import apif_extra
from zoneinfo import ZoneInfo
ROME = ZoneInfo("Europe/Rome")
AP = json.load(open("data/apif.json"))["partite"]
FILES = []
for bp in (sys.argv[1:] or ["pub/bundle_storico.json", "pub/bundle.json"]):   # dal 19/10/2026 le stagioni chiuse sono in bundle_storico.json
    if os.path.exists(bp): FILES += json.load(open(bp))["files"]
ours = collections.defaultdict(list)
for f in FILES:
    if "fixtures" in f["name"]: continue
    for r in csv.DictReader(io.StringIO(f["text"])):
        lg = (r.get("Div") or r.get("Country") or "").strip(); h = (r.get("HomeTeam") or r.get("Home") or "").strip(); a = (r.get("AwayTeam") or r.get("Away") or "").strip()
        g1, g2 = (r.get("FTHG") or r.get("HG") or "").strip(), (r.get("FTAG") or r.get("AG") or "").strip()
        try: dd = r["Date"].strip().split("/"); y = dd[2] if len(dd[2]) == 4 else "20" + dd[2]; d = datetime.date(int(y), int(dd[1]), int(dd[0]))
        except Exception: continue
        if g1.isdigit() and g2.isdigit(): ours[lg].append((d, h, a, int(g1), int(g2)))
HALF = {}
for fn in glob.glob("tempi/*.json"):
    HALF.update(json.load(open(fn)))
lim = (datetime.date.today() - datetime.timedelta(days=60)).isoformat()   # l'archivio quote parte dal 9/10/2026
bylg = collections.defaultdict(list)
for fid, v in AP.items():
    if v[9] in ("FT", "AET", "PEN"): bylg[v[1]].append((fid, v))
out, nmiss = {}, 0
for lg, L in bylg.items():
    mp = apif_extra.learn_map([(datetime.date.fromisoformat(v[0][:10]), v[2], v[3], v[4], v[5]) for _, v in L], ours.get(lg, []), lg)
    if lg in ("UCL", "UEL"):
        for _, v in L: mp.setdefault(v[2], v[2]); mp.setdefault(v[3], v[3])
    have = {(o[1], o[2], o[0]) for o in ours.get(lg, [])}
    for fid, v in L:
        if v[0][:10] < lim: continue
        h, a = mp.get(v[2]), mp.get(v[3])
        if not h or not a: nmiss += 1; continue
        dr = datetime.datetime.fromisoformat(v[0][:16] + ":00+00:00").astimezone(ROME).date()
        d = next((dr + datetime.timedelta(days=k) for k in (0, -1, 1) if (h, a, dr + datetime.timedelta(days=k)) in have), None)
        if d is None: nmiss += 1; continue
        e = {}
        H, A = v[7], v[8]
        if H and A and H[4] is not None and A[4] is not None: e["y"] = [int(H[4]), int(A[4])]
        t = HALF.get(fid)
        if t and t[3] and t[4]:
            for i, k in enumerate(("c1", "s1", "st1")):
                if t[3][i] is not None and t[4][i] is not None: e[k] = [t[3][i], t[4][i]]
        if e: out[f"{lg}|{d.isoformat()}|{h}|{a}"] = e
json.dump(out, open("esiti.json", "w"), separators=(",", ":"))
print(f"esiti.json: {len(out)} partite (gialli {sum(1 for x in out.values() if 'y' in x)}, 1° tempo {sum(1 for x in out.values() if 'c1' in x)}), non abbinate {nmiss}")
