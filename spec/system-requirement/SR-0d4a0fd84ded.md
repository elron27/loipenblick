---
id: 379e2fcb-9bac-4d6e-901d-0d4a0fd84ded
type: system-requirement
status: draft
title: Wartungsarme Quellen bevorzugen
kennung: P20
prio: soll
umfang: ausbau1
rationale: Blindspot 12. Blindspot aus dem Plan Ausbau Kufstein und Salzburg (https://claude.ai/artifact/G6vZbnSNKHfn5k9DZVERob), von Stefan am 12.11.2026 übernommen.
requirement-type: quality
acceptance-criteria:
  - Jede Ortsseiten-Quelle in sources.yaml nennt das Gebiet, das sie schließt.
packages:
  - { id: aecf250b-eb6d-41e6-9041-3ce5eb9763a3, version: n2:22b0303ec030d854, title: Datenerfassung }
derives-from:
  - { id: 93a6a006-58bf-4a79-b4f1-bc1b6d91988f, version: n2:6ca5edb7fee77c7d, title: Loipen überall abdecken }
  - { id: 88819c95-41b8-4420-a9b7-7889970ad198, version: n2:6c90010d1186d41c, title: Neue Orte ohne Programmieren }
based-on:
  - { id: f5b55793-6e34-47ce-a59c-5868328317e9, version: n2:e6476bcea146a216, title: "Ausbaustufe 1: Tirol über tirol.at, Salzburg über Ortsseiten" }
  - { id: 34172bba-0c17-4228-b571-17552a5cfa37, version: n2:22b0303ec030d854, title: "Ausbau: Südostbayern, dann Österreich bis Innsbruck und Salzburg" }
---

Das System soll große Portale vor einzelnen Ortsseiten anbinden. Eine Ortsseite kommt nur dazu, wenn sie ein Gebiet ohne andere Quelle schließt.
