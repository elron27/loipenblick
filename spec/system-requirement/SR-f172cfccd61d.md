---
id: 4c47fd0e-667b-408a-9598-f172cfccd61d
type: system-requirement
status: draft
title: Loipenstatus aus dem Tourenportal der Steiermark
kennung: P30
prio: kann
umfang: ausbau3
rationale: Für die Steiermark gibt es kein Landesportal wie tirol.at; das Tourenportal von Steiermark Tourismus zeigt alle Langlaufloipen mit dem Status der Regionen (E-22).
requirement-type: functional
acceptance-criteria:
  - Alle Seiten der Liste werden gelesen, bis die genannte Zahl der Ergebnisse erreicht ist; je Loipe gibt es Name, Status (geöffnet, teilweise geöffnet, geschlossen, ohne Meldung = unbekannt), Länge, Schwierigkeit und Startort.
  - Das Gebiet ergibt sich aus dem Startort; ein unbekannter Startort ergibt eine Warnung statt eines falschen Gebiets, ebenso weniger Loipen als genannt oder eine leere Liste.
  - Steht dieselbe Loipe auch im tourinfra-Loipenmanager von Ramsau am Dachstein, wird sie einmal gezeigt, bei Ramsau; zusammengeschriebene Namen gelten dabei als gleich („Weltcuploipe“ = „Weltcup Loipe“).
packages:
  - { id: aecf250b-eb6d-41e6-9041-3ce5eb9763a3, version: n2:22b0303ec030d854, title: Datenerfassung }
derives-from:
  - { id: 93a6a006-58bf-4a79-b4f1-bc1b6d91988f, version: n2:6ca5edb7fee77c7d, title: Loipen überall abdecken }
based-on:
  - { id: ff54d1e1-813b-4db3-9290-c9d7f1fc0f2a, version: n2:e4020d1cc4cace5f, title: Steiermark über das Tourenportal von Steiermark Tourismus }
---

Das System soll die Langlaufloipen aus dem Tourenportal von Steiermark Tourismus mit ihrem Status, ihrer Länge und ihrem Startort im passenden Gebiet anzeigen.
