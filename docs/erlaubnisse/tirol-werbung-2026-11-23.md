# Tirol Werbung GmbH: Erlaubnis für tirol.at (23.11.2026)

- **Quelle:** `tirol` in `config/sources.yaml`, Loipenstatus, Lage und Länge aller Tiroler Loipen von www.tirol.at
- **Anfrage:** Erlaubnis-Mail von Stefan vom 19.11.2026 an info@tirol.at (Vorlage `docs/livegang.md`, Abschnitt 8)
- **Antwort:** 23.11.2026, Victoria Schilcher, Projektmanagement digitale Kanäle, Tirol Werbung GmbH, Innsbruck
- **Ergebnis:** Erlaubnis liegt vor, `erlaubnis: liegt_vor` (B31, E-37)
- **Bedingung:** Quellangabe und Verlinkung zu tirol.at

## Wortlaut (ohne Signatur und Telefonnummern)

> Vielen Dank für Ihre Anfrage. Die Abholung der Daten mit Quellangabe und Verlinkung zu unserer Seite geht für
> uns auf jeden Fall in Ordnung. Ihr geplanter Weg über die Website passt für uns gut – unsere eigene direkte
> Schnittstelle ist für ein privates Projekt tatsächlich sehr komplex einzubinden.
>
> Falls Sie dennoch eine offizielle Schnittstelle bevorzugen, schauen Sie sich gerne den Open-Data-Datensatz der
> Österreich Werbung – LTO Freigabetool an. Dort sind die Loipen auch abgebildet.
>
> Viel Erfolg beim Start der neuen Seite!

## Wie Loipenblick die Bedingung erfüllt

- Jede Loipe aus tirol.at nennt unter „Quelle und Stand“ den Namen „Tirol Werbung (tirol.at)“ mit Link auf die
  Seite der Loipe bei tirol.at.
- Die Seite „Hinweise und Betreiber“ führt Tirol Werbung mit Link auf www.tirol.at.
- Ein Test prüft beides auf der öffentlichen Seite (`tests/test_erlaubnis.py`, B31).

## Spätere Option: Open Data der Österreich Werbung

Die Österreich Werbung bietet über das „LTO Freigabetool“ einen Open-Data-Datensatz, in dem auch die Loipen
stehen. Das wäre eine offizielle Schnittstelle statt des Abrufs über die Website. Noch nicht geprüft: Format,
Lizenz, wie aktuell der Status ist und ob er „geöffnet/gesperrt“ enthält. Kein Handlungsbedarf, solange der
Website-Abruf läuft.

## Achensee

Die Erlaubnis gilt für die Daten von tirol.at allgemein und nennt Achensee nicht eigens. Achensee Tourismus hat am
20.11.2026 der Verwendung seiner Loipendaten widersprochen (B30, E-30). Stefan hat am 23.11.2026 entschieden, die
Gebiete Achensee und Steinberg am Rofan über tirol.at wieder zu zeigen (E-37); die Quelle achensee.com bleibt aus.
