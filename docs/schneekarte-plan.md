# Schneekarte: Umsetzungsplan (freigegeben 23.11.2026)

Stand 23.11.2026. Grundlage: Blindspots und Business-Case vom 22.11.2026, Anforderungen in `spec/` (Paket *Schneekarte*: N-41 bis N-44, E-31 bis E-36, S1 bis S25). Filter: `schneekarte-sammeln` (schnee0, sofort), `schneekarte-v1` (schnee1), `spaeter`.

## Leitlinien

- Modul von Loipenblick, kein eigenes Projekt (E-31): gleicher Worker, gleiche Datenbank, gleicher Webspace.
- Zuerst sammeln, dann zeigen (E-34). Vorrang haben Daten, die bei der Quelle kein Archiv haben: Stationswerte der Lawinenwarndienste und die Tagesfassungen der Lageberichte.
- Keine eigene Bewertung der Lawinenlage (E-32). Gezeigt wird nur, was der Warndienst veröffentlicht, mit Datum, Höhengrenze und Link.
- Nur Quellen, deren Lizenz Einnahmen erlaubt, kein Open-Meteo (E-33). Einnahmen nur über den Spendenlink und später über gekennzeichnete Affiliate-Links.
- Warnregionen als Gebietszuschnitt (E-35). Gesammelt wird ab sofort für Bayern, Österreich, Südtirol und Trentino, gezeigt werden in Version 1 Bayern, Tirol, Salzburg und Südtirol.

## Schritte

Stand 23.11.2026: Schritte 1 bis 4 umgesetzt (Quellen und Lizenzen in [schneekarte-quellen.md](schneekarte-quellen.md), Datenmodell und Sammel-Job in [schneekarte-datenmodell.md](schneekarte-datenmodell.md)). Reihenfolge der Regionen laut Stefan: Bayern, Tirol, Salzburg, Südtirol, dann der übrige Alpenraum.

| # | Schritt | Anforderungen | Ergebnis |
|---|---|---|---|
| 1 | Quellen prüfen: Endpunkte, Lizenz, robots.txt und Archiv je Quelle; echte Schnappschüsse ablegen | S6, S3, S4 | `docs/schneekarte-quellen.md`, Fixtures |
| 2 | Datenmodell und Migration: Station, Messwert, Lagebericht-Fassung, Gefahrenstufe, Rohdatei | S9, S2 | Alembic-Migration, Tests |
| 3 | Adapter für Lageberichte (CAAML) und Stationen, mit Fixture-Tests, Ausreißer-Regeln und Lücken-Meldung | S3, S4, S7, S8, S21 | Adapter, Tests grün |
| 4 | Sammel-Job in den Worker einhängen (dreimal am Tag), Image bauen | S1 | PR gemergt, neues Image |
| 5 | Auf dem NAS: Container aktualisieren und sieben Tage beobachten; Platzbedarf messen | S1, S9 | Nachweis 7 Tage fehlerfrei |
| 6 | Archive nachladen: frühere Lageberichte und SNOWGRID je Region und Höhenband | S5, S10 | frühere Winter in der Datenbank |
| 7 | **Stopp:** vier Entwürfe für Karte und Zeitachse zur Auswahl (Design-Verbotsliste gilt) | S11, S12 | Auswahl durch Stefan |
| 8 | Oberfläche nach dem gewählten Entwurf, mit Playwright-Screenshots Desktop und Handy | S11 bis S20 | Testseite auf test.loipen-blick.de |
| später | Vergleich mit früheren Wintern, Affiliate-Links, Schweiz, Neuschnee-Push | S22 bis S25 | eigene Freigabe |

Zeitbudget: Schritte 1 bis 4 ca. 3 bis 4 Stunden Arbeit, mit Zwischenstand nach Schritt 1. Ziel ist, dass der Sammel-Job noch in dieser Woche auf dem NAS läuft.

## Bekannte Hürden

- Die Cloud-Umgebung kennt die Domains der Lawinenwarndienste noch nicht (z. B. avalanche.report, lawinen-warnung.eu, lawinenwarndienst-bayern.de). Die Threads arbeiten dann wie bisher mit Schnappschüssen; der Live-Abruf läuft auf dem NAS.
- Die Bedingungen der Warndienste Bayern, Salzburg, Vorarlberg, Kärnten und Steiermark sind noch nicht geprüft. Eine Quelle mit unklarer Lizenz wird gesammelt, aber nur in der Testversion gezeigt (S6).
- Haftung: vor dem ersten Affiliate-Link kurz anwaltlich prüfen lassen (S15). Keine Rechtsberatung.

## Was Stefan tun muss

1. Diesen Plan freigeben (oder ändern).
2. Nach Schritt 4 den Container auf dem NAS aktualisieren (Anleitung `docs/nas-update.md`).
3. Nach dem ersten Prototyp beim Betreiber von Skitourenguru wegen eines gegenseitigen Links fragen (E-36).
