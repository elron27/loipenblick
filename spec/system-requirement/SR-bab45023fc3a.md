---
id: 439316b2-790a-4010-bb45-bab45023fc3a
type: system-requirement
status: draft
title: Zeitplan pro Quelle
kennung: P8
prio: soll
umfang: v1
rationale: "Herkunft: [Anforderungsdokument](https://claude.ai/artifact/RWrftfaPcM8nDDuxnN5MDA), P8."
requirement-type: functional
acceptance-criteria:
  - In der Saison läuft jede Quelle stündlich zwischen 6 und 22 Uhr.
  - Außerhalb der Saison läuft sie höchstens täglich.
packages:
  - { id: aecf250b-eb6d-41e6-9041-3ce5eb9763a3, version: n2:22b0303ec030d854, title: Datenerfassung }
derives-from:
  - { id: 88819c95-41b8-4420-a9b7-7889970ad198, version: n2:6c90010d1186d41c, title: Neue Orte ohne Programmieren }
  - { id: 914f2148-aa61-463c-839d-0cd4039bc354, version: n2:946e559473e10418, title: Daten fair und rechtlich sauber übernehmen }
---

Das System soll pro Quelle einen Zeitplan haben: in der Saison z. B. stündlich 6–22 Uhr, außerhalb der Saison täglich oder aus.
