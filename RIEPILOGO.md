# Laboratorio di Prevista · 2026-11-21

Regola: in verifica (2024-25) miglioramento con intervallo al 99% sotto zero, stesso segno in holdout (da luglio 2025, solo confronto), maggioranza dei campionati. Riferimento: previsioni dell'app con la sola costante stimata nel periodo scelta. Negativo = meglio.

## F1 · Derby (falli) — INTEGRATA NELL'APP (provata il 2026-11-18)
derby (lista di derby.py): un coefficiente sui falli di entrambe le squadre

coefficienti (stima, errore standard): costante +0.0003 ± 0.0020, derby +0.0572 ± 0.0114

- verosimiglianza per squadra · verifica -0.00178 (-0.033%) [99%: -0.00311 / -0.00022] · campionati 19/31 · holdout -0.00152 (-0.028%) [99%: -0.00276 / -0.00040] · campionati 21/31
- 1X2 · verifica +0.00004 (+0.004%) [99%: -0.00002 / +0.00009] · campionati 14/31 · holdout -0.00002 (-0.002%) [99%: -0.00006 / +0.00004] · campionati 17/31
- Over/Under sulla linea vicina · verifica -0.00058 (-0.083%) [99%: -0.00142 / +0.00028] · campionati 22/31 · holdout -0.00021 (-0.030%) [99%: -0.00091 / +0.00045] · campionati 17/31

## F2 · Differenza di forza (falli) — SCARTATA (provata il 2026-11-18)
λ gol squadra − λ gol avversaria: la sfavorita fa più falli?

coefficienti (stima, errore standard): costante +0.0019 ± 0.0020, forza -0.0045 ± 0.0029

- verosimiglianza per squadra · verifica -0.00014 (-0.003%) [99%: -0.00056 / +0.00032] · campionati 14/31 · holdout +0.00006 (+0.001%) [99%: -0.00027 / +0.00042] · campionati 15/31
- 1X2 · verifica -0.00023 (-0.027%) [99%: -0.00056 / +0.00009] · campionati 17/31 · holdout +0.00001 (+0.001%) [99%: -0.00021 / +0.00025] · campionati 15/31
- Over/Under sulla linea vicina · verifica -0.00003 (-0.004%) [99%: -0.00025 / +0.00018] · campionati 14/31 · holdout +0.00002 (+0.002%) [99%: -0.00018 / +0.00021] · campionati 16/31

## F3 · Partita che conta (falli) — SCARTATA (provata il 2026-11-18)
classifica prima della partita: entrambe nelle ultime 4, entrambe nelle prime 4, distanza ≤ 3 punti (dalla 10ª giornata), ultime 6 giornate

coefficienti (stima, errore standard): costante +0.0047 ± 0.0023, salvezza +0.0441 ± 0.0122, vertice +0.0394 ± 0.0113, vicine +0.0005 ± 0.0054, fine -0.0309 ± 0.0053

- verosimiglianza per squadra · verifica -0.00158 (-0.030%) [99%: -0.00332 / +0.00017] · campionati 21/31 · holdout -0.00148 (-0.028%) [99%: -0.00321 / +0.00001] · campionati 20/31
- 1X2 · verifica -0.00000 (-0.000%) [99%: -0.00009 / +0.00011] · campionati 15/31 · holdout -0.00003 (-0.003%) [99%: -0.00009 / +0.00003] · campionati 19/31
- Over/Under sulla linea vicina · verifica -0.00051 (-0.073%) [99%: -0.00176 / +0.00084] · campionati 16/31 · holdout +0.00053 (+0.076%) [99%: -0.00037 / +0.00137] · campionati 12/31

## F4 · Riposo (falli) — SCARTATA (provata il 2026-11-18)
ln(giorni dall'ultima partita / 7), campionato + coppe europee, squadra e avversaria

coefficienti (stima, errore standard): costante +0.0023 ± 0.0020, riposo squadra +0.0036 ± 0.0066, riposo avversaria +0.0011 ± 0.0066

- verosimiglianza per squadra · verifica -0.00013 (-0.002%) [99%: -0.00043 / +0.00013] · campionati 19/31 · holdout -0.00022 (-0.004%) [99%: -0.00060 / +0.00010] · campionati 18/31
- 1X2 · verifica +0.00001 (+0.002%) [99%: -0.00003 / +0.00006] · campionati 12/31 · holdout -0.00002 (-0.003%) [99%: -0.00006 / +0.00001] · campionati 19/31
- Over/Under sulla linea vicina · verifica -0.00074 (-0.107%) [99%: -0.00144 / +0.00016] · campionati 25/31 · holdout +0.00069 (+0.100%) [99%: +0.00016 / +0.00117] · campionati 9/31

## F5 · Avvio di stagione (falli) — SCARTATA (provata il 2026-11-18)
prime 5 giornate della stagione

coefficienti (stima, errore standard): costante -0.0029 ± 0.0021, avvio +0.0316 ± 0.0054

- verosimiglianza per squadra · verifica -0.00068 (-0.013%) [99%: -0.00225 / +0.00078] · campionati 16/31 · holdout -0.00159 (-0.030%) [99%: -0.00391 / +0.00031] · campionati 21/31
- 1X2 · verifica -0.00002 (-0.002%) [99%: -0.00007 / +0.00003] · campionati 18/31 · holdout +0.00005 (+0.006%) [99%: -0.00000 / +0.00011] · campionati 14/31
- Over/Under sulla linea vicina · verifica -0.00105 (-0.152%) [99%: -0.00258 / +0.00073] · campionati 21/31 · holdout -0.00015 (-0.022%) [99%: -0.00122 / +0.00091] · campionati 19/31

## F6 · Tetto dell'arbitro a +8% (falli) — IN OMBRA (dal 2026-11-18)
fattore arbitro sui falli con tetto +8% invece di +4% (verso il basso nessun limite, come oggi)

Test del 18/11/2026 (tools/p2/falli_tetto.py, 34.254 partite, produzione + derby): rispetto al +4% log-loss per squadra −0,0009 sviluppo, −0,0008 verifica, −0,0005 holdout; il migliore nello sviluppo (+10%) non è significativo in verifica (intervallo al 95% −0,0017 / +0,0001, 16/31 campionati). In ombra per decisione di Denny: si guarda se sulle partite nuove continua ad andare meglio.

In coda: nessuna (servono idee nuove)

## In ombra (partite nuove, negativo = idea meglio)
- F1: integrata nell'app, prova in ombra chiusa (593 partite registrate)
- F6: 31 partite (6 in cui l'idea cambia la previsione) · idea − riferimento -0.00400 ± 0.00857 · idea − app -0.00400 · sulle cambiate +0.0089


## Corner V2 (prova in ombra, dettaglio in CORNER_V2.md)
- Corner V2 in ombra: 795 partite registrate, 31 con risultato · log-loss squadra V2 − app +0.00839, 1X2 -0.00342


## Cartellini V2 (prova in ombra, dettaglio in CARTELLINI_V2.md)
- Cartellini V2 in ombra: registrate 3522, concluse 25, utilizzabili 23 (totali) / 23 (per squadra)
