"""Richieste API-Football per prove, test e download storici: solo quelle che avanzano DOPO aver messo da parte quanto serve
all'app fino alla fine della giornata API (le richieste si azzerano a mezzanotte UTC).
Consumo dell'app misurato domenica 18/10/2026: ~200-225 richieste l'ora (quote ~2.000 al giorno, partite e statistiche ~1.600);
dal 19/10/2026 (calendari per data, statistiche solo 3 volte per partita) le partite scendono a ~250 al giorno.
Riserva = 300 fisse + 250 per ogni ora che manca a mezzanotte UTC. Alle 23:25 UTC (orario delle prove) restano ~450 di riserva.
28/10/2026: ricalcolata sui consumi reali dopo la rimozione di 14 campionati e con il micro-processo delle formazioni e gli infortuni:
mercoledì 28/10 dalle 5:44 alle 21:24 UTC da 473 a 1.852 richieste, ~90 l'ora (comprese le diagnosi). Riserva = 300 fisse + 175 per
ogni ora che manca a mezzanotte UTC (margine per i weekend più pieni). Alle 23:25 UTC ~400 di riserva; alle 0:35 UTC (secondo giro
notturno, dopo l'azzeramento) ~4.300."""
import datetime

def app_reserve(now=None):
    now = now or datetime.datetime.now(datetime.timezone.utc)
    left = 24 - (now.hour + now.minute / 60)
    return int(300 + 175 * left)

def requests_of(status_json):
    """Blocco "requests" della chiamata status; vuoto se le richieste sono finite ("response" è una lista)."""
    r = (status_json or {}).get("response")
    return (r.get("requests") or {}) if isinstance(r, dict) else {}

def test_budget(rq, now=None):
    """Richieste usabili da prove e test adesso (0 se lo stato non è leggibile)."""
    if not rq: return 0
    return max(0, int(rq.get("limit_day", 100)) - int(rq.get("current", 0)) - app_reserve(now))
