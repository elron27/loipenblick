---
id: fa24084a-b7ac-484c-b0e8-a8f5b418a5af
type: system-requirement
status: draft
title: Loipenzustand St. Anton am Arlberg
kennung: P27
prio: soll
umfang: ausbau3
rationale: "Schnappschuss vom 13.11.2026: die Seite meldet je Loipe geöffnet oder geschlossen und den Zeitpunkt der letzten Aktualisierung (E-21)."
requirement-type: functional
acceptance-criteria:
  - Ein Abruf liefert alle Loipen von St. Anton mit Status, Schwierigkeit, Länge aus dem Namen und dem Stand der Seite; Winterwanderwege fallen weg.
  - Eine geöffnete Loipe wird offen mit dem Rohtext der Seite; ändert sich der Seitenaufbau, gibt es eine Warnung statt falscher Daten.
packages:
  - { id: aecf250b-eb6d-41e6-9041-3ce5eb9763a3, version: n2:22b0303ec030d854, title: Datenerfassung }
derives-from:
  - { id: 93a6a006-58bf-4a79-b4f1-bc1b6d91988f, version: n2:6ca5edb7fee77c7d, title: Loipen überall abdecken }
based-on:
  - { id: 51c5009c-3324-4d83-a266-8cad3ac1fe26, version: n2:134e097ec42d66be, title: St. Anton am Arlberg und Kärnten }
---

Das System soll den Loipenzustand von St. Anton am Arlberg je Loipe mit Status, Schwierigkeit und Stand der Seite abrufen.
