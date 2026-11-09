---
id: 4160d107-78f1-4421-9c78-4fb97d8ae7d9
type: system-requirement
status: draft
title: Rücksichtsvoll abrufen
kennung: P7
prio: muss
umfang: v1
rationale: "Herkunft: [Anforderungsdokument](https://claude.ai/artifact/RWrftfaPcM8nDDuxnN5MDA), P7."
requirement-type: constraint
acceptance-criteria:
  - Zwischen zwei Anfragen an dieselbe Domain liegt mindestens der Crawl-delay der Quelle (derzeit 5 s).
  - Eine durch robots.txt gesperrte URL wird nicht abgerufen.
  - Jede Anfrage trägt den eigenen User-Agent mit Kontaktangabe.
packages:
  - { id: aecf250b-eb6d-41e6-9041-3ce5eb9763a3, version: n2:22b0303ec030d854, title: Datenerfassung }
derives-from:
  - { id: 914f2148-aa61-463c-839d-0cd4039bc354, version: n2:946e559473e10418, title: Daten fair und rechtlich sauber übernehmen }
---

Das System muss robots.txt beachten, ein Rate-Limit pro Domain einhalten, einen eigenen User-Agent mit Kontakt senden und per ETag/Last-Modified cachen.
