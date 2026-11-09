---
id: e648c0b6-917a-4393-af75-ae18d5eaec27
type: system-requirement
status: draft
title: Schneequalität einschätzen
kennung: U17
prio: kann
umfang: spaeter
rationale: "Aus dem Interview mit Stefan am 08.11.2026. Am 09.11.2026 auf später gestellt: Die Loipenqualität ist schwer herauszufinden und einzuschätzen. In Version 1 zeigt die Seite nur die Rohdaten (Neuschnee D11, Präparierung D3, Wetter U15)."
requirement-type: functional
acceptance-criteria:
  - „Gute Bedingungen“ erscheint nur, wenn es in den letzten 48 h Neuschnee gab (D11), die Präparierung nach dem Schneefall lag (D3) und die Temperatur nicht unter der eingestellten Grenze liegt (U15).
  - Die Schwellen (Neuschnee in cm, Zeitraum, Temperaturgrenze) stehen in der Konfiguration, nicht im Code.
  - Ein Tipp auf die Einschätzung zeigt, woraus sie sich ergibt.
packages:
  - { id: 7b29aa02-4a82-499c-9654-8d13c0c2d64c, version: n2:22b0303ec030d854, title: Oberfläche }
derives-from:
  - { id: 336b2c0a-3750-430a-a545-ffb48f31dedb, version: n2:fb1eee7dc7f860a6, title: "Wissen, wo guter Schnee liegt" }
---

Das System soll pro Gebiet eine einfache Einschätzung der Schneebedingungen zeigen, nach Stefans Regel: Gut ist es, wenn es kürzlich geschneit hat, danach gespurt wurde und es nicht zu kalt ist. Strenger Frost macht die Loipe hart. Die Einschätzung ist als solche gekennzeichnet, keine Garantie.
