---
id: 5cee563c-584f-4553-aeab-66f6d3bbd9a5
type: system-requirement
status: draft
title: Dubletten über mehrere Quellen
kennung: D15
prio: muss
umfang: ausbau1
rationale: Blindspot 2. Blindspot aus dem Plan Ausbau Kufstein und Salzburg (https://claude.ai/artifact/G6vZbnSNKHfn5k9DZVERob), von Stefan am 12.11.2026 übernommen.
requirement-type: functional
acceptance-criteria:
  - Zwei Einträge mit ähnlichem Namen und Startpunkt unter 300 m Abstand werden als eine Loipe gezeigt.
  - Die führende Quelle steht in sources.yaml.
packages:
  - { id: 1554c39a-9747-4c4a-b1a2-2d04b1153c7d, version: n2:22b0303ec030d854, title: Datenmodell }
derives-from:
  - { id: 93a6a006-58bf-4a79-b4f1-bc1b6d91988f, version: n2:6ca5edb7fee77c7d, title: Loipen überall abdecken }
  - { id: 3cc0b4ba-48ea-4c59-bc3e-a269e781aa26, version: n2:641911ee7fdb8aa9, title: "Wissen, wie alt und woher die Daten sind" }
based-on:
  - { id: f5b55793-6e34-47ce-a59c-5868328317e9, version: n2:e6476bcea146a216, title: "Ausbaustufe 1: Tirol über tirol.at, Salzburg über Ortsseiten" }
  - { id: 34172bba-0c17-4228-b571-17552a5cfa37, version: n2:22b0303ec030d854, title: "Ausbau: Südostbayern, dann Österreich bis Innsbruck und Salzburg" }
---

Jede Loipe muss genau eine führende Quelle haben. Liefern mehrere Quellen dieselbe Loipe, erkennt das System die Dublette über Name und Startkoordinate und zeigt sie einmal.
