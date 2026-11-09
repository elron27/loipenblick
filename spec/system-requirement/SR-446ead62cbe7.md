---
id: 6b804900-104a-483a-a32c-446ead62cbe7
type: system-requirement
status: draft
title: Anreise-Block auf Loipen- und Gebietsseite
kennung: U14
prio: muss
umfang: v1
rationale: Aus der Bedarfsrunde mit Stefan am 08.11.2026.
requirement-type: functional
acceptance-criteria:
  - Ein Tipp auf einen Parkplatz öffnet die Navigation in der Karten-App des Handys.
  - Gebühren stehen mit Betrag oder „unbekannt“.
packages:
  - { id: 7b29aa02-4a82-499c-9654-8d13c0c2d64c, version: n2:22b0303ec030d854, title: Oberfläche }
derives-from:
  - { id: db78e0b8-511a-4848-b88e-3ec9fe9d3892, version: n2:9cbef3ba9b12eee5, title: "Anreise planen: Parkplatz und Gebühr" }
---

Das System muss auf Loipen- und Gebietsseite einen Anreise-Block zeigen: Parkplätze mit Navigationslink, Parkgebühr und Loipengebühr.
