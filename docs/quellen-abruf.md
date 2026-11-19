# Wie Loipenblick die Quellen abruft

Stand 19.11.2026, aus `config/sources.yaml`, `loipen/fetcher.py`, `loipen/zeitplan.py`, den Adaptern in
`loipen/adapters/` und `.github/workflows/live.yml`. Anlass: Rückfrage eines Quellbetreibers zur Erlaubnis-Mail
("Welche Schnittstelle nutzen Sie?"). Diese Seite soll ehrlich beantworten, was wir abrufen und wie oft.

## Kurz gesagt

- **Offizielle, dokumentierte Schnittstelle nutzen wir nur bei einer Quelle**: Open Data Hub Südtirol (CC0).
- Bei den **tourinfra-Quellen** (Chiemgau, Tannheimer Tal, Seefeld, Engadin, Davos Klosters, Goms, Gastein, Ramsau)
  lesen wir die **JSON-Antwort des Loipenmanager-Widgets**, die auch der Browser beim Anzeigen des Loipenberichts
  lädt. Das ist öffentlich erreichbar, aber keine uns zugesagte oder dokumentierte API und ohne Schlüssel.
- **Alle anderen Quellen lesen wir als öffentliche HTML-Seiten** (Schneebericht, Loipenbericht, Kartenliste) und ziehen
  daraus Name, Status, gespurte km, Länge und Stand. Kaernten (NLW) ist ein öffentliches PDF.
- Texte und Bilder übernehmen wir nicht. Besucher von Loipenblick lösen **keine** Abrufe bei den Quellen aus: die
  Seite ist statisch und wird auf dem NAS erzeugt.

## Wie jeder Abruf abläuft (für alle Quellen gleich)

| Punkt | Umsetzung | Wo |
|---|---|---|
| Abrufzeiten | Saison 1.11.–30.4.: 7, 12 und 17 Uhr (3 Läufe am Tag). Außerhalb: 1 Lauf um 8 Uhr. Ausnahmen siehe Tabelle unten. | `zeitplan` in `config/sources.yaml`, `loipen/zeitplan.py` |
| Abstand zwischen Anfragen | Mindestens `LOIPEN_REQUEST_DELAY_S` = **5 s** je Domain, nacheinander, nie parallel. Verlangt die robots.txt einen größeren `Crawl-delay` (z. B. St. Anton 10 s), gilt der. | `HoeflicherFetcher._warte`, `abstand_fuer` |
| robots.txt | Wird je Domain gelesen und vor jeder URL geprüft. Verbot = URL wird nicht angefragt. robots.txt mit 401/403 gilt als Verbot, fehlt sie (404), gilt alles als erlaubt. | `HoeflicherFetcher._robots_fuer` |
| Folgen der robots.txt | Gesperrt und darum **nicht** abgerufen: GPX von tirol.mapservices.eu und von Berchtesgaden, Kartendaten von Dolomiti NordicSki, salzkammergut.at, bergfex, zillertal.at. | `nutzung`, `strecke_hinweis` in `sources.yaml` |
| User-Agent | `LoipenBot/0.1 (...)` aus `LOIPEN_USER_AGENT` in der `.env` auf dem NAS. Vorgabe: `LoipenBot/0.1 (privat; Kontakt: siehe .env)`. **Die echte Kontaktadresse steht nur, wenn sie in der NAS-`.env` eingetragen ist** (Vorlage hat noch `HIER-DEINE-MAIL`). | `loipen/config.py`, `.env.example` |
| Zwischenspeicher | Liefert eine Seite `ETag` oder `Last-Modified`, fragen wir beim nächsten Mal mit `If-None-Match` / `If-Modified-Since`; bei 304 wird nichts neu übertragen. | `HoeflicherFetcher.get` |
| Zeitlimit | 30 s je Anfrage, keine automatischen Wiederholungen bei Fehlern. | `HoeflicherFetcher` |
| Abschalten | Je Quelle über `enabled` in der Datenbank, z. B. wenn ein Betreiber das wünscht (B16). | `Quelle.enabled` |

Zusätzlich zum NAS ruft der GitHub-Workflow **Live-Prüfung** (`.github/workflows/live.yml`) in der Saison einmal
täglich alle Quellen (geplant 6:30 Uhr, GitHub startet ihn in der Praxis erst mittags) von einem GitHub-Server ab, mit dem User-Agent
`LoipenBot/0.1 (+https://github.com/elron27/loipenblick)` (oder der Repo-Variable `LOIPEN_USER_AGENT`). Seit dem
14.11. bricht er nach 30 Minuten ab. Damit kommen heute in der Saison bis zu **vier** Läufe am Tag zusammen, nicht
drei wie in den Erlaubnis-Mails geschrieben. Empfehlung: den Zeitplan des Workflows entfernen und ihn nur noch von Hand
starten.

## Je Quelle

Anfragen je Lauf = Seiten, die ein Lauf höchstens holt (ohne robots.txt). Bei 5 s Abstand dauert ein Lauf je
Domain also etwa Anfragen × 5 s.

| Quelle (Betreiber) | Was wir abrufen | Art | Anfragen je Lauf | Läufe am Tag (Saison) |
|---|---|---|---|---|
| Tegernseer Tal Tourismus | `www.tegernsee.com/langlaufen` (+ Folgeseiten) und 26 Schneebericht-Seiten `/a-…` | HTML | ca. 28 | 3 |
| Bayrischzell Tourismus | `www.bayrischzell.de/langlaufen` und 9 Schneebericht-Seiten `/a-…` | HTML | ca. 10 | 3 |
| Fischbachau | `www.fischbachau.de/langlaufen` und 6 Schneebericht-Seiten `/a-…` | HTML | ca. 7 | 3 |
| Aschau i. Chiemgau (Sachrang) | `www.aschau.de/schneebericht-sachrang` | HTML | 1 | 3 |
| Chiemgau Tourismus | `module.tourinfra.com/chiemgau/inc/ajax.php?ajaxtype=getLoipenmanager` | JSON des Loipenmanager-Widgets | 1 | 3 |
| TVB Tannheimer Tal | `module.tourinfra.com/tannheimer/inc/ajax.php?ajaxtype=getLoipenmanager` | JSON des Widgets | 1 | 3 |
| Olympiaregion Seefeld | `www.seefeld.com/de/loipenbericht.html` **und** `module.tourinfra.com/seefeld/…getLoipenmanager` | HTML + JSON des Widgets | 2 | 3 |
| Achensee Tourismus | `www.achensee.com/de/live/schneebericht/` | HTML | 1 | 3 |
| Kufsteinerland | `www.kufstein.com/de/schneebericht.html` | HTML | 1 | 3 |
| TVB Kaiserwinkl | `www.kaiserwinkl.com/de/langlaufen-tirol/geoeffnete-loipen.html` | HTML | 1 | 3 |
| TVB St. Anton am Arlberg | `www.stantonamarlberg.com/de/service/aktueller-loipenzustand` (Crawl-delay 10 s) | HTML | 1 | 3 |
| Tirol Werbung (tirol.at) | Kartenliste `www.tirol.at/aktivitaeten/sport/langlaufen/loipen` (Markerdaten im HTML), dieselbe Liste gefiltert auf geöffnet mit bis zu 19 Folgeseiten, dazu bis zu 40 Detailseiten im Wechsel | HTML | bis 61 (meist deutlich weniger Folgeseiten) | 3 |
| Kitzbüheler Alpen | `www.kitzbueheler-alpen.com/de/bri/aktuelles/loipen-status.html` | HTML | 1 | 3 |
| Langlaufdorf Faistenau/Hintersee | `www.langlaufdorf.at/` | HTML | 1 | 3 |
| Bergerlebnis Berchtesgaden | 6 Touren-/POI-Seiten auf `www.berchtesgaden.de` (nur Stammdaten) | HTML | 6 | **1** (7 Uhr) |
| Ferienregion Salzburger Lungau | **nichts von lungau.at**: die Karte maps.lungau.at ist nicht angebunden. Nur die Prebersee-Loipe kommt über steiermark.com. | – | 0 | – |
| Dolomiti NordicSki | `www.dolomitinordicski.com/de/regionen/alta-badia/geoeffnete-loipen/2.html` (Tabelle aller Regionen) | HTML | 1 | 3 |
| Open Data Hub Südtirol | `tourism.api.opendatahub.com/v1/ODHActivityPoi?odhtagfilter=loipen&pagesize=400…` | **offizielle JSON-API**, CC0 | 1 | 3 |
| Engadin, Davos Klosters, Goms, Gastein, Ramsau | je `module.tourinfra.com/<region>/inc/ajax.php?ajaxtype=getLoipenmanager` | JSON des Widgets | je 1 | 3 |
| Schweiz Tourismus | rund 100 Ortsseiten `snow.myswitzerland.com/schneebericht/<ort>/` (Daten infosnow.ch) | HTML | ca. 100 (ca. 9 min) | **2** (7, 13 Uhr) |
| Nassfeld-Pressegger See (NLW) | `tools.nlw.at/sportbericht/print/wintersportbericht-nps.pdf` (ca. 5 MB) | PDF | 1 | **2** (7, 13 Uhr) |
| Steiermark Tourismus | Tourenportal `www.steiermark.com/de/Urlaub-planen/Tourenportal?tourCategory=46459526` (+ `&page=n`) | HTML | bis 10 (derzeit 6) | 3 |

Wetter (keine Loipenbetreiber): Bright Sky (`api.brightsky.dev`, offizielle API), GeoSphere Austria
(`dataset.api.hub.geosphere.at`, offizielle API), DWD Open Data (`opendata.dwd.de`).

## Was wir einem Betreiber anbieten können

- Umstellen auf eine **offizielle Schnittstelle**, einen Export oder Open Data, auch mit API-Schlüssel (der Schlüssel käme
  in die NAS-`.env`, nie ins Repo).
- **Seltener abrufen** (z. B. nur einmal morgens) oder einen größeren Abstand: je Quelle über `zeitplan` in
  `config/sources.yaml`, ohne Codeänderung.
- **Einen bestimmten User-Agent oder eine feste IP** nennen, damit der Betreiber uns erkennt.
- **Abschalten** der Quelle, sofort, über `Quelle.enabled`.
