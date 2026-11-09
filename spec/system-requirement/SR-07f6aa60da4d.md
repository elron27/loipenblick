---
id: 82580c82-f084-436b-8522-07f6aa60da4d
type: system-requirement
status: draft
title: Anreise mit Bus und Bahn
kennung: U26
prio: soll
umfang: v1
rationale: "Blindspot-Analyse vom 09.11.2026, Punkt 9: Stefan hat „übernehmen“ gewählt."
requirement-type: functional
acceptance-criteria:
  - Jedes Gebiet hat eine nächste Haltestelle mit Name und Koordinaten oder den Hinweis „keine bekannt“.
  - Der Link öffnet die Fahrplanauskunft mit der Haltestelle als Ziel.
packages:
  - { id: 7b29aa02-4a82-499c-9654-8d13c0c2d64c, version: n2:22b0303ec030d854, title: Oberfläche }
derives-from:
  - { id: e5fd91c1-42ec-4a31-9623-03048e8ee30b, version: n2:e4581818e467b06a, title: Anreise ohne Auto }
---

Das System soll pro Gebiet die nächste Haltestelle zeigen und einen Link zur Fahrplanauskunft (DB, ÖBB) mit dem Gebiet als Ziel.
