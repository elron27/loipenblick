---
id: 370e1680-f3a9-41ad-be4a-4f1e7fff19db
type: system-requirement
status: draft
title: Statistik-Seite mit Saisonverlauf
kennung: U37
prio: soll
umfang: v1
rationale: "Stefan am 13.11.2026: Statistik-Seite gewählt (Saisonverlauf, offene Tage, Zuverlässigkeit der Quellen)."
requirement-type: functional
acceptance-criteria:
  - Ein Tag zählt als befahrbar, wenn die Quelle an ihm irgendwann offen oder eingeschränkt meldete; Tage ohne Abruf oder nur mit unbekannt sind Lücken und zählen nicht.
  - Der Verlauf zeigt jeden Tag des Winters; Lücken bleiben im Diagramm sichtbar leer.
  - Beim Zeigen auf einen Tag nennt die Seite Datum und Wert, die Werte gibt es auch als Tabelle je Monat.
  - Auswahl nach Winter, Region und Gebiet; für ein Gebiet erscheint die Schneehöhe als eigenes Diagramm.
  - Die Beispielansicht zeigt einen erfundenen, gekennzeichneten Winter.
packages:
  - { id: 7b29aa02-4a82-499c-9654-8d13c0c2d64c, version: n2:22b0303ec030d854, title: Oberfläche }
derives-from:
  - { id: a53c4a80-87f7-4dde-bea4-ede3361fcd00, version: n2:0fccd7eeb33c5af7, title: Statistiken über die Winter }
---

Das System soll eine Seite Statistik zeigen: pro Winter und wahlweise pro Region oder Gebiet die Zahl der befahrbaren Loipen an jedem Tag als Verlauf, dazu Kennzahlen (Tage mit befahrbarer Loipe, Tage mit Daten, erster und letzter befahrbarer Tag) und für ein Gebiet die gemessene Schneehöhe. Befahrbar heißt: die Quelle meldete an diesem Tag offen oder eingeschränkt.
