---
id: 28aa682a-29da-494e-9572-8cb7f667dffd
type: system-requirement
status: draft
title: Rahmendaten je Gebiet und Region
kennung: U43
prio: muss
umfang: ausbau1
rationale: "Stefan am 13.11.2026 nach dem Test am NAS: Viele Loipen lassen sich nicht anklicken, Daten sind oft unbekannt, die Rahmendaten (wie viele km es gibt, wie viele offen sind) sollten bekannt sein; Snowfarming-, Opening- und Gletscherloipen stehen als offen da."
requirement-type: functional
acceptance-criteria:
  - Die Gebietsseite zeigt Loipen offen (x von y), km offen (x von y km), gespurte km laut Quelle und für wie viele Loipen die Länge bekannt ist; offene Loipen ohne Länge werden eigens genannt.
  - Die Liste zeigt je Region die gleichen Zahlen für alle Loipen der Region, die Karten der Startseite je Gebiet.
  - Fehlt einer Loipe die Länge, eine Dublette derselben Loipe aus einer anderen Quelle nennt sie aber, gilt diese Länge mit Angabe der Quelle.
packages:
  - { id: 7b29aa02-4a82-499c-9654-8d13c0c2d64c, version: n2:22b0303ec030d854, title: Oberfläche }
derives-from:
  - { id: a1ad23a0-cdad-4ff8-bb51-af00893d9a9d, version: n2:83edd6a0956f785e, title: Heute gut langlaufen in meiner Nähe }
---

Das System muss je Gebiet und Region zeigen, wie viele Loipen und Kilometer es gibt und wie viele davon offen sind, und Unbekanntes als unbekannt ausweisen.
