
## Distanza tra atteso di Prevista e linea del book (8/11/2026, da un post di un "software" esterno)
Ipotesi: quando l'atteso è molto sopra la linea Over/Under, l'Over rende (e a specchio l'Under). Archivio 1xBet 9/10 → 8/11 (31 giorni,
5.738 linee), previsioni walk-forward (tools/radar_mercato.js → tools/p2/test_distanza_linea.py).
- Prevista non si allontana quasi mai di 2-3 unità dalla linea: corner totali 0 casi oltre +2, corner squadra 3 su 2.634. La linea del book
  e l'atteso di Prevista sbagliano quasi uguale (corner totali: errore medio 2,77 contro 2,74; corner squadra 2,15 contro 2,12).
- Corner totali Over con atteso tra +1 e +2: 51 giocate, +5,7% ±23 · corner squadra +1/+2: 105, +2,0% ±16 → nulla di significativo.
- Corner casa + ospite entrambi oltre la linea di 1,5: nessuna partita.
- Unico spunto: cartellini Over con atteso ≥ 125% della linea, 34 giocate, +24% ±25 (metà 1 +13%, metà 2 +43%): campione troppo piccolo,
  da rileggere al punto del 7/12. Non adottato.

## Nazionali · fattibilità (8/11/2026, richiesta di Denny) · tools/p2/nazionali.py
Dati API-Football 2020 → oggi: 3.338 partite giocate nelle competizioni ufficiali (amichevoli escluse), 2.675 con statistiche complete
(Mondiale, Europeo, Nations League, Copa América, Coppa d'Africa e qualificazioni UEFA e CONMEBOL complete; AFC 244/455, CONCACAF 151/218, CAF 31/414).
Modello semplice per squadra (fatti/subiti con decadimento di 18 mesi, ritirato verso la media) contro la media di tutte le partite precedenti, walk-forward:
- Chi ne fa di più (Brier contro 0,250, scelta · verifica · holdout): corner −0,051 · −0,039 · −0,048; tiri −0,080 · −0,055 · −0,073;
  tiri in porta −0,072 · −0,061 · −0,066; falli −0,014 · −0,024 · −0,018; cartellini −0,015 · −0,011 · −0,016 → tutti significativi in ogni periodo.
  Fuorigioco: verifica −0,004 non significativo → non passa.
- Totale della partita (errore medio contro la media): tiri in porta −0,06 · −0,14 · −0,11 (passa); tiri −0,20 · −0,37 · −0,16 (passa); falli −0,62 · −0,28 · −0,10 (passa);
  corner +0,02 · −0,06 · +0,00 (non passa); cartellini −0,01 · −0,07 · +0,10 significativo al contrario in holdout (non passa); fuorigioco non passa.
- Quote via API-Football sulle prossime partite di nazionali: 10 partite, 10 book; corner presenti (O/U, 1X2, per squadra, 1° tempo), cartellini assenti.
Nota: il confronto è con la media, non con il mercato; il valore contro le quote resta da misurare (nessun archivio di quote per le nazionali).
