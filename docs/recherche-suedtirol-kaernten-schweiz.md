# Recherche: Loipenquellen Südtirol, Kärnten, Schweiz

Stand 2026-11-13.

**Umsetzung:** Südtirol angebunden (E-19, PR #18). Schweiz und Liechtenstein angebunden (E-20, P29, P26): Engadin, Davos Klosters und Goms über den tourinfra-Loipenmanager (die Schnappschüsse zeigten, dass diese Regionen denselben Dienst wie der Chiemgau nutzen), alle übrigen 94 Langlauforte über Schweiz Tourismus. Dabei gefunden und mit angebunden: Gastein, Ramsau am Dachstein und Seefeld im selben tourinfra-Dienst. Danach (E-21, P27, P28): St. Anton am Arlberg über die eigene Seite zum Loipenzustand (Status je Loipe mit Zeitstempel) und Kärnten über den täglichen Wintersportbericht Nassfeld-Pressegger See (PDF auf tools.nlw.at). Der Bericht zählt nur offene und alle Loipen je Ort (Hermagor, Gitschtal, Kirchbach, Dellach, Kötschach-Mauthen, Weissensee); daraus wird je Ort ein „Loipennetz“. Nicht angebunden: Serfaus (Status ohne Datum), Wilder Kaiser (Status nur per JavaScript), Nauders und Tiroler Oberland (nichts Verwertbares).

Ursprünglicher Stand: nur Recherche, noch keine Adapter. Alle Seiten wurden über den Workflow „Schnappschuss“ auf einem GitHub-Runner geholt (robots.txt beachtet, 5 s Abstand). Die Schnappschüsse liegen unter `tests/fixtures/recherche-2026-11-13/<region>/<quelle>/`, das Abrufprotokoll in `tests/fixtures/schnappschuss-protokoll.txt`.

Wichtig: Mitte November ist überall Vorsaison. Fast alle Loipen stehen auf „geschlossen“. Ob eine Quelle im Winter wirklich täglich gepflegt wird, lässt sich erst im Dezember prüfen (gehört in den Dezember-Satz aus dem Backlog).

## Empfehlung zur Ausbau-Reihenfolge

1. **Dolomiti NordicSki** (Südtirol Ost + Osttirol + Cortina/Comelico). Eine einzige HTML-Seite liefert 173 Loipen mit 840 km, je Loipe Status in fünf Stufen, Länge, Höhe, Schwierigkeit und Hinweistext. robots.txt erlaubt alles. Geringster Aufwand, größter Gewinn.
2. **Open Data Hub Südtirol** (ganz Südtirol). Offene JSON-API, Lizenz CC0, 272 Loipen mit Koordinaten (Start/Ziel), Tourismusverein, „IsOpen“ und „IsPrepared“. Deckt den Westen ab (Vinschgau, Ulten, Martell, Ridnaun, Sarntal, Eggental), den Dolomiti NordicSki nicht hat. Der Status ist aber noch fraglich (siehe unten), deshalb erst Stammdaten, Status nach Dezember-Prüfung.
3. **Schweiz, zuerst Engadin und Davos**, dann **snow.myswitzerland.com** für den Rest. Engadin hat die beste Datenqualität aller gefundenen Quellen (JSON in der Seite, 108 Loipen, Status je klassisch/Skating, gespurte km, Zeitstempel). Schweiz Tourismus deckt 126 Langlauforte ab, je Loipe offen/zu und km, Daten von infosnow.ch.
4. **Kärnten zuletzt.** Es gibt kein Landesportal mit Status je Loipe. kaernten.at zeigt nur Gebietsberichte, deren Daten von bergfex stammen („Data provided by Bergfex.at“). Lokale Seiten (Nassfeld/Weissensee) haben Loipenlisten, den Status aber nur als PDF mit Symbolen.

Begründung der Reihenfolge: Südtirol ist am nächsten an der Ausbau-Richtung Innsbruck, die Daten sind am besten zugänglich, und die Pustertal-Loipen hängen direkt an Osttirol (tirol.at). Die Schweiz hat sehr gute Daten, ist aber weiter weg. Kärnten hat die schwächsten und rechtlich unklarsten Quellen.

## Quellen im Einzelnen

### Südtirol

| Quelle | URL | Format | Abdeckung | Status / Datum | robots / Bedingungen | Aufwand |
|---|---|---|---|---|---|---|
| Dolomiti NordicSki | `https://www.dolomitinordicski.com/de/regionen/alta-badia/geoeffnete-loipen/2.html` (zeigt alle Regionen) | HTML-Tabelle, `td[data-status]` | 173 Loipen, 840 km: Antholz, Gsies, 3 Zinnen, Osttirol, Comelico, Cortina, Ahrntal, Seiser Alm, Gröden | `open`, `partially_open`, `open_not_prepared`, `closed`, `unknown`; Länge, max. Höhe, Hinweis; **kein** Aktualisierungsdatum | robots: alles erlaubt. Impressum ohne Nutzungsregeln, vor Veröffentlichung beim Komitee fragen (info@dolomitinordicski.com) | klein: 1 Abruf je Lauf |
| Open Data Hub (NOI/IDM, Daten von LTS) | `https://tourism.api.opendatahub.com/v1/ODHActivityPoi?odhtagfilter=loipen&pagesize=300&language=de&removenullvalues=true` | JSON-API | 272 Loipen (356 mit Tag „langlaufen“), 37 Tourismusvereine | `IsOpen`, `IsPrepared`, `LastChange`; keine Länge, kein GPX im Datensatz, nur Start-/Zielpunkt | Lizenz CC0 je Datensatz (`LicenseInfo`), ohne Anmeldung, 10–20 Anfragen/s, `Referer`-Header empfohlen | klein bis mittel |
| ODH Schneebericht | `https://tourism.api.opendatahub.com/v1/Weather/SnowReport?lang=de` | JSON | 26 Skigebiete | `totaltracks`/`opentracks` je Skigebiet, Schneehöhen | wie oben | nur Ergänzung |
| suedtirol.info | `https://www.suedtirol.info/de/erleben/winter/langlaufen/loipen` | HTML | Portalansicht der ODH-Daten | kein eigener Status | robots ok | nicht nötig |
| Seiser Alm | `https://www.seiseralm.it/opentrails` | HTML, Status per JavaScript | Seiser Alm | im Schnappschuss kein Status | robots ok | nicht nötig, steckt in Dolomiti NordicSki |
| val-gardena.com | – | – | Gröden | – | robots.txt antwortet 403, also gesperrt | entfällt, Gröden steckt in Dolomiti NordicSki |

Befund ODH-Status: Im November stehen 7 von 272 Loipen auf `IsOpen=true`, darunter Einträge mit `LastChange` aus Dezember 2024 und ein „TEST“-Eintrag. Einzelne Vereine setzen den Status also nach der Saison nicht zurück. Der Status ist daher nur zusammen mit `LastChange` brauchbar (z. B. „offen“ nur, wenn in den letzten 48 h geändert). Das muss im Dezember an echten Daten geprüft werden.

Überschneidung: Dolomiti NordicSki enthält rund 50 Osttiroler Loipen, die tirol.at schon liefert. Das ist ein Fall für die Dubletten-Regel D15.

### Schweiz

| Quelle | URL | Format | Abdeckung | Status / Datum | robots / Bedingungen | Aufwand |
|---|---|---|---|---|---|---|
| Engadin Tourismus | `https://www.engadin.ch/de/berichte/schneesportberichte?tab=trails` | JSON in der HTML-Seite | 108 Loipen, 262 km (Engadin St. Moritz) | `status`, `statusClassic`, `statusSkating`, `lengthPreparedClassic/Skating`, `condition`, `liveUpdate` (Zeitstempel), `hasGeometry` | robots ok; AGB nicht geprüft | klein |
| Davos Klosters | `https://www.davos.ch/aktivitaeten/schneesport/langlauf/loipenbericht-davos-klosters` | HTML | 31 Loipen (Davos, Klosters) | OPEN/CLOSED, „3500 m von 4800 m offen“, Zustand; zusätzlich Spurgeräte-Tracking | robots ok | klein |
| Schweiz Tourismus | `https://snow.myswitzerland.com/schneebericht/langlauf/` (Übersicht), je Ort `…/schneebericht/<ort>-<id>/` | HTML | 126 Langlauforte, je Ort Loipenliste | je Loipe Typ, Zustand (closed/open), „0.0/2.7 km open“, Stand je Ort („Last update: 13.11.2026, 04:05“); Quelle infosnow.ch und SchweizMobil | robots ok (nur `?noidx=` gesperrt). Nutzungsbedingungen nicht ladbar, vor Veröffentlichung prüfen | mittel: 1 Abruf je Ort |
| Arosa Lenzerheide | `https://arosalenzerheide.swiss/de/Lenzerheide/Winter/Langlaufen` | HTML | Gebiet: 57 km | nur Summe km offen, mit Zeitstempel | robots ok | nur als Ergänzung |
| Goms | `https://www.goms.ch/wintersportbericht/loipen-bericht` | Status per JavaScript | Goms (100+ km) | im Schnappschuss kein Status; Inhalte CC-BY | robots ok | später, myswitzerland nutzen |
| infosnow.ch | `https://www.infosnow.ch/` | Kartenanwendung | Datenlieferant hinter myswitzerland | – | – | nicht direkt nötig |

### Kärnten

| Quelle | URL | Format | Abdeckung | Status / Datum | robots / Bedingungen | Aufwand |
|---|---|---|---|---|---|---|
| kaernten.at Loipenberichte | `https://www.kaernten.at/service/wetter/loipenberichte/` | HTML | je Gebiet, im November nur 2 Gebiete (Gerlitzen, Wörthersee-Rosental) | „geschlossen“, „Letztes Update: 11.11.2026 - 12:27“, km gespurt/gesamt je Stil | robots.txt fehlt (404). Daten ausdrücklich von bergfex.at, Weiterverwendung daher heikel | klein, aber nur Gebietsebene |
| bergfex Kärnten | `https://www.bergfex.at/kaernten/langlaufen/loipenberichte/` | HTML | wie oben | wie oben | robots erlaubt die Seite; bergfex ist kommerziell, Nutzung ohne Zustimmung nicht empfohlen | – |
| Nassfeld / NLW | `https://www.nassfeld.at/de/Winter-World/Outdoor-Relax-World/Langlaufen/Alle-Loipen`, Tagesbericht `https://tools.nlw.at/sportbericht/print/wintersportbericht-nps.pdf` (auch `-ws.pdf` für Weissensee) | HTML-Liste, Status nur im PDF als Symbole | Nassfeld, Gailtal, Lesachtal, Weissensee | PDF: „Loipen 0/8“, je Loipe Symbol | robots ok; PDF 5–9 MB, nicht ins Repo gelegt | groß (PDF-Auswertung) |
| Tourenportal Kärnten | `https://touren.kaernten.at/de/touren/#cat=Langlauf` | outdooractive-Karte (JavaScript) | ganz Kärnten | outdooractive kennt einen Öffnungsstatus | braucht outdooractive-API-Zugang | groß |

## Was in der Cloud-Umgebung „loipenblick“ fehlt

Für die Entwicklung der Adapter müssten diese Hosts in der Umgebung freigegeben werden: `www.dolomitinordicski.com`, `tourism.api.opendatahub.com`, `www.engadin.ch`, `www.davos.ch`, `snow.myswitzerland.com`. Für die Recherche war das nicht nötig, weil der Schnappschuss-Workflow auf GitHub läuft.

## Offene Punkte

- Dezember: Status von Dolomiti NordicSki, ODH und Engadin bei echtem Betrieb prüfen (zweiter Schnappschuss-Satz).
- Vor öffentlicher Seite: Nutzungsbedingungen von Schweiz Tourismus, Engadin, Davos und Dolomiti NordicSki klären. Nur der Open Data Hub hat eine klare offene Lizenz (CC0).
- GPX: Keine der Status-Quellen liefert GPX direkt. Engadin meldet `hasGeometry`, Dolomiti NordicSki verlinkt eine Karte mit Loipen-ID. Das wäre eine eigene Recherche.
