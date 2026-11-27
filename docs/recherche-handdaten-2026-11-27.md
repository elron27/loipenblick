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

## Nächste Etappe

Alpbachtal und Wildschönau über die eigenen Seiten, Pillerseetal/St. Johann (Webcams, Verleih), dazu die
Verleih-Lücken im Tegernseer Tal, Ruhpolding, Inzell und Berchtesgaden.
