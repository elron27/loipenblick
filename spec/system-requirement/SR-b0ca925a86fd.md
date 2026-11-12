---
id: 36883843-038e-4a60-985f-b0ca925a86fd
type: system-requirement
status: draft
title: Bedienbar mit über 700 Loipen
kennung: U32
prio: muss
umfang: ausbau1
rationale: "Blindspot 5: tirol.at verzehnfacht den Bestand. Blindspot aus dem Plan Ausbau Kufstein und Salzburg (https://claude.ai/artifact/G6vZbnSNKHfn5k9DZVERob), von Stefan am 12.11.2026 übernommen."
requirement-type: quality
acceptance-criteria:
  - Ein Playwright-Test mit 750 synthetischen Loipen lädt die Startseite auf dem Handy in unter 3 s.
  - Die Karte lädt Streckenverläufe nur für die gewählte Region.
packages:
  - { id: 7b29aa02-4a82-499c-9654-8d13c0c2d64c, version: n2:22b0303ec030d854, title: Oberfläche }
derives-from:
  - { id: 93a6a006-58bf-4a79-b4f1-bc1b6d91988f, version: n2:6ca5edb7fee77c7d, title: Loipen überall abdecken }
  - { id: 821fb411-edac-4849-b578-b3f97905ea5c, version: n2:f73ce3102c1dc85f, title: "Finden, ohne zu wissen, wo man suchen muss" }
based-on:
  - { id: f5b55793-6e34-47ce-a59c-5868328317e9, version: n2:e6476bcea146a216, title: "Ausbaustufe 1: Tirol über tirol.at, Salzburg über Ortsseiten" }
  - { id: 34172bba-0c17-4228-b571-17552a5cfa37, version: n2:22b0303ec030d854, title: "Ausbau: Südostbayern, dann Österreich bis Innsbruck und Salzburg" }
---

Startseite, Karte, Liste und Push-Abos müssen mit über 700 Loipen schnell und übersichtlich bleiben. Neue Regionen werden in Stufen zugeschaltet.
