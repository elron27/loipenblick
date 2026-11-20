# Kontaktliste: Stellen, die wir fragen oder informieren müssen

Stand 19.11.2026. Wird bei jeder neuen Quelle ergänzt. Gepflegt im Repo, Kopie für Stefan unter
`livegang/vorbereitung/kontaktliste.md` im Projektordner.

**Vorgehen (Stefan, 19.11.2026):** Daten von Quellen ohne Zustimmung dürfen in die **Testversion**. Die Quelle steht dann in
`config/sources.yaml` auf `erlaubnis: nur_test` und erscheint auf der öffentlichen Seite nicht. Gefragt wird, wenn die
Anbindung funktioniert, mit einer Vorführung der Testseite. Vor dem Livegang wird jede Quelle auf `nur_test` geprüft
(Pflichtpunkt in [livegang-checkliste-stefan.md](livegang-checkliste-stefan.md)).

Erlaubnis-Status in `sources.yaml` (`nutzung.erlaubnis`):

| Wert | Bedeutung | Öffentliche Seite |
|---|---|---|
| `liegt_vor` | Betreiber hat zugestimmt (Datum und Wortlaut in der Notiz unten) | wird gezeigt |
| `ausstehend` | angefragt oder Anfrage geplant; Nutzungsbedingungen verbieten die Übernahme nicht ausdrücklich | wird mit Quellenhinweis gezeigt (Regel aus der Livegang-Planung: bei Schweigen bis 11.12. mit Quellenhinweis zeigen) |
| `nur_test` | Nutzungsbedingungen verbieten Übernahme/Speichern ohne Einwilligung, oder noch nicht geprüft | wird **nicht** gezeigt |

## 1. Quellbetreiber mit Loipendaten

| Stelle | Quelle / Region | Wofür | Kontakt | Stand | Notiz |
|---|---|---|---|---|---|
| Tirol Werbung GmbH | tirol.at, ganz Tirol | Loipenstatus, Lage, Länge | info@tirol.at | angefragt 19.11.2026 | nachfassen, falls bis 11.12. keine Antwort |
| Tegernseer Tal Tourismus GmbH | tegernsee.com | Loipenstatus, gespurte km | info@tegernsee.com | angefragt 19.11.2026 | |
| Tourist-Info Bayrischzell | bayrischzell.de | Loipenstatus | tourist-info@bayrischzell.de | angefragt 19.11.2026 | |
| Gemeinde Fischbachau | fischbachau.de | Loipenstatus | rathaus@fischbachau.de | angefragt 19.11.2026 | |
| Gemeinde Aschau i. Chiemgau | aschau.de (Sachrang) | Loipenstatus | gemeinde@aschau.de | angefragt 19.11.2026 | |
| Chiemgau Tourismus | tourinfra Loipenmanager Chiemgau | Loipenstatus, Strecken | Adresse fehlt (Impressum chiemgau-tourismus.de) | **nicht angefragt** | Mail lag ohne Adresse bereit |
| TVB Tannheimer Tal | tourinfra Loipenmanager | Loipenstatus, Strecken | info@tannheimertal.com | angefragt 19.11.2026 | |
| TVB Olympiaregion Seefeld | seefeld.com, tourinfra | Loipenstatus, gespurte km | region@seefeld.com | angefragt 19.11.2026 | deckt beide Seefeld-Quellen ab |
| TVB Achensee | achensee.com | Schneebericht | info@achensee.com | angefragt 19.11.2026 | |
| TVB Kufsteinerland | kufstein.com | Schneebericht | info@kufstein.com | angefragt 19.11.2026 | |
| TVB Kaiserwinkl | kaiserwinkl.com | Loipenbericht | info@kaiserwinkl.com | angefragt 19.11.2026, **Antwort 19.11.** (fragt nach Schnittstelle) | Antwortentwurf: livegang/vorbereitung/antwort-schnittstelle.md |
| Kitzbüheler Alpen | kitzbueheler-alpen.com | Loipenstatus | Adresse fehlt (Impressum) | **nicht angefragt** | Mail lag ohne Adresse bereit |
| Tourismusbüro Faistenau | langlaufdorf.at | Loipenstatus | faistenau@salzkammergut.at | angefragt 19.11.2026 | |
| Zweckverband Bergerlebnis Berchtesgaden | berchtesgaden.de | Lage, Länge | info@berchtesgaden.de | angefragt 19.11.2026 | |
| Ferienregion Salzburger Lungau | (noch keine Quelle) | Loipenstatus | info@lungau.at | angefragt 19.11.2026 | lungau.at wird derzeit nicht abgerufen |
| **Zillertal Tourismus GmbH** | zillertal.at, Zillertal | Schneehöhe, Wetter, Anfahrt, Loipendetails (Querprüfung tirol.at) | info@zillertal.at, +43 5288 87187 | **nicht angefragt**, erst nach Vorführung | Impressum: Speichern und Vervielfältigen ohne Einwilligung unzulässig (geprüft 19.11.2026). robots.txt erlaubt alles. Bis zur Zustimmung `nur_test`. |
| TVB St. Anton am Arlberg | stantonamarlberg.com | Loipenzustand | noch suchen | nicht angefragt | |
| Dolomiti NordicSki | dolomitinordicski.com | Loipenstatus Südtirol/Cortina | noch suchen | nicht angefragt | Impressum ohne Nutzungsregeln, beim Komitee fragen |
| Engadin Tourismus | tourinfra Engadin | Loipenstatus | noch suchen | nicht angefragt | |
| Destination Davos Klosters | tourinfra Davos | Loipenstatus | noch suchen | nicht angefragt | |
| Goms Tourismus | tourinfra Goms | Loipenstatus | noch suchen | nicht angefragt | |
| Gastein Tourismus | tourinfra Gastein | Loipenstatus | noch suchen | nicht angefragt | |
| Tourismusverband Ramsau am Dachstein | tourinfra Ramsau | Loipenstatus | noch suchen | nicht angefragt | |
| Schweiz Tourismus / infosnow.ch (APGSGA) | snow.myswitzerland.com | Schneeberichte Schweiz, Liechtenstein | noch suchen | nicht angefragt | Nutzungsbedingungen noch prüfen |
| Nassfeld-Pressegger See (NLW) | tools.nlw.at | Wintersportbericht (PDF) | noch suchen | nicht angefragt | |
| Steiermark Tourismus | steiermark.com | Loipenstatus Tourenportal | noch suchen | nicht angefragt | |

## 2. Daten ohne Anfrage, aber mit Pflichten

| Stelle | Wofür | Bedingung | Stand |
|---|---|---|---|
| GeoSphere Austria | Schneehöhe, Neuschnee Österreich | CC BY 4.0, Namensnennung | erfüllt (Quelle steht bei jedem Wert) |
| Deutscher Wetterdienst | Schneehöhe Bayern | Open Data, Quellenvermerk | erfüllt |
| Bright Sky | Vorhersage (Daten DWD MOSMIX) | freier Dienst, Quellenvermerk DWD | erfüllt |
| Open Data Hub Südtirol | Loipen Südtirol | CC0 je Datensatz | erfüllt |
| OpenStreetMap | Kartenkacheln | Tile Usage Policy (kein Massenabruf, Attribution) | vor dem Livegang prüfen, ob eigener Kachelanbieter nötig ist |
| MeteoSchweiz | Schneehöhen Schweiz (geplant) | Open Data, Bedingungen noch prüfen | noch nicht angebunden |

## 3. Ortsseiten für die Querprüfung von tirol.at (in Arbeit)

Wird ergänzt, sobald je Region die Ortsseite gefunden und geprüft ist (robots.txt, Nutzungsbedingungen, was dort steht).

### Zillertal (P35, geprüft 19.11.2026)

| Ortsseite | Region | Was dort steht | robots.txt | Ergebnis | Notiz |
|---|---|---|---|---|---|
| zillertal.at (Karte maps.zillertal.at) | Zillertal | Je Loipe Schneehöhe, Wetter, Anfahrt, Details; Quelle „Zillertal Tourismus GmbH“ | www.zillertal.at erlaubt, **maps.zillertal.at verbietet alles** (geprüft 19.11.2026) | **nicht anbindbar** | Die Loipenliste auf www.zillertal.at kommt nur aus der Karte. Der Schneebericht dort nennt nur Skigebiete (Lifte, Pisten). Bei der Anfrage an Zillertal Tourismus deshalb auch um einen Datenzugang bitten (Export, Schnittstelle oder Freigabe in robots.txt). |

### Alpbachtal, Wildschönau, Wilder Kaiser, Kitzbühel, St. Johann (P34, geprüft 19.11.2026)

| Stelle | Region | Wofür | Kontakt | Stand | Notiz zu den Nutzungsbedingungen |
|---|---|---|---|---|---|
| Tourismusverband Alpbachtal & Tiroler Seenland | Alpbachtal (Quelle `alpbachtal`) | Loipenbericht-Tabelle: Status, gespurte km, Ort | info@alpbachtal.at | nicht angefragt | robots.txt erlaubt; Impressum und AGB ohne Regel zur Übernahme von Daten |
| Tourismusverband Wildschönau | Wildschönau (Quelle `wildschoenau`) | Öffnungsstatus der Loipen, gespurte km | info@wildschoenau.com | nicht angefragt | robots.txt erlaubt (nur Suchparameter gesperrt); Impressum: Elemente urheberrechtlich geschützt, alle Rechte vorbehalten |
| Tourismusverband Wilder Kaiser | Ellmau, Going, Scheffau, Söll (Quelle `wilderkaiser`) | Loipenstatus mit Ort, Stil, Länge | office@wilderkaiser.info | nicht angefragt | robots.txt erlaubt; Impressum: Links erwünscht, Einbinden in fremde Frames unzulässig, zur Datenübernahme nichts |
| Kitzbühel Tourismus | Kitzbühel, Reith, Aurach, Jochberg | nicht angebunden | info@kitzbuehel.com | nicht nötig | Keine eigene Statusliste; die Karte maps.kitzbuehel.com lädt tirol.mapservices.eu, also dieselben Daten wie tirol.at |
| Kitzbüheler Alpen, St. Johann in Tirol | St. Johann, Oberndorf, Kirchdorf, Erpfendorf | nicht neu angebunden | (wie Kitzbüheler Alpen, Abschnitt 1) | nicht nötig | /de/stjo/aktuelles/loipen-status.html ist eine Teilmenge der schon angebundenen Quelle `kitzbueheler-alpen`; zusätzlich nur Schneehöhe des Skigebiets |

### Ötztal, Pitztal, Tiroler Oberland, Nauders, Serfaus-Fiss-Ladis, Paznaun (P31, geprüft 19.11.2026)

| Stelle | Region | Wofür | Kontakt | Stand | Notiz zu den Nutzungsbedingungen |
|---|---|---|---|---|---|
| Ötztal Tourismus (Körperschaft öffentlichen Rechts), Sölden | Ötztal (oetztal.com) | Loipenstatus, Länge, Schwierigkeit je Detailseite | info@oetztal.com, +43 57200 200 | nicht angefragt | Impressum und AGB (nur Buchungen) ohne Regel zur Weiterverwendung; robots.txt regelt nur Meta-Bots. Liste per Outdooractive-Schlüssel der Seite, den wir nicht nutzen. Geprüft 19.11.2026, `nur_test`. |
| Tourismusverband Pitztal, Wenns | Pitztal (pitztal.com) | Loipenstatus, Länge, Startpunkt | info@pitztal.com, +43 5414 86 999 | nicht angefragt | Impressum: Verwendung von Grafiken und Texten in anderen Publikationen nur mit Zustimmung; robots.txt erlaubt alles. Geprüft 19.11.2026, `nur_test`. |
| TVB Tiroler Oberland, Ried i. O. | Tiroler Oberland, Kaunertal, Kaunergrat (tiroler-oberland.com) | Loipenstatus | office@tiroler-oberland.com, +43 50 225 100 | nicht angefragt | Impressum und AGB ohne Regel zur Weiterverwendung; robots.txt erlaubt alles. Geprüft 19.11.2026, `nur_test`. |
| TVB Tiroler Oberland, Erlebnisraum Nauders | Nauders (nauders.com) | Loipenstatus, Länge, Technik, Stand | office@nauders.com, +43 50 225 400 | nicht angefragt | wie Tiroler Oberland (derselbe Verband, eine Anfrage reicht). Geprüft 19.11.2026, `nur_test`. |
| Serfaus-Fiss-Ladis Marketing GmbH (für den TVB), Serfaus | Serfaus-Fiss-Ladis (serfaus-fiss-ladis.at) | Loipenstatus, Länge, Technik | info@serfaus-fiss-ladis.at, +43 5476 6239 | nicht angefragt | Impressum: Inhalte und Bilder für andere Seiten nur mit ausdrücklicher Erlaubnis der Redaktion; robots.txt erlaubt alles. Geprüft 19.11.2026, `nur_test`. |
| Tourismusverband Paznaun-Ischgl, Ischgl | Paznaun mit Galtür und Silvretta (ischgl.com) | Loipenstatus, Länge, Technik, Startpunkt, Stand | info@paznaun-ischgl.com, +43 50990 100 | nicht angefragt | Fußzeile „Alle Rechte vorbehalten“, Impressum-Volltext extern (datareporter), AGB nur Buchungen; robots.txt sperrt ajaxRequestType, nicht ajax=1. Geprüft 19.11.2026, `nur_test`. |

### Innsbruck, Stubai, Wipptal, Hall-Wattens, Silberregion Karwendel (P32, geprüft 19.11.2026)

| Ortsseite | Region | Was dort steht | robots.txt | Ergebnis | Notiz |
|---|---|---|---|---|---|
| innsbruck.info, Wintersportbericht von Intermaps (sdds4.intermaps.com) | Innsbruck und Feriendörfer, Sellrain, Kühtai, Mieminger Plateau | 40 Loipen in 9 Orten mit Status-Symbol und „Letzte Aktualisierung“, Temperatur je Ort | Intermaps ohne robots.txt (404) = keine Sperre (geprüft 19.11.2026) | **angebunden, `nur_test`** (P32) | Intermaps ist Bezahldienst (E-15/P17); Stefan 19.11.2026: Ausnahme nur für die Testversion. Impressum innsbruck.info: Elemente urheberrechtlich geschützt. Kontakt office@innsbruck.info, +43 512 53 56; öffentlich nur mit Zustimmung von Innsbruck Tourismus (ggf. auch Intermaps). |
| hall-wattens.at/de/langlaufen.html | Hall-Wattens (Rinn, Gnadenwald) | 7 Loipen mit Status, Länge, Schwierigkeit, Lage (JSON im Seitenquelltext) | erlaubt alles (geprüft 19.11.2026) | **angebunden, `nur_test`** (P32) | Impressum: Verwendung von Texten, Grafiken, Bildern nur mit ausdrücklicher Genehmigung. Kontakt info@hall-wattens.at |
| silberregion-karwendel.com/de/langlaufen.html | Silberregion Karwendel (Weerberg, Pill, Vomp, Hinterriß) | 7 Loipen mit Status, Länge, Schwierigkeit, Startpunkt, Lage | erlaubt alles (geprüft 19.11.2026) | **angebunden, `nur_test`** (P32) | Impressum: Vervielfältigung ohne Einverständnis nicht erlaubt. Kontakt info@silberregion-karwendel.com, +43 5242 63240 |
| stubai.at/aktivitaeten/winter-aktiv/langlaufen/ | Stubaital | 10 Loipen mit Status (geöffnet/gesperrt) | erster Abruf erlaubt, danach 403 von Cloudflare auf robots.txt = Sperre; crawl-delay 10 | **nicht anbindbar** | Impressum: Vervielfältigung nur mit vorheriger Zustimmung. Kontakt info@stubai.at; bei einer Anfrage um Datenzugang bitten |
| wipptal.at/langlaufen (Karte maps.wipptal.at) | Wipptal mit Vals, Gschnitz, Obernberg | Beschreibung, kein Loipenstatus; die Karte nutzt tirol.mapservices.eu (dieselben Daten wie tirol.at) | erlaubt alles (geprüft 19.11.2026) | **kein Mehrwert** | Kontakt tourismus@wipptal.at |

### Außerfern und Osttirol (P33, geprüft 19.11.2026)

| Stelle | Region | Wofür | Kontakt | Stand | Notiz zu den Nutzungsbedingungen |
|---|---|---|---|---|---|
| Tourismusverband Osttirol (osttirol.com) | Osttirol (P33) | Status, Länge, Schwierigkeit von 59 Loipen (Seite „Alle Loipen“), Querprüfung tirol.at | info@osttirol.com | nicht angefragt | robots.txt ohne Sperre (geprüft 19.11.2026). Impressum: „Alle Inhalte und Bilder sind urheberrechtlich geschützt“, keine Freigabe zur Übernahme. Quelle mit erlaubnis nur_test. Der eigentliche Loipenzustandsbericht liegt bei Intermaps und wird nach P17 nicht abgerufen; in der Anfrage miterwähnen. |
| Tiroler Zugspitz Arena (zugspitzarena.com), Intermaps (sdds4.intermaps.com) | Außerfern (P33) | Loipenstatus, Länge, Schwierigkeit und Stand von 21 Loipen (Ehrwald, Lermoos, Biberwier, Berwang, Bichlbach, Heiterwang) aus dem Wintersportbericht, Querprüfung tirol.at | info@zugspitzarena.com | nicht angefragt | Eigene Seiten zeigen keinen Loipenstatus, nur ein eingebettetes Intermaps-Fenster. Intermaps ist ein Bezahldienst (P17); Stefan hat am 19.11.2026 eine Ausnahme nur für die Testversion erlaubt (erlaubnis nur_test, p17_ausnahme). robots.txt bei Intermaps fehlt (404). Impressum der Zugspitz Arena: Vervielfältigung und Verwertung nur mit schriftlicher Zustimmung, Kopien nur privat. In der Anfrage ausdrücklich nach der Nutzung des Intermaps-Berichts fragen; ggf. Intermaps selbst fragen. |
| Lechtal Tourismus (lechtal.at), Holzgau (holzgau.at) | Außerfern (P33) | keine eigene Statusangabe gefunden | info@lechtal.at | nicht nötig | Loipenliste lädt per JavaScript, Karte maps.lechtal.at nutzt tirol.mapservices.eu (robots-Sperre, dieselben Daten wie tirol.at). holzgau.at nennt keine Loipen. Kein Mehrwert gegenüber tirol.at, nicht angebunden. |
| Naturparkregion Reutte (reutte.com) | Außerfern (P33) | keine eigene Statusangabe gefunden | info@reutte.com | nicht nötig | Langlaufseite zeigt nur die contwise-Karte (reutte.mapservices.eu) und eine Liste über phoenix.contwise.io, beide aus der Tiroler Datenbank wie tirol.at. Kein Mehrwert, nicht angebunden. |

## 4. Allgäu (geprüft 20.11.2026)

Das Allgäu liegt westlich unseres bisherigen Ausbaus (Südostbayern, Tirol, Salzburg), zwischen Bodensee, Lech und
Tannheimer Tal. Nach E-13 ist es eine spätere Ausbaustufe. Anbindung der eigentlichen Quellen (Gemeinden,
Tourismusämter, Loipenvereine) wäre ein eigener Ausbau; dieser Abschnitt hält nur den Befund zum Vorbild fest.

| Stelle | Region | Was dort steht | robots.txt | Ergebnis | Notiz |
|---|---|---|---|---|---|
| loipen-allgaeu.de (Vorbild aus der Produktdefinition) | ganzes Allgäu mit Kleinwalsertal und Tannheimer Tal | Klickbare Karte mit rund 90 Orten, 72 Gebiete in 10 Regionen, rund 371 Loipen, Seite „Aktuelles“ (laut Stefans Screenshots vom 27.10.2026, Unterseiten nicht gesehen) | Abruf durch unseren Abrufdienst am 20.11.2026 wegen robots.txt abgelehnt; Inhalt der robots.txt selbst konnte nicht gelesen werden | **nicht anbindbar** | Selbst ein Sammeldienst (wie bergfex, D-17552a5cfa37): als Quelle ungeeignet, auch ohne robots-Sperre. Nutzen: Gebietsliste als Startkatalog (SR-40d931b69d60). Betreiber und Impressum unbekannt; bei Interesse an einer Zusammenarbeit kann Stefan das Impressum im Browser nachsehen. |

Bestand am 20.11.2026: Von den 72 Gebieten des Vorbilds haben wir nur das Tannheimer Tal (mit Jungholz, aus
tourinfra und tirol.at). Es fehlen alle bayerischen Allgäu-Gebiete, darunter Oberstdorf, die Hörnerdörfer
(Fischen, Ofterschwang, Bolsterlang, Obermaiselstein, Balderschwang), Bad Hindelang mit Oberjoch und Unterjoch,
Oberstaufen, Pfronten, Nesselwang, Füssen, Isny, Scheidegg und das Unterallgäu, außerdem das Kleinwalsertal und
Sulzberg (beide Vorarlberg, dort haben wir gar nichts).
