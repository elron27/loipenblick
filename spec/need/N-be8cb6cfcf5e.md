---
id: 61222249-ffc3-4fb4-802a-be8cb6cfcf5e
type: need
status: draft
title: Offensichtliche Fehlmeldungen nicht als offen sehen
kennung: N-39
priority: high
validation-criteria:
  - Am Saisonanfang 2026 (19.11.) erscheint keine Loipe als offen, die nur ein Landesportal ohne Datum meldet, während die Station des Gebiets 0 cm misst.
rationale: "Stefan am 19.11.2026: Die Testseite zeigt die Ginzling Loipe offen, obwohl kein Schnee liegt. Sanity Checks für die frühe Phase, prüfen, wo es tatsächlich geschneit hat."
packages:
  - { id: 1554c39a-9747-4c4a-b1a2-2d04b1153c7d, version: n2:22b0303ec030d854, title: Datenmodell }
---

Als Langläufer will ich, dass eine Loipe nicht als offen erscheint, wenn eine Quelle sie offensichtlich falsch meldet, etwa ohne Schnee bei Plusgraden oder mit einer Meldung von vor Wochen, damit ich nicht umsonst hinfahre.
