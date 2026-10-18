"""Curated popularity ranking for the Fyucha FC player profile API."""

# Keys are normalized player names; values are ranking weights.
POPULAR_PLAYERS = {
    'lionel messi': 1000,  # Lionel Messi
    'cristiano ronaldo': 1000,  # Cristiano Ronaldo
    'neymar': 950,  # Neymar
    'kylian mbappe': 950,  # Kylian Mbappe
    'pele': 950,  # Pele
    'diego maradona': 950,  # Diego Maradona
    'ronaldinho': 900,  # Ronaldinho
    'zinedine zidane': 900,  # Zinedine Zidane
    'david beckham': 900,  # David Beckham
    'ronaldo nazario': 900,  # Ronaldo Nazario
    'mohamed salah': 900,  # Mohamed Salah
    'erling haaland': 900,  # Erling Haaland
    'kevin de bruyne': 850,  # Kevin De Bruyne
    'vinicius junior': 850,  # Vinicius Junior
    'jude bellingham': 850,  # Jude Bellingham
    'robert lewandowski': 850,  # Robert Lewandowski
    'luka modric': 800,  # Luka Modric
    'andres iniesta': 800,  # Andres Iniesta
    'xavi': 800,  # Xavi
    'thierry henry': 850,  # Thierry Henry
    'didier drogba': 850,  # Didier Drogba
    'samuel eto o': 700,  # Samuel Eto'o
    'george weah': 800,  # George Weah
    'sadio mane': 800,  # Sadio Mane
    'yaya toure': 800,  # Yaya Toure
    'jay jay okocha': 800,  # Jay-Jay Okocha
    'riyad mahrez': 750,  # Riyad Mahrez
    'victor osimhen': 750,  # Victor Osimhen
    'franz beckenbauer': 700,  # Franz Beckenbauer
    'johan cruyff': 700,  # Johan Cruyff
    'alfredo di stefano': 700,  # Alfredo Di Stefano
    'ferenc puskas': 700,  # Ferenc Puskas
    'eusebio': 700,  # Eusebio
    'garrincha': 700,  # Garrincha
    'bobby charlton': 700,  # Bobby Charlton
    'george best': 700,  # George Best
    'michel platini': 700,  # Michel Platini
    'marco van basten': 700,  # Marco van Basten
    'ruud gullit': 700,  # Ruud Gullit
    'paolo maldini': 700,  # Paolo Maldini
    'franco baresi': 700,  # Franco Baresi
    'roberto baggio': 700,  # Roberto Baggio
    'gianluigi buffon': 700,  # Gianluigi Buffon
    'andrea pirlo': 700,  # Andrea Pirlo
    'fabio cannavaro': 700,  # Fabio Cannavaro
    'francesco totti': 700,  # Francesco Totti
    'alessandro del piero': 700,  # Alessandro Del Piero
    'gerd muller': 700,  # Gerd Muller
    'lothar matthaus': 700,  # Lothar Matthaus
    'miroslav klose': 700,  # Miroslav Klose
    'oliver kahn': 700,  # Oliver Kahn
    'philipp lahm': 700,  # Philipp Lahm
    'bastian schweinsteiger': 700,  # Bastian Schweinsteiger
    'thomas muller': 700,  # Thomas Muller
    'manuel neuer': 700,  # Manuel Neuer
    'toni kroos': 700,  # Toni Kroos
    'mesut ozil': 700,  # Mesut Ozil
    'rivaldo': 700,  # Rivaldo
    'romario': 700,  # Romario
    'kaka': 700,  # Kaka
    'roberto carlos': 700,  # Roberto Carlos
    'cafu': 700,  # Cafu
    'zico': 700,  # Zico
    'socrates': 700,  # Socrates
    'falcao': 700,  # Falcao
    'carlos valderrama': 700,  # Carlos Valderrama
    'hugo sanchez': 700,  # Hugo Sanchez
    'rafael marquez': 700,  # Rafael Marquez
    'javier zanetti': 700,  # Javier Zanetti
    'gabriel batistuta': 700,  # Gabriel Batistuta
    'juan roman riquelme': 700,  # Juan Roman Riquelme
    'carlos tevez': 700,  # Carlos Tevez
    'luis suarez': 700,  # Luis Suarez
    'edinson cavani': 700,  # Edinson Cavani
    'diego forlan': 700,  # Diego Forlan
    'enzo francescoli': 700,  # Enzo Francescoli
    'hristo stoichkov': 700,  # Hristo Stoichkov
    'dimitar berbatov': 700,  # Dimitar Berbatov
    'ryan giggs': 700,  # Ryan Giggs
    'paul scholes': 700,  # Paul Scholes
    'eric cantona': 700,  # Eric Cantona
    'wayne rooney': 700,  # Wayne Rooney
    'alan shearer': 700,  # Alan Shearer
    'steven gerrard': 700,  # Steven Gerrard
    'frank lampard': 700,  # Frank Lampard
    'paul gascoigne': 700,  # Paul Gascoigne
    'bobby moore': 700,  # Bobby Moore
    'gordon banks': 700,  # Gordon Banks
    'peter schmeichel': 700,  # Peter Schmeichel
    'dennis bergkamp': 700,  # Dennis Bergkamp
    'patrick vieira': 700,  # Patrick Vieira
    'roy keane': 700,  # Roy Keane
    'didier deschamps': 700,  # Didier Deschamps
    'claude makelele': 700,  # Claude Makelele
    'arjen robben': 700,  # Arjen Robben
    'wesley sneijder': 700,  # Wesley Sneijder
    'robin van persie': 700,  # Robin van Persie
    'ruud van nistelrooy': 700,  # Ruud van Nistelrooy
    'kenny dalglish': 700,  # Kenny Dalglish
    'ian rush': 700,  # Ian Rush
    'graeme souness': 650,  # Graeme Souness
    'john barnes': 650,  # John Barnes
    'david seaman': 650,  # David Seaman
    'tony adams': 650,  # Tony Adams
    'ian wright': 650,  # Ian Wright
    'michael owen': 650,  # Michael Owen
    'gary lineker': 650,  # Gary Lineker
    'peter shilton': 650,  # Peter Shilton
    'jimmy greaves': 650,  # Jimmy Greaves
    'stanley matthews': 650,  # Stanley Matthews
    'tom finney': 650,  # Tom Finney
    'kevin keegan': 650,  # Kevin Keegan
    'chris waddle': 650,  # Chris Waddle
    'gary neville': 650,  # Gary Neville
    'rio ferdinand': 650,  # Rio Ferdinand
    'john terry': 650,  # John Terry
    'ashley cole': 650,  # Ashley Cole
    'david silva': 650,  # David Silva
    'sergio aguero': 650,  # Sergio Aguero
    'vincent kompany': 650,  # Vincent Kompany
    'didier zokora': 650,  # Didier Zokora
    'cesc fabregas': 650,  # Cesc Fabregas
    'fernando torres': 650,  # Fernando Torres
    'xabi alonso': 650,  # Xabi Alonso
    'sergio ramos': 650,  # Sergio Ramos
    'iker casillas': 650,  # Iker Casillas
    'carles puyol': 650,  # Carles Puyol
    'gerard pique': 650,  # Gerard Pique
    'sergio busquets': 650,  # Sergio Busquets
    'david villa': 650,  # David Villa
    'fernando hierro': 650,  # Fernando Hierro
    'luis figo': 650,  # Luis Figo
    'deco': 650,  # Deco
    'pepe': 650,  # Pepe
    'bernardo silva': 650,  # Bernardo Silva
    'bruno fernandes': 650,  # Bruno Fernandes
    'ruben dias': 650,  # Ruben Dias
    'joao felix': 650,  # Joao Felix
    'joao cancelo': 650,  # Joao Cancelo
    'ricardo quaresma': 650,  # Ricardo Quaresma
    'nani': 650,  # Nani
    'pauleta': 650,  # Pauleta
    'eder': 650,  # Eder
    'gheorghe hagi': 650,  # Gheorghe Hagi
    'gheorghe popescu': 650,  # Gheorghe Popescu
    'davor suker': 650,  # Davor Suker
    'zvonimir boban': 650,  # Zvonimir Boban
    'robert prosinecki': 650,  # Robert Prosinecki
    'dejan savicevic': 650,  # Dejan Savicevic
    'dragan stojkovic': 650,  # Dragan Stojkovic
    'predrag mijatovic': 650,  # Predrag Mijatovic
    'nemanja vidic': 650,  # Nemanja Vidic
    'dejan stankovic': 650,  # Dejan Stankovic
    'edin dzeko': 650,  # Edin Dzeko
    'luka jovic': 650,  # Luka Jovic
    'zlatan ibrahimovic': 650,  # Zlatan Ibrahimovic
    'henrik larsson': 650,  # Henrik Larsson
    'freddie ljungberg': 650,  # Freddie Ljungberg
    'tomas brolin': 650,  # Tomas Brolin
    'anders svensson': 650,  # Anders Svensson
    'michael laudrup': 650,  # Michael Laudrup
    'brian laudrup': 650,  # Brian Laudrup
    'christian eriksen': 650,  # Christian Eriksen
    'erling braut haaland': 650,  # Erling Braut Haaland
    'martin odegaard': 650,  # Martin Odegaard
    'ole gunnar solskjaer': 650,  # Ole Gunnar Solskjaer
    'john arne riise': 650,  # John Arne Riise
    'kjetil rekdal': 650,  # Kjetil Rekdal
    'abedi pele': 650,  # Abedi Pele
    'asamoah gyan': 650,  # Asamoah Gyan
    'michael essien': 650,  # Michael Essien
    'sulley muntari': 650,  # Sulley Muntari
    'stephen appiah': 650,  # Stephen Appiah
    'tony yeboah': 650,  # Tony Yeboah
    'kwadwo asamoah': 650,  # Kwadwo Asamoah
    'thomas partey': 650,  # Thomas Partey
    'andre ayew': 650,  # Andre Ayew
    'jordan ayew': 650,  # Jordan Ayew
    'abedi ayew': 650,  # Abedi Ayew
    'rabah madjer': 650,  # Rabah Madjer
    'lakhdar belloumi': 650,  # Lakhdar Belloumi
    'mustapha hadji': 650,  # Mustapha Hadji
    'el hadji diouf': 650,  # El Hadji Diouf
    'kalusha bwalya': 650,  # Kalusha Bwalya
    'benni mccarthy': 650,  # Benni McCarthy
    'lucas radebe': 650,  # Lucas Radebe
    'steven pienaar': 650,  # Steven Pienaar
    'percy tau': 650,  # Percy Tau
    'bongani khumalo': 650,  # Bongani Khumalo
    'ahmed hassan': 650,  # Ahmed Hassan
    'mohamed aboutrika': 650,  # Mohamed Aboutrika
    'mahmoud el khatib': 650,  # Mahmoud El Khatib
    'essam el hadary': 650,  # Essam El Hadary
    'hossam hassan': 650,  # Hossam Hassan
    'islam slimani': 650,  # Islam Slimani
    'seydou keita': 650,  # Seydou Keita
    'frederic kanoute': 650,  # Frederic Kanoute
    'salif keita': 650,  # Salif Keita
    'roger milla': 650,  # Roger Milla
    'patrick mboma': 650,  # Patrick Mboma
    'lauren': 650,  # Lauren
    'rigobert song': 650,  # Rigobert Song
    'joseph yobo': 650,  # Joseph Yobo
    'nwankwo kanu': 650,  # Nwankwo Kanu
    'finidi george': 650,  # Finidi George
    'rashidi yekini': 650,  # Rashidi Yekini
    'victor ikpeba': 650,  # Victor Ikpeba
    'emmanuel adebayor': 650,  # Emmanuel Adebayor
    'adebayor': 650,  # Adebayor
    'seydou doumbia': 650,  # Seydou Doumbia
    'kolo toure': 650,  # Kolo Toure
    'emmanuel eboue': 650,  # Emmanuel Eboue
    'gervinho': 650,  # Gervinho
    'wilfried zaha': 650,  # Wilfried Zaha
    'wilfried bony': 650,  # Wilfried Bony
    'kalidou koulibaly': 650,  # Kalidou Koulibaly
    'papiss cisse': 650,  # Papiss Cisse
    'pierre emerick aubameyang': 650,  # Pierre-Emerick Aubameyang
    'achraf hakimi': 650,  # Achraf Hakimi
    'hakim ziyech': 650,  # Hakim Ziyech
    'mehdi benatia': 650,  # Mehdi Benatia
    'abdeljalil hadda': 650,  # Abdeljalil Hadda
    'hossam ghaly': 650,  # Hossam Ghaly
    'mohamed zidan': 650,  # Mohamed Zidan
    'mohamed elneny': 650,  # Mohamed Elneny
    'ramy bensebaini': 650,  # Ramy Bensebaini
    'john obi mikel': 650,  # John Obi Mikel
    'obafemi martins': 650,  # Obafemi Martins
    'yakubu aiyegbeni': 650,  # Yakubu Aiyegbeni
    'ahmed musa': 650,  # Ahmed Musa
    'jairzinho': 650,  # Jairzinho
    'didi': 650,  # Didi
    'vava': 650,  # Vava
    'tostao': 650,  # Tostao
    'carlos alberto torres': 650,  # Carlos Alberto Torres
    'nilton santos': 650,  # Nilton Santos
    'djalma santos': 650,  # Djalma Santos
    'friedenreich': 650,  # Friedenreich
    'leonidas da silva': 650,  # Leonidas da Silva
    'bebeto': 650,  # Bebeto
    'juninho pernambucano': 650,  # Juninho Pernambucano
    'juninho paulista': 650,  # Juninho Paulista
    'dunga': 650,  # Dunga
    'gilberto silva': 650,  # Gilberto Silva
    'ronaldo de assis moreira': 650,  # Ronaldo de Assis Moreira
    'adriano': 650,  # Adriano
    'robinho': 650,  # Robinho
    'alex de souza': 650,  # Alex de Souza
    'djalminha': 650,  # Djalminha
    'diego ribas': 650,  # Diego Ribas
    'rafinha': 600,  # Rafinha
    'dani alves': 600,  # Dani Alves
    'marcelo': 600,  # Marcelo
    'thiago silva': 600,  # Thiago Silva
    'alisson becker': 600,  # Alisson Becker
    'ederson': 600,  # Ederson
    'casemiro': 600,  # Casemiro
    'fabinho': 600,  # Fabinho
    'raphinha': 600,  # Raphinha
    'rodrygo': 600,  # Rodrygo
    'gabriel jesus': 600,  # Gabriel Jesus
    'gabriel martinelli': 600,  # Gabriel Martinelli
    'endrick': 600,  # Endrick
    'richarlison': 600,  # Richarlison
    'bruno guimaraes': 600,  # Bruno Guimaraes
    'alexis sanchez': 600,  # Alexis Sanchez
    'arturo vidal': 600,  # Arturo Vidal
    'ivan zamorano': 600,  # Ivan Zamorano
    'marcelo salas': 600,  # Marcelo Salas
    'claudio bravo': 600,  # Claudio Bravo
    'gary medel': 600,  # Gary Medel
    'james rodriguez': 600,  # James Rodriguez
    'radamel falcao': 600,  # Radamel Falcao
    'juan cuadrado': 600,  # Juan Cuadrado
    'luis diaz': 600,  # Luis Diaz
    'freddy rincon': 600,  # Freddy Rincon
    'faustino asprilla': 600,  # Faustino Asprilla
    'rene higuita': 600,  # René Higuita
    'ivan cordoba': 600,  # Iván Córdoba
    'enner valencia': 600,  # Enner Valencia
    'antonio valencia': 600,  # Antonio Valencia
    'alex aguinaga': 600,  # Alex Aguinaga
    'paolo guerrero': 600,  # Paolo Guerrero
    'claudio pizarro': 600,  # Claudio Pizarro
    'teofilo cubillas': 600,  # Teofilo Cubillas
    'hector chumpitaz': 600,  # Hector Chumpitaz
    'juan manuel vargas': 600,  # Juan Manuel Vargas
    'lionel scaloni': 600,  # Lionel Scaloni
    'angel di maria': 600,  # Angel Di Maria
    'javier mascherano': 600,  # Javier Mascherano
    'esteban cambiasso': 600,  # Esteban Cambiasso
    'hernan crespo': 600,  # Hernan Crespo
    'ariel ortega': 600,  # Ariel Ortega
    'pablo aimar': 600,  # Pablo Aimar
    'diego simeone': 600,  # Diego Simeone
    'sergio goycochea': 600,  # Sergio Goycochea
    'oscar ruggeri': 600,  # Oscar Ruggeri
    'mario kempes': 600,  # Mario Kempes
    'ubaldo fillol': 600,  # Ubaldo Fillol
    'daniel passarella': 600,  # Daniel Passarella
    'omar sivori': 600,  # Omar Sivori
    'keylor navas': 600,  # Keylor Navas
    'cuauhtemoc blanco': 600,  # Cuauhtemoc Blanco
    'jorge campos': 600,  # Jorge Campos
    'javier hernandez': 600,  # Javier Hernandez
    'andres guardado': 600,  # Andres Guardado
    'hirving lozano': 600,  # Hirving Lozano
    'giovani dos santos': 600,  # Giovani dos Santos
    'clint dempsey': 600,  # Clint Dempsey
    'landon donovan': 600,  # Landon Donovan
    'christian pulisic': 600,  # Christian Pulisic
    'tim howard': 600,  # Tim Howard
    'brad friedel': 600,  # Brad Friedel
    'claudio reyna': 600,  # Claudio Reyna
    'cobi jones': 600,  # Cobi Jones
    'mia hamm': 600,  # Mia Hamm
    'abby wambach': 600,  # Abby Wambach
    'megan rapinoe': 600,  # Megan Rapinoe
    'alex morgan': 600,  # Alex Morgan
    'carli lloyd': 600,  # Carli Lloyd
    'marta': 600,  # Marta
    'birgit prinz': 600,  # Birgit Prinz
    'homare sawa': 600,  # Homare Sawa
    'sun wen': 600,  # Sun Wen
    'michelle akers': 600,  # Michelle Akers
    'kristine lilly': 600,  # Kristine Lilly
    'christine sinclair': 600,  # Christine Sinclair
    'sam kerr': 600,  # Sam Kerr
    'aitana bonmati': 600,  # Aitana Bonmati
    'alexia putellas': 600,  # Alexia Putellas
    'ada hegerberg': 600,  # Ada Hegerberg
    'wendie renard': 600,  # Wendie Renard
    'lucy bronze': 600,  # Lucy Bronze
    'hope solo': 600,  # Hope Solo
    'briana scurry': 600,  # Briana Scurry
    'julie foudy': 600,  # Julie Foudy
    'tiffeny milbrett': 600,  # Tiffeny Milbrett
    'hege riise': 600,  # Hege Riise
    'kelly smith': 600,  # Kelly Smith
    'kelly lindsey': 600,  # Kelly Lindsey
    'kelly o hara': 600,  # Kelly O'Hara
    'tobin heath': 600,  # Tobin Heath
    'lindsey horan': 600,  # Lindsey Horan
    'rose lavelle': 600,  # Rose Lavelle
    'sophia smith': 600,  # Sophia Smith
    'trinity rodman': 600,  # Trinity Rodman
    'mallory swanson': 600,  # Mallory Swanson
    'catarina macario': 600,  # Catarina Macario
    'lauren james': 600,  # Lauren James
    'alessia russo': 600,  # Alessia Russo
    'chloe kelly': 600,  # Chloe Kelly
    'fran kirby': 600,  # Fran Kirby
    'beth mead': 600,  # Beth Mead
    'mary earps': 600,  # Mary Earps
    'ellen white': 600,  # Ellen White
    'fara williams': 600,  # Fara Williams
    'rachel yankey': 600,  # Rachel Yankey
    'vivianne miedema': 600,  # Vivianne Miedema
    'lieke martens': 600,  # Lieke Martens
    'pernille harder': 600,  # Pernille Harder
    'caroline graham hansen': 600,  # Caroline Graham Hansen
    'ada stolsmo hegerberg': 600,  # Ada Stolsmo Hegerberg
    'alexia putellas segura': 600,  # Alexia Putellas Segura
    'irene paredes': 600,  # Irene Paredes
    'jennifer hermoso': 600,  # Jennifer Hermoso
    'salma paralluelo': 600,  # Salma Paralluelo
    'patri guijarro': 600,  # Patri Guijarro
    'olga carmona': 600,  # Olga Carmona
    'claudia pina': 600,  # Claudia Pina
    'keira walsh': 600,  # Keira Walsh
    'georgia stanway': 600,  # Georgia Stanway
    'lauren hemp': 600,  # Lauren Hemp
    'jill scott': 600,  # Jill Scott
    'eugenie le sommer': 600,  # Eugénie Le Sommer
    'amandine henry': 600,  # Amandine Henry
    'louisa necib': 600,  # Louisa Nécib
    'camille abily': 600,  # Camille Abily
    'marie laure delie': 600,  # Marie-Laure Delie
    'sakina karchaoui': 600,  # Sakina Karchaoui
    'kadidiatou diani': 600,  # Kadidiatou Diani
    'dzsenifer marozsan': 600,  # Dzsenifer Marozsan
    'nadine angerer': 600,  # Nadine Angerer
    'silvia neid': 600,  # Silvia Neid
    'maren meinert': 600,  # Maren Meinert
    'nilla fischer': 600,  # Nilla Fischer
    'lotta schelin': 600,  # Lotta Schelin
    'caroline seger': 600,  # Caroline Seger
    'hanna ljungberg': 600,  # Hanna Ljungberg
    'marta vieira da silva': 600,  # Marta Vieira da Silva
    'formiga': 600,  # Formiga
    'cristiane': 600,  # Cristiane
    'sissi': 600,  # Sissi
    'debinha': 600,  # Debinha
    'andressa alves': 600,  # Andressa Alves
    'kerolin': 600,  # Kerolin
    'geyse': 600,  # Geyse
    'yuki nagasato': 600,  # Yuki Nagasato
    'mana iwabuchi': 600,  # Mana Iwabuchi
    'aya miyama': 600,  # Aya Miyama
    'saki kumagai': 600,  # Saki Kumagai
    'yukari kinga': 600,  # Yukari Kinga
    'hanae shibata': 600,  # Hanae Shibata
    'ji so yun': 600,  # Ji So-yun
    'park eun sun': 600,  # Park Eun-sun
    'bai jie': 600,  # Bai Jie
    'wang shuang': 600,  # Wang Shuang
    'wang frost': 600,  # Wang Frost
    'yoko tanaka': 600,  # Yoko Tanaka
    'kozue ando': 600,  # Kozue Ando
    'nadine kessler': 600,  # Nadine Kessler
    'megan klingenberg': 600,  # Megan Klingenberg
    'julie ertz': 600,  # Julie Ertz
    'heather o reilly': 600,  # Heather O'Reilly
    'shannon boxx': 600,  # Shannon Boxx
    'lori chalupny': 600,  # Lori Chalupny
    'christie pearce': 600,  # Christie Pearce
    'lev yashin': 600,  # Lev Yashin
    'dino zoff': 600,  # Dino Zoff
    'sepp maier': 600,  # Sepp Maier
    'ricardo zamora': 600,  # Ricardo Zamora
    'amadeo carrizo': 600,  # Amadeo Carrizo
    'jose leandro andrade': 600,  # José Leandro Andrade
    'obdulio varela': 600,  # Obdulio Varela
    'jose nasazzi': 600,  # José Nasazzi
    'alcides ghiggia': 600,  # Alcides Ghiggia
    'juan alberto schiaffino': 600,  # Juan Alberto Schiaffino
    'hector scarone': 600,  # Héctor Scarone
    'jose manuel moreno': 600,  # José Manuel Moreno
    'adolfo pedernera': 600,  # Adolfo Pedernera
    'angel labruna': 600,  # Ángel Labruna
    'oreste corbatta': 600,  # Oreste Corbatta
    'daniel alberto bertoni': 600,  # Daniel Alberto Bertoni
    'mario alberto kempes': 600,  # Mario Alberto Kempes
    'jorge valdano': 600,  # Jorge Valdano
    'jorge burruchaga': 600,  # Jorge Burruchaga
    'claudio caniggia': 600,  # Claudio Caniggia
    'juan sebastian veron': 600,  # Juan Sebastián Verón
    'walter samuel': 600,  # Walter Samuel
    'roberto ayala': 600,  # Roberto Ayala
    'gabriel heinze': 600,  # Gabriel Heinze
    'carlos marchena': 600,  # Carlos Marchena
    'david trezeguet': 600,  # David Trezeguet
    'emmanuel petit': 600,  # Emmanuel Petit
    'marcel desailly': 600,  # Marcel Desailly
    'lilian thuram': 600,  # Lilian Thuram
    'bixente lizarazu': 600,  # Bixente Lizarazu
    'laurent blanc': 600,  # Laurent Blanc
    'youri djorkaeff': 600,  # Youri Djorkaeff
    'robert pires': 600,  # Robert Pirès
    'sylvain wiltord': 600,  # Sylvain Wiltord
    'david ginola': 600,  # David Ginola
    'jean pierre papin': 600,  # Jean-Pierre Papin
    'just fontaine': 600,  # Just Fontaine
    'raymond kopa': 600,  # Raymond Kopa
    'alain giresse': 600,  # Alain Giresse
    'jean tigana': 600,  # Jean Tigana
    'dominique rocheteau': 600,  # Dominique Rocheteau
    'marius tresor': 600,  # Marius Trésor
    'patrick battiston': 600,  # Patrick Battiston
    'jean michel larque': 600,  # Jean-Michel Larqué
    'jean pierre adams': 600,  # Jean-Pierre Adams
    'jurgen klinsmann': 600,  # Jürgen Klinsmann
    'rudi voller': 600,  # Rudi Völler
    'andreas brehme': 600,  # Andreas Brehme
    'karl heinz rummenigge': 600,  # Karl-Heinz Rummenigge
    'uwe seeler': 600,  # Uwe Seeler
    'fritz walter': 600,  # Fritz Walter
    'helmut rahn': 600,  # Helmut Rahn
    'paul breitner': 600,  # Paul Breitner
    'bernd holzenbein': 600,  # Bernd Hölzenbein
    'horst hrubesch': 600,  # Horst Hrubesch
    'jurgen kohler': 600,  # Jürgen Kohler
    'matthias sammer': 600,  # Matthias Sammer
    'michael ballack': 600,  # Michael Ballack
    'lukas podolski': 600,  # Lukas Podolski
    'jens lehmann': 600,  # Jens Lehmann
    'bernd schuster': 600,  # Bernd Schuster
    'gunter netzer': 600,  # Günter Netzer
    'andreas moller': 600,  # Andreas Möller
    'stefan effenberg': 600,  # Stefan Effenberg
    'pierre littbarski': 600,  # Pierre Littbarski
    'klaus fischer': 600,  # Klaus Fischer
    'karl heinz schnellinger': 600,  # Karl-Heinz Schnellinger
    'hans schafer': 600,  # Hans Schäfer
    'giuseppe meazza': 600,  # Giuseppe Meazza
    'silvio piola': 600,  # Silvio Piola
    'gianni rivera': 600,  # Gianni Rivera
    'gigi riva': 600,  # Gigi Riva
    'roberto donadoni': 600,  # Roberto Donadoni
    'demetrio albertini': 600,  # Demetrio Albertini
    'angelo peruzzi': 600,  # Angelo Peruzzi
    'christian vieri': 600,  # Christian Vieri
    'filippo inzaghi': 600,  # Filippo Inzaghi
    'gianluca vialli': 600,  # Gianluca Vialli
    'roberto mancini': 600,  # Roberto Mancini
    'antonio di natale': 600,  # Antonio Di Natale
    'daniele de rossi': 600,  # Daniele De Rossi
    'gennaro gattuso': 600,  # Gennaro Gattuso
    'marco tardelli': 600,  # Marco Tardelli
    'claudio gentile': 600,  # Claudio Gentile
    'giuseppe bergomi': 550,  # Giuseppe Bergomi
    'gaetano scirea': 550,  # Gaetano Scirea
    'dino baggio': 550,  # Dino Baggio
    'christian panucci': 550,  # Christian Panucci
    'angelo di livio': 550,  # Angelo Di Livio
    'marco materazzi': 550,  # Marco Materazzi
    'giorgio chiellini': 550,  # Giorgio Chiellini
    'leonardo bonucci': 550,  # Leonardo Bonucci
    'gianluca zambrotta': 550,  # Gianluca Zambrotta
    'gianfranco zola': 550,  # Gianfranco Zola
    'pierluigi casiraghi': 550,  # Pierluigi Casiraghi
    'massimo oddo': 550,  # Massimo Oddo
    'mauro camoranesi': 550,  # Mauro Camoranesi
    'pavel nedved': 550,  # Pavel Nedved
    'josef masopust': 550,  # Josef Masopust
    'antonin panenka': 550,  # Antonin Panenka
    'petr cech': 550,  # Petr Cech
    'tomas rosicky': 550,  # Tomas Rosicky
    'pavel kuka': 550,  # Pavel Kuka
    'jan koller': 550,  # Jan Koller
    'marek hamsik': 550,  # Marek Hamsik
    'milan baros': 550,  # Milan Baros
    'peter dubovsky': 550,  # Peter Dubovsky
    'andriy shevchenko': 550,  # Andriy Shevchenko
    'oleh blokhin': 550,  # Oleh Blokhin
    'igor belanov': 550,  # Igor Belanov
    'andrei kanchelskis': 550,  # Andrei Kanchelskis
    'anatoliy tymoshchuk': 550,  # Anatoliy Tymoshchuk
    'serhiy rebrov': 550,  # Serhiy Rebrov
    'artem dovbyk': 550,  # Artem Dovbyk
    'henrik mkhitaryan': 550,  # Henrik Mkhitaryan
    'arshavin': 550,  # Arshavin
    'andrey arshavin': 550,  # Andrey Arshavin
    'igor akinfeev': 550,  # Igor Akinfeev
    'rinat dasayev': 550,  # Rinat Dasayev
    'oleg salenko': 550,  # Oleg Salenko
    'valery lobanovskyi': 550,  # Valery Lobanovskyi
    'igor netto': 550,  # Igor Netto
    'eduard streltsov': 550,  # Eduard Streltsov
    'grigory fedotov': 550,  # Grigory Fedotov
    'vladimir beschastnykh': 550,  # Vladimir Beschastnykh
    'hakan sukur': 550,  # Hakan Sukur
    'arda turan': 550,  # Arda Turan
    'nihat kahveci': 550,  # Nihat Kahveci
    'emre belozoglu': 550,  # Emre Belozoglu
    'rustu recber': 550,  # Rustu Recber
    'tugay kerimoglu': 550,  # Tugay Kerimoglu
    'burak yilmaz': 550,  # Burak Yilmaz
    'hamit altintop': 550,  # Hamit Altintop
    'shota arveladze': 550,  # Shota Arveladze
    'kakha kaladze': 550,  # Kakha Kaladze
    'georgi kinkladze': 550,  # Georgi Kinkladze
    'gheorghe muresan': 550,  # Gheorghe Muresan
    'sandor kocsis': 550,  # Sándor Kocsis
    'nandor hidegkuti': 550,  # Nándor Hidegkuti
    'florian albert': 550,  # Florian Albert
    'laszlo kubala': 550,  # László Kubala
    'jozsef bozsik': 550,  # Jozsef Bozsik
    'gyula grosics': 550,  # Gyula Grosics
    'zoltan czibor': 550,  # Zoltan Czibor
    'istvan nyers': 550,  # Istvan Nyers
    'ferenc bene': 550,  # Ferenc Bene
    'lajos tichy': 550,  # Lajos Tichy
    'jozsef zakarias': 550,  # Jozsef Zakarias
    'dragan dzajic': 550,  # Dragan Dzajic
    'safet susic': 550,  # Safet Susic
    'mehmed bazdarevic': 550,  # Mehmed Bazdarevic
    'robert jarni': 550,  # Robert Jarni
    'alen boksic': 550,  # Alen Boksic
    'dario simic': 550,  # Dario Simic
    'ivica olic': 550,  # Ivica Olic
    'mario mandzukic': 550,  # Mario Mandzukic
    'ivan rakitic': 550,  # Ivan Rakitic
    'mateo kovacic': 550,  # Mateo Kovacic
    'marcelo brozovic': 550,  # Marcelo Brozovic
    'ivan perisic': 550,  # Ivan Perisic
    'josip simunic': 550,  # Josip Simunic
    'nemanja matic': 550,  # Nemanja Matic
    'branislav ivanovic': 550,  # Branislav Ivanovic
    'aleksandar kolarov': 550,  # Aleksandar Kolarov
    'sinisa mihajlovic': 550,  # Siniša Mihajlović
    'darko pancev': 550,  # Darko Pancev
    'vladimir jugovic': 550,  # Vladimir Jugovic
    'savo milosevic': 550,  # Savo Milosevic
    'hristo bonev': 550,  # Hristo Bonev
    'krasimir balakov': 550,  # Krasimir Balakov
    'yordan letchkov': 550,  # Yordan Letchkov
    'stiliyan petrov': 550,  # Stiliyan Petrov
    'dimitar penev': 550,  # Dimitar Penev
    'stoichkov': 550,  # Stoichkov
    'dumitru marcu': 550,  # Dumitru Marcu
    'gheorghe craioveanu': 550,  # Gheorghe Craioveanu
    'ilie dumitrescu': 550,  # Ilie Dumitrescu
    'miodrag belodedici': 550,  # Miodrag Belodedici
    'dorinel munteanu': 550,  # Dorinel Munteanu
    'adrian mutu': 550,  # Adrian Mutu
    'cristian chivu': 550,  # Cristian Chivu
    'ali daei': 550,  # Ali Daei
    'ali karimi': 550,  # Ali Karimi
    'mehdi mahdavikia': 550,  # Mehdi Mahdavikia
    'javad nekounam': 550,  # Javad Nekounam
    'ashkan dejagah': 550,  # Ashkan Dejagah
    'sardar azmoun': 550,  # Sardar Azmoun
    'mehdi taremi': 550,  # Mehdi Taremi
    'park ji sung': 550,  # Park Ji-sung
    'son heung min': 550,  # Son Heung-min
    'cha bum kun': 550,  # Cha Bum-kun
    'hong myung bo': 550,  # Hong Myung-bo
    'lee dong gook': 550,  # Lee Dong-gook
    'hidetoshi nakata': 550,  # Hidetoshi Nakata
    'shinji ono': 550,  # Shinji Ono
    'shunsuke nakamura': 550,  # Shunsuke Nakamura
    'keisuke honda': 550,  # Keisuke Honda
    'shinji kagawa': 550,  # Shinji Kagawa
    'takefusa kubo': 550,  # Takefusa Kubo
    'kaoru mitoma': 550,  # Kaoru Mitoma
    'maya yoshida': 550,  # Maya Yoshida
    'yasuhito endo': 550,  # Yasuhito Endo
    'kazuyoshi miura': 550,  # Kazuyoshi Miura
    'tim cahill': 550,  # Tim Cahill
    'harry kewell': 550,  # Harry Kewell
    'mark viduka': 550,  # Mark Viduka
    'mark schwarzer': 550,  # Mark Schwarzer
    'brett emerton': 550,  # Brett Emerton
    'lucas neill': 550,  # Lucas Neill
    'mile jedinak': 550,  # Mile Jedinak
    'sami al jaber': 550,  # Sami Al-Jaber
    'majed abdullah': 550,  # Majed Abdullah
    'yasser al qahtani': 550,  # Yasser Al-Qahtani
    'salem al dawsari': 550,  # Salem Al-Dawsari
    'saeed al owairan': 550,  # Saeed Al-Owairan
    'nawaf al temyat': 550,  # Nawaf Al-Temyat
    'mohamed noor': 550,  # Mohamed Noor
    'bader al mutawa': 550,  # Bader Al-Mutawa
    'jasem yaqoub': 550,  # Jasem Yaqoub
    'fahad al herafy': 550,  # Fahad Al-Herafy
    'bashar abdullah': 550,  # Bashar Abdullah
    'ahmed radhi': 550,  # Ahmed Radhi
    'younis mahmoud': 550,  # Younis Mahmoud
    'nashat akram': 550,  # Nashat Akram
    'hawar mulla mohammed': 550,  # Hawar Mulla Mohammed
    'alaa abdul zahra': 550,  # Alaa Abdul-Zahra
    'sunil chhetri': 550,  # Sunil Chhetri
    'bhaichung bhutia': 550,  # Bhaichung Bhutia
    'im vijayan': 550,  # IM Vijayan
    'gurpreet singh sandhu': 550,  # Gurpreet Singh Sandhu
    'ali ashfaq': 550,  # Ali Ashfaq
    'fandi ahmad': 550,  # Fandi Ahmad
    'bambang pamungkas': 550,  # Bambang Pamungkas
    'robby darwis': 550,  # Robby Darwis
    'rizky ridho': 550,  # Rizky Ridho
    'chanathip songkrasin': 550,  # Chanathip Songkrasin
    'teerasil dangda': 550,  # Teerasil Dangda
    'kiatisuk senamuang': 550,  # Kiatisuk Senamuang
    'le cong vinh': 550,  # Le Cong Vinh
    'nguyen quang hai': 550,  # Nguyen Quang Hai
    'le huynh đuc': 550,  # Lê Huỳnh Đức
    'soh chin aun': 550,  # Soh Chin Aun
    'safee sali': 550,  # Safee Sali
    'indra putra mahayuddin': 550,  # Indra Putra Mahayuddin
    'stefano lilipaly': 550,  # Stefano Lilipaly
    'neil etheridge': 550,  # Neil Etheridge
    'phil younghusband': 550,  # Phil Younghusband
    'paulino alcantara': 550,  # Paulino Alcántara
    'alyssa naeher': 550,  # Alyssa Naeher
    'jessie fleming': 550,  # Jessie Fleming
    'kadeisha buchanan': 550,  # Kadeisha Buchanan
    'ashley lawrence': 550,  # Ashley Lawrence
    'janine beckie': 550,  # Janine Beckie
    'christine latham': 550,  # Christine Latham
    'christine nairn': 550,  # Christine Nairn
    'carolina morace': 550,  # Carolina Morace
    'brandi chastain': 550,  # Brandi Chastain
    'julie johnston': 550,  # Julie Johnston
    'abby dahlkemper': 550,  # Abby Dahlkemper
    'becky sauerbrunn': 550,  # Becky Sauerbrunn
    'crystal dunn': 550,  # Crystal Dunn
    'emily sonnett': 550,  # Emily Sonnett
    'alyssa thompson': 550,  # Alyssa Thompson
    'michelle cooper': 550,  # Michelle Cooper
    'ali krieger': 550,  # Ali Krieger
    'christen press': 550,  # Christen Press
    'lauren cheney': 550,  # Lauren Cheney
    'amy rodriguez': 550,  # Amy Rodriguez
    'lynn williams': 550,  # Lynn Williams
    'sydney leroux': 550,  # Sydney Leroux
    'kristen hamilton': 550,  # Kristen Hamilton
    'sophie schmidt': 550,  # Sophie Schmidt
    'diana matheson': 550,  # Diana Matheson
    'charmaine hooper': 550,  # Charmaine Hooper
    'silvana burtini': 550,  # Silvana Burtini
    'andrea neil': 550,  # Andrea Neil
    'kara lang': 550,  # Kara Lang
    'marta cox': 550,  # Marta Cox
    'deyna castellanos': 550,  # Deyna Castellanos
    'yoreli rincon': 550,  # Yoreli Rincon
    'linda caicedo': 550,  # Linda Caicedo
    'mayra ramirez': 550,  # Mayra Ramirez
    'pretinha': 550,  # Pretinha
    'roseli': 550,  # Roseli
    'rosana': 550,  # Rosana
    'liu ailing': 550,  # Liu Ailing
    'pu wei': 550,  # Pu Wei
    'cho so hyun': 550,  # Cho So-hyun
    'caitlin foord': 550,  # Caitlin Foord
    'mary fowler': 550,  # Mary Fowler
    'steph catley': 550,  # Steph Catley
    'ellie carpenter': 550,  # Ellie Carpenter
    'hayley raso': 550,  # Hayley Raso
    'kyah simon': 550,  # Kyah Simon
    'lisa de vanna': 550,  # Lisa De Vanna
    'heather garriock': 550,  # Heather Garriock
    'cheryl salisbury': 550,  # Cheryl Salisbury
    'pia sundhage': 550,  # Pia Sundhage
    'silke rottenberg': 550,  # Silke Rottenberg
    'renate lingor': 550,  # Renate Lingor
    'inka grings': 550,  # Inka Grings
    'solveig gulbrandsen': 550,  # Solveig Gulbrandsen
    'maren mjelde': 550,  # Maren Mjelde
    'manon melis': 550,  # Manon Melis
    'sari van veenendaal': 550,  # Sari van Veenendaal
    'wieke kaptein': 550,  # Wieke Kaptein
    'alexandra popp': 550,  # Alexandra Popp
    'rachel daly': 550,  # Rachel Daly
    'beth england': 550,  # Beth England
    'steph houghton': 550,  # Steph Houghton
    'ousmane dembele': 550,  # Ousmane Dembele
    'antoine griezmann': 550,  # Antoine Griezmann
    'olivier giroud': 550,  # Olivier Giroud
    'karim benzema': 550,  # Karim Benzema
    'franck ribery': 550,  # Franck Ribery
    'eric abidal': 550,  # Eric Abidal
    'raphael varane': 550,  # Raphael Varane
    'n golo kante': 550,  # N'Golo Kante
    'paul pogba': 550,  # Paul Pogba
    'eduardo camavinga': 550,  # Eduardo Camavinga
    'aurelien tchouameni': 550,  # Aurelien Tchouameni
    'william saliba': 550,  # William Saliba
    'jules kounde': 550,  # Jules Kounde
    'theo hernandez': 550,  # Theo Hernandez
    'kingsley coman': 550,  # Kingsley Coman
    'blaise matuidi': 550,  # Blaise Matuidi
    'didier six': 550,  # Didier Six
    'luis enrique': 550,  # Luis Enrique
    'pep guardiola': 550,  # Pep Guardiola
    'luis suarez miramontes': 550,  # Luis Suarez Miramontes
    'josep samitier': 550,  # Josep Samitier
    'telmo zarra': 550,  # Telmo Zarra
    'andoni zubizarreta': 550,  # Andoni Zubizarreta
    'emilio butragueno': 550,  # Emilio Butragueno
    'raul gonzalez': 500,  # Raul Gonzalez
    'fernando morientes': 500,  # Fernando Morientes
    'juanito': 500,  # Juanito
    'quini': 500,  # Quini
    'jose antonio camacho': 500,  # Jose Antonio Camacho
    'manolo sanchis': 500,  # Manolo Sanchis
    'fernando redondo': 500,  # Fernando Redondo
    'fernando gago': 500,  # Fernando Gago
    'amancio amaro': 500,  # Amancio Amaro
    'luis arconada': 500,  # Luis Arconada
    'andoni goikoetxea': 500,  # Andoni Goikoetxea
    'julen guerrero': 500,  # Julen Guerrero
    'aritz aduriz': 500,  # Aritz Aduriz
    'mikel arteta': 500,  # Mikel Arteta
    'cesar azpilicueta': 500,  # Cesar Azpilicueta
    'santi cazorla': 500,  # Santi Cazorla
    'isco': 500,  # Isco
    'david de gea': 500,  # David de Gea
    'victor valdes': 500,  # Victor Valdes
    'pedro rodriguez': 500,  # Pedro Rodriguez
    'jordi alba': 500,  # Jordi Alba
    'sergio canales': 500,  # Sergio Canales
    'juan mata': 500,  # Juan Mata
    'david alaba': 500,  # David Alaba
    'marcel sabitzer': 500,  # Marcel Sabitzer
    'konrad laimer': 500,  # Konrad Laimer
    'david raum': 500,  # David Raum
    'florian wirtz': 500,  # Florian Wirtz
    'jamal musiala': 500,  # Jamal Musiala
    'kai havertz': 500,  # Kai Havertz
    'ilkay gundogan': 500,  # Ilkay Gundogan
    'mats hummels': 500,  # Mats Hummels
    'jerome boateng': 500,  # Jerome Boateng
    'mario gomez': 500,  # Mario Gomez
    'kevin kuranyi': 500,  # Kevin Kuranyi
    'torsten frings': 500,  # Torsten Frings
    'thomas hitzlsperger': 500,  # Thomas Hitzlsperger
    'oliver bierhoff': 500,  # Oliver Bierhoff
    'stefan kuntz': 500,  # Stefan Kuntz
    'andreas kopke': 500,  # Andreas Köpke
    'berti vogts': 500,  # Berti Vogts
    'rainer bonhof': 500,  # Rainer Bonhof
    'klaus allofs': 500,  # Klaus Allofs
    'klaus augenthaler': 500,  # Klaus Augenthaler
    'dieter hoeness': 500,  # Dieter Hoeness
    'fredi bobic': 500,  # Fredi Bobic
    'mehmet scholl': 500,  # Mehmet Scholl
    'lars ricken': 500,  # Lars Ricken
    'dieter muller': 500,  # Dieter Müller
    'horst szymaniak': 500,  # Horst Szymaniak
    'toni polster': 500,  # Toni Polster
    'hans krankl': 500,  # Hans Krankl
    'andreas herzog': 500,  # Andreas Herzog
    'ivica vastic': 500,  # Ivica Vastic
    'jan ceulemans': 500,  # Jan Ceulemans
    'enzo scifo': 500,  # Enzo Scifo
    'eden hazard': 500,  # Eden Hazard
    'kevin mirallas': 500,  # Kevin Mirallas
    'dries mertens': 500,  # Dries Mertens
    'romelu lukaku': 500,  # Romelu Lukaku
    'thibaut courtois': 500,  # Thibaut Courtois
    'jan vertonghen': 500,  # Jan Vertonghen
    'toby alderweireld': 500,  # Toby Alderweireld
    'axel witsel': 500,  # Axel Witsel
    'youri tielemans': 500,  # Youri Tielemans
    'thomas vermaelen': 500,  # Thomas Vermaelen
    'marc wilmots': 500,  # Marc Wilmots
    'franky van der elst': 500,  # Franky Van der Elst
    'paul van himst': 500,  # Paul Van Himst
    'jean marie pfaff': 500,  # Jean-Marie Pfaff
    'michel preud homme': 500,  # Michel Preud'homme
    'wim kieft': 500,  # Wim Kieft
    'frank rijkaard': 500,  # Frank Rijkaard
    'edwin van der sar': 500,  # Edwin van der Sar
    'jaap stam': 500,  # Jaap Stam
    'ronald koeman': 500,  # Ronald Koeman
    'frank de boer': 500,  # Frank de Boer
    'ronald de boer': 500,  # Ronald de Boer
    'clarence seedorf': 500,  # Clarence Seedorf
    'edgar davids': 500,  # Edgar Davids
    'philip cocu': 500,  # Philip Cocu
    'marc overmars': 500,  # Marc Overmars
    'pierre van hooijdonk': 500,  # Pierre van Hooijdonk
    'dirk kuyt': 500,  # Dirk Kuyt
    'ruud krol': 500,  # Ruud Krol
    'wim jansen': 500,  # Wim Jansen
    'johnny rep': 500,  # Johnny Rep
    'willy van de kerkhof': 500,  # Willy van de Kerkhof
    'diego godin': 500,  # Diego Godin
    'diego lugano': 500,  # Diego Lugano
    'luis alberto suarez': 500,  # Luis Alberto Suarez
    'alvaro recoba': 500,  # Alvaro Recoba
    'sebastian abreu': 500,  # Sebastian Abreu
    'diego perez': 500,  # Diego Perez
    'fernando muslera': 500,  # Fernando Muslera
    'darwin nunez': 500,  # Darwin Nunez
    'federico valverde': 500,  # Federico Valverde
    'ronald araujo': 500,  # Ronald Araujo
    'sebastian coates': 500,  # Sebastian Coates
    'jose santamaria': 500,  # Jose Santamaria
    'pablo bengoechea': 500,  # Pablo Bengoechea
    'ruben sosa': 500,  # Ruben Sosa
    'antonio alzamendi': 500,  # Antonio Alzamendi
    'juan pablo angel': 500,  # Juan Pablo Angel
    'mario yepes': 500,  # Mario Yepes
    'david ospina': 500,  # David Ospina
    'yerry mina': 500,  # Yerry Mina
    'juan fernando quintero': 500,  # Juan Fernando Quintero
    'teofilo gutierrez': 500,  # Teofilo Gutierrez
    'ivan ramiro cordoba': 500,  # Ivan Ramiro Cordoba
    'willington ortiz': 500,  # Willington Ortiz
    'arnoldo iguaran': 500,  # Arnoldo Iguaran
    'faryd mondragon': 500,  # Faryd Mondragon
    'carlos sanchez': 500,  # Carlos Sanchez
    'luis fernando muriel': 500,  # Luis Fernando Muriel
    'duvan zapata': 500,  # Duvan Zapata
    'jorge bermudez': 500,  # Jorge Bermudez
    'ivan kaviedes': 500,  # Ivan Kaviedes
    'agustin delgado': 500,  # Agustin Delgado
    'alberto spencer': 500,  # Alberto Spencer
    'christian benitez': 500,  # Christian Benitez
    'jefferson montero': 500,  # Jefferson Montero
    'pervis estupinan': 500,  # Pervis Estupinan
    'moises caicedo': 500,  # Moisés Caicedo
    'pablo zabaleta': 500,  # Pablo Zabaleta
    'javier saviola': 500,  # Javier Saviola
    'maxi rodriguez': 500,  # Maxi Rodriguez
    'ezequiel lavezzi': 500,  # Ezequiel Lavezzi
    'gonzalo higuain': 500,  # Gonzalo Higuain
    'juan arango': 500,  # Juan Arango
    'salomon rondon': 500,  # Salomon Rondon
    'josef martinez': 500,  # Josef Martinez
    'rafael dudamel': 500,  # Rafael Dudamel
    'bradley wright phillips': 500,  # Bradley Wright-Phillips
    'jozy altidore': 500,  # Jozy Altidore
    'brian mcbride': 500,  # Brian McBride
    'damarcus beasley': 500,  # DaMarcus Beasley
    'michael bradley': 500,  # Michael Bradley
    'clint mathis': 500,  # Clint Mathis
    'tab ramos': 500,  # Tab Ramos
    'eric wynalda': 500,  # Eric Wynalda
    'marcelo balboa': 500,  # Marcelo Balboa
    'carlos ruiz': 500,  # Carlos Ruiz
    'ramon ramirez': 500,  # Ramon Ramirez
    'luis hernandez': 500,  # Luis Hernandez
    'andres escobar': 500,  # Andres Escobar
    'pavel pardo': 500,  # Pavel Pardo
    'rafael marquez lugo': 500,  # Rafael Marquez Lugo
    'jared borgetti': 500,  # Jared Borgetti
    'luis roberto alves': 500,  # Luis Roberto Alves
    'claudio suarez': 500,  # Claudio Suarez
    'carlos hermosillo': 500,  # Carlos Hermosillo
    'hugo sanchez portugal': 500,  # Hugo Sanchez Portugal
    'baichung bhutia': 500,  # Baichung Bhutia
    'ali parvin': 500,  # Ali Parvin
    'khodadad azizi': 500,  # Khodadad Azizi
    'andranik teymourian': 500,  # Andranik Teymourian
    'park chu young': 500,  # Park Chu-young
    'ki sung yueng': 500,  # Ki Sung-yueng
    'hwang sun hong': 500,  # Hwang Sun-hong
    'cha du ri': 500,  # Cha Du-ri
    'lee young pyo': 500,  # Lee Young-pyo
    'kim joo sung': 500,  # Kim Joo-sung
    'shinji okazaki': 500,  # Shinji Okazaki
    'yuto nagatomo': 500,  # Yuto Nagatomo
    'makoto hasebe': 500,  # Makoto Hasebe
    'takumi minamino': 500,  # Takumi Minamino
    'daichi kamada': 500,  # Daichi Kamada
    'wataru endo': 500,  # Wataru Endo
    'ritsu doan': 500,  # Ritsu Doan
    'robbie slater': 500,  # Robbie Slater
    'archie thompson': 500,  # Archie Thompson
    'mark bosnich': 500,  # Mark Bosnich
    'ali mabkhout': 500,  # Ali Mabkhout
    'omar abdulrahman': 500,  # Omar Abdulrahman
    'ismail matar': 500,  # Ismail Matar
    'mohamed barakat': 500,  # Mohamed Barakat
    'tarek hamed': 500,  # Tarek Hamed
    'amr zaki': 500,  # Amr Zaki
    'mohamed nagy gedo': 500,  # Mohamed Nagy Gedo
    'noureddine naybet': 500,  # Noureddine Naybet
    'medhi benatia': 500,  # Medhi Benatia
    'youssef en nesyri': 500,  # Youssef En-Nesyri
    'abdelmajid dolmy': 500,  # Abdelmajid Dolmy
    'salaheddine bassir': 500,  # Salaheddine Bassir
    'tarik sektioui': 500,  # Tarik Sektioui
    'ali bencheikh': 500,  # Ali Bencheikh
    'sofiane feghouli': 500,  # Sofiane Feghouli
    'rachid mekhloufi': 500,  # Rachid Mekhloufi
    'mahamadou diarra': 500,  # Mahamadou Diarra
    'lauren etame mayer': 500,  # Lauren Etame Mayer
    'vincent enyeama': 500,  # Vincent Enyeama
    'sunday oliseh': 500,  # Sunday Oliseh
    'emmanuel amunike': 500,  # Emmanuel Amunike
    'daniel amokachi': 500,  # Daniel Amokachi
    'mutiu adepoju': 500,  # Mutiu Adepoju
    'emmanuel emenike': 500,  # Emmanuel Emenike
    'john utaka': 500,  # John Utaka
    'kanu nwankwo': 500,  # Kanu Nwankwo
    'stephen keshi': 500,  # Stephen Keshi
    'tijani babangida': 500,  # Tijani Babangida
    'taribo west': 500,  # Taribo West
    'austin okocha': 500,  # Austin Okocha
    'henri camara': 500,  # Henri Camara
    'habib beye': 500,  # Habib Beye
    'aliou cisse': 500,  # Aliou Cisse
    'moussa sow': 500,  # Moussa Sow
    'ismaila sarr': 500,  # Ismaila Sarr
    'idrissa gueye': 500,  # Idrissa Gueye
    'nicolas pepe': 500,  # Nicolas Pepe
    'christopher wreh': 500,  # Christopher Wreh
    'michael kojo essien': 500,  # Michael Kojo Essien
    'quinton fortune': 500,  # Quinton Fortune
    'aaron mokoena': 500,  # Aaron Mokoena
    'siphiwe tshabalala': 500,  # Siphiwe Tshabalala
    'teko modise': 500,  # Teko Modise
    'doctor khumalo': 500,  # Doctor Khumalo
    'mark fish': 500,  # Mark Fish
    'phil masinga': 500,  # Phil Masinga
    'john moshoeu': 500,  # John Moshoeu
    'christopher katongo': 500,  # Christopher Katongo
    'rainford kalaba': 500,  # Rainford Kalaba
    'godfrey chitalu': 500,  # Godfrey Chitalu
    'moses simwala': 500,  # Moses Simwala
    'abdul kadir': 500,  # Abdul Kadir
    'mohamed timoumi': 500,  # Mohamed Timoumi
    'ahmed faras': 500,  # Ahmed Faras
    'badou zaki': 500,  # Badou Zaki
    'mahmoud hassan trezeguet': 500,  # Mahmoud Hassan Trezeguet
    'salah hissou': 500,  # Salah Hissou
    'djalma feitosa dias': 500,  # Djalma Feitosa Dias
    'zizinho': 500,  # Zizinho
    'junior': 500,  # Júnior
    'eder aleixo': 500,  # Éder Aleixo
    'careca': 500,  # Careca
    'muller': 500,  # Müller
    'paulo roberto falcao': 500,  # Paulo Roberto Falcão
    'clodoaldo': 500,  # Clodoaldo
    'amarildo': 500,  # Amarildo
    'jose altafini': 500,  # José Altafini
    'giuseppe signori': 500,  # Giuseppe Signori
    'paolo rossi': 500,  # Paolo Rossi
    'bruno conti': 500,  # Bruno Conti
    'antonio cabrini': 500,  # Antonio Cabrini
    'fulvio collovati': 500,  # Fulvio Collovati
    'salvatore schillaci': 500,  # Salvatore Schillaci
    'marco amelia': 500,  # Marco Amelia
    'fernando couto': 500,  # Fernando Couto
    'rui costa': 500,  # Rui Costa
    'nuno gomes': 500,  # Nuno Gomes
}

# Curated display-name aliases for players whose REEP canonical labels differ.
POPULAR_PLAYER_ALIASES = {
    "lionel messi": ["Lionel Andrés Messi Cuccittini"],
    "cristiano ronaldo": ["Cristiano Ronaldo dos Santos Aveiro"],
    "pele": ["Édson Arantes do Nascimento", "Edson Arantes do Nascimento"],
    "ronaldinho": ["Ronaldo de Assis Moreira"],
    "ronaldo nazario": ["Ronaldo Luís Nazário de Lima", "Ronaldo Luis Nazario de Lima"],
    "andres iniesta": ["Andrés Iniesta Luján", "Andres Iniesta Lujan"],
    "xavi": ["Xavi Hernández", "Xavi Hernandez"],
    "vinicius junior": ["Vinícius José Paixão de Oliveira Júnior", "Vinicius Junior"],
    "kylian mbappe": ["Kylian Mbappé Lottin", "Kylian Mbappe"],
}

POPULAR_PLAYER_NAMES = {
    'lionel messi': 'Lionel Messi',
    'cristiano ronaldo': 'Cristiano Ronaldo',
    'neymar': 'Neymar',
    'kylian mbappe': 'Kylian Mbappe',
    'pele': 'Pele',
    'diego maradona': 'Diego Maradona',
    'ronaldinho': 'Ronaldinho',
    'zinedine zidane': 'Zinedine Zidane',
    'david beckham': 'David Beckham',
    'ronaldo nazario': 'Ronaldo Nazario',
    'mohamed salah': 'Mohamed Salah',
    'erling haaland': 'Erling Haaland',
    'kevin de bruyne': 'Kevin De Bruyne',
    'vinicius junior': 'Vinicius Junior',
    'jude bellingham': 'Jude Bellingham',
    'robert lewandowski': 'Robert Lewandowski',
    'luka modric': 'Luka Modric',
    'andres iniesta': 'Andres Iniesta',
    'xavi': 'Xavi',
    'thierry henry': 'Thierry Henry',
    'didier drogba': 'Didier Drogba',
    'samuel eto o': "Samuel Eto'o",
    'george weah': 'George Weah',
    'sadio mane': 'Sadio Mane',
    'yaya toure': 'Yaya Toure',
    'jay jay okocha': 'Jay-Jay Okocha',
    'riyad mahrez': 'Riyad Mahrez',
    'victor osimhen': 'Victor Osimhen',
    'franz beckenbauer': 'Franz Beckenbauer',
    'johan cruyff': 'Johan Cruyff',
    'alfredo di stefano': 'Alfredo Di Stefano',
    'ferenc puskas': 'Ferenc Puskas',
    'eusebio': 'Eusebio',
    'garrincha': 'Garrincha',
    'bobby charlton': 'Bobby Charlton',
    'george best': 'George Best',
    'michel platini': 'Michel Platini',
    'marco van basten': 'Marco van Basten',
    'ruud gullit': 'Ruud Gullit',
    'paolo maldini': 'Paolo Maldini',
    'franco baresi': 'Franco Baresi',
    'roberto baggio': 'Roberto Baggio',
    'gianluigi buffon': 'Gianluigi Buffon',
    'andrea pirlo': 'Andrea Pirlo',
    'fabio cannavaro': 'Fabio Cannavaro',
    'francesco totti': 'Francesco Totti',
    'alessandro del piero': 'Alessandro Del Piero',
    'gerd muller': 'Gerd Muller',
    'lothar matthaus': 'Lothar Matthaus',
    'miroslav klose': 'Miroslav Klose',
    'oliver kahn': 'Oliver Kahn',
    'philipp lahm': 'Philipp Lahm',
    'bastian schweinsteiger': 'Bastian Schweinsteiger',
    'thomas muller': 'Thomas Muller',
    'manuel neuer': 'Manuel Neuer',
    'toni kroos': 'Toni Kroos',
    'mesut ozil': 'Mesut Ozil',
    'rivaldo': 'Rivaldo',
    'romario': 'Romario',
    'kaka': 'Kaka',
    'roberto carlos': 'Roberto Carlos',
    'cafu': 'Cafu',
    'zico': 'Zico',
    'socrates': 'Socrates',
    'falcao': 'Falcao',
    'carlos valderrama': 'Carlos Valderrama',
    'hugo sanchez': 'Hugo Sanchez',
    'rafael marquez': 'Rafael Marquez',
    'javier zanetti': 'Javier Zanetti',
    'gabriel batistuta': 'Gabriel Batistuta',
    'juan roman riquelme': 'Juan Roman Riquelme',
    'carlos tevez': 'Carlos Tevez',
    'luis suarez': 'Luis Suarez',
    'edinson cavani': 'Edinson Cavani',
    'diego forlan': 'Diego Forlan',
    'enzo francescoli': 'Enzo Francescoli',
    'hristo stoichkov': 'Hristo Stoichkov',
    'dimitar berbatov': 'Dimitar Berbatov',
    'ryan giggs': 'Ryan Giggs',
    'paul scholes': 'Paul Scholes',
    'eric cantona': 'Eric Cantona',
    'wayne rooney': 'Wayne Rooney',
    'alan shearer': 'Alan Shearer',
    'steven gerrard': 'Steven Gerrard',
    'frank lampard': 'Frank Lampard',
    'paul gascoigne': 'Paul Gascoigne',
    'bobby moore': 'Bobby Moore',
    'gordon banks': 'Gordon Banks',
    'peter schmeichel': 'Peter Schmeichel',
    'dennis bergkamp': 'Dennis Bergkamp',
    'patrick vieira': 'Patrick Vieira',
    'roy keane': 'Roy Keane',
    'didier deschamps': 'Didier Deschamps',
    'claude makelele': 'Claude Makelele',
    'arjen robben': 'Arjen Robben',
    'wesley sneijder': 'Wesley Sneijder',
    'robin van persie': 'Robin van Persie',
    'ruud van nistelrooy': 'Ruud van Nistelrooy',
    'kenny dalglish': 'Kenny Dalglish',
    'ian rush': 'Ian Rush',
    'graeme souness': 'Graeme Souness',
    'john barnes': 'John Barnes',
    'david seaman': 'David Seaman',
    'tony adams': 'Tony Adams',
    'ian wright': 'Ian Wright',
    'michael owen': 'Michael Owen',
    'gary lineker': 'Gary Lineker',
    'peter shilton': 'Peter Shilton',
    'jimmy greaves': 'Jimmy Greaves',
    'stanley matthews': 'Stanley Matthews',
    'tom finney': 'Tom Finney',
    'kevin keegan': 'Kevin Keegan',
    'chris waddle': 'Chris Waddle',
    'gary neville': 'Gary Neville',
    'rio ferdinand': 'Rio Ferdinand',
    'john terry': 'John Terry',
    'ashley cole': 'Ashley Cole',
    'david silva': 'David Silva',
    'sergio aguero': 'Sergio Aguero',
    'vincent kompany': 'Vincent Kompany',
    'didier zokora': 'Didier Zokora',
    'cesc fabregas': 'Cesc Fabregas',
    'fernando torres': 'Fernando Torres',
    'xabi alonso': 'Xabi Alonso',
    'sergio ramos': 'Sergio Ramos',
    'iker casillas': 'Iker Casillas',
    'carles puyol': 'Carles Puyol',
    'gerard pique': 'Gerard Pique',
    'sergio busquets': 'Sergio Busquets',
    'david villa': 'David Villa',
    'fernando hierro': 'Fernando Hierro',
    'luis figo': 'Luis Figo',
    'deco': 'Deco',
    'pepe': 'Pepe',
    'bernardo silva': 'Bernardo Silva',
    'bruno fernandes': 'Bruno Fernandes',
    'ruben dias': 'Ruben Dias',
    'joao felix': 'Joao Felix',
    'joao cancelo': 'Joao Cancelo',
    'ricardo quaresma': 'Ricardo Quaresma',
    'nani': 'Nani',
    'pauleta': 'Pauleta',
    'eder': 'Eder',
    'gheorghe hagi': 'Gheorghe Hagi',
    'gheorghe popescu': 'Gheorghe Popescu',
    'davor suker': 'Davor Suker',
    'zvonimir boban': 'Zvonimir Boban',
    'robert prosinecki': 'Robert Prosinecki',
    'dejan savicevic': 'Dejan Savicevic',
    'dragan stojkovic': 'Dragan Stojkovic',
    'predrag mijatovic': 'Predrag Mijatovic',
    'nemanja vidic': 'Nemanja Vidic',
    'dejan stankovic': 'Dejan Stankovic',
    'edin dzeko': 'Edin Dzeko',
    'luka jovic': 'Luka Jovic',
    'zlatan ibrahimovic': 'Zlatan Ibrahimovic',
    'henrik larsson': 'Henrik Larsson',
    'freddie ljungberg': 'Freddie Ljungberg',
    'tomas brolin': 'Tomas Brolin',
    'anders svensson': 'Anders Svensson',
    'michael laudrup': 'Michael Laudrup',
    'brian laudrup': 'Brian Laudrup',
    'christian eriksen': 'Christian Eriksen',
    'erling braut haaland': 'Erling Braut Haaland',
    'martin odegaard': 'Martin Odegaard',
    'ole gunnar solskjaer': 'Ole Gunnar Solskjaer',
    'john arne riise': 'John Arne Riise',
    'kjetil rekdal': 'Kjetil Rekdal',
    'abedi pele': 'Abedi Pele',
    'asamoah gyan': 'Asamoah Gyan',
    'michael essien': 'Michael Essien',
    'sulley muntari': 'Sulley Muntari',
    'stephen appiah': 'Stephen Appiah',
    'tony yeboah': 'Tony Yeboah',
    'kwadwo asamoah': 'Kwadwo Asamoah',
    'thomas partey': 'Thomas Partey',
    'andre ayew': 'Andre Ayew',
    'jordan ayew': 'Jordan Ayew',
    'abedi ayew': 'Abedi Ayew',
    'rabah madjer': 'Rabah Madjer',
    'lakhdar belloumi': 'Lakhdar Belloumi',
    'mustapha hadji': 'Mustapha Hadji',
    'el hadji diouf': 'El Hadji Diouf',
    'kalusha bwalya': 'Kalusha Bwalya',
    'benni mccarthy': 'Benni McCarthy',
    'lucas radebe': 'Lucas Radebe',
    'steven pienaar': 'Steven Pienaar',
    'percy tau': 'Percy Tau',
    'bongani khumalo': 'Bongani Khumalo',
    'ahmed hassan': 'Ahmed Hassan',
    'mohamed aboutrika': 'Mohamed Aboutrika',
    'mahmoud el khatib': 'Mahmoud El Khatib',
    'essam el hadary': 'Essam El Hadary',
    'hossam hassan': 'Hossam Hassan',
    'islam slimani': 'Islam Slimani',
    'seydou keita': 'Seydou Keita',
    'frederic kanoute': 'Frederic Kanoute',
    'salif keita': 'Salif Keita',
    'roger milla': 'Roger Milla',
    'patrick mboma': 'Patrick Mboma',
    'lauren': 'Lauren',
    'rigobert song': 'Rigobert Song',
    'joseph yobo': 'Joseph Yobo',
    'nwankwo kanu': 'Nwankwo Kanu',
    'finidi george': 'Finidi George',
    'rashidi yekini': 'Rashidi Yekini',
    'victor ikpeba': 'Victor Ikpeba',
    'emmanuel adebayor': 'Emmanuel Adebayor',
    'adebayor': 'Adebayor',
    'seydou doumbia': 'Seydou Doumbia',
    'kolo toure': 'Kolo Toure',
    'emmanuel eboue': 'Emmanuel Eboue',
    'gervinho': 'Gervinho',
    'wilfried zaha': 'Wilfried Zaha',
    'wilfried bony': 'Wilfried Bony',
    'kalidou koulibaly': 'Kalidou Koulibaly',
    'papiss cisse': 'Papiss Cisse',
    'pierre emerick aubameyang': 'Pierre-Emerick Aubameyang',
    'achraf hakimi': 'Achraf Hakimi',
    'hakim ziyech': 'Hakim Ziyech',
    'mehdi benatia': 'Mehdi Benatia',
    'abdeljalil hadda': 'Abdeljalil Hadda',
    'hossam ghaly': 'Hossam Ghaly',
    'mohamed zidan': 'Mohamed Zidan',
    'mohamed elneny': 'Mohamed Elneny',
    'ramy bensebaini': 'Ramy Bensebaini',
    'john obi mikel': 'John Obi Mikel',
    'obafemi martins': 'Obafemi Martins',
    'yakubu aiyegbeni': 'Yakubu Aiyegbeni',
    'ahmed musa': 'Ahmed Musa',
    'jairzinho': 'Jairzinho',
    'didi': 'Didi',
    'vava': 'Vava',
    'tostao': 'Tostao',
    'carlos alberto torres': 'Carlos Alberto Torres',
    'nilton santos': 'Nilton Santos',
    'djalma santos': 'Djalma Santos',
    'friedenreich': 'Friedenreich',
    'leonidas da silva': 'Leonidas da Silva',
    'bebeto': 'Bebeto',
    'juninho pernambucano': 'Juninho Pernambucano',
    'juninho paulista': 'Juninho Paulista',
    'dunga': 'Dunga',
    'gilberto silva': 'Gilberto Silva',
    'ronaldo de assis moreira': 'Ronaldo de Assis Moreira',
    'adriano': 'Adriano',
    'robinho': 'Robinho',
    'alex de souza': 'Alex de Souza',
    'djalminha': 'Djalminha',
    'diego ribas': 'Diego Ribas',
    'rafinha': 'Rafinha',
    'dani alves': 'Dani Alves',
    'marcelo': 'Marcelo',
    'thiago silva': 'Thiago Silva',
    'alisson becker': 'Alisson Becker',
    'ederson': 'Ederson',
    'casemiro': 'Casemiro',
    'fabinho': 'Fabinho',
    'raphinha': 'Raphinha',
    'rodrygo': 'Rodrygo',
    'gabriel jesus': 'Gabriel Jesus',
    'gabriel martinelli': 'Gabriel Martinelli',
    'endrick': 'Endrick',
    'richarlison': 'Richarlison',
    'bruno guimaraes': 'Bruno Guimaraes',
    'alexis sanchez': 'Alexis Sanchez',
    'arturo vidal': 'Arturo Vidal',
    'ivan zamorano': 'Ivan Zamorano',
    'marcelo salas': 'Marcelo Salas',
    'claudio bravo': 'Claudio Bravo',
    'gary medel': 'Gary Medel',
    'james rodriguez': 'James Rodriguez',
    'radamel falcao': 'Radamel Falcao',
    'juan cuadrado': 'Juan Cuadrado',
    'luis diaz': 'Luis Diaz',
    'freddy rincon': 'Freddy Rincon',
    'faustino asprilla': 'Faustino Asprilla',
    'rene higuita': 'René Higuita',
    'ivan cordoba': 'Iván Córdoba',
    'enner valencia': 'Enner Valencia',
    'antonio valencia': 'Antonio Valencia',
    'alex aguinaga': 'Alex Aguinaga',
    'paolo guerrero': 'Paolo Guerrero',
    'claudio pizarro': 'Claudio Pizarro',
    'teofilo cubillas': 'Teofilo Cubillas',
    'hector chumpitaz': 'Hector Chumpitaz',
    'juan manuel vargas': 'Juan Manuel Vargas',
    'lionel scaloni': 'Lionel Scaloni',
    'angel di maria': 'Angel Di Maria',
    'javier mascherano': 'Javier Mascherano',
    'esteban cambiasso': 'Esteban Cambiasso',
    'hernan crespo': 'Hernan Crespo',
    'ariel ortega': 'Ariel Ortega',
    'pablo aimar': 'Pablo Aimar',
    'diego simeone': 'Diego Simeone',
    'sergio goycochea': 'Sergio Goycochea',
    'oscar ruggeri': 'Oscar Ruggeri',
    'mario kempes': 'Mario Kempes',
    'ubaldo fillol': 'Ubaldo Fillol',
    'daniel passarella': 'Daniel Passarella',
    'omar sivori': 'Omar Sivori',
    'keylor navas': 'Keylor Navas',
    'cuauhtemoc blanco': 'Cuauhtemoc Blanco',
    'jorge campos': 'Jorge Campos',
    'javier hernandez': 'Javier Hernandez',
    'andres guardado': 'Andres Guardado',
    'hirving lozano': 'Hirving Lozano',
    'giovani dos santos': 'Giovani dos Santos',
    'clint dempsey': 'Clint Dempsey',
    'landon donovan': 'Landon Donovan',
    'christian pulisic': 'Christian Pulisic',
    'tim howard': 'Tim Howard',
    'brad friedel': 'Brad Friedel',
    'claudio reyna': 'Claudio Reyna',
    'cobi jones': 'Cobi Jones',
    'mia hamm': 'Mia Hamm',
    'abby wambach': 'Abby Wambach',
    'megan rapinoe': 'Megan Rapinoe',
    'alex morgan': 'Alex Morgan',
    'carli lloyd': 'Carli Lloyd',
    'marta': 'Marta',
    'birgit prinz': 'Birgit Prinz',
    'homare sawa': 'Homare Sawa',
    'sun wen': 'Sun Wen',
    'michelle akers': 'Michelle Akers',
    'kristine lilly': 'Kristine Lilly',
    'christine sinclair': 'Christine Sinclair',
    'sam kerr': 'Sam Kerr',
    'aitana bonmati': 'Aitana Bonmati',
    'alexia putellas': 'Alexia Putellas',
    'ada hegerberg': 'Ada Hegerberg',
    'wendie renard': 'Wendie Renard',
    'lucy bronze': 'Lucy Bronze',
    'hope solo': 'Hope Solo',
    'briana scurry': 'Briana Scurry',
    'julie foudy': 'Julie Foudy',
    'tiffeny milbrett': 'Tiffeny Milbrett',
    'hege riise': 'Hege Riise',
    'kelly smith': 'Kelly Smith',
    'kelly lindsey': 'Kelly Lindsey',
    'kelly o hara': "Kelly O'Hara",
    'tobin heath': 'Tobin Heath',
    'lindsey horan': 'Lindsey Horan',
    'rose lavelle': 'Rose Lavelle',
    'sophia smith': 'Sophia Smith',
    'trinity rodman': 'Trinity Rodman',
    'mallory swanson': 'Mallory Swanson',
    'catarina macario': 'Catarina Macario',
    'lauren james': 'Lauren James',
    'alessia russo': 'Alessia Russo',
    'chloe kelly': 'Chloe Kelly',
    'fran kirby': 'Fran Kirby',
    'beth mead': 'Beth Mead',
    'mary earps': 'Mary Earps',
    'ellen white': 'Ellen White',
    'fara williams': 'Fara Williams',
    'rachel yankey': 'Rachel Yankey',
    'vivianne miedema': 'Vivianne Miedema',
    'lieke martens': 'Lieke Martens',
    'pernille harder': 'Pernille Harder',
    'caroline graham hansen': 'Caroline Graham Hansen',
    'ada stolsmo hegerberg': 'Ada Stolsmo Hegerberg',
    'alexia putellas segura': 'Alexia Putellas Segura',
    'irene paredes': 'Irene Paredes',
    'jennifer hermoso': 'Jennifer Hermoso',
    'salma paralluelo': 'Salma Paralluelo',
    'patri guijarro': 'Patri Guijarro',
    'olga carmona': 'Olga Carmona',
    'claudia pina': 'Claudia Pina',
    'keira walsh': 'Keira Walsh',
    'georgia stanway': 'Georgia Stanway',
    'lauren hemp': 'Lauren Hemp',
    'jill scott': 'Jill Scott',
    'eugenie le sommer': 'Eugénie Le Sommer',
    'amandine henry': 'Amandine Henry',
    'louisa necib': 'Louisa Nécib',
    'camille abily': 'Camille Abily',
    'marie laure delie': 'Marie-Laure Delie',
    'sakina karchaoui': 'Sakina Karchaoui',
    'kadidiatou diani': 'Kadidiatou Diani',
    'dzsenifer marozsan': 'Dzsenifer Marozsan',
    'nadine angerer': 'Nadine Angerer',
    'silvia neid': 'Silvia Neid',
    'maren meinert': 'Maren Meinert',
    'nilla fischer': 'Nilla Fischer',
    'lotta schelin': 'Lotta Schelin',
    'caroline seger': 'Caroline Seger',
    'hanna ljungberg': 'Hanna Ljungberg',
    'marta vieira da silva': 'Marta Vieira da Silva',
    'formiga': 'Formiga',
    'cristiane': 'Cristiane',
    'sissi': 'Sissi',
    'debinha': 'Debinha',
    'andressa alves': 'Andressa Alves',
    'kerolin': 'Kerolin',
    'geyse': 'Geyse',
    'yuki nagasato': 'Yuki Nagasato',
    'mana iwabuchi': 'Mana Iwabuchi',
    'aya miyama': 'Aya Miyama',
    'saki kumagai': 'Saki Kumagai',
    'yukari kinga': 'Yukari Kinga',
    'hanae shibata': 'Hanae Shibata',
    'ji so yun': 'Ji So-yun',
    'park eun sun': 'Park Eun-sun',
    'bai jie': 'Bai Jie',
    'wang shuang': 'Wang Shuang',
    'wang frost': 'Wang Frost',
    'yoko tanaka': 'Yoko Tanaka',
    'kozue ando': 'Kozue Ando',
    'nadine kessler': 'Nadine Kessler',
    'megan klingenberg': 'Megan Klingenberg',
    'julie ertz': 'Julie Ertz',
    'heather o reilly': "Heather O'Reilly",
    'shannon boxx': 'Shannon Boxx',
    'lori chalupny': 'Lori Chalupny',
    'christie pearce': 'Christie Pearce',
    'lev yashin': 'Lev Yashin',
    'dino zoff': 'Dino Zoff',
    'sepp maier': 'Sepp Maier',
    'ricardo zamora': 'Ricardo Zamora',
    'amadeo carrizo': 'Amadeo Carrizo',
    'jose leandro andrade': 'José Leandro Andrade',
    'obdulio varela': 'Obdulio Varela',
    'jose nasazzi': 'José Nasazzi',
    'alcides ghiggia': 'Alcides Ghiggia',
    'juan alberto schiaffino': 'Juan Alberto Schiaffino',
    'hector scarone': 'Héctor Scarone',
    'jose manuel moreno': 'José Manuel Moreno',
    'adolfo pedernera': 'Adolfo Pedernera',
    'angel labruna': 'Ángel Labruna',
    'oreste corbatta': 'Oreste Corbatta',
    'daniel alberto bertoni': 'Daniel Alberto Bertoni',
    'mario alberto kempes': 'Mario Alberto Kempes',
    'jorge valdano': 'Jorge Valdano',
    'jorge burruchaga': 'Jorge Burruchaga',
    'claudio caniggia': 'Claudio Caniggia',
    'juan sebastian veron': 'Juan Sebastián Verón',
    'walter samuel': 'Walter Samuel',
    'roberto ayala': 'Roberto Ayala',
    'gabriel heinze': 'Gabriel Heinze',
    'carlos marchena': 'Carlos Marchena',
    'david trezeguet': 'David Trezeguet',
    'emmanuel petit': 'Emmanuel Petit',
    'marcel desailly': 'Marcel Desailly',
    'lilian thuram': 'Lilian Thuram',
    'bixente lizarazu': 'Bixente Lizarazu',
    'laurent blanc': 'Laurent Blanc',
    'youri djorkaeff': 'Youri Djorkaeff',
    'robert pires': 'Robert Pirès',
    'sylvain wiltord': 'Sylvain Wiltord',
    'david ginola': 'David Ginola',
    'jean pierre papin': 'Jean-Pierre Papin',
    'just fontaine': 'Just Fontaine',
    'raymond kopa': 'Raymond Kopa',
    'alain giresse': 'Alain Giresse',
    'jean tigana': 'Jean Tigana',
    'dominique rocheteau': 'Dominique Rocheteau',
    'marius tresor': 'Marius Trésor',
    'patrick battiston': 'Patrick Battiston',
    'jean michel larque': 'Jean-Michel Larqué',
    'jean pierre adams': 'Jean-Pierre Adams',
    'jurgen klinsmann': 'Jürgen Klinsmann',
    'rudi voller': 'Rudi Völler',
    'andreas brehme': 'Andreas Brehme',
    'karl heinz rummenigge': 'Karl-Heinz Rummenigge',
    'uwe seeler': 'Uwe Seeler',
    'fritz walter': 'Fritz Walter',
    'helmut rahn': 'Helmut Rahn',
    'paul breitner': 'Paul Breitner',
    'bernd holzenbein': 'Bernd Hölzenbein',
    'horst hrubesch': 'Horst Hrubesch',
    'jurgen kohler': 'Jürgen Kohler',
    'matthias sammer': 'Matthias Sammer',
    'michael ballack': 'Michael Ballack',
    'lukas podolski': 'Lukas Podolski',
    'jens lehmann': 'Jens Lehmann',
    'bernd schuster': 'Bernd Schuster',
    'gunter netzer': 'Günter Netzer',
    'andreas moller': 'Andreas Möller',
    'stefan effenberg': 'Stefan Effenberg',
    'pierre littbarski': 'Pierre Littbarski',
    'klaus fischer': 'Klaus Fischer',
    'karl heinz schnellinger': 'Karl-Heinz Schnellinger',
    'hans schafer': 'Hans Schäfer',
    'giuseppe meazza': 'Giuseppe Meazza',
    'silvio piola': 'Silvio Piola',
    'gianni rivera': 'Gianni Rivera',
    'gigi riva': 'Gigi Riva',
    'roberto donadoni': 'Roberto Donadoni',
    'demetrio albertini': 'Demetrio Albertini',
    'angelo peruzzi': 'Angelo Peruzzi',
    'christian vieri': 'Christian Vieri',
    'filippo inzaghi': 'Filippo Inzaghi',
    'gianluca vialli': 'Gianluca Vialli',
    'roberto mancini': 'Roberto Mancini',
    'antonio di natale': 'Antonio Di Natale',
    'daniele de rossi': 'Daniele De Rossi',
    'gennaro gattuso': 'Gennaro Gattuso',
    'marco tardelli': 'Marco Tardelli',
    'claudio gentile': 'Claudio Gentile',
    'giuseppe bergomi': 'Giuseppe Bergomi',
    'gaetano scirea': 'Gaetano Scirea',
    'dino baggio': 'Dino Baggio',
    'christian panucci': 'Christian Panucci',
    'angelo di livio': 'Angelo Di Livio',
    'marco materazzi': 'Marco Materazzi',
    'giorgio chiellini': 'Giorgio Chiellini',
    'leonardo bonucci': 'Leonardo Bonucci',
    'gianluca zambrotta': 'Gianluca Zambrotta',
    'gianfranco zola': 'Gianfranco Zola',
    'pierluigi casiraghi': 'Pierluigi Casiraghi',
    'massimo oddo': 'Massimo Oddo',
    'mauro camoranesi': 'Mauro Camoranesi',
    'pavel nedved': 'Pavel Nedved',
    'josef masopust': 'Josef Masopust',
    'antonin panenka': 'Antonin Panenka',
    'petr cech': 'Petr Cech',
    'tomas rosicky': 'Tomas Rosicky',
    'pavel kuka': 'Pavel Kuka',
    'jan koller': 'Jan Koller',
    'marek hamsik': 'Marek Hamsik',
    'milan baros': 'Milan Baros',
    'peter dubovsky': 'Peter Dubovsky',
    'andriy shevchenko': 'Andriy Shevchenko',
    'oleh blokhin': 'Oleh Blokhin',
    'igor belanov': 'Igor Belanov',
    'andrei kanchelskis': 'Andrei Kanchelskis',
    'anatoliy tymoshchuk': 'Anatoliy Tymoshchuk',
    'serhiy rebrov': 'Serhiy Rebrov',
    'artem dovbyk': 'Artem Dovbyk',
    'henrik mkhitaryan': 'Henrik Mkhitaryan',
    'arshavin': 'Arshavin',
    'andrey arshavin': 'Andrey Arshavin',
    'igor akinfeev': 'Igor Akinfeev',
    'rinat dasayev': 'Rinat Dasayev',
    'oleg salenko': 'Oleg Salenko',
    'valery lobanovskyi': 'Valery Lobanovskyi',
    'igor netto': 'Igor Netto',
    'eduard streltsov': 'Eduard Streltsov',
    'grigory fedotov': 'Grigory Fedotov',
    'vladimir beschastnykh': 'Vladimir Beschastnykh',
    'hakan sukur': 'Hakan Sukur',
    'arda turan': 'Arda Turan',
    'nihat kahveci': 'Nihat Kahveci',
    'emre belozoglu': 'Emre Belozoglu',
    'rustu recber': 'Rustu Recber',
    'tugay kerimoglu': 'Tugay Kerimoglu',
    'burak yilmaz': 'Burak Yilmaz',
    'hamit altintop': 'Hamit Altintop',
    'shota arveladze': 'Shota Arveladze',
    'kakha kaladze': 'Kakha Kaladze',
    'georgi kinkladze': 'Georgi Kinkladze',
    'gheorghe muresan': 'Gheorghe Muresan',
    'sandor kocsis': 'Sándor Kocsis',
    'nandor hidegkuti': 'Nándor Hidegkuti',
    'florian albert': 'Florian Albert',
    'laszlo kubala': 'László Kubala',
    'jozsef bozsik': 'Jozsef Bozsik',
    'gyula grosics': 'Gyula Grosics',
    'zoltan czibor': 'Zoltan Czibor',
    'istvan nyers': 'Istvan Nyers',
    'ferenc bene': 'Ferenc Bene',
    'lajos tichy': 'Lajos Tichy',
    'jozsef zakarias': 'Jozsef Zakarias',
    'dragan dzajic': 'Dragan Dzajic',
    'safet susic': 'Safet Susic',
    'mehmed bazdarevic': 'Mehmed Bazdarevic',
    'robert jarni': 'Robert Jarni',
    'alen boksic': 'Alen Boksic',
    'dario simic': 'Dario Simic',
    'ivica olic': 'Ivica Olic',
    'mario mandzukic': 'Mario Mandzukic',
    'ivan rakitic': 'Ivan Rakitic',
    'mateo kovacic': 'Mateo Kovacic',
    'marcelo brozovic': 'Marcelo Brozovic',
    'ivan perisic': 'Ivan Perisic',
    'josip simunic': 'Josip Simunic',
    'nemanja matic': 'Nemanja Matic',
    'branislav ivanovic': 'Branislav Ivanovic',
    'aleksandar kolarov': 'Aleksandar Kolarov',
    'sinisa mihajlovic': 'Siniša Mihajlović',
    'darko pancev': 'Darko Pancev',
    'vladimir jugovic': 'Vladimir Jugovic',
    'savo milosevic': 'Savo Milosevic',
    'hristo bonev': 'Hristo Bonev',
    'krasimir balakov': 'Krasimir Balakov',
    'yordan letchkov': 'Yordan Letchkov',
    'stiliyan petrov': 'Stiliyan Petrov',
    'dimitar penev': 'Dimitar Penev',
    'stoichkov': 'Stoichkov',
    'dumitru marcu': 'Dumitru Marcu',
    'gheorghe craioveanu': 'Gheorghe Craioveanu',
    'ilie dumitrescu': 'Ilie Dumitrescu',
    'miodrag belodedici': 'Miodrag Belodedici',
    'dorinel munteanu': 'Dorinel Munteanu',
    'adrian mutu': 'Adrian Mutu',
    'cristian chivu': 'Cristian Chivu',
    'ali daei': 'Ali Daei',
    'ali karimi': 'Ali Karimi',
    'mehdi mahdavikia': 'Mehdi Mahdavikia',
    'javad nekounam': 'Javad Nekounam',
    'ashkan dejagah': 'Ashkan Dejagah',
    'sardar azmoun': 'Sardar Azmoun',
    'mehdi taremi': 'Mehdi Taremi',
    'park ji sung': 'Park Ji-sung',
    'son heung min': 'Son Heung-min',
    'cha bum kun': 'Cha Bum-kun',
    'hong myung bo': 'Hong Myung-bo',
    'lee dong gook': 'Lee Dong-gook',
    'hidetoshi nakata': 'Hidetoshi Nakata',
    'shinji ono': 'Shinji Ono',
    'shunsuke nakamura': 'Shunsuke Nakamura',
    'keisuke honda': 'Keisuke Honda',
    'shinji kagawa': 'Shinji Kagawa',
    'takefusa kubo': 'Takefusa Kubo',
    'kaoru mitoma': 'Kaoru Mitoma',
    'maya yoshida': 'Maya Yoshida',
    'yasuhito endo': 'Yasuhito Endo',
    'kazuyoshi miura': 'Kazuyoshi Miura',
    'tim cahill': 'Tim Cahill',
    'harry kewell': 'Harry Kewell',
    'mark viduka': 'Mark Viduka',
    'mark schwarzer': 'Mark Schwarzer',
    'brett emerton': 'Brett Emerton',
    'lucas neill': 'Lucas Neill',
    'mile jedinak': 'Mile Jedinak',
    'sami al jaber': 'Sami Al-Jaber',
    'majed abdullah': 'Majed Abdullah',
    'yasser al qahtani': 'Yasser Al-Qahtani',
    'salem al dawsari': 'Salem Al-Dawsari',
    'saeed al owairan': 'Saeed Al-Owairan',
    'nawaf al temyat': 'Nawaf Al-Temyat',
    'mohamed noor': 'Mohamed Noor',
    'bader al mutawa': 'Bader Al-Mutawa',
    'jasem yaqoub': 'Jasem Yaqoub',
    'fahad al herafy': 'Fahad Al-Herafy',
    'bashar abdullah': 'Bashar Abdullah',
    'ahmed radhi': 'Ahmed Radhi',
    'younis mahmoud': 'Younis Mahmoud',
    'nashat akram': 'Nashat Akram',
    'hawar mulla mohammed': 'Hawar Mulla Mohammed',
    'alaa abdul zahra': 'Alaa Abdul-Zahra',
    'sunil chhetri': 'Sunil Chhetri',
    'bhaichung bhutia': 'Bhaichung Bhutia',
    'im vijayan': 'IM Vijayan',
    'gurpreet singh sandhu': 'Gurpreet Singh Sandhu',
    'ali ashfaq': 'Ali Ashfaq',
    'fandi ahmad': 'Fandi Ahmad',
    'bambang pamungkas': 'Bambang Pamungkas',
    'robby darwis': 'Robby Darwis',
    'rizky ridho': 'Rizky Ridho',
    'chanathip songkrasin': 'Chanathip Songkrasin',
    'teerasil dangda': 'Teerasil Dangda',
    'kiatisuk senamuang': 'Kiatisuk Senamuang',
    'le cong vinh': 'Le Cong Vinh',
    'nguyen quang hai': 'Nguyen Quang Hai',
    'le huynh đuc': 'Lê Huỳnh Đức',
    'soh chin aun': 'Soh Chin Aun',
    'safee sali': 'Safee Sali',
    'indra putra mahayuddin': 'Indra Putra Mahayuddin',
    'stefano lilipaly': 'Stefano Lilipaly',
    'neil etheridge': 'Neil Etheridge',
    'phil younghusband': 'Phil Younghusband',
    'paulino alcantara': 'Paulino Alcántara',
    'alyssa naeher': 'Alyssa Naeher',
    'jessie fleming': 'Jessie Fleming',
    'kadeisha buchanan': 'Kadeisha Buchanan',
    'ashley lawrence': 'Ashley Lawrence',
    'janine beckie': 'Janine Beckie',
    'christine latham': 'Christine Latham',
    'christine nairn': 'Christine Nairn',
    'carolina morace': 'Carolina Morace',
    'brandi chastain': 'Brandi Chastain',
    'julie johnston': 'Julie Johnston',
    'abby dahlkemper': 'Abby Dahlkemper',
    'becky sauerbrunn': 'Becky Sauerbrunn',
    'crystal dunn': 'Crystal Dunn',
    'emily sonnett': 'Emily Sonnett',
    'alyssa thompson': 'Alyssa Thompson',
    'michelle cooper': 'Michelle Cooper',
    'ali krieger': 'Ali Krieger',
    'christen press': 'Christen Press',
    'lauren cheney': 'Lauren Cheney',
    'amy rodriguez': 'Amy Rodriguez',
    'lynn williams': 'Lynn Williams',
    'sydney leroux': 'Sydney Leroux',
    'kristen hamilton': 'Kristen Hamilton',
    'sophie schmidt': 'Sophie Schmidt',
    'diana matheson': 'Diana Matheson',
    'charmaine hooper': 'Charmaine Hooper',
    'silvana burtini': 'Silvana Burtini',
    'andrea neil': 'Andrea Neil',
    'kara lang': 'Kara Lang',
    'marta cox': 'Marta Cox',
    'deyna castellanos': 'Deyna Castellanos',
    'yoreli rincon': 'Yoreli Rincon',
    'linda caicedo': 'Linda Caicedo',
    'mayra ramirez': 'Mayra Ramirez',
    'pretinha': 'Pretinha',
    'roseli': 'Roseli',
    'rosana': 'Rosana',
    'liu ailing': 'Liu Ailing',
    'pu wei': 'Pu Wei',
    'cho so hyun': 'Cho So-hyun',
    'caitlin foord': 'Caitlin Foord',
    'mary fowler': 'Mary Fowler',
    'steph catley': 'Steph Catley',
    'ellie carpenter': 'Ellie Carpenter',
    'hayley raso': 'Hayley Raso',
    'kyah simon': 'Kyah Simon',
    'lisa de vanna': 'Lisa De Vanna',
    'heather garriock': 'Heather Garriock',
    'cheryl salisbury': 'Cheryl Salisbury',
    'pia sundhage': 'Pia Sundhage',
    'silke rottenberg': 'Silke Rottenberg',
    'renate lingor': 'Renate Lingor',
    'inka grings': 'Inka Grings',
    'solveig gulbrandsen': 'Solveig Gulbrandsen',
    'maren mjelde': 'Maren Mjelde',
    'manon melis': 'Manon Melis',
    'sari van veenendaal': 'Sari van Veenendaal',
    'wieke kaptein': 'Wieke Kaptein',
    'alexandra popp': 'Alexandra Popp',
    'rachel daly': 'Rachel Daly',
    'beth england': 'Beth England',
    'steph houghton': 'Steph Houghton',
    'ousmane dembele': 'Ousmane Dembele',
    'antoine griezmann': 'Antoine Griezmann',
    'olivier giroud': 'Olivier Giroud',
    'karim benzema': 'Karim Benzema',
    'franck ribery': 'Franck Ribery',
    'eric abidal': 'Eric Abidal',
    'raphael varane': 'Raphael Varane',
    'n golo kante': "N'Golo Kante",
    'paul pogba': 'Paul Pogba',
    'eduardo camavinga': 'Eduardo Camavinga',
    'aurelien tchouameni': 'Aurelien Tchouameni',
    'william saliba': 'William Saliba',
    'jules kounde': 'Jules Kounde',
    'theo hernandez': 'Theo Hernandez',
    'kingsley coman': 'Kingsley Coman',
    'blaise matuidi': 'Blaise Matuidi',
    'didier six': 'Didier Six',
    'luis enrique': 'Luis Enrique',
    'pep guardiola': 'Pep Guardiola',
    'luis suarez miramontes': 'Luis Suarez Miramontes',
    'josep samitier': 'Josep Samitier',
    'telmo zarra': 'Telmo Zarra',
    'andoni zubizarreta': 'Andoni Zubizarreta',
    'emilio butragueno': 'Emilio Butragueno',
    'raul gonzalez': 'Raul Gonzalez',
    'fernando morientes': 'Fernando Morientes',
    'juanito': 'Juanito',
    'quini': 'Quini',
    'jose antonio camacho': 'Jose Antonio Camacho',
    'manolo sanchis': 'Manolo Sanchis',
    'fernando redondo': 'Fernando Redondo',
    'fernando gago': 'Fernando Gago',
    'amancio amaro': 'Amancio Amaro',
    'luis arconada': 'Luis Arconada',
    'andoni goikoetxea': 'Andoni Goikoetxea',
    'julen guerrero': 'Julen Guerrero',
    'aritz aduriz': 'Aritz Aduriz',
    'mikel arteta': 'Mikel Arteta',
    'cesar azpilicueta': 'Cesar Azpilicueta',
    'santi cazorla': 'Santi Cazorla',
    'isco': 'Isco',
    'david de gea': 'David de Gea',
    'victor valdes': 'Victor Valdes',
    'pedro rodriguez': 'Pedro Rodriguez',
    'jordi alba': 'Jordi Alba',
    'sergio canales': 'Sergio Canales',
    'juan mata': 'Juan Mata',
    'david alaba': 'David Alaba',
    'marcel sabitzer': 'Marcel Sabitzer',
    'konrad laimer': 'Konrad Laimer',
    'david raum': 'David Raum',
    'florian wirtz': 'Florian Wirtz',
    'jamal musiala': 'Jamal Musiala',
    'kai havertz': 'Kai Havertz',
    'ilkay gundogan': 'Ilkay Gundogan',
    'mats hummels': 'Mats Hummels',
    'jerome boateng': 'Jerome Boateng',
    'mario gomez': 'Mario Gomez',
    'kevin kuranyi': 'Kevin Kuranyi',
    'torsten frings': 'Torsten Frings',
    'thomas hitzlsperger': 'Thomas Hitzlsperger',
    'oliver bierhoff': 'Oliver Bierhoff',
    'stefan kuntz': 'Stefan Kuntz',
    'andreas kopke': 'Andreas Köpke',
    'berti vogts': 'Berti Vogts',
    'rainer bonhof': 'Rainer Bonhof',
    'klaus allofs': 'Klaus Allofs',
    'klaus augenthaler': 'Klaus Augenthaler',
    'dieter hoeness': 'Dieter Hoeness',
    'fredi bobic': 'Fredi Bobic',
    'mehmet scholl': 'Mehmet Scholl',
    'lars ricken': 'Lars Ricken',
    'dieter muller': 'Dieter Müller',
    'horst szymaniak': 'Horst Szymaniak',
    'toni polster': 'Toni Polster',
    'hans krankl': 'Hans Krankl',
    'andreas herzog': 'Andreas Herzog',
    'ivica vastic': 'Ivica Vastic',
    'jan ceulemans': 'Jan Ceulemans',
    'enzo scifo': 'Enzo Scifo',
    'eden hazard': 'Eden Hazard',
    'kevin mirallas': 'Kevin Mirallas',
    'dries mertens': 'Dries Mertens',
    'romelu lukaku': 'Romelu Lukaku',
    'thibaut courtois': 'Thibaut Courtois',
    'jan vertonghen': 'Jan Vertonghen',
    'toby alderweireld': 'Toby Alderweireld',
    'axel witsel': 'Axel Witsel',
    'youri tielemans': 'Youri Tielemans',
    'thomas vermaelen': 'Thomas Vermaelen',
    'marc wilmots': 'Marc Wilmots',
    'franky van der elst': 'Franky Van der Elst',
    'paul van himst': 'Paul Van Himst',
    'jean marie pfaff': 'Jean-Marie Pfaff',
    'michel preud homme': "Michel Preud'homme",
    'wim kieft': 'Wim Kieft',
    'frank rijkaard': 'Frank Rijkaard',
    'edwin van der sar': 'Edwin van der Sar',
    'jaap stam': 'Jaap Stam',
    'ronald koeman': 'Ronald Koeman',
    'frank de boer': 'Frank de Boer',
    'ronald de boer': 'Ronald de Boer',
    'clarence seedorf': 'Clarence Seedorf',
    'edgar davids': 'Edgar Davids',
    'philip cocu': 'Philip Cocu',
    'marc overmars': 'Marc Overmars',
    'pierre van hooijdonk': 'Pierre van Hooijdonk',
    'dirk kuyt': 'Dirk Kuyt',
    'ruud krol': 'Ruud Krol',
    'wim jansen': 'Wim Jansen',
    'johnny rep': 'Johnny Rep',
    'willy van de kerkhof': 'Willy van de Kerkhof',
    'diego godin': 'Diego Godin',
    'diego lugano': 'Diego Lugano',
    'luis alberto suarez': 'Luis Alberto Suarez',
    'alvaro recoba': 'Alvaro Recoba',
    'sebastian abreu': 'Sebastian Abreu',
    'diego perez': 'Diego Perez',
    'fernando muslera': 'Fernando Muslera',
    'darwin nunez': 'Darwin Nunez',
    'federico valverde': 'Federico Valverde',
    'ronald araujo': 'Ronald Araujo',
    'sebastian coates': 'Sebastian Coates',
    'jose santamaria': 'Jose Santamaria',
    'pablo bengoechea': 'Pablo Bengoechea',
    'ruben sosa': 'Ruben Sosa',
    'antonio alzamendi': 'Antonio Alzamendi',
    'juan pablo angel': 'Juan Pablo Angel',
    'mario yepes': 'Mario Yepes',
    'david ospina': 'David Ospina',
    'yerry mina': 'Yerry Mina',
    'juan fernando quintero': 'Juan Fernando Quintero',
    'teofilo gutierrez': 'Teofilo Gutierrez',
    'ivan ramiro cordoba': 'Ivan Ramiro Cordoba',
    'willington ortiz': 'Willington Ortiz',
    'arnoldo iguaran': 'Arnoldo Iguaran',
    'faryd mondragon': 'Faryd Mondragon',
    'carlos sanchez': 'Carlos Sanchez',
    'luis fernando muriel': 'Luis Fernando Muriel',
    'duvan zapata': 'Duvan Zapata',
    'jorge bermudez': 'Jorge Bermudez',
    'ivan kaviedes': 'Ivan Kaviedes',
    'agustin delgado': 'Agustin Delgado',
    'alberto spencer': 'Alberto Spencer',
    'christian benitez': 'Christian Benitez',
    'jefferson montero': 'Jefferson Montero',
    'pervis estupinan': 'Pervis Estupinan',
    'moises caicedo': 'Moisés Caicedo',
    'pablo zabaleta': 'Pablo Zabaleta',
    'javier saviola': 'Javier Saviola',
    'maxi rodriguez': 'Maxi Rodriguez',
    'ezequiel lavezzi': 'Ezequiel Lavezzi',
    'gonzalo higuain': 'Gonzalo Higuain',
    'juan arango': 'Juan Arango',
    'salomon rondon': 'Salomon Rondon',
    'josef martinez': 'Josef Martinez',
    'rafael dudamel': 'Rafael Dudamel',
    'bradley wright phillips': 'Bradley Wright-Phillips',
    'jozy altidore': 'Jozy Altidore',
    'brian mcbride': 'Brian McBride',
    'damarcus beasley': 'DaMarcus Beasley',
    'michael bradley': 'Michael Bradley',
    'clint mathis': 'Clint Mathis',
    'tab ramos': 'Tab Ramos',
    'eric wynalda': 'Eric Wynalda',
    'marcelo balboa': 'Marcelo Balboa',
    'carlos ruiz': 'Carlos Ruiz',
    'ramon ramirez': 'Ramon Ramirez',
    'luis hernandez': 'Luis Hernandez',
    'andres escobar': 'Andres Escobar',
    'pavel pardo': 'Pavel Pardo',
    'rafael marquez lugo': 'Rafael Marquez Lugo',
    'jared borgetti': 'Jared Borgetti',
    'luis roberto alves': 'Luis Roberto Alves',
    'claudio suarez': 'Claudio Suarez',
    'carlos hermosillo': 'Carlos Hermosillo',
    'hugo sanchez portugal': 'Hugo Sanchez Portugal',
    'baichung bhutia': 'Baichung Bhutia',
    'ali parvin': 'Ali Parvin',
    'khodadad azizi': 'Khodadad Azizi',
    'andranik teymourian': 'Andranik Teymourian',
    'park chu young': 'Park Chu-young',
    'ki sung yueng': 'Ki Sung-yueng',
    'hwang sun hong': 'Hwang Sun-hong',
    'cha du ri': 'Cha Du-ri',
    'lee young pyo': 'Lee Young-pyo',
    'kim joo sung': 'Kim Joo-sung',
    'shinji okazaki': 'Shinji Okazaki',
    'yuto nagatomo': 'Yuto Nagatomo',
    'makoto hasebe': 'Makoto Hasebe',
    'takumi minamino': 'Takumi Minamino',
    'daichi kamada': 'Daichi Kamada',
    'wataru endo': 'Wataru Endo',
    'ritsu doan': 'Ritsu Doan',
    'robbie slater': 'Robbie Slater',
    'archie thompson': 'Archie Thompson',
    'mark bosnich': 'Mark Bosnich',
    'ali mabkhout': 'Ali Mabkhout',
    'omar abdulrahman': 'Omar Abdulrahman',
    'ismail matar': 'Ismail Matar',
    'mohamed barakat': 'Mohamed Barakat',
    'tarek hamed': 'Tarek Hamed',
    'amr zaki': 'Amr Zaki',
    'mohamed nagy gedo': 'Mohamed Nagy Gedo',
    'noureddine naybet': 'Noureddine Naybet',
    'medhi benatia': 'Medhi Benatia',
    'youssef en nesyri': 'Youssef En-Nesyri',
    'abdelmajid dolmy': 'Abdelmajid Dolmy',
    'salaheddine bassir': 'Salaheddine Bassir',
    'tarik sektioui': 'Tarik Sektioui',
    'ali bencheikh': 'Ali Bencheikh',
    'sofiane feghouli': 'Sofiane Feghouli',
    'rachid mekhloufi': 'Rachid Mekhloufi',
    'mahamadou diarra': 'Mahamadou Diarra',
    'lauren etame mayer': 'Lauren Etame Mayer',
    'vincent enyeama': 'Vincent Enyeama',
    'sunday oliseh': 'Sunday Oliseh',
    'emmanuel amunike': 'Emmanuel Amunike',
    'daniel amokachi': 'Daniel Amokachi',
    'mutiu adepoju': 'Mutiu Adepoju',
    'emmanuel emenike': 'Emmanuel Emenike',
    'john utaka': 'John Utaka',
    'kanu nwankwo': 'Kanu Nwankwo',
    'stephen keshi': 'Stephen Keshi',
    'tijani babangida': 'Tijani Babangida',
    'taribo west': 'Taribo West',
    'austin okocha': 'Austin Okocha',
    'henri camara': 'Henri Camara',
    'habib beye': 'Habib Beye',
    'aliou cisse': 'Aliou Cisse',
    'moussa sow': 'Moussa Sow',
    'ismaila sarr': 'Ismaila Sarr',
    'idrissa gueye': 'Idrissa Gueye',
    'nicolas pepe': 'Nicolas Pepe',
    'christopher wreh': 'Christopher Wreh',
    'michael kojo essien': 'Michael Kojo Essien',
    'quinton fortune': 'Quinton Fortune',
    'aaron mokoena': 'Aaron Mokoena',
    'siphiwe tshabalala': 'Siphiwe Tshabalala',
    'teko modise': 'Teko Modise',
    'doctor khumalo': 'Doctor Khumalo',
    'mark fish': 'Mark Fish',
    'phil masinga': 'Phil Masinga',
    'john moshoeu': 'John Moshoeu',
    'christopher katongo': 'Christopher Katongo',
    'rainford kalaba': 'Rainford Kalaba',
    'godfrey chitalu': 'Godfrey Chitalu',
    'moses simwala': 'Moses Simwala',
    'abdul kadir': 'Abdul Kadir',
    'mohamed timoumi': 'Mohamed Timoumi',
    'ahmed faras': 'Ahmed Faras',
    'badou zaki': 'Badou Zaki',
    'mahmoud hassan trezeguet': 'Mahmoud Hassan Trezeguet',
    'salah hissou': 'Salah Hissou',
    'djalma feitosa dias': 'Djalma Feitosa Dias',
    'zizinho': 'Zizinho',
    'junior': 'Júnior',
    'eder aleixo': 'Éder Aleixo',
    'careca': 'Careca',
    'muller': 'Müller',
    'paulo roberto falcao': 'Paulo Roberto Falcão',
    'clodoaldo': 'Clodoaldo',
    'amarildo': 'Amarildo',
    'jose altafini': 'José Altafini',
    'giuseppe signori': 'Giuseppe Signori',
    'paolo rossi': 'Paolo Rossi',
    'bruno conti': 'Bruno Conti',
    'antonio cabrini': 'Antonio Cabrini',
    'fulvio collovati': 'Fulvio Collovati',
    'salvatore schillaci': 'Salvatore Schillaci',
    'marco amelia': 'Marco Amelia',
    'fernando couto': 'Fernando Couto',
    'rui costa': 'Rui Costa',
    'nuno gomes': 'Nuno Gomes',
}
