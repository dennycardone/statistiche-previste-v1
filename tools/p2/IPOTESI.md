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
| 28/10 | Tiri e tiri in porta costruiti dal basso (titolari ufficiali: tiri ogni 90' ristretti verso il ruolo × minuti attesi + subentrati), unito al modello con peso stimato mese per mese | tiri, tiri in porta 1X2 | no | tiri +0,0001 / −0,0002, tiri in porta +0,0001 / 0,0000 (IC sempre a cavallo dello zero); peso stimato piccolo (0,03-0,09); tiri per giocatore di API-Football ~29% sotto quelli di squadra |
| 28/10 | 1° tempo: quota di 1° tempo propria di ogni squadra (prodotto e concesso, K=10) contro la frazione fissa del campionato | tiri 1°T 1X2 | no, ma da riprovare | verifica −0,0007 (IC −0,0014 / +0,0001), holdout −0,0007 (IC −0,0013 / −0,0001), 19/31 e 23/31 campionati: verifica corta (dati per tempo dal 2024-25) |
| 28/10 | idem | corner 1°T 1X2 | no | −0,0001 / −0,0004 (holdout significativo, verifica no) |
| 28/10 | idem | tiri in porta 1°T, gol 1°T (1X2 del primo tempo) | no | ≈ 0 |
| 28/10 | Livello gol per campionato dagli ultimi 90/120 giorni (gol reali / attesi, K gol fittizi; W, K scelti sul periodo scelta: 90 g, K=120) | Over 1,5 · 2,5 · 3,5, 1X2 | no (peggiora) | O2,5 +0,0015 (IC +0,0006 / +0,0025) / +0,0006, 6/33 campionati: troppo rumore per campionato |
| 28/10 | Livello gol di tutti i campionati insieme dagli ultimi 30 giorni (W scelto sul periodo scelta) | Over 1,5 · 2,5 · 3,5, 1X2 | no, ma da riprovare | O2,5 +0,0002 (IC −0,0007 / +0,0011) / −0,0015 (IC −0,0024 / −0,0007), 25/33 campionati in holdout; O1,5 −0,0002 / −0,0015; 1X2 0,0000 / +0,0003. L'effetto c'è solo nella stagione 2026 (−0,0043): da settembre O2,5 app 51,3 · riallineato 56,2 · reale 56,7. Verifica non significativa → non si tocca; si ripete al checkpoint del 7/12 |
| 28/10 | 1xBet prezza il 1° tempo dei corner come frazione fissa del totale? (archivio, 1.052 partite) | corner 1°T | sì, quasi fissa | rapporto 1°T/partita 0,493, deviazione 0,008 (0,005 nello stesso campionato); non segue l'indice di 1° tempo delle squadre (+0,05). Ma su 396 partite con il risultato la linea equilibrata del 1°T è calibrata: Over 49,8 senza margine contro 48,5 reale (−1,3 ±4,9) e l'indice delle squadre non prevede la quota reale (−0,06): nessun vantaggio dimostrabile |

## Studi sull'archivio reale delle quote 1xBet (regola dei 100 giorni)
Stessa regola per tutti: si decide solo con almeno 100 giorni di archivio (primi due terzi solo da guardare, ultimo terzo verifica);
checkpoint di sola lettura il 7/12/2026 (~60 giorni), decisione il 18/1/2027 (~100 giorni). Sempre la probabilità corretta per esito.

| Data | Ipotesi | Strumento | Stato |
|---|---|---|---|
| 25/10 | Quota 2 / Quota 3: metodo di scelta della combinazione del giorno | `tools/quota23.py` | in raccolta |
| 26/10 | Gestione del capitale: Kelly 1/8 e 1/4 (tetto 3% per giocata) e fasce di Grado/valore contro puntata fissa 1%/2%, su singole e migliore Quota 2 / Quota 3 del giorno, per perimetro (solo statistiche, statistiche + formazioni falli, tutti, solo gol; dal 26/10 anche solo 1X2 statistiche, senza Over/Under cartellini), tetto giornaliero 10% della cassa, astensione senza valore atteso positivo. Entra nell'app (Gioco responsabile / Diario, cassa solo nel localStorage) solo se nella verifica ha rendimento corretto per il rischio più alto della fissa 1% (IC 95% bootstrap settimanale sopra zero) o calo massimo più basso a rendimento non inferiore, con yield non peggiore del −margine 1xBet | `tools/bankroll.py` | in raccolta |

| 27/10 | Radar Mercato: riuscita minima 65% di base, evidenza dal 70% (Over/Under 1xBet di tiri, tiri in porta, corner, falli, cartellini). Archivio 9-27/10: senza soglia presa 52% (dich. 61%), −4,0%; dal 65% +2,0% e +11,3% nelle due metà; dal 70% +20% e +34% (campioni piccoli, soglie viste sui dati). Si giudica SOLO sulle partite dal 28/10: resta se dal 65% il rendimento non è peggiore del −margine 1xBet e la presa è entro ±5 punti dal dichiarato | `tools/radar_mercato.js` (ogni lunedì) | in raccolta |
## In coda
- 1° tempo con falli, fuorigioco e cartellini per tempo (API-Football li dà in statistics_1h, il ramo tempi finora salvava solo corner, tiri, tiri in porta) e ripetizione su tiri e corner con più stagioni di verifica.
- Infortunati e squalificati (API-Football, archivio con l'ora di registrazione dal 28/10/2026): da testare con `tools/harness.py` quando l'archivio avrà qualche mese (solo segnalazioni viste prima del fischio).
- Arbitro designato / formazione nota come fattori del Grado (si registrano da oggi: provabili tra qualche mese).
- Formazioni su tiri e fuorigioco: da riprovare con più partite.
- Meteo e campo (sintetico, dimensioni): servono dati nuovi.
