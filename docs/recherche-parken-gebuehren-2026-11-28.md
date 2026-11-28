# Handrecherche Parken und Loipengebühren, 28.11.2026

Auftrag: Parkplätze und Gebühren (Loipengebühr, Tageskarte, Parken) großflächig ergänzen, Südostbayern zuerst,
dann Tirol und Salzburg. Webcams und Verleih macht ein anderer Thread. Gelesen über Websuche und Web-Abruf (die
Cloud-Umgebung erreicht die Ortsseiten per curl nicht). Jede Angabe steht mit Quell-URL und `geprueft_am: 2026-11-28`
in `config/gebiete.yaml`. Übernommen sind nur Fakten (Beträge, „kostenlos“), keine Texte.

`eur` ist die Tageskarte für Erwachsene ohne Gästekarte. `eur: null` heißt: Betrag unbekannt oder freiwillig, der
Text sagt, was bekannt ist.

## Ergebnis

Gebiete mit Loipengebühr: **40 statt 14** (von 267). Neu:

| Gebiet | Loipengebühr | Quelle |
|---|---|---|
| Inzell | freiwillige Nutzungsgebühr, Kassen an den Einstiegen (kein Betrag) | inzell.de, Faltblatt Loipenpflege 12/2024 |
| Chieming | kostenlos (tourinfra-Merkmal „Kostenfrei“ bei beiden Loipen) | tourinfra details.php |
| Seefeld, Leutasch | Tageskarte 15 €, mit Gästekarte 11 €, Kinder bis 15 frei (2026/27) | seefeld.com, Trail tickets and prices |
| Brixental | kostenlos (Kitzbüheler Alpen, nur Pillerseetal kostet) | kitzbueheler-alpen.com |
| Kitzbühel | Sportloipe: Loipe und Parken kostenlos; übrige Loipen ohne Angabe | kitzbueheler-alpen.com |
| Gastein | Dorf-, Bad Hofgastein, Bad Gastein kostenlos; Sportgastein ab 9 € | gastein.com |
| Bad Mitterndorf (Tauplitz) | 17 €, mit Auffahrt 25 €, Kinder bis 15 frei (2026/27) | steiermark.com/loipengebuehren |
| Ramsau am Dachstein | 21,50 €, mit WinterCard 18,50 €, Kinder bis 15 frei (2026/27) | schladming-dachstein.at |
| Ötztal, Sölden, Obergurgl, Vent | kostenlos | oetztal.com |
| Pitztal, Pitztaler Gletscher | Tageskarte 12 €, Saison 70 €, mit Guest Card inklusive, Kinder unter 10 frei | pitztal.com/de/loipentickets |
| Zugspitz Arena, Berwang, Namlos | kostenlos | Pressetext Tiroler Zugspitz Arena Winter 26/27 |
| Serfaus-Fiss-Ladis | kostenlos (Bergbahn zu Höhenloipen kostet) | serfaus-fiss-ladis.at |
| Tannheimer Tal | kostenlos; nur beschneite Loipe Grän/Haldensee vor Saisonstart 5 € | tirol.at, tannheimertal.com |
| Lienz, Hochpustertal, Defereggental, Matrei, Kals | Tageskarte 12 € (beim Kontrolleur 17 €), Kinder bis 13 frei (2026/27) | osttirol.com |

Parkplätze: Bischofswiesen neu mit **Parkplatz Aschauerweiher, kostenlos** (berchtesgaden.de; Koordinate vom
gleichnamigen Parkplatz im OSM-Auszug).

Nebenbei: Die Saisonprüfung (B32) erkennt jetzt auch Beträge der Form „Euro 12,00“ (Pitztal), sonst hätte sie
die Gebühr jedes Jahr als „nicht mehr gefunden“ gemeldet.

## Gefunden, aber nicht eingetragen

- **Tannheimer Tal Parken**: Parkgebühren je nach Ort 1–8 € (Schmieden 7 €, Vilsalpsee 8 €), „Tannheimer Tal Ticket“
  5 € für 24 h nur per App Parkster; im Winter Nachtparkverbot (tannheimertal.com, FAQ Parken). Ohne Zuordnung zu
  einzelnen Loipenparkplätzen, deshalb kein Eintrag. Ein Feld „Parken im Gebiet“ (Text ohne Koordinate) fehlt.
- **Lungau (Loipenfuchs)**: Tageskarte 6 €, nur für Loipen in Mauterndorf, Lignitz und St. Andrä; unser Gebiet
  Prebersee gehört nicht dazu.
- **Dolomiti NordicSki (Südtirol)**: Wochenkarte 65 €, Saison 145 €, Kinder bis 13,9 frei (2026/27), aber keine
  Tageskarte auf der Seite; regionale Tageskarten stehen nur in den Shops der Regionen. Südtirol bleibt offen.
- **Isny**: Saisonpickerl 25 € laut schneehoehen.de (Fremdseite), auf isny.de noch nicht bestätigt.
- **Oberstdorf**: keine Loipengebühr genannt; Zufahrt Rohrmoos nur über private Mautstraße, ca. 5 € in Münzen.
- **Tiroler Zugspitz Arena**: Parkplätze Ponöfen, Hochmoosexpress, Egghof, Sonnbichllift, Hotel Fischer am See
  (Faltblatt 2019/20, ohne Gebühr, veraltet).
- **Kitzbühel**: Parkplatz Golfplatz Schwarzsee „Free car park“ (kitzbuehel.com), aber keine bestätigte Koordinate;
  steht deshalb nur im Gebührentext.
- **Wildschönau**: nur Bergbahn Markbachjoch (Erwachsene 23,50 €), keine Loipengebühr.
- **Ötztal**: Parkplätze ohne Beträge (Niederthai Sennhof, Längenfeld, Sölden Postplatz, Vent, Obergurgl
  Festkoglbahn frei, Ortsmitte kostenpflichtig) nur aus der Zusammenfassung des Web-Abrufs, nicht wörtlich geprüft.

## Gesucht, keine Angabe gefunden (Lücken)

- **Südostbayern**: Tegernseer Tal (tegernsee.com nennt weder Gebühr noch „kostenlos“), Fischbachau, Sachrang
  (Loipe), Siegsdorf, Berchtesgaden, Schönau, Ramsau, Marktschellenberg (berchtesgaden.de-Tourenseiten ohne
  Gebühr und ohne Parkplatz außer Aschauerweiher). Inzell: Parkgebühren unbekannt.
- **Tirol**: Kufsteinerland, Wilder Kaiser, Alpbachtal, Wildschönau, Zillertal (Fügen, Zell-Gerlos, Mayrhofen, Tux),
  St. Anton/Arlberg, Paznaun, Innsbruck und Umgebung (innsbruck.info nicht abrufbar), Stubai, Kühtai, Sellraintal,
  Wipptal, Hall-Wattens, Imst, Kaunertal, Landeck, Tiroler Oberland, Reutte, Lechtal, Jochberg, Obertilliach
  (Osttirol-Seite nennt Obertilliach nicht ausdrücklich), Silberregion Karwendel, Mieming.
- **Salzburg**: Prebersee (Lungau).
- **Allgäu**: Oberstdorf, Hörnerdörfer, Balderschwang, Wertach, Pfronten, Füssen, Kleinwalsertal (Seiten ohne Gebühr).
- Nicht angefangen: Schweiz (Loipenpass), Südtirol, Steiermark außer Ausseerland/Ramsau, Kärnten.
- Parkgebühren mit Betrag: auf fast keiner offiziellen Seite. Die meisten Ortsseiten nennen Parkplätze ohne Preis.
  Ergiebiger wären die Loipen-Detailseiten bei bergfex (z. B. „Parkplatz Blattlhof – kostenlos“), die wir aber als
  Quelle bisher nicht von Hand auswerten.

## Nächste Schritte

1. Schweiz: Loipenpass Schweiz (landesweit) und regionale Tageskarten, viele Gebiete auf einmal.
2. Südtirol: Tageskarten je Dolomiti-NordicSki-Region (Drei Zinnen, Antholz, Gsies, Ahrntal, Seiser Alm, Gröden).
3. Tirol-Lücken über tirol.at-Loipenseiten (dürfen wir nutzen, B31) nach Parkplatzangaben durchsuchen.
4. Entscheidung Stefan: Feld für Parkinfo je Gebiet ohne Koordinate anzeigen (z. B. Tannheimer Tal Ticket)?
