---
id: aa95c6fc-2234-4c91-aede-c53c82edbd20
type: system-requirement
status: draft
title: Parser-Tests mit Beispielseiten
kennung: P9
prio: muss
umfang: v1
rationale: "Herkunft: [Anforderungsdokument](https://claude.ai/artifact/RWrftfaPcM8nDDuxnN5MDA), P9."
requirement-type: quality
acceptance-criteria:
  - Jeder Adapter hat Tests gegen gespeicherte Beispielseiten.
  - Die Tests laufen in der CI bei jedem Pull Request.
packages:
  - { id: aecf250b-eb6d-41e6-9041-3ce5eb9763a3, version: n2:22b0303ec030d854, title: Datenerfassung }
derives-from:
  - { id: 88819c95-41b8-4420-a9b7-7889970ad198, version: n2:6c90010d1186d41c, title: Neue Orte ohne Programmieren }
---

Das System muss für jeden Adapter Tests mit gespeicherten HTML-Beispielseiten (Fixtures) haben, die bei jeder Änderung laufen.
