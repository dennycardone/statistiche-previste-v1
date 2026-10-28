# Archivio di Prevista: dove sta ogni dato (28/10/2026)

Regola: niente deve esistere solo nella cartella di lavoro di Claude (persa il 26/10/2026). Ogni dato sta in un ramo del repository
o nel magazzino privato di GitHub Actions con la copia cifrata giornaliera.

## Materie prime
| Dato | Dove | Pubblico |
|---|---|---|
| Partite e statistiche delle stagioni passate (API-Football) | ramo `storico` | sì |
| Statistiche in più (fuorigioco, tiri in area…) | ramo `statextra` | sì |
| Formazioni e statistiche per giocatore (dal 2023) | ramo `formazioni` | sì |
| Statistiche per tempo (dal 28/10/2026 tutte: corner, tiri, tiri in porta, falli, fuorigioco, gialli, rossi, tiri in area, xG…; dalla stagione 2024-25) | ramo `tempi` | sì |
| Eventi con il minuto (cartellini, gol) e risultato del 1° tempo, dal 2022 | ramo `eventi` | sì |
| Valori dei giocatori (falli, cartellini) | ramo `valori` | sì |
| Formazioni ufficiali prese prima del fischio (ultimi giorni) | ramo `xi` | sì |
| Dati dell'app (bundle, extra, quote del giorno…) | ramo `pages` | sì |
| Archivio quote 1xBet (`odds_hist.json`), archivio partite (`apif.json`), quote (`odds.json`), formazioni registrate (`formazioni_hist.json`), giocate del Radar bloccate al fischio (`mercato_storico.json`), infortunati e squalificati con l'ora in cui sono stati visti (`infortuni_hist.json`, dal 28/10/2026) | magazzino privato di Actions + copia cifrata giornaliera sul ramo `backup` (due copie) | **no** (solo numeri aggregati) |

## Dati derivati per la ricerca (ramo `ricerca`, ricostruito ogni domenica da `.github/workflows/ricerca.yml`)
- `base/<campionato>.json`: per ogni partita giocata dal 2023 le previsioni dell'app con i soli dati dei giorni precedenti
  (corner, tiri, tiri in porta, falli, fuorigioco, gol) e i valori reali. Base di tutti i test con `tools/harness.py`.
- `feat2.pkl` (titolari), `feat_rest.pkl` (riposo), `feat_stakes.pkl` (posta in gioco).
- `indice.json`: data e partite per campionato.

## Studi sull'archivio privato delle quote
Girano solo dentro GitHub Actions e stampano solo numeri aggregati: `quota23.yml` (Quota 2/3 e Gestione del capitale),
`radar_mercato.yml`, `controlli.yml`, `diagnosi.yml`.

## Lavorare in locale
`bash tools/ricerca_locale.sh` scarica i rami pubblici in `ricerca/` (base, caratteristiche, formazioni, statistiche in più,
storico). Gli script in `tools/p2` leggono la cartella da `RICERCA` (predefinita `ricerca/`).
Da ricostruire se servono di nuovo: `cards_xi.py` (lettore dei cartellini storici) e `f21_grado.py` (file intermedi del backtest Grado).
