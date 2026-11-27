---
id: c0a16c77-ced8-4438-ad56-5785c4da5abc
type: system-requirement
status: draft
title: Bayerischer Wald und Fichtelgebirge über den tourinfra-Loipenmanager anbinden
kennung: P44
prio: kann
umfang: ausbau1
rationale: "Recherche vom 27.11.2026 (docs/recherche-neue-regionen-2026-11-27.md): beide Tourismusverbände nutzen denselben Loipenmanager wie Chiemgau; Stefan gab die Umsetzung am 27.11. frei."
requirement-type: functional
acceptance-criteria:
  - "Bayerischer Wald: alle Loipen des Abrufs `bayerischer-wald` mit Status je Technik, Länge, Streckenverlauf und Grund der Sperre; jeder Startort ist einem der elf Gebiete zugeordnet (keine gebiet_map-Warnung). Der Teilabruf `arberland` wird nicht angebunden, sonst entstehen Dubletten."
  - "Fichtelgebirge: alle Loipen des Abrufs `fichtelgebirge`, jeder Startort einem der fünf Gebiete zugeordnet."
  - "Beide Quellen haben Rang 2 und Erlaubnis nur_test, bis die Erlaubnis-Mail beantwortet ist. Jedes neue Gebiet hat Lage und eine Region mit Land und Bundesland."
packages:
  - { id: aecf250b-eb6d-41e6-9041-3ce5eb9763a3, version: n2:22b0303ec030d854, title: Datenerfassung }
derives-from:
  - { id: 93a6a006-58bf-4a79-b4f1-bc1b6d91988f, version: n2:6ca5edb7fee77c7d, title: Loipen überall abdecken }
based-on:
  - { id: a2715ad5-85dd-40c4-a964-8148c8fe3659, version: n2:cd357b270c742bf5, title: "Quellen ohne Zustimmung erst testen, dann mit Vorführung fragen" }
---

Das System soll die Loipenberichte des Bayerischen Walds und des Fichtelgebirges aus dem tourinfra-Loipenmanager lesen, damit die schneesichersten Mittelgebirge Bayerns abgedeckt sind.
