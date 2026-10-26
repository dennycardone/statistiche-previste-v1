# Agente di ricerca · registro delle ipotesi (Prevista 2.0)

Ogni ipotesi passa da `tools/harness.py` (scelta fino a giugno 2024, verifica luglio 2024 – giugno 2025, holdout da luglio 2025).
Regola: entra nell'app solo se migliora in modo significativo nella verifica, nello stesso verso nell'holdout e nella maggioranza dei campionati.

| Data | Ipotesi | Mercati | Esito | Numeri (log-loss, verifica / holdout) |
|---|---|---|---|---|
| 25/10 | Formazione ufficiale (titolari contro abituali) | falli | **ADOTTATA** | −0,0053 / −0,0057, 35/42 e 39/44 campionati |
| 25/10 | Formazione ufficiale | tiri, tiri in porta, corner, fuorigioco | no (tiri al limite) | −0,0010 / −0,0005 tiri; resto ≈ 0 |
| 25/10 | Formazione probabile | tutti | no | ≈ 0 |
| 26/10 | Calibrazione per mercato e per campionato | tutti | no | 0,0000 / −0,0004 (solo gol, solo ultima stagione) |
| 26/10 | Grado meta-modello (storia errori, inizio stagione, campione) | tutti | no | 0,0000 |
| 26/10 | Media gol del campionato più reattiva (60/120 giorni) | Over/Under 2,5 | no | ≈ 0 |
| 26/10 | Correlazione casa-ospite appresa (copula) | corner, tiri, falli, fuorigioco | no | ≈ 0 |
| 26/10 | Doppi vuoti dei fuorigioco più severi (eccesso sullo 0-0 atteso) | fuorigioco | no | BUL −0,0019 / −0,0006, HUN 0,0000 / +0,0009, N1 ≈ 0 (campioni piccoli) |
| 26/10 | Giorni di riposo, partite in 14 giorni, coppa europea | tiri, tiri in porta, falli, corner, cartellini | no | ≈ 0 |
| 26/10 | Posta in gioco (ultime 10 giornate, nulla in gioco, distanza in classifica) | tiri, tiri in porta, falli, corner | no (tiri −0,0001: trascurabile) | ≈ 0 |
| 26/10 | Titolari sui cartellini: falli commessi dei titolari (XF) | cartellini | piccolo ma stabile | −0,0002 ±0,0001 / −0,0004 ±0,0002 |
| 26/10 | Titolari sui cartellini: cartellini dei titolari (XC) | cartellini | no (prima stagione non significativa) | −0,0003 ±0,0004 / −0,0004 ±0,0003 |

## Studi sull'archivio reale delle quote 1xBet (regola dei 100 giorni)
Stessa regola per tutti: si decide solo con almeno 100 giorni di archivio (primi due terzi solo da guardare, ultimo terzo verifica);
checkpoint di sola lettura il 7/12/2026 (~60 giorni), decisione il 18/1/2027 (~100 giorni). Sempre la probabilità corretta per esito.

| Data | Ipotesi | Strumento | Stato |
|---|---|---|---|
| 25/10 | Quota 2 / Quota 3: metodo di scelta della combinazione del giorno | `tools/quota23.py` | in raccolta |
| 26/10 | Gestione del capitale: Kelly 1/8 e 1/4 (tetto 3% per giocata) e fasce di Grado/valore contro puntata fissa 1%/2%, su singole e migliore Quota 2 / Quota 3 del giorno, per perimetro (solo statistiche, statistiche + formazioni falli, tutti, solo gol), tetto giornaliero 10% della cassa, astensione senza valore atteso positivo. Entra nell'app (Gioco responsabile / Diario, cassa solo nel localStorage) solo se nella verifica ha rendimento corretto per il rischio più alto della fissa 1% (IC 95% bootstrap settimanale sopra zero) o calo massimo più basso a rendimento non inferiore, con yield non peggiore del −margine 1xBet | `tools/bankroll.py` | in raccolta |

## In coda
- Arbitro designato / formazione nota come fattori del Grado (si registrano da oggi: provabili tra qualche mese).
- Formazioni su tiri e fuorigioco: da riprovare con più partite.
- Meteo e campo (sintetico, dimensioni): servono dati nuovi.
