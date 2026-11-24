---
id: f36a3a5a-0909-4836-8296-e7d29fee9ffb
type: system-requirement
status: draft
title: Stammdaten einer Loipe mit Herkunft
kennung: D21
prio: muss
umfang: details
rationale: "Plan „Mehr Daten je Loipe“, von Stefan am 24.11.2026 freigegeben (Issue #46)."
requirement-type: functional
acceptance-criteria:
  - Jede Angabe trägt die Herkunft (quelle, osm, hand, berechnet), eine Quell-URL und ein Prüfdatum.
  - "Merkmale stammen aus einer festen Liste: einkehr, familientauglich, hoehenloipe, bergbahn, schneesicher, hundeloipe, kunstschnee, nachtloipe, kostenlos."
  - Eine Handangabe geht einer automatischen vor; eine automatische überschreibt nie eine Handangabe.
  - Gepflegte Stammdaten liegen als YAML im Repo (config/stammdaten/) und werden beim Start in die Datenbank übernommen.
packages:
  - { id: 1554c39a-9747-4c4a-b1a2-2d04b1153c7d, version: n2:22b0303ec030d854, title: Datenmodell }
derives-from:
  - { id: efd60347-f4c8-4c6c-9b38-143045ad81d2, version: n2:1b243baea1d51dc3, title: Passende Loipe für die Gruppe }
  - { id: 3cc0b4ba-48ea-4c59-bc3e-a269e781aa26, version: n2:641911ee7fdb8aa9, title: "Wissen, wie alt und woher die Daten sind" }
based-on:
  - { id: 52813318-9ba2-438e-b682-0ab83ba29190, version: n2:f26b8546b0616ea4, title: "Nur Fakten übernehmen, keine Beschreibungstexte und kein Outdooractive" }
---

Das System muss Stammdaten einer Loipe (Höhenmeter, höchster und tiefster Punkt, Dauer, Kondition, Technikbewertung, Merkmale, Einstiege, Loipengebiet, Kunstschnee) mit Herkunft und Prüfdatum führen.
