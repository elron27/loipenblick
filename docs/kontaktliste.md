# Kontaktliste: Stellen, die wir fragen oder informieren müssen

Stand 27.11.2026. Wird bei jeder neuen Quelle ergänzt. Gepflegt im Repo, Kopie für Stefan unter
`livegang/vorbereitung/kontaktliste.md` im Projektordner.

**Vorgehen (Stefan, 19.11.2026):** Daten von Quellen ohne Zustimmung dürfen in die **Testversion**. Die Quelle steht dann in
`config/sources.yaml` auf `erlaubnis: nur_test` und erscheint auf der öffentlichen Seite nicht. Gefragt wird, wenn die
Anbindung funktioniert, mit einer Vorführung der Testseite. Vor dem Livegang wird jede Quelle auf `nur_test` geprüft
(Pflichtpunkt in [livegang-checkliste-stefan.md](livegang-checkliste-stefan.md)).

Erlaubnis-Status in `sources.yaml` (`nutzung.erlaubnis`):

| Wert | Bedeutung | Öffentliche Seite |
|---|---|---|
| `liegt_vor` | Betreiber hat zugestimmt (Datum und Wortlaut in `docs/erlaubnisse/`, Pflicht nach B31) | wird gezeigt |
| `ausstehend` | angefragt oder Anfrage geplant; Nutzungsbedingungen verbieten die Übernahme nicht ausdrücklich | wird mit Quellenhinweis gezeigt (Regel aus der Livegang-Planung: bei Schweigen bis 11.12. mit Quellenhinweis zeigen) |
| `nur_test` | Nutzungsbedingungen verbieten Übernahme/Speichern ohne Einwilligung, oder noch nicht geprüft | wird **nicht** gezeigt |
| `abgelehnt` | Betreiber hat der Übernahme widersprochen (B30) | wird **nie** abgerufen und **nirgends** gezeigt, auch nicht in der Testversion; Gebiete, deren Loipen auch über andere Quellen kommen, stehen in `config/gebiete.yaml` unter `ausgeblendet` |

## 1. Quellbetreiber mit Loipendaten

| Stelle | Quelle / Region | Wofür | Kontakt | Stand | Notiz |
|---|---|---|---|---|---|
| Tirol Werbung GmbH | tirol.at, ganz Tirol | Loipenstatus, Lage, Länge | info@tirol.at; geantwortet hat Victoria Schilcher, Projektmanagement digitale Kanäle | angefragt 19.11.2026, **Erlaubnis am 23.11.2026** | Abholung über die Website mit Quellangabe und Link auf tirol.at ist in Ordnung. Seit 23.11. `erlaubnis: liegt_vor` (B31, E-37), Beleg [erlaubnisse/tirol-werbung-2026-11-23.md](erlaubnisse/tirol-werbung-2026-11-23.md). Spätere Option: Open-Data-Datensatz der Österreich Werbung (LTO Freigabetool). Kein Nachfassen mehr nötig. |
| Tegernseer Tal Tourismus GmbH | tegernsee.com | Loipenstatus, gespurte km | info@tegernsee.com | angefragt 19.11.2026 | |
| Tourist-Info Bayrischzell | bayrischzell.de | Loipenstatus | tourist-info@bayrischzell.de | angefragt 19.11.2026 | |
| Gemeinde Fischbachau | fischbachau.de | Loipenstatus | rathaus@fischbachau.de | angefragt 19.11.2026 | |
| Gemeinde Aschau i. Chiemgau | aschau.de (Sachrang) | Loipenstatus | gemeinde@aschau.de | angefragt 19.11.2026 | |
| Chiemgau GmbH (Chiemgau Tourismus) | tourinfra Loipenmanager Chiemgau (Ruhpolding, Reit im Winkl, Inzell, Achental u. a.) | Loipenstatus, Strecken | Martina Tremel, Digitale Medien, Martina.Tremel@chiemgau.bayern | angefragt, **Antwort 20.11.2026: vorerst keine Freigabe**; Antwort von Stefan verschickt 21.11.2026 | Fragt, ob wir eine tourinfra-Schnittstelle nutzen oder Seiten auslesen; klärt intern und mit dem Systemanbieter (green-solutions). Bitte: Loipenmanager-Daten vorerst nicht übernehmen. Seit 20.11. `nur_test`. Antwortentwurf im Projekt-Thread "Chiemgau-Rückfrage". |
| TVB Tannheimer Tal | tourinfra Loipenmanager | Loipenstatus, Strecken | info@tannheimertal.com | angefragt 19.11.2026 | |
| TVB Olympiaregion Seefeld | seefeld.com, tourinfra | Loipenstatus, gespurte km | region@seefeld.com | angefragt 19.11.2026, **Erlaubnis am 27.11.2026** | Wortlaut: „ja, sehr gerne können Sie den Loipenstatus wie beschrieben auf loipen-blick.de anzeigen. Vielen Dank für die Quellenangabe und den Link zu unserer Seite.“ Seit 27.11. `seefeld` (Loipenbericht seefeld.com) `erlaubnis: liegt_vor` (B31, E-45), Beleg [erlaubnisse/seefeld-2026-11-27.md](erlaubnisse/seefeld-2026-11-27.md). Die Anfrage beschrieb nur seefeld.com; `seefeld-tourinfra` (Loipenmanager desselben Verbands, mit Streckenverlauf) bleibt deshalb `ausstehend`, die Anzeige ändert sich nicht. Seefelder Loipen von tirol.at sind durch die Tirol-Werbung-Freigabe gedeckt (E-37). Kein Nachfassen nötig; für eine ausdrückliche tourinfra-Freigabe reicht eine kurze Rückfrage. |
| TVB Achensee (Achensee Tourismus) | achensee.com; Gebiete Achensee (Maurach, Pertisau, Wiesing) und Steinberg am Rofan (Achenkirch, Steinberg) | Schneebericht | Martina Unterberger, Welcome-CENTER Achensee, info@achensee.com | angefragt 19.11.2026, **abgelehnt am 20.11.2026** | Wortlaut: „Wir stimmen dem automatisierten Abruf und der Übernahme unserer Loipendaten jedoch nicht zu. Bitte sehen Sie daher von einer Verwendung unserer Daten auf Ihrer Website ab.“ Seit 20.11. `erlaubnis: abgelehnt`, Quelle aus (B30, E-30). Die Gebiete `achensee` und `steinberg-rofan` sowie die Wiesinger Loipe „W1 - Loipe Buchbergl“ waren vom 20. bis 23.11. auch für tirol.at-Daten ausgeblendet. Seit 23.11.2026 (Freigabe der Tirol Werbung) zeigt die Seite sie wieder **nur über tirol.at** (Stefans Entscheidung, E-37); achensee.com bleibt aus. Hinweis: Die Absage bat, „von einer Verwendung unserer Daten auf Ihrer Website abzusehen“; meldet sich Achensee deshalb, die Gebiete wieder unter `ausgeblendet` in `config/gebiete.yaml` eintragen und mit Achensee sprechen. Antwort- und Nachfrage-Entwurf im Projekt-Thread „Achensee nach Absage abschalten“. **Endgültig abgelehnt am 25.11.2026** (Patrick Benko, Digitale Medien, auf Stefans Nachfrage): kein Test der Anbindung möglich gewesen; „Der Status unserer Langlaufloipen ist in der Region ein sensibles Thema. Daher ist es uns wichtig, diesen ausschließlich auf Websites darzustellen, die von uns betreut und gewartet werden.“; Deadline und automatische Anbindung bei Schweigen hätten die Entscheidung bestärkt. Seit 25.11. stehen die Gebiete unter `nur_test` in `config/gebiete.yaml` (B30 AK 5, E-43): nur Stefans Testseite (`LOIPEN_OEFFENTLICH=false`) zeigt sie über tirol.at, mit Hinweis „nur Test, nicht öffentlich“; die öffentliche Seite, Abo und Push lassen sie weg. |
| TVB Kufsteinerland | kufstein.com | Schneebericht | info@kufstein.com | angefragt 19.11.2026 | |
| TVB Kaiserwinkl | kaiserwinkl.com | Loipenbericht | info@kaiserwinkl.com | angefragt 19.11.2026, Rückfrage nach Schnittstelle 19.11. beantwortet, **Erlaubnis am 24.11.2026** | Umsetzung wie angefragt (Quellangabe und Link) ist erlaubt. Seit 24.11. `erlaubnis: liegt_vor` (B31, E-41), Beleg [erlaubnisse/kaiserwinkl-2026-11-24.md](erlaubnisse/kaiserwinkl-2026-11-24.md). **Vorbehalt:** gilt bis zur Klärung, ob die Agentur ein Widget für externe Seiten baut; der Verband meldet sich dann wieder. Eine Schnittstelle ist nicht geplant. Kein Nachfassen nötig. |
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
| Tourismusverband Ostbayern e.V. (Bayerischer Wald) | tourinfra Loipenmanager `bayerischer-wald` (253 Loipen, 11 Gebiete) | Loipenstatus, Strecken | Adresse aus dem Impressum von bayerischer-wald.de ergänzen (Sitz Regensburg) | **nicht angefragt**, Entwurf liegt bereit | Seit 28.11.2026 angebunden, `nur_test` (P44, E-24). Entwurf: Projektdateien `livegang/vorbereitung/erlaubnis-mails-p44.md`. |
| Tourismuszentrale Fichtelgebirge e.V. | tourinfra Loipenmanager `fichtelgebirge` (75 Loipen, 5 Gebiete) | Loipenstatus, Strecken | Adresse aus dem Impressum von fichtelgebirge.bayern ergänzen (Sitz Fichtelberg, Tel. +49 9272 969030) | **nicht angefragt**, Entwurf liegt bereit | Seit 28.11.2026 angebunden, `nur_test` (P44, E-24). |

## 2. Daten ohne Anfrage, aber mit Pflichten

| Stelle | Wofür | Bedingung | Stand |
|---|---|---|---|
| GeoSphere Austria | Schneehöhe, Neuschnee Österreich | CC BY 4.0, Namensnennung | erfüllt (Quelle steht bei jedem Wert) |
| Deutscher Wetterdienst | Schneehöhe Bayern | Open Data, Quellenvermerk | erfüllt |
| Bright Sky | Vorhersage (Daten DWD MOSMIX) | freier Dienst, Quellenvermerk DWD | erfüllt |
| Open Data Hub Südtirol | Loipen Südtirol | CC0 je Datensatz | erfüllt |
| OpenStreetMap | Kartenkacheln | Tile Usage Policy (kein Massenabruf, Attribution) | vor dem Livegang prüfen, ob eigener Kachelanbieter nötig ist |
| MeteoSchweiz | Schneehöhen Schweiz (geplant) | Open Data, Bedingungen noch prüfen | noch nicht angebunden |


## 3. tourinfra-Loipenmanager (green-solutions)

Zehn Quellen lesen dieselbe Abfrage `module.tourinfra.com/<kunde>/inc/ajax.php?ajaxtype=getLoipenmanager`, also das
JSON, das auch das Loipenbericht-Widget auf der Webseite des Betreibers lädt. Das ist keine für Dritte freigegebene oder
dokumentierte Schnittstelle. Systemanbieter: green-solutions GmbH & Co. KG, Viehmarktplatz 6, 82418 Murnau,
office@green-solutions.info, +49 8841 4874011 (Impressum green-solutions.info, gelesen 20.11.2026). Auf ihren Seiten steht
nichts zu einer offenen Schnittstelle oder zur Weitergabe an externe Plattformen.

Die Daten gehören dem jeweiligen Tourismusverband, nicht green-solutions. Die Rückfrage der Chiemgau GmbH (20.11.2026)
betrifft deshalb zunächst nur den Chiemgau. Sagt green-solutions aber allgemein, dass der Abruf des Widget-JSON durch Dritte
nicht gewünscht ist, gilt das für alle zehn:

| Quelle (`key`) | Betreiber | Erlaubnis-Stand |
|---|---|---|
| `chiemgau` | Chiemgau GmbH | `nur_test` seit 20.11.2026 (Freigabe ausstehend) |
| `tannheimer` | TVB Tannheimer Tal | angefragt 19.11.2026 |
| `seefeld-tourinfra` | TVB Olympiaregion Seefeld | angefragt 19.11.2026; Zusage vom 27.11. nennt nur seefeld.com, daher weiter `ausstehend` (E-45) |
| `engadin` | Engadin Tourismus | nicht angefragt |
| `davos-klosters` | Destination Davos Klosters | nicht angefragt |
| `goms` | Goms Tourismus | nicht angefragt |
| `gastein` | Gastein Tourismus | nicht angefragt |
| `ramsau` | TVB Ramsau am Dachstein | nicht angefragt |
| `bayerischer-wald` | Tourismusverband Ostbayern e.V. | `nur_test` seit 28.11.2026, nicht angefragt (P44) |
| `fichtelgebirge` | Tourismuszentrale Fichtelgebirge e.V. | `nur_test` seit 28.11.2026, nicht angefragt (P44) |

## 4. Ortsseiten für die Querprüfung von tirol.at (in Arbeit)

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

### Allgäu über Gemeinde- und Tourismusseiten (P38, E-27, geprüft 20.11.2026)

Stefan 20.11.2026: Allgäu über die Seiten der Gemeinden und Tourismusämter anbinden, nicht über loipen-allgaeu.de.
Schnappschüsse Runden 23 bis 26 unter `tests/fixtures/recherche-2026-11-20/`. robots.txt war überall ohne Sperre.

| Stelle | Region | Wofür | Kontakt | Stand | Notiz zu den Nutzungsbedingungen |
|---|---|---|---|---|---|
| Tourismus Oberstdorf (oberstdorf.de, Wintersportbericht) | Oberallgäu | Status, Länge und Stand von 14 Loipen (inkl. Nordic Zentrum, Nachtloipe); die Seite nennt auch Parkplätze mit Gebühr | info@oberstdorf.de | nicht angefragt | Impressum: Vervielfältigung und Verwertung nur mit schriftlicher Zustimmung, Kopien nur privat. Quelle mit erlaubnis nur_test. Bericht ruht bis ca. Ende November. |
| Tourist-Info Wertach (wertach.de, Wintersportbericht) | Oberallgäu | Status, Länge, Schwierigkeit von 3 Loipen, Stand | info@wertach.de | nicht angefragt | Impressum wie Oberstdorf (gleiche Tramino-Vorlage). nur_test. |
| Tourismus Hörnerdörfer (hoernerdoerfer.de), Intermaps (sdds4.intermaps.com) | Oberallgäu, Balderschwang | Status, Länge und Stand von 26 Loipen in Fischen, Obermaiselstein, Bolsterlang, Ofterschwang, Balderschwang | info@hoernerdoerfer.de | nicht angefragt | Eigene Seite bettet nur den Intermaps-Bericht ein. Intermaps ist Bezahldienst (P17), Ausnahme nur Testversion wie Innsbruck. Impressum: Nutzung der Daten zu anderen Zwecken nur mit schriftlicher Zustimmung der Tourismus Hörnerdörfer GmbH. In der Anfrage nach dem Intermaps-Bericht fragen. |
| Pfronten Tourismus (pfronten.de, Wintersportbericht) | Ostallgäu | Status, letztes Präparierdatum, Länge, Technik, Einstieg mit Koordinate von 10 Loipen | info@pfronten.de | nicht angefragt | Impressum ohne Freigabe zur Übernahme. Daten stehen im HTML der Liste (eo-POI-Widget von eberl online); der API-Schlüssel der Seite wird nicht genutzt. nur_test. |
| Füssen Tourismus und Marketing (fuessen.de) | Ostallgäu | Status der Loipengruppen Füssen (F1), Weißensee (W1, W2), Hopfen (H1, H2) | tourismus@fuessen.de | nicht angefragt | Impressum ohne Freigabe zur Übernahme. nur_test. |
| Isny Marketing, Stadt Isny (isny.de) | Württembergisches Allgäu | Status, Länge, Technik, Schwierigkeit von 12 Loipen in Isny und Maierhöfen | info@isny-marketing.de | nicht angefragt | Impressum Stadt Isny: Verwertung nur mit schriftlicher Zustimmung. nur_test. |
| Kleinwalsertal Tourismus (kleinwalsertal.com, Loipen aktiv) | Kleinwalsertal (Vorarlberg) | Status und Technik von 19 Runden (Schwarzwasser-, Schwende-, Steinbockloipe) | info@kleinwalsertal.com | nicht angefragt | Impressum und AGB ohne Freigabe zur Übernahme. nur_test. |
| Bad Hindelang Tourismus (badhindelang.de) | Oberallgäu | 10 Loipen in Oberjoch, Unterjoch, Bad Hindelang | Kontakt laut Impressum | **nicht angebunden** | Status nur über das eo-POI-Widget, das erst im Browser mit Schlüssel lädt, und im PDF „Schneebericht zum Ausdrucken“ von bergsportbericht.de (OYA media GmbH, kostenpflichtiger Dienst für Orte, Status nur als Farbsymbol). Möglich wäre: Bad Hindelang fragen, ob eine Liste wie in Pfronten ins HTML kann. |
| Allgäu GmbH (allgaeu.de, Schneebericht) | ganzes Allgäu | Sammelbericht | Kontakt laut Impressum | **nicht angebunden** | Lädt den Status ebenfalls nur im Browser über das eo-POI-Widget mit Schlüssel. |
| Scheidegg, Westallgäu (scheidegg.de, westallgaeu.de) | Westallgäu | – | – | **nicht angebunden** | Scheidegg: eo-POI-Widget nur im Browser; westallgaeu.de ohne Loipenstatus. |
| Oberstaufen, Nesselwang, Sulzberg (Vorarlberg) | Oberallgäu, Ostallgäu | – | – | **kein Status gefunden** | Langlaufseiten nur mit Beschreibung, kein Loipenstatus (Sulzberg: nur Startseite der Gemeinde). |

## 5. Allgäu (geprüft 20.11.2026)

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

Nachtrag 20.11.2026: Die Gemeinde- und Tourismusseiten sind inzwischen angebunden, Befund und Stand im Abschnitt 4 unter „Allgäu über Gemeinde- und Tourismusseiten“ (P38, E-27).
