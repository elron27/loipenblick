---
id: dc6e0f26-7629-4281-9ea7-02ba1dedbef4
type: system-requirement
status: draft
title: Docker Compose und Umgebungsvariablen
kennung: B4
prio: muss
umfang: v1
rationale: "Herkunft: [Anforderungsdokument](https://claude.ai/artifact/RWrftfaPcM8nDDuxnN5MDA), B4."
requirement-type: constraint
acceptance-criteria:
  - docker compose up startet Web, Worker und Datenbank auf dem NAS.
  - Kein Secret steht im Repository.
packages:
  - { id: a1e07cef-f067-4f3b-a290-7b0bc167bcfa, version: n2:22b0303ec030d854, title: Betrieb }
derives-from:
  - { id: 1ad58a1d-3eca-49df-8609-68c23dac832b, version: n2:5919be98155e8537, title: "Privat betreiben, später umziehen können" }
based-on:
  - { id: 91c72a2d-c935-429e-9260-39b344677af0, version: n2:22b0303ec030d854, title: Version 1 privat auf dem Synology-NAS }
---

Das System muss per Docker Compose auf dem Synology-NAS laufen, Konfiguration und Secrets über Umgebungsvariablen.
