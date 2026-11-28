---
id: ac0080b3-2466-4419-8fde-4cb60be952eb
type: system-requirement
status: draft
title: Geschlossen und unbekannt auf Karte und Talprofil unterscheidbar
kennung: U50
prio: soll
umfang: ausbau1
rationale: "Impeccable-Prüfung vom 25.11.2026, Vorschlag 2 und Markergröße; von Stefan am 28.11.2026 freigegeben."
requirement-type: functional
acceptance-criteria:
  - Auf Karte und Talprofil sind geschlossen (gedämpftes Rot mit Kreuz) und ohne Angabe (hell, gestrichelter Rand, Fragezeichen) in Farbe und Form verschieden.
  - Karte und Talprofil haben eine Legende mit allen vier Zuständen.
  - Jeder Kartenmarker hat eine Tippfläche von mindestens 44 × 44 px, auf Handy und Desktop.
packages:
  - { id: 7b29aa02-4a82-499c-9654-8d13c0c2d64c, version: n2:22b0303ec030d854, title: Oberfläche }
derives-from:
  - { id: 21549a25-7de6-45a5-9fb3-19a1873e2bb4, version: n2:c59908d64ea67dab, title: Überblick über die Lage in der Region }
---

Das System soll den Zustand einer Loipe auf Karte und Talprofil nicht nur über die Farbe zeigen, sondern auch über ein Zeichen, damit geschlossene und unbekannte Loipen auch bei Farbschwäche und in der Sonne unterscheidbar sind.
