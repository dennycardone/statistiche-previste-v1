
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

## Ricerca a 360 gradi (9/11/2026, richiesta di Denny) · tools/p2/ricerca360.py e ricerca360b.py
Archivio quote 5/10 → 9/11 (2.072 partite; Pinnacle su corner e cartellini; multi-book solo dal 6/11), 56 regole provate.
1. Sharp contro soft: Pinnacle più preciso di 1xBet solo sui cartellini (Brier 0,235 contro 0,242 sulle stesse linee); sui corner identici.
   Cartellini 1xBet con quota > equa di Pinnacle +3%: 154 giocate, +21,5% ±13 (p 0,001), metà +12% / +31%; con abbinamento diretto dei
   gialli/rossi 107 giocate +16,9% ±16; rosso contato 2 → +13,6%; solo gialli +18,6%. Corner O/U e tiri contro Pinnacle: nulla (−3% … −9%).
   Quota più alta tra i book (dal 6/11): cartellini +26% su 88, troppo pochi giorni.
2. Struttura: alla cieca tutte le linee 1xBet perdono il margine (intere, x,5, quarti: −5% … −16%). Asiatico corner 1xBet contro Pinnacle:
   +13% su 516 ma con giocate opposte sulla stessa partita (falsa precisione); una giocata per partita +11% ±14, 16 campionati su 31 → non provato.
3. 1° tempo corner: 1xBet usa una frazione fissa (0,494 ± 0,009); valore con la frazione reale del campionato +2,9% su 3.568, nullo.
4. Formazioni: 1xBet non quota più i falli 1X2 dal 24/10 → non misurabile.
5. Studio del sistema (lunedì 9/11): prima metà +14,4%, seconda +4,4% (non significativo); Under cartellini +17,4% → +1,5%; in avanti dal 4/11
   (5 giorni) Under cartellini −13,6% su 33, Operatività −9,1% su 61. Under cartellini con il rosso contato 2: −5 punti circa.
Esito: nessuna regola provata oltre il caso tenendo conto dei 56 test. Candidata più forte: sharp sui cartellini; seguita in avanti dal 10/11
(sezione 7 dello studio del lunedì); rilettura al 7/12.

## Audit completo di calibrazione (9/11/2026, richiesta di Denny) · tools/calib_full.js + calib_full.py, workflow calibrazione_completa.yml
36.031 partite dal 1/7/2023, probabilità dell'app con i soli dati precedenti; scelta 2023-24, verifica 2024-25, holdout 2025-26 e ultimi 120 giorni.
Già calibrati (scarto entro ±1,5 punti in verifica e holdout, ECE ≤ 1,6): 1X2 di corner, falli, fuorigioco, tiri in porta; tutti gli Over/Under di
corner (totali e squadra, code comprese), fuorigioco, cartellini (solo holdout: previsioni dei cartellini da ottobre 2025); 1X2 gol, doppia chance.
Scarti: pareggio gol sottostimato +1,5 (12 sovrastimato −1,5) in tutti i periodi; Over gol e Gol/No gol +2,2…+3,5 in holdout e +3,6…+5,3 negli
ultimi 120 giorni (in verifica a posto); Over tiri totali +3,7 in holdout e +8,5 negli ultimi 120 giorni, tiri squadra +5,2, tiri in porta +3,3,
falli +1,8 (code: lo scarto cresce sulle linee alte) → livello medio che cresce più in fretta del modello nella stagione in corso, non errore di forma.
Ricalibrazione Platt walk-forward (con e senza la distanza dalla linea): passa SOLO l'1X2 dei tiri (casa: verifica −0,00061 [−0,00101, −0,00018],
holdout −0,00001, 66% campionati; ospite: −0,00052, holdout −0,00003, 69%) → applicato (CAL_1X2 nell'app, effetto ±1-2 punti agli estremi).
Over/Under gol, Gol/No gol, Over tiri: migliorano solo in holdout (verifica non significativa) → non adottati; da riprovare al 7/12 con un
riallineamento del livello sugli ultimi mesi.
1° tempo (statistiche per tempo dal 2024-25): corner 1° tempo Over/Under sottostimati (+1,3 verifica, +2,3 holdout), Platt passa (100% campionati)
ma l'app non mostra probabilità Over/Under del 1° tempo → nulla da applicare ora; cartellini 1° tempo +7,1 (solo holdout, Poisson troppo stretta);
fuorigioco 1° tempo +2,4/+2,8 con Platt al limite (verifica [−0,00447, +0,00004]) → non adottato; in scheda resta il valore atteso con la quota
reale del 1° tempo del campionato (pubblicato il 9/11).


## 10/11/2026 · Riallineo del livello (gol, tiri, tiri in porta, falli, corner) — NON adottato
Prova: fattore reale/atteso sugli ultimi 60/120/240 giorni, globale o per campionato, solo con i giorni precedenti (tools/calib_livello.py, 8 shard).
Nessuna statistica passa la regola: in verifica il miglioramento non è significativo per nessuna.
- Tiri: verifica −0,00033 [−0,00138, +0,00062] (non significativo) · holdout −0,00484 [−0,00778, −0,00215] · ultimi 120 giorni −0,01591, scarto Over +9,1 → −1,3 · campionati migliorati 84% · fattore oggi 1,053.
- Gol: verifica +0,00018 (peggiora) · holdout −0,00133 · 120 giorni −0,00444, scarto Over +4,7 → +1,2 · fattore oggi 1,086.
- Tiri in porta: verifica +0,00026 · holdout −0,00107 · 120 giorni −0,00360 · fattore oggi 1,043.
- Falli: verifica −0,00020 (non significativo) · holdout −0,00184 · fattore oggi 1,011. Corner (controllo): nulla, fattore 1,03.
Lettura: la sottostima degli Over è reale ma recente (holdout e ultimi 120 giorni), nel periodo di verifica non c'era: la regola non la lascia passare. Da rileggere al 7/12 con un mese in più (i Tiri sono il candidato).

## 10/11/2026 · Freno 1X2 corner oltre quota 2,50 e quota equa Pinnacle sui cartellini
- Operatività: gli 1X2 corner oltre 2,50 restano visibili "in osservazione", senza peso (registro 3–8/11: 34 giocate, 9 prese, −39,8% a puntata fissa). Vengono refertati a parte nel registro.
- Cartellini: linee Pinnacle (quota senza margine) in linee.json "pk" con il massimo degli altri book; scheda partita e blocco 5 di Operatività. Solo indicazione, in verifica dal 10/11.


## 14/11/2026 · Cartellini delle nazionali in osservazione (senza peso)
Audit del 13/11: sui cartellini il modello delle nazionali sbaglia più della media semplice (errore totale 1,779 contro 1,705, α 0,005).
Registro 12-13/11: 11 giocate, 3 prese contro 6,0 attese, −50,6% a puntata fissa, −2,91% della cassa (club nello stesso periodo +0,41%).
Da Denny (14/11): restano visibili e refertati in "In osservazione", fuori da singole, pesi e combinate. Tornano solo se il modello batte la media.
