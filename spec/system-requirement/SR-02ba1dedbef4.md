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
  - { id: 74e4361d-47e5-4ab3-b04d-3e2e5f25ec16, version: n2:cdda38f1ace5147f, title: Günstiger Betrieb }
based-on:
  - { id: 2ae0ad55-3d2e-461b-975b-237a0a1f0ac5, version: n2:22b0303ec030d854, title: "Parsen auf dem NAS, Website extern" }
---

Das System muss per Docker Compose auf dem Synology-NAS laufen, Konfiguration und Secrets über Umgebungsvariablen.
