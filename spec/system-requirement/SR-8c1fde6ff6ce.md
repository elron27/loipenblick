---
id: 05ca839d-ddb0-4f4a-83b7-8c1fde6ff6ce
type: system-requirement
status: draft
title: Ein Adapter pro Quellsystem
kennung: P1
prio: muss
umfang: v1
rationale: "Herkunft: [Anforderungsdokument](https://claude.ai/artifact/RWrftfaPcM8nDDuxnN5MDA), P1."
requirement-type: functional
acceptance-criteria:
  - Adapter A liest Tegernseer Tal, Bayrischzell und Fischbachau mit demselben Code, nur die Konfiguration unterscheidet sich.
  - Ein weiterer Ort mit demselben System braucht keine Codeänderung.
packages:
  - { id: aecf250b-eb6d-41e6-9041-3ce5eb9763a3, version: n2:22b0303ec030d854, title: Datenerfassung }
derives-from:
  - { id: 88819c95-41b8-4420-a9b7-7889970ad198, version: n2:6c90010d1186d41c, title: Neue Orte ohne Programmieren }
---

Das System muss pro Quellsystem einen Adapter haben statt einen Parser pro Ort. Der Parser für das /a-<slug>-Schema (Tegernsee, Bayrischzell, Fischbachau) ist generisch und wird per Konfiguration auf weitere Orte mit demselben System angewendet.
