"""Derby per il modello cartellini (24/10/2026): stracittadine e rivalità storiche note, lista scritta a mano senza guardare i
cartellini, nomi delle squadre come su API-Football (alcune coppie compaiono con due grafie). Test walk-forward su circa 60.000
partite 2022-2026: nei derby i cartellini erano sottostimati di circa uno (America 5,3 previsti contro 6,9 e 6,1 reali; Europa
4,4 contro 5,2 e 5,0); con il derby nel modello peso 0,180 / 0,184 nei due periodi di prova (circa +20%), log-loss su tutte le
partite −0,0022 ±0,0011 (lug 2024 – giu 2025) e −0,0015 ±0,0010 (lug 2025 – ott 2026), sui derby −0,077 e −0,034.
Per aggiungere un derby: una coppia (casa, ospite in qualsiasi ordine) nel campionato giusto."""
D = {
"ARG": [("Lanus","Banfield"),("Boca Juniors","River Plate"),("Racing Club","Independiente"),("Rosario Central","Newells Old Boys"),("Estudiantes L.P.","Gimnasia L.P."),
        ("Huracan","San Lorenzo"),("Colon Santa Fe","Union Santa Fe"),("Talleres Cordoba","Belgrano Cordoba"),("Instituto Cordoba","Talleres Cordoba"),("Instituto Cordoba","Belgrano Cordoba"),
        ("Godoy Cruz","Independ. Rivadavia"),("Gimnasia M.","Independ. Rivadavia"),("Godoy Cruz","Gimnasia M."),("Velez Sarsfield","Ferro"),("Banfield","Los Andes"),("Lanus","Arsenal Sarandi"),
        ("Tigre","Platense"),("Atletico Tucuman","San Martin T."),("Argentinos JRS","Platense")],
"BRA": [("Flamengo","Fluminense"),("Flamengo","Vasco DA Gama"),("Flamengo","Botafogo"),("Fluminense","Vasco DA Gama"),("Fluminense","Botafogo"),("Vasco DA Gama","Botafogo"),
        ("Corinthians","Palmeiras"),("Corinthians","Sao Paulo"),("Palmeiras","Sao Paulo"),("Santos","Corinthians"),("Santos","Palmeiras"),("Santos","Sao Paulo"),
        ("Gremio","Internacional"),("Atletico-MG","Cruzeiro"),("America Mineiro","Atletico-MG"),("America Mineiro","Cruzeiro"),("Bahia","Vitoria"),("Atletico Paranaense","Coritiba"),
        ("Ceara","Fortaleza EC"),("Goias","Atletico Goianiense"),("Sport Recife","Nautico")],
"I1": [("AC Milan","Inter"),("AS Roma","Lazio"),("Juventus","Torino"),("Genoa","Sampdoria"),("Juventus","Inter"),("Fiorentina","Juventus"),("Napoli","AS Roma"),("Hellas Verona","Chievo")],
"SP1": [("Real Madrid","Atletico Madrid"),("Barcelona","Espanyol"),("Sevilla","Real Betis"),("Athletic Club","Real Sociedad"),("Valencia","Levante"),("Real Madrid","Barcelona"),
        ("Real Madrid","Getafe"),("Real Madrid","Rayo Vallecano"),("Atletico Madrid","Getafe"),("Atletico Madrid","Rayo Vallecano"),("Getafe","Rayo Vallecano"),("Celta Vigo","Deportivo La Coruna"),
        ("Valencia","Villarreal"),("Osasuna","Athletic Club"),("Alaves","Athletic Club")],
"E0": [("Liverpool","Everton"),("Manchester City","Manchester United"),("Arsenal","Tottenham"),("Chelsea","Tottenham"),("Arsenal","Chelsea"),("Newcastle","Sunderland"),
       ("Aston Villa","Wolves"),("West Ham","Tottenham"),("West Ham","Chelsea"),("Crystal Palace","Brighton"),("Southampton","Bournemouth"),("Nottingham Forest","Leicester"),
       ("Liverpool","Manchester United"),("Leeds","Manchester United"),("Fulham","Chelsea"),("Brentford","Fulham")],
"D1": [("Borussia Dortmund","FC Schalke 04"),("1. FC Köln","Borussia Mönchengladbach"),("1. FC Köln","Borussia Monchengladbach"),("Hamburger SV","Werder Bremen"),("Bayern München","Borussia Dortmund"),
       ("Bayern Munich","Borussia Dortmund"),("Union Berlin","Hertha Berlin"),("Eintracht Frankfurt","FSV Mainz 05"),("1. FC Köln","Fortuna Dusseldorf"),("VfB Stuttgart","SC Freiburg"),("Hamburger SV","FC St. Pauli"),
       ("Borussia Dortmund","VfL Bochum"),("FC Schalke 04","VfL Bochum")],
"F1": [("Paris Saint Germain","Marseille"),("Lyon","Saint Etienne"),("Nice","Monaco"),("Lens","Lille"),("Nantes","Rennes"),("Marseille","Lyon"),("Nice","Marseille"),("Montpellier","Nimes"),("Paris FC","Paris Saint Germain")],
"P1": [("Benfica","Sporting CP"),("FC Porto","Benfica"),("FC Porto","Sporting CP"),("SC Braga","Vitória SC"),("FC Porto","Boavista")],
"N1": [("Ajax","Feyenoord"),("Ajax","PSV Eindhoven"),("Feyenoord","PSV Eindhoven"),("Feyenoord","Sparta Rotterdam"),("Feyenoord","Excelsior"),("Groningen","Heerenveen"),("Twente","Heracles"),("Utrecht","Ajax"),("Vitesse","NEC Nijmegen")],
"T1": [("Galatasaray","Fenerbahçe"),("Galatasaray","Beşiktaş"),("Fenerbahçe","Beşiktaş"),("Trabzonspor","Fenerbahçe"),("Göztepe","Karşıyaka")],
"G1": [("Olympiakos Piraeus","Panathinaikos"),("Olympiakos Piraeus","AEK Athens FC"),("Panathinaikos","AEK Athens FC"),("PAOK","Aris Thessalonikis"),("PAOK","Olympiakos Piraeus")],
"SC0": [("Celtic","Rangers"),("Heart Of Midlothian","Hibernian"),("Dundee","Dundee Utd"),("Aberdeen","Rangers"),("Motherwell","Hamilton")],
"RUS": [("Spartak Moscow","CSKA Moscow"),("Spartak Moscow","Lokomotiv Moscow"),("Spartak Moscow","Dinamo Moscow"),("CSKA Moscow","Lokomotiv Moscow"),("CSKA Moscow","Dinamo Moscow"),("Lokomotiv Moscow","Dinamo Moscow"),
        ("Zenit Saint Petersburg","Spartak Moscow"),("Zenit","Spartak Moscow"),("Spartak Moscow","Lokomotiv"),("CSKA Moscow","Lokomotiv"),("Spartak Moscow","Dynamo"),("CSKA Moscow","Dynamo")],
"MEX": [("Club America","Guadalajara Chivas"),("Club America","U.N.A.M. - Pumas"),("Club America","Cruz Azul"),("Monterrey","Tigres UANL"),("Atlas","Guadalajara Chivas"),("Cruz Azul","U.N.A.M. - Pumas")],
"B1": [("Anderlecht","Club Brugge KV"),("Anderlecht","Standard Liege"),("Club Brugge KV","Cercle Brugge"),("Antwerp","Beerschot VA"),("Standard Liege","Genk"),("Anderlecht","Union St. Gilloise")],
"POL": [("Legia Warszawa","Lech Poznan"),("Wisla Krakow","Cracovia Krakow"),("Widzew Łódź","ŁKS Łódź"),("Lechia Gdansk","Arka Gdynia"),("Gornik Zabrze","Ruch Chorzów"),("Gornik Zabrze","Piast Gliwice")],
"ROU": [("FCSB","Dinamo Bucuresti"),("FCSB","Rapid"),("Dinamo Bucuresti","Rapid"),("CFR 1907 Cluj","Universitatea Cluj"),("Universitatea Craiova","U Craiova 1948"),("FCSB","Universitatea Craiova")],
"SRB": [("FK Crvena Zvezda","FK Partizan"),("Vojvodina","FK Partizan"),("Vojvodina","FK Crvena Zvezda"),("FK Partizan","OFK Beograd"),("FK Crvena Zvezda","OFK Beograd")],
"CRO": [("Dinamo Zagreb","HNK Hajduk Split"),("HNK Hajduk Split","HNK Rijeka"),("Dinamo Zagreb","HNK Rijeka"),("Dinamo Zagreb","NK Lokomotiva Zagreb"),("Dinamo Zagreb","NK Osijek")],
"BUL": [("CSKA Sofia","Levski Sofia"),("Botev Plovdiv","Lokomotiv Plovdiv"),("CSKA Sofia","Slavia Sofia"),("Levski Sofia","Slavia Sofia"),("CSKA 1948","CSKA Sofia"),("CSKA 1948","Levski Sofia"),("Ludogorets","CSKA Sofia"),("Ludogorets","Levski Sofia")],
"AUT": [("Rapid Vienna","Austria Vienna"),("Sturm Graz","Grazer AK"),("Lask Linz","FC BW Linz"),("Red Bull Salzburg","Rapid Vienna")],
"SWZ": [("FC Zurich","Grasshoppers"),("FC Basel 1893","FC Zurich"),("FC Basel 1893","BSC Young Boys"),("Servette FC","Lausanne"),("FC Sion","Servette FC")],
"CZE": [("Slavia Praha","Sparta Praha"),("Bohemians 1905","Slavia Praha"),("Bohemians 1905","Sparta Praha"),("Baník Ostrava","Sigma Olomouc"),("Zbrojovka Brno","Slovácko")],
"HUN": [("Ferencvarosi TC","Ujpest"),("Ferencvarosi TC","MTK Budapest"),("Ujpest","MTK Budapest"),("Budapest Honved","Ferencvarosi TC"),("Debreceni VSC","Nyiregyhaza")],
"ISR": [("Maccabi Tel Aviv","Hapoel Tel Aviv"),("Maccabi Haifa","Hapoel Haifa"),("Beitar Jerusalem","Hapoel Katamon"),("Maccabi Petah Tikva","Hapoel Petah Tikva"),("Beitar Jerusalem","Bnei Sakhnin"),("Maccabi Haifa","Maccabi Tel Aviv"),("Beitar Jerusalem","Maccabi Tel Aviv")],
"DNK": [("FC Copenhagen","Brondby"),("Aarhus","Aalborg"),("FC Midtjylland","Aarhus"),("FC Copenhagen","Lyngby"),("Brondby","Hvidovre")],
"SWE": [("AIK Stockholm","Djurgardens IF"),("AIK Stockholm","Hammarby FF"),("Djurgardens IF","Hammarby FF"),("IFK Goteborg","Gais"),("IFK Goteborg","Orgryte IS"),("Gais","Orgryte IS"),("Malmo FF","Helsingborg"),("IFK Goteborg","BK Hacken"),("IFK Norrkoping","Degerfors IF")],
"NOR": [("Valerenga","Lillestrom"),("Rosenborg","Molde"),("Brann","Viking"),("Valerenga","KFUM Oslo"),("Sarpsborg 08 FF","Fredrikstad"),("Viking","Bryne")],
}
SET = {lg: {frozenset(p) for p in L} for lg, L in D.items()}
def is_derby(lg, h, a): return frozenset((h, a)) in SET.get(lg, ())
