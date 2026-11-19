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
