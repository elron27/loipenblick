# Handrecherche Loipen, 27.11.2026 (Parken, Webcams, Verleih, Merkmale)

Fortsetzung von Issue #46 / PR #47 ("Handrecherche je Gebiet in Etappen"). Die Cloud-Umgebung erreicht die
Ortsseiten per curl nicht (Proxy 403), gelesen wurde über den Web-Abruf. Jede Angabe steht mit Quell-URL und
`geprueft_am: 2026-11-27` in `config/gebiete.yaml`. Übernommen werden nur Fakten und Links, keine Texte und
keine Bilder (D-0ab83ba29190). Webcams sind nur verlinkt, nicht eingebettet (U49). Rohe Bildadressen (`.jpg`)
und reine Einbett-Player wurden nicht übernommen, nur Seiten zum Ansehen.

## Eingepflegt

| Gebiet | Webcams | Verleih | Gebühr / Parken |
|---|---|---|---|
| Rottach-Egern | Wallbergbahn (feratel), Blick vom Wallberg (foto-webcam.org) | – (OSM-Treffer bleibt) | – |
| Kreuth | Blick auf die Loipe (foto-webcam.org) | – | – |
| Bayrischzell | (schon da) | Sportalm Bayrischzell | Tagesticket 7 € inkl. Parken bestätigt |
| Sachrang | Kampenwandbahn Aschau (feratel, Nachbarort) | Skischule Sachrang | Parkplätze 5 €/Tag bestätigt |
| Reit im Winkl | Ort und Winklmoos-Alm (panomax) | Gasthof SonnenAlm, Hausberg Snowsport | – |
| Schleching | Gscheuerwand (foto-webcam.eu) | – | keine Loipengebühr (Achental) |
| Marquartstein-Grassau | Schnappenberg, Oed (foto-webcam.eu) | – | keine Loipengebühr (Achental) |
| Unterwössen | Unterwössen, Oberwössen (rundumwebcam) | – | – |
| Bergen | Hochfelln Nord, Mittelstation (terra-hd) | – | – |
| Siegsdorf | Osterham (terra-hd) | – | – |
| Kufstein | Pendling Ost/West (foto-webcam.eu) | – | – |
| Schwoich | Langlauf-Webcam Biathlonzentrum | – | – |
| Ebbs | Fohlenhof / St. Nikolaus (skylinewebcams) | – | – |
| Walchsee | Seespitz (panomax), Moorgebiet Schwemm (feratel) | – | keine Loipengebühr, Parken gratis mit Kaiserwinkl Card |
| Kössen | Moserberg, Unterberghorn (feratel) | Nordic Center, Sport Mühlberger, Intersport Planer | wie Walchsee |
| Schwendt | – | – | wie Walchsee |
| Faistenau | panomax | Sport Auer | (schon da, 11 €) |
| Hintersee | Loipe Hintersee (panomax) | KÄSTLE Cross Country, DAS Hintersee | (schon da) |

Merkmale je Loipe: Die Langlaufen-Listen von Tegernsee, Bayrischzell und Fischbachau haken je Tour
"Einkehrmöglichkeit" und "Familienfreundlich" ab. Der ATS-Adapter liest diese Haken jetzt als Merkmale
`einkehr` und `familientauglich` (D21 AK 2), Test `test_d21_merkmale_aus_den_haken_der_liste`.

## Hunde und Beleuchtung (D25, seit Etappe 2 mit eigenem Feld)

Seit D25 tragen Gebiete `hunde` {erlaubt, text, url, geprueft_am} und `beleuchtet` [{name, zeiten, url, geprueft_am}]; die Gebietsseite zeigt beides unter Anreise. Eingetragen sind die folgenden Befunde.


- Hunde verboten: Bayrischzell ("Die Nutzung der Loipen mit Hunden ist nicht gestattet",
  https://www.bayrischzell.de/langlaufen), Faistenau/Hintersee ("Hunde auf der Loipe sind nicht gestattet",
  https://www.langlaufdorf.at/loipen.html).
- Beleuchtete Loipen: Sachrang ca. 3 km, Di–Fr 17:30–21:00 (https://www.aschau.de/langlauf); Reit im Winkl
  Flutlicht im Langlaufstadion Di und Do 18–20 Uhr (https://www.reitimwinkl.de/langlaufen); Inzell Nachtloipe am
  Campingplatz Di, Do, Fr ab 17 Uhr (https://www.inzell.de/schneebericht); Schwoich SC3a Ganzer-Runde, beleuchtet
  und beschneit, 1,1 km (https://www.kufstein.com/de/aktivitaeten/winter/langlaufloipen-in-schwoich.html);
  Faistenau Kugelberg-Loipe bis 21 Uhr (https://www.langlaufdorf.at/loipen.html). Kaiserwinkl: Loipen zwischen
  17:30 und 07:00 Uhr gesperrt (nicht eingetragen, weil kein Gebiet mit Licht).
Weiter ohne Feld:

- Klassisch/Skating: steht bei Aschau je Loipe (Schützenstraße und Sachrang-Rundkurs beides, Prientalloipe nur
  klassisch); die Technik kommt aber aus der Quelle, ein Handfeld fehlt.
- Ticket-Automaten Bayrischzell: Sportalm, Stocker, Geitau, Bäckeralm, auch per App Parkster.

## Gesucht, nicht gefunden

- Langlaufverleih: Tegernseer Tal (tegernsee.com nennt keinen), Fischbachau, Ruhpolding, Inzell, Achental
  (nur allgemein "Sportgeschäfte ... halten Leihmaterial bereit"), Bergen, Siegsdorf, Kufsteinerland.
- Webcams: Fischbachau (nur ohne Detail-Link), Ruhpolding und Inzell (nur rohe Bilder bzw. Einbett-Player),
  Gmund, Bad Wiessee, Tegernsee (nur ohne Detail-Link).
- Unsicher, deshalb weggelassen: Webcam "Sachrang" bei skiresort (Betreiber unbekannt); "Skiverleih Brandauer"
  (Kaiserwinkl-Seite ohne Ortszuordnung); Reit-im-Winkl-Verleihe ohne ausdrückliches Langlauf (Sport Dorner,
  Intersport Rent).

## Nutzungsbedingungen

feratel (AGB III): Inhalte nur zur Information der Nutzer, jede andere Verwertung ausgeschlossen; Links auf die
öffentlichen Seiten sind nicht geregelt. Wir verlinken nur, wie bei den Bayrischzell-Webcams seit 24.11.2026.
Vor der öffentlichen Seite gehört das zur Backlog-Prüfung der Nutzungsbedingungen.

## Etappe 2 (27.11.2026): Berchtesgaden, Kitzbüheler Alpen, Wilder Kaiser, Alpbachtal

| Gebiet | Eingepflegt |
|---|---|
| Berchtesgaden | Webcams Lockstein (feratel), Jenner Süd (foto-webcam.eu) |
| Schönau am Königssee | Webcam Jennerbahn (feratel) |
| Ramsau | Webcam Hochschwarzeck (feratel) |
| Hohe Salve | Webcam Gipfel Hohe Salve; keine Loipengebühr, Parken kostenlos; beleuchtet: Trainingsloipen Wörgl und Angerberg bis 21 Uhr |
| Pillerseetal | beleuchtet: Nachtloipe Waidring, Nachtloipe Fieberbrunn, Dorfloipe Hochfilzen (ohne Zeiten) |
| St. Johann in Tirol | beleuchtet: Trainings-Nachtloipe (ohne Zeiten) |
| Ellmau | Webcams Hartkaiserbahn, Panoramakamera |
| Söll | Webcam Bergstation Gondelbahn |

Gefunden, aber nicht eingepflegt:

- Berchtesgadener Land: keine Langlaufverleihe genannt; Detailseiten Schönau und Aschauerweiher gaben
  Serverfehler. Taubensee (Ramsau) und Scheffau-Schellenberg: klassisch und Skating. Längenangaben
  widersprechen sich auf den Seiten (Taubensee 4 bzw. 5,6 km, Scheffau 5 bzw. 7,7 km).
- Hohe Salve: Sport Fuchs (Itter), Skiverleih Kurz und Intersport Oberhauser (Hopfgarten) sind gelistet, aber
  ohne ausdrückliches Langlauf; deshalb nicht übernommen.
- Wilder Kaiser: Langlaufverleih ausdrücklich nur Bike Sport Knaubert in Scheffau (kein eigenes Gebiet bei uns);
  beleuchtete Dorfloipe Scheffau ohne Zeiten. Alle Loipen klassisch und Skating. Keine Gebühr genannt.
- Alpbachtal, Wildschönau, Kitzbühel, Jochberg, Pillerseetal und St. Johann: eigene Seiten nicht erreicht.
- Hunde: auf keiner Seite dieser Etappe erwähnt.

## Etappe 3 (27.11.2026): Pillerseetal, Alpbachtal, Wildschönau

| Gebiet | Eingepflegt |
|---|---|
| Pillerseetal | Loipengebühr Tageskarte 10 € (beim Loipenbetreuer 14 €), Saisonkarte 80 €; Hunde nicht erlaubt; Nachtloipe Fieberbrunn täglich bis 21 Uhr |
| Alpbachtal | Webcam Wiedersberger Horn (panomax) |
| Wildschönau | Verleih Ski & Board Margreiter (Niederau, Auffach, Oberau) |

Gefunden, aber nicht eingepflegt:

- Pillerseetal: die Verleih-Seite listet Langlaufschulen (Waidring, St. Ulrich, Fieberbrunn, Hochfilzen), sagt aber
  nicht, wer Ski verleiht. Loipen täglich 8 bis 18 Uhr, Nachtloipen ausgenommen.
- Alpbachtal: keine Gebühr, kein Verleih, keine Hunde- oder Lichtangabe; Gesamtlänge widersprüchlich (70 bzw. 100 km).
- Wildschönau: Skisport Thaler nennt nur "Leihausrüstung" ohne Langlauf; Webcams ohne Detail-Link.

## Etappe 4 (27.11.2026 nachmittags): Lücken, St. Johann, Seefeld, Zillertal

| Gebiet | Eingepflegt |
|---|---|
| Ruhpolding | Verleih Sport Plenk (Langlaufausrüstung) |
| Berchtesgaden | Verleih Sport M+R Brandner (Langlaufski) |
| St. Johann in Tirol | keine Loipengebühr; Hunde nicht erlaubt; Trainings-Nachtloipe täglich 17–21 Uhr, Lärchenhofloipe Erpfendorf Mo und Do 17–20 Uhr |
| Pillerseetal | Webcams Reckmoos Fieberbrunn, Steinplatte Waidring (panomax) |
| Seefeld | Hunde nur auf der Hundeloipe A3 (Wildmoos, Leinenpflicht); A1 Nachtloipe Mo–Fr 17:00–20:30; Verleih Cross Country Academy |
| Leutasch | Verleih Skischule Leutasch |
| Tux | Hunde nicht erlaubt; Webcams Wanglspitz (foto-webcam.eu), Eggalm (panomax) |
| Zell-Gerlos | Schönachtal-Loipe beleuchtet täglich 17–22 Uhr |

Gefunden, aber nicht eingepflegt:

- Inzell, Ramsau, Schönau, Bischofswiesen: weiter kein Langlaufverleih genannt (Sport Renoth an der Jennerbahn verleiht
  nur Schneeschuhe und Schlitten). Ruhpolding: Skischule Ruhpolding und Rent-a-Ski ohne ausdrückliches Langlauf.
- Bischofswiesen: beleuchtete Stadionrunde am Aschauerweiher ohne Zeiten.
- St. Johann: Verleih-Seite nennt keine Betriebe; Webcams nur als Bilder ohne Detailseite.
- Seefeld: Loipengebühr für Erwachsene nicht im gelesenen Text (Kinder bis 15 frei); Leutasch Sport Norz und Sport
  Wedl nur als Verleih von Kinderanhängern genannt.
- Zillertal: keine Gebühr und kein Langlaufverleih mit Namen auf den gelesenen Seiten; Mayrhofen und Fügen ohne
  Hunde- oder Lichtangabe.
- Achensee bewusst nicht recherchiert (Achensee Tourismus hat abgelehnt, E-43).

## Etappe 5 (28.11.2026 abends): Sachrang-Webcams, Webcam- und Verleih-Lücken

| Gebiet | Eingepflegt |
|---|---|
| Sachrang | acht Webcams von terra-hd: Sachrang-Loipe am Bergerhof (Blick über die Loipe), Ortsmitte Mitterleiten, Kaiserblick Skilift (Video), Niederndorferberg (Tirol, Blick ins Priental), Reichenau, Ölbergkapelle, Priener Hütte Süd und West (Geigelstein, 1410 m) |
| Ruhpolding | Webcams Chiemgau Arena (Start Fritz-Fischer-Loipe) und Bojern (feratel) |
| Bad Wiessee | Webcam Skizentrum Sonnenbichl (foto-webcam.eu) |

Quelle der Sachrang-Liste ist die Webcam-Seite der Gemeinde (https://www.aschau.de/wetter), sie verlinkt 18 Kameras,
davon sechs in Sachrang und zwei an der Priener Hütte. Die Links auf terra-hd.de leiten auf terra-hd.com weiter,
eingetragen ist die Zieladresse. Webcam-Partner laut terra-hd: Bergsteigerdorf Sachrang bzw. Gemeinde Aschau (Loipe,
Ortsmitte), Pfarrverband Priental (Ölbergkapelle), Kaiserblick Skilift, Alpenchalet Sachrang (Reichenau), Priener
Hütte und DAV Sektion Prien; Niederndorferberg ohne Partner.

Die Gebietsseite zeigte bisher höchstens vier Webcams je Gebiet. Jetzt erscheinen alle von Hand gepflegten, die
Webcams aus tourinfra füllen weiter nur bis vier auf (Test `test_d9_handwebcams_alle_tourinfra_nur_bis_zum_limit`).

Nutzungsbedingungen terra-hd: Auf den Kameraseiten steht "Gerne darf das Livebild dieser Webcam bis auf Widerruf in
einer anderen Webseite eingebunden werden", unter Bedingungen (Bild nicht verändern, nur verkleinern, Link über dem
ganzen Bild auf die Kamera oder terra-hd.com). Bei der Kaiserblick-Videokamera fehlt dieser Satz. Das Impressum
erlaubt Downloads und Kopien nur für privaten, nicht kommerziellen Gebrauch. Wir verlinken weiter nur (U49);
Einbetten wäre bei sieben der acht Kameras erlaubt, ist aber eine eigene Entscheidung.

Gesucht, nicht gefunden:

- Langlaufverleih: Tegernseer Tal, Fischbachau, Inzell (Chiemgau-Karte nennt nur Schlitten- und Radverleih), Bergen,
  Siegsdorf, Kufstein, Ebbs, Schwoich, Langkampfen. Achental: bergfex-Verleihlisten sind per robots.txt gesperrt.
  Thiersee (Schneeberglifte) und Bad Häring stehen im WKO-Verzeichnis nur als "Skiverleih" ohne Langlauf, deshalb
  nicht übernommen; die tirol.at-Seite von Sport Thaler Hinterthiersee gab einen Serverfehler.
- Webcams: Inzell (Kessel-Alm, Wimmerhof) und weitere Ruhpoldinger Kameras (Rauschberg, Bojernhof) nur bei
  Sammelseiten ohne Betreiber; Gmund nur bei tourispo ohne Betreiber; Fischbachau weiter ohne Treffer.
  Bayernwebcam.de (Sachrang-Ortsansicht) war nicht lesbar.

## Nächste Etappe

Mieming, Silberregion Karwendel, Hinterriß; Südostbayern und Salzburger Land nach der Regionen-Reihenfolge;
Verleih-Lücken Inzell und Berchtesgadener Land über die Sportgeschäfte vor Ort.
