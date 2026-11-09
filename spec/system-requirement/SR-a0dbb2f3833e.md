---
id: 94a70a87-0e0b-4a1f-ae58-a0dbb2f3833e
type: system-requirement
status: draft
title: Zuletzt geladene Daten offline anzeigen
kennung: U29
prio: soll
umfang: spaeter
rationale: "Blindspot-Analyse vom 09.11.2026, Punkt 2: Stefan hat „später“ gewählt."
requirement-type: functional
acceptance-criteria:
  - Im Flugmodus zeigt die installierte Seite die zuletzt geladenen Loipen- und Gebietsseiten.
  - Offline steht sichtbar „offline, Stand <Zeit>“.
packages:
  - { id: 7b29aa02-4a82-499c-9654-8d13c0c2d64c, version: n2:22b0303ec030d854, title: Oberfläche }
derives-from:
  - { id: 126ab50c-946d-4fd5-88b1-86e25065f60e, version: n2:5dc4549252838984, title: Infos auch ohne Netz }
based-on:
  - { id: 2ae0ad55-3d2e-461b-975b-237a0a1f0ac5, version: n2:22b0303ec030d854, title: "Parsen auf dem NAS, Website extern" }
---

Das System soll die zuletzt geladenen Seiten und Daten im Browser zwischenspeichern (PWA), damit sie ohne Handynetz sichtbar bleiben, mit deutlichem Hinweis auf ihr Alter.
