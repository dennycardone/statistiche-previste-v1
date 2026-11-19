"""Derby · tipo e nome per l'avviso nell'app (19/11/2026, Denny). Solo informazione: NON cambia nessun modello (la lista dei derby resta
derby.py, usata da cartellini e falli). Stesso ordine delle coppie di derby.py, campionato per campionato.
Tipo: s = stracittadina (stessa città o area urbana; con la città), r = derby regionale (stessa regione), t = rivalità storica (nazionale).
Nome vuoto quando non c'è un nome noto e sicuro. update_data.py scrive data/derby.json (partita → [tipo, nome, città])."""
from derby import D
I = {
"ARG": [("r","Clásico del Sur",""),("s","Superclásico","Buenos Aires"),("s","Clásico de Avellaneda","Avellaneda"),("s","Clásico rosarino","Rosario"),("s","Clásico platense","La Plata"),
        ("s","","Buenos Aires"),("s","Clásico santafesino","Santa Fe"),("s","Clásico cordobés","Córdoba"),("s","","Córdoba"),("s","","Córdoba"),
        ("s","","Mendoza"),("s","Clásico mendocino","Mendoza"),("s","","Mendoza"),("s","Clásico del Oeste","Buenos Aires"),("r","",""),("r","",""),
        ("r","",""),("s","Clásico tucumano","San Miguel de Tucumán"),("r","","")],
"BRA": [("s","Fla-Flu","Rio de Janeiro"),("s","Clássico dos Milhões","Rio de Janeiro"),("s","Clássico da Rivalidade","Rio de Janeiro"),("s","Clássico dos Gigantes","Rio de Janeiro"),("s","Clássico Vovô","Rio de Janeiro"),("s","Clássico da Amizade","Rio de Janeiro"),
        ("s","Derby Paulista","San Paolo"),("s","Majestoso","San Paolo"),("s","Choque-Rei","San Paolo"),("r","Clássico Alvinegro",""),("r","Clássico da Saudade",""),("r","San-São",""),
        ("s","Gre-Nal","Porto Alegre"),("s","Clássico Mineiro","Belo Horizonte"),("s","","Belo Horizonte"),("s","","Belo Horizonte"),("s","Ba-Vi","Salvador"),("s","Atletiba","Curitiba"),
        ("s","Clássico-Rei","Fortaleza"),("s","","Goiânia"),("s","Clássico dos Clássicos","Recife")],
"I1": [("s","Derby della Madonnina","Milano"),("s","Derby della Capitale","Roma"),("s","Derby della Mole","Torino"),("s","Derby della Lanterna","Genova"),("t","Derby d'Italia",""),("t","",""),("t","Derby del Sole",""),("s","Derby della Scala","Verona")],
"SP1": [("s","Derbi madrileño","Madrid"),("s","Derbi barcelonés","Barcellona"),("s","Gran Derbi","Siviglia"),("r","Derbi vasco",""),("s","Derbi valenciano","Valencia"),("t","El Clásico",""),
        ("r","",""),("s","","Madrid"),("r","",""),("s","","Madrid"),("r","",""),("r","Derbi gallego",""),
        ("r","Derbi de la Comunitat",""),("r","",""),("r","Derbi vasco","")],
"E0": [("s","Merseyside derby","Liverpool"),("s","Manchester derby","Manchester"),("s","North London derby","Londra"),("s","","Londra"),("s","","Londra"),("r","Tyne-Wear derby",""),
       ("r","West Midlands derby",""),("s","","Londra"),("s","","Londra"),("r","M23 derby",""),("r","South Coast derby",""),("r","East Midlands derby",""),
       ("t","North West derby",""),("t","",""),("s","West London derby","Londra"),("s","West London derby","Londra")],
"D1": [("r","Revierderby",""),("r","Rheinderby",""),("r","Rheinderby",""),("r","Nordderby",""),("t","Der Klassiker",""),
       ("t","Der Klassiker",""),("s","","Berlino"),("r","Rhein-Main-Derby",""),("r","Rheinderby",""),("r","",""),("s","","Amburgo"),
       ("r","Revierderby",""),("r","Revierderby","")],
"F1": [("t","Le Classique",""),("r","Derby du Rhône",""),("r","Derby de la Côte d'Azur",""),("r","Derby du Nord",""),("r","",""),("t","Olympico",""),("r","",""),("r","",""),("s","","Parigi")],
"P1": [("s","Derby de Lisboa","Lisbona"),("t","O Clássico",""),("t","",""),("r","Derby do Minho",""),("s","Derby da Invicta","Porto")],
"N1": [("t","De Klassieker",""),("t","",""),("t","",""),("s","","Rotterdam"),("s","","Rotterdam"),("r","Derby van het Noorden",""),("r","",""),("t","",""),("r","Gelderse derby","")],
"T1": [("s","Kıtalararası Derbi","Istanbul"),("s","","Istanbul"),("s","","Istanbul"),("t","",""),("s","","Smirne")],
"G1": [("s","Derby degli eterni nemici","Atene"),("s","","Atene"),("s","","Atene"),("s","","Salonicco"),("t","","")],
"SC0": [("s","Old Firm","Glasgow"),("s","Edinburgh derby","Edimburgo"),("s","Dundee derby","Dundee"),("t","",""),("r","Lanarkshire derby","")],
"RUS": [("s","","Mosca"),("s","","Mosca"),("s","","Mosca"),("s","","Mosca"),("s","","Mosca"),("s","","Mosca"),
        ("t","",""),("t","",""),("s","","Mosca"),("s","","Mosca"),("s","","Mosca"),("s","","Mosca")],
"MEX": [("t","Clásico Nacional",""),("s","Clásico Capitalino","Città del Messico"),("s","Clásico Joven","Città del Messico"),("s","Clásico Regio","Monterrey"),("s","Clásico Tapatío","Guadalajara"),("s","","Città del Messico")],
"B1": [("t","De Topper",""),("t","",""),("s","","Bruges"),("s","","Anversa"),("t","",""),("s","","Bruxelles")],
"POL": [("t","",""),("s","Święta Wojna","Cracovia"),("s","","Łódź"),("r","Derby Trójmiasta",""),("r","Wielkie Derby Śląska",""),("r","","")],
"ROU": [("s","Eternul derby","Bucarest"),("s","","Bucarest"),("s","","Bucarest"),("s","","Cluj-Napoca"),("s","","Craiova"),("t","","")],
"SRB": [("s","Večiti derbi","Belgrado"),("t","",""),("t","",""),("s","","Belgrado"),("s","","Belgrado")],
"CRO": [("t","Vječni derbi",""),("t","Jadranski derbi",""),("t","",""),("s","","Zagabria"),("t","","")],
"BUL": [("s","Večnoto derbi","Sofia"),("s","","Plovdiv"),("s","","Sofia"),("s","","Sofia"),("s","","Sofia"),("s","","Sofia"),("t","",""),("t","","")],
"AUT": [("s","Wiener Derby","Vienna"),("s","Grazer Derby","Graz"),("s","Linzer Derby","Linz"),("t","","")],
"SWZ": [("s","Zürcher Derby","Zurigo"),("t","",""),("t","",""),("r","Derby lémanique",""),("r","","")],
"CZE": [("s","Pražské derby","Praga"),("s","","Praga"),("s","","Praga"),("r","",""),("r","","")],
"HUN": [("s","","Budapest"),("s","","Budapest"),("s","","Budapest"),("s","","Budapest"),("r","","")],
"ISR": [("s","","Tel Aviv"),("s","","Haifa"),("s","","Gerusalemme"),("s","","Petah Tikva"),("t","",""),("t","",""),("t","","")],
"DNK": [("s","New Firm","Copenaghen"),("r","",""),("r","",""),("s","","Copenaghen"),("s","","Copenaghen")],
"SWE": [("s","Tvillingderbyt","Stoccolma"),("s","","Stoccolma"),("s","","Stoccolma"),("s","","Göteborg"),("s","","Göteborg"),("s","","Göteborg"),("r","Skånederbyt",""),("s","","Göteborg"),("t","","")],
"NOR": [("r","",""),("t","",""),("t","",""),("s","","Oslo"),("r","",""),("r","","")],
}
for lg in D: assert len(I.get(lg, [])) == len(D[lg]), (lg, len(I.get(lg, [])), len(D[lg]))
INFO = {(lg, frozenset(p)): list(I[lg][k]) for lg, L in D.items() for k, p in enumerate(L)}
def info(lg, h, a): return INFO.get((lg, frozenset((h, a))))
