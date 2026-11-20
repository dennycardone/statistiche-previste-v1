
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

## 14/11/2026 · Player props (giocatore singolo, solo titolari, Top 5) — ricognizione e primo test
Script: tools/props/copertura.py, tools/props/sonda_quote.py (workflow diagnosi, input "giocatori"), tools/props/test_props.py, tools/props/test_props_cal.py.
**Dati (archivio formazioni, nessuna chiamata nuova).** Top 5: 7.370 partite, 100% con statistiche dei giocatori, 99,6% con 11 titolari. Per giocatore e partita:
minuti, ruolo, titolare/subentrato, gol, assist, gialli, rossi, falli fatti e subiti, tiri, tiri in porta, fuorigioco, contrasti, intercetti, duelli, dribbling, passaggi, voto.
Somma dei giocatori contro squadra: tiri in porta 100% identici, falli 99,9%; tiri −26,6% nei Top 5 e −26,2% nel resto, perché i "tiri" del giocatore
di API-Football NON contano i tiri respinti (somma = tiri − respinti nel 99,6% delle squadre). Non è un problema di qualità dei Top 5: è la definizione.
**Quote.** Mercati giocatore solo su Bet365 (partite del 20-24/11): Player Shots, Player Shots On Target, marcatori. Falli commessi (266/271/277)
e Ammonito (102/251) esistono nel catalogo ma non erano quotati sulle partite controllate (6 giorni prima): da ricontrollare il giorno della partita.
Champions (Bodø/Glimt–LASK, 24/11): nessun mercato giocatore per ora.
**Test (121.614 titolari, scelta fino a 6/2024, verifica 2024-25, holdout da 7/2025).** Parametri scelti nel periodo scelta: DP 0,97 e K 5 (tiri, tiri in porta,
falli), DP 0,99 e K 20 (cartellini); α 0,1 / 0,2 / 0,1 / 0.
- A contro riferimento di ruolo: passa su tutti e 7 i mercati, 5/5 campionati (log-loss da −0,005 sull'ammonito a −0,029 su tiri Over 1,5 e falli Over 1,5).
- B contro A: passa su tutti e 7 (verifica / holdout): TP 0,5 −0,0032/−0,0034 · TP 1,5 −0,0019/−0,0013 · Tiri 1,5 −0,0050/−0,0041 · Tiri 2,5 −0,0031/−0,0024 ·
  Falli 0,5 −0,0011/−0,0023 · Falli 1,5 −0,0012/−0,0025 · Ammonito −0,0007/−0,0006 (verifica 3/5 campionati, il più debole).
- Calibrazione: B sovrastima del 5-15% (gli ingressi dalla panchina gonfiano i valori ogni 90'). Scala per statistica stimata nel periodo scelta: tiri ×0,93,
  tiri in porta ×0,94, falli ×0,97 → passa su tiri 1,5/2,5, tiri in porta 0,5/1,5, falli 1,5; neutro su falli 0,5; cartellini ×1,01 non passa
  (holdout prevista 16,1% contro 14,8% reale: i cartellini sono calati nelle ultime stagioni).
- Bonus assenze: senza il tiratore principale, gli altri centrocampisti e attaccanti titolari tirano +1,5% rispetto all'atteso (IC −0,1% / +3,2%), tiri in porta
  +1,6% (IC −1,1% / +4,0%): non misurabile, non si usa.
Esito: modello da usare = B con la scala (tiri, tiri in porta, falli); ammonito = B senza scala, con la nota della sovrastima recente. Interfaccia: non ancora toccata.

## 14/11/2026 (sera) · Player props: falli subiti e anteprima della tab Giocatori
Falli subiti dei giocatori contro falli commessi dall'avversaria (Top 5): −4,9% in totale, identici nel 57% delle squadre, entro 1 fallo nell'88%
(non allineati al 100% come tiri in porta e falli commessi: API-Football non attribuisce a un giocatore circa 1 fallo subito su 20).
Harness (Modello B = A × falli attesi dell'AVVERSARIA da Prevista / media abituale dei falli attesi degli avversari della squadra):
- A contro riferimento di ruolo: Over 0,5 −0,0419/−0,0444 · Over 1,5 −0,0426/−0,0431 · Over 2,5 −0,0287/−0,0267 (verifica/holdout, 5/5 campionati).
- B contro A: Over 0,5 −0,0019/−0,0020 (5/5) · Over 1,5 −0,0023/−0,0029 (5/5) · Over 2,5 −0,0014/−0,0020 (4/5). Passa.
- Scala 0,96 (scelta): passa su tutte e tre le linee; holdout dopo la scala: 53,2% previsto contro 52,8% reale (Over 0,5), 8,8% contro 8,4% (Over 2,5).
Tab Giocatori (anteprima, ramo anteprima-giocatori): tiri in porta 0,5/1,5, falli commessi 0,5/1,5, falli subiti 0,5/1,5/2,5, ammonito Sì
(tiri totali esclusi: API-Football senza i tiri respinti, i book li contano). Dati: tools/props/giocatori.py ogni sera (lineups.yml → ramo valori → data/giocatori.json).
Archivio formazioni: la stagione in corso restava indietro (le partite già nel ramo storico non entravano nell'elenco): corretto il 14/11, Top 5 e Champions
completi con i nomi dei giocatori (235 richieste fuori dalla riserva dell'app).

## 15/11/2026 · Regola della lettura (Denny)
"Tutto deve basarsi sulla lettura della partita": in Operatività (singole, Quota 2/3, osservazione) e nel Mercato del Radar si propone solo il
segno che Prevista dà più probabile (1X2) o il lato sopra il 50% (Over/Under); la quota decide solo se conviene. La controtendenza resta (è
Prevista che legge la partita al contrario del book). Caso: Finlandia–San Marino, corner 2 a 20,25 (Prevista 1 al 77%) in osservazione.
Ultimi 7 giorni: le singole erano già dalla parte della lettura 65 volte su 66 (l'unica contro: cartellini, persa); le giocate contro la lettura
stavano quasi tutte in osservazione (1X2 corner a quota lunga). Non è un test dell'harness: è una regola di coerenza decisa da Denny.
- 15/11 (Denny): anche il blocco 5 (cartellini sopra la quota equa di Pinnacle) e il riquadro Pinnacle della scheda partita seguono la lettura:
  solo le linee che Prevista dà sopra il 50% (es. Tenerife–Ceuta, attesi 6,52: niente più Under 4,5/5,5). Lo studio "sharp" in sistema.py
  (sezione 7) resta com'è, solo prezzo, come confronto.
- 15/11 (check-up "tutto sulla lettura", Denny): corretti gli ultimi punti che sceglievano per valore: Fuorigioco 1X2 della scheda (evidenziava il
  segno col valore più alto), "Quota minima da cercare" (solo il segno più probabile, anche quando le formazioni alzano l'altro), Segnali Over 3,5
  gol (soglia da 40% a 50%), studio settimanale del Mercato (tools/radar_mercato.js: il lato della lettura, come l'app). Già sulla lettura:
  Grado, Segnali, Operatività, Mercato, Pinnacle, Giocatori (solo probabilità).

## 15/11/2026 · Cartellini: livello non passa → Under in osservazione
Studio del livello (tools/calib_livello.py, run del 15/11): Cartellini non passa (fattore oggi 1,02; holdout log-loss +0,00051 [−0,00063, +0,00184],
120 giorni +0,00211, campionati migliorati 42%). Controllo mese per mese su extra.json: livello allineato (reale/atteso 0,91-1,04 da agosto).
La perdita viene dalla scelta per valore (Under dove il modello si stacca di più dal book). Da Denny (15/11): cartellini Under in osservazione,
senza peso, visibili e refertati. Over restano (club 7 giocate, 4 prese, attese 4,0). Da rileggere al 7/12 e al 18/1.

## 15/11/2026 · Basket (API-Basketball Pro fino al 15/12): archivio e primo modello
Archivio (ramo basket, tools/basket/archivio.py, workflow basket.yml ogni mattina): NBA, Eurolega, Eurocup, Serie A, ACB, BBL, LNB dal 2019,
~23.000 partite finite con punteggi per quarto, statistiche di squadra (tiri da 2/3, liberi, rimbalzi, assist, recuperi, stoppate, perse, falli)
e dei giocatori (minuti, punti, tiri, rimbalzi, assist), 1.946 richieste. Quote: tools/basket/quote.py ogni 3 ore, 9 book (Pinnacle e Bet365
compresi), apertura e chiusura, cifrate sul ramo basket-quote.
Modello (tools/basket/modello.py): ritmo (possessi) × attacco/difesa ogni 100 possessi (media mobile DP 0,97, K 6 partite verso il campionato)
+ vantaggio del campo; scarto e totale Normali con σ robuste per campionato (scarto 11,5-13,3, totale 16,0-18,3). Tolte 609 partite (All-Star,
interrotte, a tavolino, senza quarti). Log-loss contro la media del campionato (verifica / holdout): vittoria −0,067 / −0,070, totale −0,030 / −0,029.
Vittoria calibrata nell'holdout (es. 55% → 59%, 65% → 65%, 75% → 75%, 84% → 83%). Contro le quote reali: non ancora (le quote si accumulano da oggi).
- 15/11 basket: soglia All-Star resa relativa (metà della mediana delle partite delle squadre nella stagione): con 15 fisso la stagione in corso
  dei campionati europei restava fuori dal modello. Adeguamento più rapido del livello del campionato (0,995/0,99/0,98): NON passa nel periodo
  scelta (resta 0,998). Scarto reale − previsto sul totale 2026-27: ACB +7,6, ITA +2,6, LNB +1,9, BBL +1,4, EL +1,3, EC −1,8, NBA −1,4.

## 15/11/2026 · Basket: ricognizione giocatori e Lettura arricchita (tools/basket/test_lettura.py, test_giocatori.py, sonda_props.py)
Archivio: statistiche di squadra e giocatori già scaricate per tutte le partite (90-100% per stagione; BBL e LNB 2019-20 senza squadre). Backfill: 0 richieste.
Giocatori (API): minuti, punti, tiri da 2, da 3, liberi, rimbalzi totali, assist. Niente falli, recuperi, stoppate, palle perse, rimbalzi off/dif.
Squadre (API): dall'8/1/2026 il formato è cambiato: tiri dal campo = solo da 2, rimbalzi offensivi/difensivi e falli = vuoti (prima c'erano).
  Effetto: dal gennaio 2026 i possessi del modello usano il ripiego (punti / rendimento). Da sistemare (possessi con tiri da 2 + da 3 e rimbalzi offensivi stimati).
NBA: la preseason sta nello stesso file della stagione; nei test esclusa (bk_lib.NBA_START). Nel modello pubblicato è ancora dentro.
Quote (feed API-Basketball): moltissimi mercati di 1° tempo e quarti (O/U, handicap, 1X2, totali di squadra); nessun mercato rimbalzi di squadra.
  Giocatori: solo NBA, "Player Points Milestones" (2 book) e "Player Points and Assists" (1); niente rimbalzi, assist, doppia doppia. Eurolega: nessuno.
Lettura (19.868 partite):
- Riposo: NBA back-to-back −2,2 punti di scarto (scelta); migliora la verifica (z −3,2) ma in holdout peggiora → non adottato. In Europa il back-to-back quasi non esiste (18 casi).
- Chiavi tattiche: solo la quota rimbalzi (e % rimbalzi offensivi) è legata allo scarto oltre attacco/difesa (corr. 0,02 / 0,06 / 0,07). Correzione dello scarto:
  verifica z −1,8 (6/7), holdout z −2,4 (6/7) → non abbastanza in verifica, in osservazione. Assist, tiro da 3, liberi, falli, palle perse: niente.
- 1° tempo con la quota propria della squadra: verifica z −4,8 ma 3/7 campionati, holdout z −2,9 5/7 → non adottato. 1° quarto: niente.
- Rimbalzi totali e chi ne prende di più: il modello di squadra batte nettamente la media del campionato (z −15, 7/7 in verifica e holdout), ma i book del feed non li quotano: solo informazione.
Giocatori (287.773 giocatori-partita, ≥15 minuti attesi, quintetto noto come nel calcio):
- A batte la media semplice della stagione (log-loss −0,02, z −10/−17). φ: punti 2,5, rimbalzi 1,6, assist 1,6.
- B (α punti 0,5, rimbalzi 1,25, assist 0,75): punti e assist passano (verifica z −2,5 / −3,6, holdout z −10,6 / −10,0, maggioranza dei campionati); rimbalzi no (verifica z −1,5).
- Assenze (β punti 0,2, rimbalzi 0,2, assist 0,4): passano su tutte e tre. Grezzo: se manca uno dei primi 2 della squadra, i titolari presenti fanno +1,0 punti, +0,3 rimbalzi, +0,3 assist sopra B.
- Calibrazione buona sui punti; rimbalzi e assist sopravvalutati nelle probabilità basse (0,15 prevista, 0,10 uscita): φ da legare alla media.
- Doppia doppia con voci indipendenti calibrata (holdout 5,9% prevista, 5,3% uscita); legarle ai minuti peggiora. Tripla doppia 0,26% / 0,29%.
- Senza quintetto ufficiale (API-Basketball non lo passa prima della partita): minuti medi + assenze = chi mancava l'ultima partita (passa su punti e assist, rimbalzi solo verifica).
  Costo di non sapere il quintetto: log-loss +0,020 sui punti (quanto il salto dalla media semplice al modello A).

## 15/11/2026 · Basket: possessi, giocatori online, falli di squadra
- Possessi (test_possessi.py): formato nuovo ricostruito (tiri da 2 + da 3, rimbalzi offensivi stimati) + statistiche rotte scartate (70-160 punti/100 possessi,
  possessi delle due squadre entro il 12%). Errore sul totale in verifica 15,03 → 14,41; guadagno in Serie A ed Eurocup (dati rotti), NBA/EL invariati, LNB/BBL di poco peggio.
  Adottato come correzione di dati (OK di Denny). Preseason NBA: toglierla peggiora (verifica z +3,3, holdout z +2,4) → resta.
- Giocatori online (giocatori_pub.py): versione automatica; distribuzioni sulle soglie fisse: punti e P+A NB φ 3, rimbalzi e assist NB2 r 13 (coda bassa
  0,16/0,14 invece di 0,15/0,10); doppia/tripla doppia ricalibrate (verifica 6,56%/6,54%, holdout 6,0%/5,3%). "Player Runs" di Betano = rimbalzi (corr 0,96, scarto 0,6).
  Segnali giocatori: 72-80% (equa ≥ 1,25) o con quota del book. NBA: primo dei 2 realizzatori non quotato con ≥4 compagni quotati → "non quotato" (non verificabile sull'harness).
- Falli di squadra (test_falli.py, falli API-Basketball fino a gennaio 2026): modello (DP 0,90, K 0,5) contro media del campionato: falli totali verifica z −22,
  holdout z −14, chi ne fa di più z −13 / −7, 7/7 campionati in tutti. Informativi nella Lettura (nessun mercato nel feed). Dati correnti solo NBA (ESPN) ed
  EL/EC (sito Eurolega; falli identici ad API-Basketball 110/111; rimbalzi offensivi contati diversamente, non usati). Archivio: ramo basket-falli, basket_falli.yml.

## 16/11/2026 · Basket: audit di calibrazione voce per voce (tools/basket/audit_calibrazione.py, test_giocatori.py sezioni audit e doppia isotonica)
Probabilità esposte: Vincente, Totale e Handicap (lato della lettura), Grado (uscite), giocatori (soglie punti/rimbalzi/assist, P+A, doppia/tripla).
1° tempo, 1° quarto, punti di squadra, rimbalzi, falli, assist: solo numeri attesi, nessuna percentuale.
- Vincente: sottostimato di 1-1,6 punti in tutti i periodi (holdout 84,7 dichiarato / 86,2 uscito sopra l'80%). Platt (b 1,1): verifica z −1,7 → non passa.
- Handicap: ECE 0,3-0,6 punti, ben calibrato. Totale: ECE 1,4 punti in verifica/holdout: Under sopravvalutato (64,3 / 61-62), Over sottovalutato (66,6 / 68)
  perché i totali europei recenti escono 2-4 punti sopra l'atteso. Correzione della distorsione (media mobile dei residui): verifica non significativa → non passa.
- σ per campionato × fattore (scelto nel periodo scelta, 0,95-1,05): vittoria migliora (verifica z −2,3) ma l'handicap peggiora in holdout (z +3,9, 0/7) → non adottato.
- Partite equilibrate e supplementari (4,8%): Over 66,6 / 68,3 contro 66,6 / 67,7 nelle altre, effetto piccolo.
- Grado (tabelle sulla verifica, prova sull'holdout): A 73,5 / 72,9, A+ 84,3 / 82,8; Vincente A 74,7 / 72,2; Handicap A 72,8 / 70,2.
- Giocatori (holdout): punti ECE 0,32, rimbalzi 0,44, assist 0,41, P+A 0,15; Segnali 72-80%: 75,9 dichiarato / 75,8 uscito (15.517).
- Doppia doppia: sopra il 50% la ricalibrazione logit sottostima (holdout 58,7 / 67,2); isotonica migliora il log-loss (verifica z −4,1, 5/7; holdout z −1,3)
  ma sopravvaluta nella fascia Segnali (72-80: 74,5 / 58,1 su 93 casi) → non adottata, da rivedere con più dati.
Nessuna ricalibrazione in produzione.

## 16/11/2026 · Basket: triple, assist, palle perse attese (tools/basket/test_statistiche.py)
Fatte e concesse ogni 100 possessi (media mobile, K 3) × possessi attesi, contro la media del campionato × possessi attesi:
triple (DP 0,97) totale verifica z −22 7/7, holdout z −2,5 6/7; chi ne fa di più z −9 / −9 7/7. Assist (DP 0,95) totale z −29 / −19, chi ne fa di più z −13 / −14, 7/7.
Palle perse (DP 0,90) totale z −19 / −19, chi ne fa di più z −11 / −10, 7/7. Rimbalzi (riferimento) z −14 / −13. Adottate nella Lettura come numeri attesi.

## 16/11/2026 · Basket: statistiche e possessi in Radar, Segnali, Tendenze e Digiuni
- "Chi ne fa di più" (almeno 1 in più, il pari perde) per rimbalzi, assist, triple, palle perse, falli: probabilità da atteso casa − trasferta con σ dei residui per campionato stimata nel periodo scelta.
- Possessi sopra/sotto la media del campionato (media mobile dei possessi della lega prima della partita) con σ dal periodo scelta.
- Grado da tabelle storiche (verifica + holdout) per ogni voce, come vittoria/totale. Mercato escluso: nessuna quota nel feed per queste voci.
- Digiuni/Tendenze: elenco partite e Lettura calcolati una volta (prima andava in crash il telefono con tutti i campionati).
- 16/11 · Giocatori: abbinamento nomi book ↔ archivio in due passi (prima nome intero o cognome + iniziale, poi i ripieghi solo su voci libere con iniziale compatibile). Caso: le linee di Jaylen Brown (76ers) finivano anche su M. J. Brown (Nets) → "91% contro @1,93" era un errore di abbinamento, non un disaccordo col book. Etichetta "equa" → "vale".

## 16/11/2026 · Calcio: segnalazione dei cambi di allenatore
- Denny: con un allenatore nuovo cambia il gioco e le statistiche sono meno attendibili. Solo segnalazione (nessuna modifica al modello): API-Football /coachs per squadra (allenatori.yml, richieste solo da quelle che avanzano dopo la riserva), id squadra dai loghi del sito.
- 16/11: le date di /coachs sono sbagliate (Spalletti Juve "dal 1/9/2026", arrivato il 30/10/2025; Thioune Werder "dal 1/10/2026", arrivato a febbraio 2026): si usa l allenatore delle formazioni delle partite giocate (data esatta della prima partita, partite guidate).
- App: riquadro "Cambio di allenatore" in cima alla Lettura e "nuovo all." in Partite, finché il nuovo allenatore ha meno di 8 partite di campionato con la squadra.
- Da verificare più avanti con l'harness: le previsioni nelle prime 8 partite dopo un cambio sono davvero peggiori? Se sì, si può provare a pesare di più le partite recenti.
- 16/11 · Prima partita del nuovo allenatore segnalata in anticipo: (1) /coachs ogni giorno per chi gioca nei prossimi 3 giorni (ogni 6 ore entro 30 ore): un allenatore "in carica" mai visto nelle formazioni = nuovo annunciato; (2) al più tardi la formazione ufficiale (~1 ora prima) porta l'allenatore (hc/ac in formazioni.json) e l'app lo confronta con quello dell'ultima partita. Etichetta "1ª nuovo all." in Partite.

## 16/11/2026 · Basket: storico del Grado, possessi e palle perse solo nella Lettura
- Radar basket: giorni passati (fino a 7) con le partite giocate, la previsione fatta prima della partita, ✓/✗ e riepilogo del giorno (uscite contro attese), come il calcio. Mercato e Operatività solo per i giorni da giocare.
- Denny: possessi e palle perse tolti da Grado, Radar, Segnali, Tendenze e Digiuni; restano nella Lettura.
- 16/11 · Segnali basket: barra dei giorni come il Radar (7 giorni passati con storico ✓/✗ e riepilogo) al posto di Oggi/Domani/Giornata. Calcio: Radar con la stessa barra dei giorni (−7…+7) al posto di Oggi + tendina Data.

## 17/11/2026 · Gol attesi, fase 3 (Denny): backtest M0 / Dixon-Coles / livello / M1-M4 — NIENTE ANCORA NELL'APP
Replica Python di M0 identica all'app (36.654 partite, differenza massima 5e-7 = arrotondamento). Tabella walk-forward 50.475 partite (31 campionati,
da 9/2021): tools/p2/gol_feat.py; esperimenti gol_exp1_dc, gol_exp2_liv, gol_exp3_m14 (anche GOL_OFFSET=1), gol_exp4_forma, report gol_report.py.
- Dixon-Coles rho unico mensile (≈ −0,04): 1X2 log-loss −0,08% verifica, −0,06% holdout (significativi, 22/31 campionati), pareggi 24,6→25,6 (reali 26,3),
  ECE 1X2 1,54→1,06; risultato esatto −0,013% (verifica non significativa). Per campionato peggio (rumore); ristretto k=1000 ≈ unico.
- Riequilibrio livello: coefficienti stimati di nuovo, fattore per campionato, livello recente/stagione: migliorano solo nel periodo scelta,
  in verifica no (B peggiora +0,0008). Pendenza tra campionati scende (1,13→1,05) ma senza guadagno fuori campione → non passa.
- M1 (volume, conversione) non passa contro il precedente in verifica; M2 (conversione concessa) e M3 (forma) passano contro il precedente;
  M4 (campionato-stagione) non passa. Catena completa M4 contro M0: passa, ma 13 coefficienti.
- Candidato: M0 + forma dei tiri in porta (ultime 10, fatti dalla squadra e concessi dall'avversaria, 2 coefficienti) + Dixon-Coles unico:
  risultato esatto −0,091% verifica [significativo, 21/31], −0,094% holdout (20/31); 1X2 −0,22%/−0,19%; ECE 1X2 0,88/0,81; MAE invariato.
  Over 3+ in holdout resta sottostimato (51,4 contro 53,0): è il livello della stagione in corso, nessuna correzione del livello passa la verifica.

## 17/11/2026 · Gol attesi V2 — ADOTTATA (Denny), congelata, verifica prospettica dal 18/11/2026
V2 = M0 × e^(0,0084 + 6,4771·FS_squadra + 2,5448·FC_avversaria), K = 320, ultime 10 partite di campionato; Dixon-Coles con rho unico del mese
(gol_rho.yml il 1° del mese, ramo gol-rho → data/gol_rho.json; riserva: tabella GOL_RHO_M nel codice). Spegnimento: GV2.on = false (= M0 identico,
verificato su Serie A: 1.250 partite uguali); copia completa di M0 sul ramo backup-m0-gol (commit c13278e).
Controlli: app = Python su 36.437 partite (differenza ≤ 5e-7 su λ, rho, 1X2); M0 dentro la V2 identico al vecchio M0; corner, falli, tiri, tiri in porta,
fuorigioco identici (Serie A e MLS, 3.343 partite); precalc: cambiano solo gol, Over, Gol/No gol e i loro Confidence. Fattore V2/M0 0,85–1,30
(99,8% tra 0,89 e 1,21), λ massimo 4,40; VIF < 2 (FS correlata 0,47 con il rating strutturale: i coefficienti misurano solo l'informazione in più).
Coefficienti stimati sulla sola verifica (controllo, non usati): 5,32 e 2,80 (congelati 6,48 e 2,54). Holdout già visto = periodo di confronto.
Verifica prospettica: tools/p2/gol_prospettico.py (ogni domenica in ricerca.yml) e al checkpoint del 7/12.

## 18/11/2026 · Laboratorio automatico (Denny: "un meccanismo che testi formule migliori, una volta al giorno"), si parte dai falli
tools/lab: idee.json (formule fissate prima dei risultati), comune.py (app walk-forward + archivio API, coefficienti nuovi stimati solo nel periodo
scelta con l'app fissa; riferimento alla pari = app + sola costante), lab.py (ogni notte le prossime 2 idee), ombra.py (le idee promosse seguite
sulle partite nuove, senza toccare l'app), workflow lab.yml (ramo lab: stato.json, ombra.json, RIEPILOGO.md). Regola: 99% in verifica, stesso
segno in holdout, maggioranza dei campionati, 1X2 non peggiorato in modo sicuro.
Primo giro, falli (34.155 partite): F1 derby PASSA (+5,7% falli nei derby, verosimiglianza −0,033% verifica / −0,027% holdout, 19/31 e 21/31)
→ in ombra; F2 differenza di forza, F3 partita che conta (salvezza +4%, vertice +4%, ultime giornate −3%, ma al 99% non passa), F4 riposo,
F5 avvio di stagione: scartate.

## 18/11/2026 · Audit del modello falli (Denny) — SOLO ANALISI, niente in produzione
tools/p2/falli_dump.js (app con e senza arbitro, 35.950 partite dal 2023), falli_audit.py, falli_audit2.py; risultati ricerca/falli (ramo ricerca-falli).
- Modello attuale molto più informato dei riferimenti: media del campionato +0,134 log-loss per partita, medie squadra ristrette +0,007/+0,012.
- Distribuzione: grezza sovradispersa (var/media 1,1-1,5 per campionato), ma condizionata al modello quasi Poisson (squadra 1,04, totale 1,09);
  r stimati nello sviluppo 650/440 contro 200/150 dell'app; correlazione dei residui casa-ospite 0,05.
- Arbitro: è la variabile più forte (−0,017 per partita senza → con). Tetto +4%: toglierlo non passa (P4 contro P3: n.s. in verifica, 0 in holdout).
  Arbitro sui residui del modello (K 10) non meglio di quello di produzione. Affidabilità metà pari/dispari 0,42 (10-20 partite), 0,49 (20-40), 0,59 (40+).
- Forma ultime 5/10, casa/fuori della squadra: nessun guadagno (il modello ha già le ultime 5). Forza relativa, classifica, riposo, avvio: laboratorio, scartate.
- Derby su produzione: PASSA anche al 99% (verifica −0,057% verosimiglianza squadra, 25/31; holdout −0,045%, 20/31; totale −0,09%/−0,07%;
  Brier Over/Under −0,50%/−0,46%, 24/31 e 25/31); coefficiente +0,056 ± 0,011 (≈ +6%); nei derby 23,2 previsti contro 25,3 reali (verifica), 23,9/25,7 (holdout).
- r più alti: verosimiglianza del totale meglio in verifica, holdout non significativo, coda alta (linea +3) peggio calibrata → non adottare, eventualmente in ombra.
- Livello: la produzione sottostima di circa 0,2-0,3 falli (23,78 contro 24,10 in verifica; Over sulla linea vicina 44,6 contro 47,2).
- 18/11/2026 · INTEGRATO (Denny: "integrazione subito"): derby nei falli, FD_DERBY = { on: true, b: 0.0564 } in modelRef dopo l'arbitro
  (derby da extra.json, stesso fattore dei cartellini). Verificato: Serie A e Premier, cambiano solo le 41 partite derby con extra.json (×1,058),
  modello base invariato; "E se…" e Lettura con il derby. Laboratorio: F1 segnata "integrata", prova in ombra chiusa. Per tornare a prima: on = false.
- 18/11/2026 · Tetto dell'arbitro sui falli (Denny: "chi ha scelto il 4%? e con 5, 6, 7…?"): griglia 0-12% e senza tetto, pavimenti −3…−8%
  (tools/p2/falli_tetto.py, produzione + derby). Tetti più alti vanno un po' meglio in tutti e tre i periodi (es. +8%: −0,0009 / −0,0008 / −0,0005),
  il migliore nello sviluppo (+10%, pavimento −8%) contro +4%: verifica −0,00075 [−0,0017, +0,0001], holdout −0,00044 [−0,0014, +0,0004],
  16/31 campionati → non significativo, non passa. Pavimenti verso il basso peggiorano. Il tetto resta +4%.
- 18/11/2026 · Laboratorio: F6 "tetto dell'arbitro a +8%" in prova in ombra per decisione di Denny (ombra_diretta in idee.json): ogni giorno falli
  dell'app × min(f,1,08)/min(f,1,04) quando il fattore arbitro di extra.json supera +4%, confronto con l'app sulle partite giocate.

## 18/11/2026 · Audit del modello corner (Denny) — SOLO ANALISI, niente in produzione
tools/p2/corner_dati.py (caratteristiche pre-partita da storico + statistiche in più), corner_audit.py … corner_audit5.py; risultati in ricerca/corner (ramo ricerca-corner).
34.217 partite dell'app dal 2023 unite all'archivio API (sviluppo 10.797, verifica 10.227, holdout 13.193; 31 campionati).
- Modello attuale ricostruito e ricalcolato a mano (Inter-Torino 25/8/2025: 6,11 / 3,07; 1X2 copula 74,1/8,1/17,8 identico in Python).
  Coefficienti CDYN stimati fino al 2024-25 e CNS_B fino a giugno 2025: per l'app la verifica è in parte nel campione, l'holdout no.
- Distribuzione: r stimati 12,2 per squadra (app 12) e 65-79 sul totale (app 60, cambio non significativo); correlazione dei residui −0,20,
  copula −0,20 confermata (migliore tra 0/−0,1/−0,2/−0,3); somma con copula = NB r 60 diretta sul totale.
- Riferimenti da zero (media campionato, rating, forma 5/10/decadimento, campo, contesto) tutti peggiori dell'app. Sull'app, da sole: forma 10,
  decadimento, sede della squadra, rating 365, bloccati, possesso, xG, forza, calibrazione per campionato (mobile o fissa), inizio stagione: nessun guadagno.
- Problema: previsioni troppo lontane dalla media del campionato (pendenza casa 0,88-0,93; fascia > 11,5 attesi 11,9 reali 10,9 in verifica).
- Candidato: app × e^(c + tiri e tiri in porta ultime 10 di squadra e avversario + contrazione verso la media per sede), coefficienti nello sviluppo:
  verosimiglianza per squadra −0,0014 (verifica, 99%) / −0,0018 (holdout, 99%), 20/31 e 23/31; 1X2 −0,10% / −0,20% (99%);
  totale −0,0010 (n.s.) / −0,0012 (99%). Variante per i totali: tiri + contrazione (totale 99% in verifica e holdout). IN ATTESA DI DENNY.
- 18/11/2026 · PROVA IN OMBRA approvata da Denny (NON in produzione). index.html: CORNER_V2 (coefficienti congelati) + cornerV2(), non usati
  dall'app; precalc.js scrive data/corner_v2.json (ufficiale e V2 sulla stessa partita); tools/lab/ombra_corner.py ogni notte (lab.yml) registra
  e confronta sugli stessi eventi (report CORNER_V2.md sul ramo lab). Con dati insufficienti (< 5 partite utili in uno degli indici) V2 = ufficiale.
  Controlli: JavaScript = Python su 35.915 partite (differenza massima 1e-6, stessa accensione nel 100%), ricaduta esatta, precalc.json
  identico byte per byte con e senza la modifica, app avviata nel browser senza errori. Backup: rami backup-pre-corner-v2 e backup-pages-pre-corner-v2.
  Backtest della versione JavaScript (dati dell'app): squadra −0,0012 verifica / −0,0018 holdout (99%), 1X2 99% in entrambi, totale 99% solo holdout.
  Bootstrap anche per campionato-stagione e campionato e con Bonferroni (3 varianti): squadra e 1X2 holdout restano significativi.

## 18/11/2026 · Correzione della prova in ombra F6 (falli, tetto arbitro +8%) — documentazione separata (Denny, 19/11)
- Cosa: tools/lab/ombra.py cercava i falli reali nel bundle solo con le colonne Div/HomeTeam/AwayTeam (file football-data). I file dei campionati
  presi da API-Football (ARG.csv, USA.csv…) hanno Home/Away e nessuna colonna Div, quindi per quei campionati la prova F6 non trovava mai il risultato.
- Correzione (commit 88620a2): campionato dal nome del file quando manca Div, squadre da Home/Away quando mancano HomeTeam/AwayTeam.
- Effetto: SOLO sul conteggio della prova in ombra F6 (più campionati con risultato). Nessun effetto sulle previsioni ufficiali: ombra.py gira nel
  laboratorio (lab.yml), legge le pagine pubblicate e scrive solo sul ramo lab; precalc.json verificato identico byte per byte. Coefficienti e
  regola di F6 invariati. Le partite F6 registrate prima del 18/11 nei campionati API risultano ora con il risultato se presenti nel bundle.

## 20/11/2026 · Cartellini, studio sui soli dati (Denny: "lavorare solo sui dati e non sui book … studia tutto") — SOLO ANALISI
tools/p2/cart_dati.py (modello dell'app rifatto walk-forward come in produzione: corr 0,9987 con extra.json), cart_studio.py, cart_book.py;
risultati sul ramo ricerca-cartellini. 53.193 partite (sviluppo 20.849, verifica 13.595, holdout 18.749), 47 campionati e coppe.
- App ben tarata in generale: holdout 4,35 attesi / 4,30 reali, Under sulla linea vicina 53,8% / 53,7%; fascia Under 60-65% un po' alta (61,5 → 59,5).
- Passa la regola: cartellini PER SQUADRA con Poisson invece della NB del totale (r stimato → infinito): log-loss per squadra −0,0021 verifica /
  −0,0028 holdout (99%, 37/47 e 38/47), Brier linee fisse 0,5/1,5/2,5 meglio al 99%. Linea vicina all'atteso: invariata.
- Livello recente del campionato (reali/attesi ultimi 30 giorni, shrinkage 50, coeff. 0,75): meglio in tutti i periodi, ma il totale non arriva
  al 99% in verifica; con Poisson per squadra (F+A30+E) passa per squadra (log-loss, Brier linea vicina e fisse).
- Non passano: livello 60/120/365 giorni, avanzamento della stagione, costante per campionato (peggio), sede delle squadre, contrazione (≈0).
- Tabellone sulle linee archiviate (1.172 partite, il book solo come metro): giocate del Mercato dell'app (≥65%, valore ≥5%) 156, 89% Under,
  prese 62,8% contro 69,4% dichiarato, rendimento +5,4% (totali +10%, per squadra −8/0%). Le varianti non cambiano il quadro: lo scarto tra
  dichiarato e preso nasce dalla selezione (si scelgono le partite dove il modello si discosta di più). IN ATTESA DI DENNY.
