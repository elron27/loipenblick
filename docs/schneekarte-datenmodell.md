# Schneekarte: Datenmodell und Sammel-Job

Stand 23.11.2026. Anforderungen S1 bis S9 und S21 (Filter `schneekarte-sammeln`), Entscheidungen E-31 bis E-36.
Quellen und Lizenzen: [schneekarte-quellen.md](schneekarte-quellen.md).

## Grundsätze

- **Zuerst sammeln, dann zeigen (E-34).** Jede Antwort einer Quelle wird unverändert und gepackt abgelegt, bevor
  sie gelesen wird. Was der Leser heute noch nicht versteht, kann später aus der Rohdatei neu gelesen werden.
- **Rohwerte, keine Auswertung.** Gespeichert wird, was die Quelle meldet. Neuschnee kommt nur aus Quellen, die ihn
  messen (S7). Eine Differenz der Schneehöhe (HSD24) ist eine eigene Größe und kein Neuschnee.
- **Lawinenlage genau wie veröffentlicht (E-32).** Stufe je Höhenband und Tageszeit, Probleme und Tendenz, ohne
  eigene Bewertung, ohne Mittelwerte.
- **Getrennt von den Loipen (E-31).** Eigene Tabellen in derselben Datenbank; die Loipen-Tabellen bleiben unverändert.

## Tabellen (Migration 0010)

| Tabelle | Inhalt | Schlüssel und Regeln |
|---|---|---|
| `schnee_rohdateien` | jede Antwort einer Quelle: URL, SHA-256, Pfad, Größe, Abrufzeit | gleicher Inhalt nur einmal (SHA-256 eindeutig); Datei unter `<backup>/schnee-roh/<quelle>/<JJJJ>/<MM>/<TT>/<sha>.gz` |
| `schnee_stationen` | Messstation: Kennung der Quelle, Name, Lage, **Höhe (Pflicht)**, Betreiber, Land, Warnregion, Messart (automatisch, Hand, Modell), Messgrößen, aktiv | eindeutig je (Quelle, Kennung); ohne Höhe nicht übernommen; verschwundene Stationen werden inaktiv, nie gelöscht |
| `schnee_messwerte` | ein Rohwert: Station, Zeitpunkt, Größe, Wert, Einheit, Takt (Tag oder Einzelwert), **Fassung**, Verdacht, Rohdatei | ein zweiter Abruf legt nichts doppelt an; ändert die Quelle einen Wert, entsteht Fassung 2, Fassung 1 bleibt |
| `schnee_modellwerte` | Mittel, Minimum und Maximum je Warnregion und 500-m-Höhenband (SNOWGRID, für S10) | eindeutig je (Quelle, Region, Band, Tag, Größe) |
| `warnregionen` | EAWS-Mikroregion mit Umriss (GeoJSON, mit `start_date`/`end_date`) | ID wie `AT-07-04-01` |
| `lagebericht_fassungen` | eine veröffentlichte Fassung: Dienst, Bulletin-ID, **Ausgabezeit**, gültig von/bis, Sprache, Link, Tendenz, nachgeladen, Rohdatei | eindeutig je (Dienst, Bulletin-ID, Ausgabezeit): Abendbericht und Morgen-Aktualisierung sind zwei Zeilen |
| `lagebericht_regionen` | was eine Fassung für eine Warnregion sagt: Stufen (Stufe, Tageszeit, Höhe unten/oben oder „treeline“, Expositionen), Probleme | eindeutig je (Fassung, Region) |
| `schnee_abrufe` | ein Abruf je Quelle: Zeit, gelesene und neue Werte, Stationen, Fehler, Dauer | Grundlage für den Lücken-Alarm (S8) |

Größen in `schnee_messwerte`: `hs` Schneehöhe (cm), `hs_hand` Schneehöhe von Hand (cm, GeoSphere), `hn24`
Neuschnee 24 h (cm, nur gemessen), `hsd24` Änderung der Schneehöhe in 24 h (cm, Angabe der Quelle), `rr`/`rr24`
Niederschlag (mm), `ta`, `ta_min`, `ta_max` Lufttemperatur (°C), `ff` Wind (km/h bzw. m/s laut Einheit).

## Sammel-Job

- Der Worker ruft stündlich um :20 `schnee_tick` auf. Jede Quelle läuft zu ihren `uhrzeiten` aus
  `config/schnee.yaml`, das ganze Jahr. Lageberichte dreimal am Tag, Bayern zweimal (die API liefert nur
  2,7 Tage), Salzburg dreimal (nur aktuelle Werte).
- Fällt ein einzelner Abruf aus, laufen die übrigen weiter; jede Antwort steht in einem eigenen Savepoint.
- Um 21:20 prüft der Job je Quelle: keine Werte am Tag oder mehr als 20 % weniger Stationen als üblich ergibt eine
  ntfy-Meldung (S8).
- Von Hand: `python -m loipen.worker schnee` (alles jetzt) und
  `python -m loipen.worker schnee-archiv <quelle> [von] [bis]` (S5).

## Nachladen früherer Winter (S5)

| Quelle | ab | Befehl |
|---|---|---|
| Euregio (Tirol, Südtirol, Trentino) | 04.12.2018 | `schnee-archiv euregio` |
| lawinen-warnung.eu (Bayern, Salzburg, Vorarlberg, Steiermark, OÖ, NÖ, Slowenien) | 01.12.2024 | `schnee-archiv lawinen-warnung-eu` |
| EAWS-Sammlung für die Jahre davor | 25.01.2021 | `schnee-archiv eaws-archiv 2021-01-25 2024-11-30` |
| Kärnten | 25.01.2021 (EAWS), 2025/26 avalanche.report | `schnee-archiv kaernten 2025-11-01` |
| SLF | 15.11.2023 | `schnee-archiv slf` |
| AINEVA | 15.12.2021 | `schnee-archiv aineva` |

Nur Tage vom 1. November bis 31. Mai, höchstens eine Anfrage je Sekunde, nach jedem Tag gespeichert. Ein
Abbruch schadet nicht: Beim nächsten Start werden vorhandene Tage übersprungen. Grobe Dauer: Euregio etwa
30 Minuten, EAWS-Sammlung etwa 2 Stunden. Stationswerte von DWD, GeoSphere und SNOWGRID haben eigene Archive
bei der Quelle (ab 1900, 1775, 1961) und können jederzeit nachgeholt werden.

## Platzbedarf (Schätzung, wird nach 7 Tagen auf dem NAS gemessen, S9 AK 3)

| | pro Tag | pro Jahr |
|---|---|---|
| Rohdateien gepackt | ca. 1 MB | ca. 0,4 GB |
| Datenbank (rund 5.000 neue Messwerte am Tag; Bayern nur ein Wert je Stunde, die 10-Minuten-Werte bleiben in der Rohdatei) | ca. 1 MB | ca. 0,4 GB |

Ziel aus S9: unter 2 GB pro Winter. Rohdateien gehen nie auf den Webspace.

## Offene Punkte

- Lizenz der Lageberichte von Euregio und lawinen-warnung.eu ist nicht angegeben; Bayern verlangt für Messdaten
  eine Einwilligung, Salzburg behält alle Rechte vor. Gesammelt wird trotzdem (E-24, E-34), gezeigt erst nach
  Zustimmung. Anfragen bei Euregio, LWD Bayern und LWD Salzburg gehören vor den Livegang der Schneekarte.
- Zeitangaben der Bayern-API haben keine Zone; angenommen ist UTC. Nach einigen Tagen am NAS mit der Webseite des
  LWD vergleichen.
- Die Saison 2026/27 der Lageberichte hat bei Euregio, Bayern und Österreich am 23.11. noch nicht begonnen.
  Der Lauf meldet bis dahin „keine Werte“ für diese Quellen nicht als Fehler, wohl aber als Lücke.
