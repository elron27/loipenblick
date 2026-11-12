---
id: 9aab6bb5-e225-4602-a146-b6c1f3998fcc
type: system-requirement
status: draft
title: Quelle tirol.at für Tirol
kennung: P14
prio: muss
umfang: ausbau1
rationale: "Blindspot 5 und Quellenrecherche vom 11.11.2026: tirol.at führt 716 Loipen, robots.txt erlaubt die Loipenseiten. Blindspot aus dem Plan Ausbau Kufstein und Salzburg (https://claude.ai/artifact/G6vZbnSNKHfn5k9DZVERob), von Stefan am 12.11.2026 übernommen."
requirement-type: functional
acceptance-criteria:
  - Ein Fixture-Test mit einem echten Schnappschuss liest mindestens 5 Loipen aus dem Kufsteinerland mit Name, Status und Länge.
  - Eine weitere Tiroler Region wird nur über sources.yaml zugeschaltet, ohne Codeänderung.
packages:
  - { id: aecf250b-eb6d-41e6-9041-3ce5eb9763a3, version: n2:22b0303ec030d854, title: Datenerfassung }
derives-from:
  - { id: 93a6a006-58bf-4a79-b4f1-bc1b6d91988f, version: n2:6ca5edb7fee77c7d, title: Loipen überall abdecken }
  - { id: 05987e34-b530-4a27-af28-276e48707a7f, version: n2:49aae3ee115ffed9, title: "Im größeren Umkreis suchen, wenn Freunde da sind" }
based-on:
  - { id: f5b55793-6e34-47ce-a59c-5868328317e9, version: n2:e6476bcea146a216, title: "Ausbaustufe 1: Tirol über tirol.at, Salzburg über Ortsseiten" }
  - { id: 34172bba-0c17-4228-b571-17552a5cfa37, version: n2:22b0303ec030d854, title: "Ausbau: Südostbayern, dann Österreich bis Innsbruck und Salzburg" }
---

Das System muss Loipen aus dem Landesportal tirol.at übernehmen: Name, Status, Länge, Schwierigkeit, Stile, Beleuchtung, Startpunkt und Streckenverlauf. Welche Tiroler Regionen abgerufen werden, steht in sources.yaml; zuerst Kufsteinerland, Kaiserwinkl und Wilder Kaiser.
