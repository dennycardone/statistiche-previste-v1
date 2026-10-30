"""Analisi IA partita per partita (30/10/2026, richiesta di Denny). Per ogni partita che inizia fra 1 e 30 ore e non ha ancora un'analisi:
l'IA (API di Anthropic, chiave nel segreto ANTHROPIC_API_KEY) riceve i dati di Prevista sulla partita (tools/ia_contesto.js: valori
attesi, arbitro, forma, scontri diretti) e può fare UNA ricerca sul web (notizie: assenze, posta in gioco, clima, tensione).
Restituisce un commento breve e un segnale per mercato (−1 sotto, 0 in linea, +1 sopra rispetto a Prevista).
Ogni analisi è salvata con data e ora (ramo analisi, analisi_ia.json) PRIMA della partita: fra qualche mese si verifica con
tools/harness.py se i segnali dell'IA prevedono lo scarto fra reale e Prevista. Finché non passa la verifica NON entra nei numeri:
nell'app è solo una lettura in tendina.
Limiti di spesa: IA_MAX analisi per giro (40), IA_MAX_DAY al giorno (150). Senza chiave: avviso e nessuna richiesta."""
import json, os, sys, re, time, datetime, urllib.request, urllib.error, traceback
sys.excepthook = lambda t, v, tb: print("::error title=Analisi IA::" + " | ".join(traceback.format_exception(t, v, tb)).replace("\n", " ")[-1500:])
note = lambda m: print("::notice title=Analisi IA::" + m.replace("%", "%25").replace("\n", " "))
KEY = os.environ.get("ANTHROPIC_API_KEY", "").strip()
MODEL = os.environ.get("IA_MODEL", "").strip() or "claude-haiku-5-5"
MAXRUN, MAXDAY = int(os.environ.get("IA_MAX", "40")), int(os.environ.get("IA_MAX_DAY", "150"))
ARCH = "analisi/analisi_ia.json"
os.makedirs("analisi", exist_ok=True)
A = json.load(open(ARCH)) if os.path.exists(ARCH) else {"partite": {}}
IN = json.load(open(os.environ.get("IA_INPUT", "ia_input.json")))
now = datetime.datetime.now(datetime.timezone.utc)
today = now.strftime("%Y-%m-%d")
done_today = sum(1 for v in A["partite"].values() if v.get("ora", "").startswith(today))
todo = []
for p in IN:
    k = f"{p['lg']}|{p['d']}|{p['casa']}|{p['ospite']}"
    if k in A["partite"] or not p.get("prevista") or not p["prevista"].get("gol"): continue
    ko = datetime.datetime.fromisoformat(p["ko"]).replace(tzinfo=datetime.timezone.utc)
    h = (ko - now).total_seconds() / 3600
    if 1 <= h <= 30: todo.append((ko, k, p))
todo.sort(key=lambda t: t[0])
if not KEY:
    note(f"chiave ANTHROPIC_API_KEY assente nei segreti del repository: nessuna analisi ({len(todo)} partite in attesa)"); sys.exit(0)
SYS = """Sei l'analista di Prevista, app di statistiche calcistiche. Ricevi i numeri del modello statistico di Prevista per una partita
(valori attesi per squadra: gol, tiri, tiri in porta, corner, falli, cartellini), l'arbitro, la forma recente e gli scontri diretti con i
numeri reali. Puoi fare UNA ricerca sul web per notizie recenti (assenze importanti, posta in gioco, clima tra i club, derby, meteo).
Il modello conosce già: forza delle squadre, casa/trasferta, arbitro, derby (in media +20% di cartellini), forma recente, formazioni
ufficiali sui falli. Segnala SOLO ciò che il modello probabilmente non coglie. Sii prudente: nella maggior parte delle partite i numeri
del modello vanno bene e il segnale giusto è 0. Non inventare fatti: se la ricerca non trova nulla di rilevante, dillo.
Rispondi SOLO con un oggetto JSON, in italiano, senza testo fuori dal JSON:
{"testo": "2-4 frasi sulla partita e su cosa il modello potrebbe non vedere",
 "fattori": ["fino a 4 fattori brevi"],
 "segnali": {"gol": 0, "tiri": 0, "tiri_in_porta": 0, "corner": 0, "falli": 0, "cartellini": 0},
 "fonti": ["fino a 3 titoli o siti delle notizie usate"]}
Ogni segnale: -1 = il totale reale sarà probabilmente sotto il valore di Prevista, 0 = in linea, +1 = sopra."""
def call(p, tools=True):
    body = {"model": MODEL, "max_tokens": 900, "system": SYS,
            "messages": [{"role": "user", "content": "Partita (dati di Prevista):\n" + json.dumps(p, ensure_ascii=False)}]}
    if tools: body["tools"] = [{"type": "web_search_20250305", "name": "web_search", "max_uses": 1}]
    req = urllib.request.Request("https://api.anthropic.com/v1/messages", data=json.dumps(body).encode(),
                                 headers={"x-api-key": KEY, "anthropic-version": "2023-06-01", "content-type": "application/json"})
    with urllib.request.urlopen(req, timeout=180) as r: return json.loads(r.read().decode())
def parse(resp):
    txt = "".join(b.get("text", "") for b in resp.get("content", []) if b.get("type") == "text")
    m = re.search(r"\{.*\}", txt, re.S)
    if not m: return None
    j = json.loads(m.group(0)); s = j.get("segnali") or {}
    j["segnali"] = {k: max(-1, min(1, int(s.get(k, 0) or 0))) for k in ("gol", "tiri", "tiri_in_porta", "corner", "falli", "cartellini")}
    j["testo"] = str(j.get("testo", ""))[:900]; j["fattori"] = [str(x)[:120] for x in (j.get("fattori") or [])][:4]; j["fonti"] = [str(x)[:120] for x in (j.get("fonti") or [])][:3]
    return j
n = err = tin = tout = srch = 0; tools_ok = True
for ko, k, p in todo:
    if n >= MAXRUN or done_today + n >= MAXDAY: break
    try:
        try: resp = call(p, tools_ok)
        except urllib.error.HTTPError as e:
            msg = e.read().decode()[:300]
            if e.code in (401, 403): note(f"chiave non valida o senza permessi ({e.code}): {msg}"); break
            if e.code == 400 and "tool" in msg.lower() and tools_ok: tools_ok = False; note("ricerca web non disponibile, analisi senza ricerca: " + msg); resp = call(p, False)
            else: raise
        j = parse(resp)
        if not j: err += 1; continue
        u = resp.get("usage") or {}; tin += u.get("input_tokens", 0); tout += u.get("output_tokens", 0)
        srch += ((u.get("server_tool_use") or {}).get("web_search_requests") or 0)
        A["partite"][k] = {"ora": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M"), "ko": p["ko"], "fid": p["fid"], "modello": MODEL,
                           "prevista": p["prevista"], "arbitro": p.get("arbitro"), **j}
        n += 1
    except Exception as e:
        err += 1; print("errore", k, e)
    time.sleep(1)
A["agg"] = now.strftime("%Y-%m-%dT%H:%M")
json.dump(A, open(ARCH, "w"), ensure_ascii=False, separators=(",", ":"))
note(f"modello {MODEL} · nuove analisi {n} · errori {err} · in attesa {max(0, len(todo) - n)} · oggi {done_today + n}/{MAXDAY} · token {tin} in, {tout} out · ricerche web {srch} · archivio {len(A['partite'])} partite")
