"""Laboratorio di Prevista · giro della notte (18/11/2026, Denny: "una volta al giorno").
1) prova le prossime idee 'in coda' di idee.json (al massimo per_giro), con la regola del laboratorio (comune.py);
2) chi passa va 'in ombra' (ombra.py la segue sulle partite nuove), chi non passa è 'scartata' (resta nello storico con i numeri);
3) scrive stato.json e RIEPILOGO.md nella cartella di stato (ramo lab). Uso: python tools/lab/lab.py CARTELLA_STATO"""
import os, sys, json, importlib, datetime
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
OUT = sys.argv[1]; os.makedirs(OUT, exist_ok=True)
I = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "idee.json")))
SP = os.path.join(OUT, "stato.json"); ST = json.load(open(SP)) if os.path.exists(SP) else {"idee": {}}
oggi = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
coda = [x for x in I["idee"] if x["id"] not in ST["idee"]][: int(os.environ.get("LAB_PER_GIRO") or I.get("per_giro", 2))]
cache = {}
for x in coda:
    M = importlib.import_module(x["modulo"])
    if x["modulo"] not in cache: cache[x["modulo"]] = M.prepare()
    J, F = cache[x["modulo"]]
    r = M.run(x["id"], J, F)
    ST["idee"][x["id"]] = {"stat": x["stat"], "nome": x["nome"], "descrizione": x["descrizione"], "provata": oggi,
                           "esito": "in ombra" if r["passa"] else "scartata", "risultato": r}
    print(f"{x['id']} {x['nome']}: {'PASSA → in ombra' if r['passa'] else 'non passa'}", flush=True)
json.dump(ST, open(SP, "w"), indent=1, ensure_ascii=False, default=float)
# riepilogo leggibile
def f(v): return f"{v['diff']:+.5f} ({v['pct']:+.3f}%) [99%: {v['lo99']:+.5f} / {v['hi99']:+.5f}] · campionati {v['camp']}"
L = [f"# Laboratorio di Prevista · {oggi}", "", "Regola: in verifica (2024-25) miglioramento con intervallo al 99% sotto zero, stesso segno in holdout (da luglio 2025, solo confronto), maggioranza dei campionati. Riferimento: previsioni dell'app con la sola costante stimata nel periodo scelta. Negativo = meglio.", ""]
for k, v in ST["idee"].items():
    r = v["risultato"]; c = r["confronti"]
    L += [f"## {k} · {v['nome']} ({v['stat']}) — {v['esito'].upper()} (provata il {v['provata']})", v["descrizione"], "",
          "coefficienti (stima, errore standard): " + ", ".join(f"{n} {a[0]:+.4f} ± {a[1]:.4f}" for n, a in r["coefficienti"].items()), "",
          f"- verosimiglianza per squadra · verifica {f(c['ll_team']['verifica'])} · holdout {f(c['ll_team']['holdout'])}",
          f"- 1X2 · verifica {f(c['ll_1x2']['verifica'])} · holdout {f(c['ll_1x2']['holdout'])}",
          f"- Over/Under sulla linea vicina · verifica {f(c['ll_ou']['verifica'])} · holdout {f(c['ll_ou']['holdout'])}", ""]
coda_dopo = [x["id"] for x in I["idee"] if x["id"] not in ST["idee"]]
L += [f"In coda: {', '.join(coda_dopo) if coda_dopo else 'nessuna (servono idee nuove)'}"]
open(os.path.join(OUT, "RIEPILOGO.md"), "w").write("\n".join(L))
print(f"::notice title=Laboratorio · {oggi}::provate oggi {', '.join(x['id'] for x in coda) or 'nessuna'} · in ombra {', '.join(k for k, v in ST['idee'].items() if v['esito'] == 'in ombra') or 'nessuna'} · in coda {len(coda_dopo)}")
