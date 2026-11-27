# Recherche neue Regionen (27.11.2026)

Auftrag von Stefan: Abdeckung erweitern (Raum Augsburg, Bayerischer Wald, Mittelgebirge). Endziel ist der
**gesamte deutschsprachige Raum** (Deutschland, Österreich, Schweiz, Liechtenstein, Südtirol). Nur Recherche,
nichts angebunden. Schnappschüsse: `tests/fixtures/recherche-2026-11-27/regionen/` (Runde 28, Protokoll in
`tests/fixtures/schnappschuss-protokoll.txt`).

## Kurzfassung

1. **Bayerischer Wald zuerst.** Der Tourismusverband nutzt denselben tourinfra-Loipenmanager wie Chiemgau,
   Tannheimer Tal und Engadin. Der Abruf `module.tourinfra.com/bayerischer-wald/…getLoipenmanager` liefert
   **253 Loipen, rund 1.460 km, 41 Loipengebiete**, alle mit Koordinaten, Status getrennt nach klassisch und
   Skating, Datum der letzten Änderung und Begründung („Schneemangel“, „Saisonende“). Der Adapter existiert
   schon, die Anbindung ist im Wesentlichen ein Eintrag in `config/sources.yaml` plus Gebiete. Höchster
   Mittelgebirgs-Nutzen: schneesicherste Lagen Deutschlands außerhalb der Alpen (Arber, Bretterschachten,
   Finsterau, Mauth bis 1.100 m), von Südostbayern gut erreichbar.
2. **Fichtelgebirge direkt danach.** Gleiches Format unter `…/fichtelgebirge/…`: **75 Loipen, rund 280 km,
   5 Gebiete** (Ochsenkopf, Waldstein, Kösseine-Luisenburg, Steinwald, Kornberg). Gleicher Aufwand, kleiner.
3. **Thüringer Wald als Drittes**, aber erst nach einer Folgerecherche. Es gibt ein zentrales „Loipenportal
   Thüringer Wald“ mit täglicher Erhebung ab 7 Uhr und fünfstufigem Zustand, rund 1.400 km in 13
   DSV-Zentren. Die Liste kommt aber über Outdooractive (`api-oa.com`), das wir ohne Vertrag nicht nutzen.
   Hoffnung: Thüringen betreibt mit **ThüCAT** (`thuecat.org`) eine offene Tourismusdatenbank; ob die
   Loipenzustände dort liegen, ist offen.
4. **Schwarzwald, Harz, Sauerland, Rhön, Schwäbische Alb später.** Kein tourinfra-Kunde gefunden
   (alle Kürzel 404). Schwarzwald und Hochschwarzwald zeigen Loipen über Outdooractive, der Harz über
   destination.one. bergfex sperrt unseren Abruf (403). Hier hilft nur je Ort eine eigene Seite oder eine
   Anfrage beim Verband.
5. **Augsburg:** Keine Seite mit Loipenstatus gefunden. Die Stadt spurt bei Schnee nur einzelne Loipen
   (z. B. Stadtwald/Siebentischwald), ohne Online-Meldung. Vorschlag: als Gebiet mit Handangaben ohne Status
   aufnehmen, sobald Stefan sagt, welche Loipe er meint.

## Regionen im Einzelnen

| Region | Dienst | Umfang | Daten | robots / Bedingungen | Aufwand | Nutzen |
|---|---|---|---|---|---|---|
| Bayerischer Wald (inkl. Arberland) | tourinfra `bayerischer-wald` | 253 Loipen, ~1.460 km, 41 Gebiete | Status klassisch/Skating, Datum, Grund, Koordinaten, Länge, Schwierigkeit | robots erlaubt; tourinfra-Detailseiten: „privater Gebrauch“ → nur Fakten, wie bisher; Erlaubnis-Mail nötig | sehr klein (Konfig) | hoch: schneesicher, groß, nah |
| Fichtelgebirge | tourinfra `fichtelgebirge` | 75 Loipen, ~280 km, 5 Gebiete | wie oben | wie oben | sehr klein | mittel |
| Thüringer Wald | Loipenportal thueringer-wald.com (Outdooractive), evtl. ThüCAT | ~1.400 km, 13 Zentren | 5 Zustandsstufen, täglich | robots erlaubt; Outdooractive nur mit Vertrag | mittel bis hoch | hoch, aber weit (4–5 h) |
| Schwarzwald / Hochschwarzwald | Outdooractive auf schwarzwald-tourismus.info, hochschwarzwald.de | groß | Loipen mit Zustand „geschlossen“ sichtbar | robots erlaubt; Outdooractive nur mit Vertrag | hoch | hoch für BW-Nutzer |
| Harz | harzinfo.de (destination.one) | mittel | Touren, Status unklar | robots erlaubt | mittel bis hoch | mittel |
| Sauerland | Wintersport-Arena / Ortsseiten | mittel | unklar | – | hoch | mittel (NRW) |
| Rhön | nur bergfex gefunden | klein | – | bergfex 403 | hoch | niedrig |
| Schwäbische Alb | Ortsflyer (Westerheim, Albstadt), bergfex | klein | meist kein Online-Status | bergfex 403 | hoch | niedrig (wenig Schnee) |
| Augsburg | keiner | 1–2 Loipen | keine | – | Handangabe | niedrig, aber Stefans Wunsch |

Auffälligkeiten:
- Der `arberland`-Abruf (126 Loipen) ist eine Teilmenge von `bayerischer-wald` (120 gemeinsame IDs). Nur
  `bayerischer-wald` anbinden, sonst entstehen Dubletten.
- `bayerischer-wald` enthält das tschechische Gebiet Gibacht-Čerchov-Voithenberg (12 Loipen, grenzüberschreitend).
  Kann bleiben oder per Gebietsfilter raus.
- Das Feld `redakt` enthält Personennamen und wird wie bisher nie gespeichert.
- Am 27.11. sind alle Loipen geschlossen (Saisonstart fehlt noch). Ein Fixture-Test mit offenen Loipen braucht
  im Dezember einen zweiten Schnappschuss (passt zum Backlog-Punkt „zweiter Satz Schnappschüsse“).
- Chiemgau GmbH hatte nach dem tourinfra-Weg gefragt. Für den Bayerischen Wald und das Fichtelgebirge deshalb
  vor dem Livegang dieselbe Erlaubnis-Mail schicken und bis zur Antwort `nur_test` setzen.

## Gesamtkarte deutschsprachiger Raum

| Gebiet | Stand |
|---|---|
| Bayerische Alpen, Chiemgau, Berchtesgaden, Allgäu | angebunden |
| Tirol, Salzburg, Steiermark, Teile Kärntens, Osttirol | angebunden |
| Südtirol | angebunden (Dolomiti NordicSki, Open Data Hub) |
| Schweiz, Liechtenstein | angebunden (tourinfra, myswitzerland) |
| **Bayerischer Wald, Fichtelgebirge** | **diese Recherche: bereit zur Anbindung** |
| Thüringer Wald, Schwarzwald, Harz, Erzgebirge, Sauerland | Folgerecherche (Outdooractive-Frage, ThüCAT, Ortsseiten) |
| Vorarlberg, Oberösterreich (Mühlviertel, Salzkammergut), Niederösterreich | kaum abgedeckt, noch nicht recherchiert; salzkammergut.at hat eine Seite „Loipenberichte“ |
| Rhön, Schwäbische Alb, Bayerischer Jura, Augsburg | klein, Handangaben oder später |

## Empfohlene Reihenfolge

1. Bayerischer Wald (tourinfra) – Freigabe durch Stefan nötig.
2. Fichtelgebirge (tourinfra) – im selben PR möglich.
3. Folgerecherche: ThüCAT/Thüringer Wald, Vorarlberg, Salzkammergut/Oberösterreich, Erzgebirge.
4. Outdooractive-Frage einmal grundsätzlich klären (Anfrage nach Partnerzugang); davon hängen Schwarzwald und
   Thüringer Wald ab.
5. Harz, Sauerland, Augsburg als Handangabe, Rhön und Alb zuletzt.
