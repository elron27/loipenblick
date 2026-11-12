---
id: 53361a70-d586-4a91-8503-798a7ecfae57
type: system-requirement
status: draft
title: Österreichische Zustandswörter
kennung: P18
prio: muss
umfang: ausbau1
rationale: "Blindspot 9: Im November steht überall „gesperrt“. Blindspot aus dem Plan Ausbau Kufstein und Salzburg (https://claude.ai/artifact/G6vZbnSNKHfn5k9DZVERob), von Stefan am 12.11.2026 übernommen."
requirement-type: functional
acceptance-criteria:
  - Die Normalisierung ordnet gesperrt, geöffnet, teilweise geöffnet und eingeschränkt befahrbar zu.
  - Im Dezember kommt ein zweiter Fixture-Satz mit Saisonwörtern dazu.
packages:
  - { id: aecf250b-eb6d-41e6-9041-3ce5eb9763a3, version: n2:22b0303ec030d854, title: Datenerfassung }
derives-from:
  - { id: 93a6a006-58bf-4a79-b4f1-bc1b6d91988f, version: n2:6ca5edb7fee77c7d, title: Loipen überall abdecken }
  - { id: 3cc0b4ba-48ea-4c59-bc3e-a269e781aa26, version: n2:641911ee7fdb8aa9, title: "Wissen, wie alt und woher die Daten sind" }
based-on:
  - { id: f5b55793-6e34-47ce-a59c-5868328317e9, version: n2:e6476bcea146a216, title: "Ausbaustufe 1: Tirol über tirol.at, Salzburg über Ortsseiten" }
  - { id: 34172bba-0c17-4228-b571-17552a5cfa37, version: n2:22b0303ec030d854, title: "Ausbau: Südostbayern, dann Österreich bis Innsbruck und Salzburg" }
---

Die Zuordnungstabellen (P5) müssen österreichische Zustandswörter kennen, etwa „gesperrt“, „teilweise geöffnet“ und „eingeschränkt befahrbar“. Unbekannte Wörter landen in der Quellenmeldung.
