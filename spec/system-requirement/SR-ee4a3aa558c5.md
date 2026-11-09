---
id: 15b4396e-01c7-4f98-8a75-ee4a3aa558c5
type: system-requirement
status: draft
title: Status mit Symbol und Wort
kennung: U22
prio: muss
umfang: v1
rationale: Blindspot-Analyse vom 09.11.2026, Punkt 3, von Stefan übernommen.
requirement-type: quality
acceptance-criteria:
  - Jeder Status hat ein eigenes Symbol und ein Wort.
  - Text und Symbole erreichen ein Kontrastverhältnis von mindestens 4,5:1 (WCAG AA).
packages:
  - { id: 7b29aa02-4a82-499c-9654-8d13c0c2d64c, version: n2:22b0303ec030d854, title: Oberfläche }
derives-from:
  - { id: bf72394a-a79e-49fa-83fb-5e81245e36c1, version: n2:42e07a44d730e4fb, title: Status ohne Farben erkennen }
based-on:
  - { id: 157b6cb9-49ec-42ce-b989-ecf988c60cd5, version: n2:22b0303ec030d854, title: Startseite nach Entwurf D „Heute in deiner Nähe“ }
---

Das System muss jeden Status zusätzlich zur Farbe mit Symbol und Wort zeigen, in Liste, Detailseite und Kartenmarkern, mit ausreichendem Kontrast.
