---
id: c1ad39cd-c1dd-4cba-bd4c-00bbcfc4bd9a
type: system-requirement
status: draft
title: Keine Personendaten aus Quellen speichern
kennung: B33
prio: muss
umfang: details
rationale: "Plan „Mehr Daten je Loipe“, von Stefan am 24.11.2026 freigegeben (Issue #46). Stefan: „ja personendaten nicht speichern“."
requirement-type: functional
acceptance-criteria:
  - redakt und vergleichbare Felder fehlen in Datenbank, Rohtext und Fixture-Auswertung.
  - Ein Test prüft, dass kein Rohtext der tourinfra-Quellen das Feld redakt enthält.
packages:
  - { id: a1e07cef-f067-4f3b-a290-7b0bc167bcfa, version: n2:22b0303ec030d854, title: Betrieb }
derives-from:
  - { id: 914f2148-aa61-463c-839d-0cd4039bc354, version: n2:946e559473e10418, title: Daten fair und rechtlich sauber übernehmen }
---

Das System darf Namen von Personen aus den Quellen (z. B. das tourinfra-Feld redakt mit Fahrernamen) weder speichern noch zeigen.
