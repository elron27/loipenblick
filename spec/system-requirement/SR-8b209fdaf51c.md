---
id: f691f796-b5e1-4ef6-88d6-8b209fdaf51c
type: system-requirement
status: draft
title: Handangaben zu Saisonbeginn und Saisonende prüfen
kennung: B32
prio: soll
umfang: details
rationale: "Plan „Mehr Daten je Loipe“, von Stefan am 24.11.2026 freigegeben (Issue #46). Stefan: „vielleicht kann man das immer am Anfang und Ende der Saison mit einplanen, wenn sich Preise ändern“."
requirement-type: functional
acceptance-criteria:
  - Anfang November und Ende März erzeugt ein Workflow eine Liste aller Handangaben mit Quell-URL und Prüfdatum und öffnet dafür ein GitHub-Issue.
  - Ein Skript ruft jede Quell-URL ab und markiert nicht erreichbare Seiten und geänderte Gebührentexte.
  - Eine Handangabe, deren Prüfdatum älter als eine Saison ist, zeigt die Seite mit "Stand Winter JJJJ/JJ".
packages:
  - { id: a1e07cef-f067-4f3b-a290-7b0bc167bcfa, version: n2:22b0303ec030d854, title: Betrieb }
derives-from:
  - { id: db78e0b8-511a-4848-b88e-3ec9fe9d3892, version: n2:9cbef3ba9b12eee5, title: "Anreise planen: Parkplatz und Gebühr" }
  - { id: 3cc0b4ba-48ea-4c59-bc3e-a269e781aa26, version: n2:641911ee7fdb8aa9, title: "Wissen, wie alt und woher die Daten sind" }
---

Das System muss die von Hand gepflegten Angaben (Gebühren, Parkplätze, Webcams, Verleih, Merkmale) zweimal im Jahr zur Prüfung vorlegen.
