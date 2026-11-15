"""Controllo dei loghi (15/11/2026, audit): per ogni logo pubblicato (data/loghi.json dei campionati e "loghi" di naz.json, ucl.json, uel.json)
verifica che l'immagine si scarichi davvero (HTTP 200, tipo immagine, più di 200 byte). Nessuna richiesta API-Football (sono immagini).
Uso: python tools/controllo_loghi.py CARTELLA_DATI"""
import json, os, sys, urllib.request, concurrent.futures as cf
D = sys.argv[1] if len(sys.argv) > 1 else "data"
U = {}
for f in ("naz.json", "ucl.json", "uel.json"):
    try:
        for n, u in (json.load(open(os.path.join(D, f))).get("loghi") or {}).items(): U.setdefault(u, set()).add(f"{f[:-5].upper()} {n}")
    except Exception: pass
try:
    for lg, m in json.load(open(os.path.join(D, "loghi.json"))).items():
        if isinstance(m, dict):
            for n, u in m.items(): U.setdefault(u, set()).add(f"{lg} {n}")
except Exception: pass
def chk(u):
    try:
        req = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=20) as r:
            b = r.read(); ct = r.headers.get("Content-Type", "")
            return u, (r.status == 200 and ct.startswith("image") and len(b) > 200), f"{r.status} {ct} {len(b)}B"
    except Exception as e: return u, False, str(e)[:80]
bad = []
with cf.ThreadPoolExecutor(16) as ex:
    for u, ok, why in ex.map(chk, list(U)):
        if not ok: bad.append((sorted(U[u])[:3], why))
print(f"::{'warning' if bad else 'notice'} title=Loghi::{len(U)} immagini controllate, non scaricabili {len(bad)}" + (": " + "; ".join(f"{', '.join(n)} ({w})" for n, w in bad[:30]) if bad else ""))
