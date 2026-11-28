# Datenschutz und Nutzungsbedingungen der Quellen

Stand: 28.11.2026. Vorbereitung für den Livegang am 11.12.2026 (Backlog-Punkt „Nutzungsbedingungen aller Quellen prüfen“, B6, B16, B23, P17).

> **Keine Rechtsberatung.** Dieses Dokument fasst zusammen, was der Code tut und was die Seiten der Quellen selbst schreiben. Ob das rechtlich reicht, kann nur eine Anwältin oder ein Anwalt verbindlich sagen. Alles, was unsicher ist, steht als **zu klären** da.

## Kurzfassung

1. **Datenschutzerklärung:** Die eingebaute Vorlage (`loipen/generator/vorlagen/datenschutz.html.j2`) passt zum tatsächlichen Verhalten der Seite. Eine Lücke gab es: die **Online-Ortssuche** schickt nach Klick auf „Suchen“ den Suchbegriff und die IP an `photon.komoot.io`. Das stand nirgends, und die Sicherheits-Header (CSP) haben die Anfrage auf dem Webspace sogar gesperrt, die Suche ging dort also gar nicht. Beides ist in diesem PR behoben. Empfehlung: die Vorlage nehmen statt eines Generator-Texts, `LOIPEN_DATENSCHUTZ_DATEI` leer lassen.
2. **Quellen:** Von 24 Quellen, die nach heutigem Stand öffentlich angezeigt würden, haben 4 zugestimmt oder stehen unter offener Lizenz (tirol.at samt Achensee-Loipen, seefeld.com, kaiserwinkl.com, Open Data Hub). **Fast alle anderen Betreiber schreiben in Impressum oder Nutzungsbedingungen, dass Kopien nur privat erlaubt sind oder eine schriftliche Zustimmung brauchen.** Fünf nennen ausdrücklich „öffentliche oder kommerzielle Zwecke“ oder „Speicherung in Datenbanken“ als untersagt (Kufsteinerland, NLW/Nassfeld, Engadin, Davos Klosters, MySwitzerland).
3. **Elf Quellen wurden noch nie angefragt** (St. Anton, Kitzbüheler Alpen, Dolomiti NordicSki, Engadin, Davos Klosters, Goms, Gastein, Ramsau, MySwitzerland, Nassfeld, Steiermark). Für sie gilt die Regel „Schweigen bis 11.12. = zeigen“ nicht, weil sie die Chance nicht hatten. Empfehlung unten.

## 1. Datenschutz: was die Seite tatsächlich tut

Geprüft im Code am 28.11.2026 (`loipen/generator/static/app.js`, `sw.js`, `vorlagen/htaccess.j2`, `abo/`, `zaehler/`).

| Was | Wohin geht etwas | Wann | In der Vorlage |
|---|---|---|---|
| Seitenaufruf | Webspace netcup, Zugriffsprotokoll mit IP | immer | ja, „Hosting und Server-Protokolle“, AVV mit netcup liegt vor |
| Besucherzähler (B13) | eigener Webspace `zaehler/`, nur Tagessummen, Tages-Prüfwert ohne IP | bei jedem Ansichtswechsel, wenn `LOIPEN_ZAEHLER_PASSWORT` gesetzt | ja, „Besucherzähler“ |
| Kartenkacheln | `tile.openstreetmap.org` (OSMF) | erst nach „Karte laden“ (Einwilligung, im Browser gemerkt) | ja, „Karte“ |
| GPS-Standort | bleibt im Browser | beim ersten Besuch fragt die Seite einmal, sonst auf Knopfdruck | **korrigiert:** stand vorher „nur wenn du tippst“ |
| Online-Ortssuche | `photon.komoot.io` (komoot), Suchbegriff + IP | nur nach Klick auf „Suchen“ in der Ortswahl | **neu:** Abschnitt „Ortssuche im Internet“, dazu CSP `connect-src` freigegeben |
| `localStorage` | im Browser: `ort`, `gps_gefragt`, `karte_ok`, `app_hinweis_aus`, `merkliste`, `loipen_nicht_zaehlen` | bei Einstellungen | **ergänzt:** alle Schlüssel genannt |
| Service Worker | Cache im Browser | immer (Offline-Fähigkeit) | ja |
| E-Mail-Abo und Meldungen (E-18) | Webspace `abo/`, dann NAS; Mails über netcup | nur bei Formular, Double-Opt-In | ja, sobald `abo/` aktiv ist |
| Push über ntfy | ntfy.sh, IP und Thema | erst beim Abonnieren in der App | ja, wenn `LOIPEN_PUSH_PRAEFIX` gesetzt |
| Spendenlink | PayPal o. ä. | erst beim Klick, Link mit `noreferrer` | ja, wenn `LOIPEN_SPENDEN_URL` gesetzt |
| Google Maps, Quellen, Webcams | jeweiliger Anbieter | nur als Link | ja, „Links zu anderen Seiten“ |

Nicht gefunden: keine Cookies, keine Schriftarten oder Skripte von fremden Servern (Leaflet liegt unter `static/vendor/`), keine eingebetteten Webcam-Bilder, kein Analyse-Dienst. Ein Cookie-Banner ist damit weiter nicht nötig.

### Zu klären vor dem Livegang

- **netcup Log-Frist:** Die Vorlage schreibt „nach 7 Tagen gelöscht“ (`LOIPEN_LOG_TAGE`, Standard 7). Ob netcup die Logs wirklich nach dieser Frist löscht oder ob man es im Kundenpanel einstellen kann, ist nicht geprüft. Wer: `Stefan` schaut im CCP nach und trägt die echte Zahl ein.
- **Photon-Betreiber:** photon.komoot.io sperrt automatische Abrufe per robots.txt, die Nutzungsbedingungen und der Betreiber ließen sich deshalb nicht lesen. Die Vorlage schreibt neutral „den komoot betreibt“ und verlinkt die komoot-Datenschutzerklärung. Wer: `Stefan` öffnet photon.komoot.io einmal im Browser und prüft, ob dort Regeln zur Nutzung stehen (öffentliche Instanz, meist „fair use“). Wenn die Suche zu oft angefragt würde, wäre ein Wechsel auf die Ortsliste allein möglich.
- **ntfy-Serverstandort:** Die ntfy-Datenschutzseite (Stand 15.06.2026) nennt keinen Standort. Die Vorlage sagt deshalb „können außerhalb der EU stehen“. Nachrichten werden laut ntfy 12 Stunden zwischengespeichert, IP-Adressen nur fürs Rate-Limit und normalerweise nicht protokolliert.
- **Spendenlink und „geschäftsmäßig“:** Schon in [livegang.md](livegang.md) Abschnitt 5 und 6 beschrieben. Ein Spendenlink könnte für Quellen mit der Klausel „nicht kommerziell“ ein Argument sein, dass die Seite nicht rein privat ist. Siehe Abschnitt 2.
- **Gegenlesen:** Stefan liest die Testseite `datenschutz.html` einmal ganz und vergleicht sie mit einem Generator (z. B. datenschutz-generator.de). Fehlt dort ein Pflichtpunkt, ergänzt ein Thread die Vorlage.

## 2. Nutzungsbedingungen je Quelle

Gelesen am 28.11.2026, sofern nicht anders vermerkt. Zitate wörtlich, gekürzt. „Erlaubnis“ ist der Wert in `config/sources.yaml` (`nutzung.erlaubnis`, Standard `ausstehend` = wird öffentlich gezeigt).

**Risiko** ist eine grobe Einschätzung, keine Rechtsauskunft: *gering* = Zustimmung oder offene Lizenz; *mittel* = keine Regel zur Weiterverwendung, nur allgemeines Urheberrecht; *hoch* = die Seite verbietet Datenbank-Speicherung, öffentliche oder kommerzielle Nutzung ausdrücklich, oder erlaubt Kopien nur privat. Rechtlich zählt vor allem das Datenbankrecht (§ 87b UrhG, siehe [livegang.md](livegang.md) Abschnitt 8). Reine Fakten sind nicht geschützt, die systematische Übernahme einer ganzen Datenbank schon.

### 2.1 Mit Zustimmung oder offener Lizenz

| Quelle | Bedingung | Risiko | Quellenangabe | Empfehlung |
|---|---|---|---|---|
| tirol.at (Tirol Werbung), auch Achensee-Loipen | Zustimmung 23.11.2026, [Beleg](erlaubnisse/tirol-werbung-2026-11-23.md) | gering | „tirol.at“ mit Link | so lassen |
| seefeld.com (TVB Seefeld) | Zustimmung 27.11.2026, [Beleg](erlaubnisse/seefeld-2026-11-27.md) | gering | Name + Link | so lassen |
| kaiserwinkl.com | Zustimmung 24.11.2026 bis zur Klärung eines Widgets, [Beleg](erlaubnisse/kaiserwinkl-2026-11-24.md) | gering | Name + Link | Antwort zum Widget abwarten |
| Open Data Hub Südtirol | CC0 je Datensatz, [Beleg](erlaubnisse/opendatahub-cc0.md) | gering | freiwillig, steht dabei | so lassen |

### 2.2 Angefragt am 19.11.2026, Frist 11.12.2026, bisher keine Antwort

| Quelle | Betreiber | Was die Seite sagt | Risiko | Empfehlung |
|---|---|---|---|---|
| tegernsee.com | Tegernseer Tal Tourismus GmbH | „Die unerlaubte Verwendung einzelner Inhalte oder kompletter Seiten wird sowohl straf- als auch zivilrechtlich verfolgt werden.“ ([Impressum](https://www.tegernsee.com/impressum)) | mittel | nach Frist zeigen (Stefans Regel), nur Fakten, Link |
| bayrischzell.de | Tourist-Info Bayrischzell | „Jede Vervielfältigung, Verbreitung, Speicherung … ist ohne schriftliche Genehmigung ausdrücklich untersagt.“ ([Impressum](https://www.bayrischzell.de/impressum)) | hoch | nach Frist zeigen, Risiko bewusst tragen |
| fischbachau.de | Gemeinde Fischbachau | gleicher Wortlaut wie Bayrischzell ([Impressum](https://www.fischbachau.de/impressum)) | hoch | wie Bayrischzell |
| aschau.de (Sachrang) | Gemeinde Aschau i. Chiemgau | Kopieren und Online-Stellen nur mit schriftlicher Erlaubnis, Download nur „für den privaten, nicht-kommerziellen Gebrauch“ ([Impressum](https://www.aschau.de/impressum-aschau)) | hoch | wie Bayrischzell |
| tannheimertal.com (über tourinfra) | TVB Tannheimer Tal | „Alle auf dieser Website publizierten Inhalte und Downloads sind urheberrechtlich geschützt.“ Verwendung in anderen Publikationen nur mit Zustimmung ([Impressum](https://www.tannheimertal.com/de/impressum)) | mittel | nach Frist zeigen |
| kufstein.com | TVB Kufsteinerland | Kopien „nur für den privaten, nicht kommerziellen Gebrauch“; „Jede weitergehende Nutzung insbesondere die Speicherung in Datenbanken“ untersagt ([Impressum](https://www.kufstein.com/de/footermenue-neu/impressum.html)) | **hoch** | **zu klären:** Stefan entscheidet, ob trotz Klausel gezeigt wird |
| langlaufdorf.at (Faistenau) | TVB Fuschlseeregion, Ortsbüro Faistenau | Weitergabe an andere Websites „ist nur mit ausdrücklicher Genehmigung der Redaktion gestattet“ ([Impressum](https://www.langlaufdorf.at/impressum.html)) | hoch | nach Frist zeigen, Risiko bewusst tragen |
| berchtesgaden.de | Zweckverband Bergerlebnis Berchtesgaden | „Downloads und Kopien dieser Seite sind nur für den privaten, nicht kommerziellen Gebrauch gestattet.“ ([Impressum](https://www.berchtesgaden.de/impressum)) | hoch | nach Frist zeigen, Risiko bewusst tragen |

Lungau wurde ebenfalls angefragt; die Lungau-Loipen kommen heute nicht über eine eigene Quelle.

### 2.3 Noch nie angefragt, würden heute öffentlich gezeigt

| Quelle | Betreiber | Was die Seite sagt | Risiko | Empfehlung |
|---|---|---|---|---|
| stantonamarlberg.com | TVB St. Anton am Arlberg | Inhalte „dürfen nicht ohne Erlaubnis von uns kopiert, reproduziert, neu aufgelegt, online-gestellt“ werden, „Es bedarf dazu einer schriftlichen Erlaubnis.“ ([Impressum](https://www.stantonamarlberg.com/de/impressum)) | hoch | anfragen |
| kitzbueheler-alpen.com | nicht ermittelt | Impressum-Link war im abgerufenen Inhalt nicht zu finden | **zu klären** | Adresse fehlt ohnehin (Projektplan Abschnitt 3); Stefan sucht Impressum im Browser |
| dolomitinordicski.com | Organisationskomitee Dolomiti Nordicski, Toblach | keine Regel zur Weiterverwendung, nur Bildnachweise ([Impressum, engl.](https://www.dolomitinordicski.com/en/impressum)) | mittel | anfragen |
| tourinfra: Engadin | Engadin Tourismus AG, St. Moritz | Vervielfältigung „nur mit ausdrücklicher Erwähnung von www.engadin.ch gestattet“; „für öffentliche oder kommerzielle Zwecke ist ohne vorherige schriftliche Zustimmung unsererseits untersagt“ ([Impressum](https://www.engadin.ch/de/impressum)) | **hoch** | anfragen, bis dahin `nur_test` |
| tourinfra: Davos Klosters | Destination Davos Klosters | gleicher Wortlaut wie Engadin ([AGB](https://www.davos.ch/service/agb)) | **hoch** | anfragen, bis dahin `nur_test` |
| tourinfra: Goms, Gastein, Ramsau | jeweiliger Verband, Technik green-solutions | Impressum von module.tourinfra.com: „Downloads und Kopien dieser Seite sind nur für den privaten, nicht kommerziellen Gebrauch gestattet.“ ([Impressum](https://module.tourinfra.com/chiemgau/impressum.php)); Seiten der Verbände nicht gelesen | hoch | anfragen |
| snow.myswitzerland.com | Schweiz Tourismus | „freely accessible for browsing purposes only“; Vervielfältigung nur mit Nennung von MySwitzerland.com; „for public or commercial purposes is prohibited without the prior written consent of Switzerland Tourism“ ([Terms of use](https://www.myswitzerland.com/en/planning/about-switzerland/terms-of-use)) | **hoch** | anfragen, bis dahin `nur_test` |
| tools.nlw.at (Nassfeld) | NLW Tourismus Marketing GmbH, Hermagor | Vervielfältigung „zu Informationszwecken“ erlaubt, aber auch: „Jede weitergehende Nutzung insbesondere die Speicherung in Datenbanken … ist untersagt.“ Widerspruch im selben Impressum ([Impressum](https://nlw.at/de/Impressum)) | **hoch** | anfragen, bis dahin `nur_test` |
| steiermark.com (Tourenportal) | Steiermark Tourismus (laut Bildnachweisen) | Impressum und Nutzungsbedingungen ließen sich nicht automatisch finden; auf der Tourenportal-Seite steht keine Regel | **zu klären** | Stefan öffnet das Impressum im Browser; dann anfragen |
| module.tourinfra.com/seefeld | TVB Seefeld | Zustimmung nennt nur seefeld.com | mittel | Rückfrage an den TVB, Anzeige ändert sich nicht (seefeld.com ist schon frei) |

**Mein Vorschlag für die Tabelle 2.3:** Die elf Quellen bekommen jetzt dieselbe Erlaubnis-Mail wie am 19.11., mit Frist zwei Wochen. Bis zur Antwort laufen die vier mit ausdrücklichem Verbot „öffentlich oder kommerziell“ bzw. „Datenbanken“ (Engadin, Davos, MySwitzerland, Nassfeld) als `nur_test`. Die übrigen sieben gehen nach Stefans Regel nach Ablauf der Frist mit Quellenhinweis online. Das ist keine Nachfass-Mail, sondern die erste Anfrage. Entscheidung: `Stefan`.

### 2.4 Nur auf der Testseite (`nur_test`)

Chiemgau (Freigabe offen), Alpbachtal, Wildschönau, Wilder Kaiser, Ötztal, Pitztal, Tiroler Oberland, Nauders, Serfaus-Fiss-Ladis, Paznaun, Hall-Wattens, Silberregion Karwendel, Osttirol, Innsbruck und Zugspitz Arena (Intermaps), Oberstdorf, Wertach, Pfronten, Kleinwalsertal, Füssen, Isny, Hörnerdörfer. Die Befunde aus den Impressen stehen schon im Feld `hinweis` in `config/sources.yaml` (geprüft 19. und 20.11.). Öffentlich nur mit Zustimmung. achensee.com ist `abgelehnt`.

### 2.5 Weitere Daten und Dienste

| Dienst | Bedingung | Risiko | Quellenangabe | Stand |
|---|---|---|---|---|
| OSM-Kacheln (tile.openstreetmap.org) | Attribution, gültiger Referer, eigener User-Agent, Caching; verboten: „Bulk download (“scrape”) tiles or offer prefetch features“; Sperre ohne Ankündigung möglich, kein SLA ([Tile Policy](https://operations.osmfoundation.org/policies/tiles/)) | gering | „© OpenStreetMap-Mitwirkende“ | erfüllt: Attribution in der Karte, Referrer-Policy sendet die Herkunft, Service Worker lädt keine Kacheln vor. Bei viel Verkehr selbst hosten (PMTiles, livegang.md) |
| OSM-Daten (Strecken, Parkplätze, Haltestellen, Verleih) | ODbL 1.0 | gering | steht in den Hinweisen mit Link | erfüllt. Waymarked Trails: Startseite ohne Regeln, Daten sind OSM (ODbL); **zu klären**, ob die Seite selbst einen Vermerk wünscht |
| Photon (Ortssuche) | robots.txt sperrt Abruf, Bedingungen nicht gelesen | **zu klären** | neu in den Hinweisen: Photon von komoot, Ortsdaten © OSM | siehe Abschnitt 1 |
| DWD über Bright Sky und direkt | Bright Sky: „free-to-use for all purposes“, es gelten die DWD-Bedingungen. DWD: Daten kostenlos, Nutzungsbedingungen unter dwd.de (Seite sperrt Bots, Wortlaut nicht gelesen) | gering | „Quelle: Deutscher Wetterdienst“ steht in den Hinweisen | **zu klären:** Wortlaut auf dwd.de von Hand prüfen (alter Punkt aus livegang.md) |
| GeoSphere Austria | CC BY 4.0 | gering | Pflichttext mit Link steht in den Hinweisen | erfüllt |
| Copernicus DEM | frei mit Quellenangabe | gering | bei Höhenangaben | Höhenmodell ist laut Projekt-Memory verworfen; nichts zu tun |
| ntfy.sh | öffentlicher Dienst, Nachrichten 12 h im Cache | gering | keine | in der Datenschutzerklärung |
| tourinfra-Detailseiten (Höhenmeter, Dauer) | Fußzeile: nicht auf kommerziellen Seiten | mittel | mit der jeweiligen Quelle | hängt an der Erlaubnis der Verbände |

### Was „kommerziell“ für Loipenblick heißt

Viele Klauseln unterscheiden privat und kommerziell. Loipenblick hat keine Werbung und keinen Verkauf. Ein Spendenlink ist kein Verkauf, kann aber von einem Betreiber als „nicht rein privat“ gesehen werden. Öffentlich ist die Seite in jedem Fall, und mehrere Klauseln verbieten schon die öffentliche Nutzung. **Zu klären**, falls Stefan das Risiko genauer wissen will: kurze Erstberatung bei einer Anwältin oder einem Anwalt für IT- und Urheberrecht, mit dieser Tabelle als Grundlage.

## 3. Was in diesem PR geändert wurde

- `htaccess.j2`: `connect-src 'self' https://photon.komoot.io`, damit die Online-Ortssuche (U35 AK 2) auf dem Webspace funktioniert.
- `datenschutz.html.j2`: neuer Abschnitt „Ortssuche im Internet“, Standort-Abschnitt passend zur Frage beim ersten Besuch, alle Schlüssel im Browser-Speicher genannt, Kurzfassung erwähnt „Suchen“.
- `hinweise.html.j2`: Quellenvermerk für Photon.
- `config/sources.yaml`: `nutzungsbedingungen_geprueft: 2026-11-28` für die 15 hier gelesenen Quellen.
- Test `test_online_ortssuche_erlaubt_und_in_der_datenschutzerklaerung` (U35 AK 2, B6 AK 3).
