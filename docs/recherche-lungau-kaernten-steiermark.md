# Recherche Lungau, Kärnten und Steiermark (14.11.2026)

Auftrag (Stefan, 14.11.2026): „Ja gleich runter bis Kärnten und der Steiermark suchen und einbauen“.
Schnappschüsse: Workflow „Schnappschuss“, Runden 14–19, Protokoll in `tests/fixtures/schnappschuss-protokoll.txt`.

## Ergebnis

| Gebiet | Quelle | Befund | Stand |
|---|---|---|---|
| Steiermark (ganz) | Tourenportal von Steiermark Tourismus, `https://www.steiermark.com/de/Urlaub-planen/Tourenportal?tourCategory=46459526` | 89 Langlaufloipen auf 6 Seiten, Status-Badge je Loipe (geöffnet, teilweise, geschlossen), Länge, Startort, Schwierigkeit; kein Datum, keine Koordinaten. Ausseerland („Loipenbericht Ausseerland“) und Murau („Der Loipenstatus“) verlinken genau diese Liste. robots.txt erlaubt `/de/`. | **angebunden (P30)** |
| Ramsau am Dachstein | tourinfra-Loipenmanager (seit E-20) | mit Stand je Loipe, bleibt führend (Rang 2) | unverändert |
| Schladming-Dachstein | `https://www.schladming-dachstein.at/de/aktivitaeten/langlaufen/geoeffnete-loipen` | 42 Loipen in 6 Reitern mit Status, Technik, Länge, Hinweistext; dieselben Loipen wie im Tourenportal | nicht nötig |
| Lungau | `https://www.lungau.at/de/winter/abseits-der-piste/langlaufen/loipenbericht` | Inhalt kommt nur über ein bergfex-Skript; kein tourinfra (lungau, tamsweg, mariapfarr, katschberg u. a. 404) | offen, Entscheidung Stefan |
| Lungau, Prebersee | Tourenportal Steiermark (Start Tamsweg) | eine Lungauer Loipe | angebunden |
| Kärnten außer Nassfeld/Weissensee | `https://www.kaernten.at/service/wetter/loipenberichte/` | nur Gebietsebene, Daten von bergfex; Tourenportal Kärnten und seeundberg.at = outdooractive mit API-Schlüssel | offen, Entscheidung Stefan |
| Weissensee | `tools.nlw.at/sportbericht/print/wintersportbericht-ws.pdf` | Status je Loipe nur als Symbol (L1–L4, S1, S2, ÜL1, ÜL2), Zähler wie im NPS-Bericht | über P28 abgedeckt |
| Lesachtal | `lesachtal.com` | kein Status in der Seite, kein eigener NLW-Bericht (`-lt`, `-la`, `-ls` = 404) | ohne Quelle |

Getestete tourinfra-Instanzen ohne Treffer (404): lungau, salzburgerlungau, tamsweg, mariapfarr, stmichael, katschberg,
steiermark, schladming-dachstein, ausseerland, murtal, murau, hochsteiermark, mariazell, erzberg-leoben, thermenland,
oststeiermark, almenland, region-graz, seeundberg, bad-kleinkirchheim, nockberge, millstaettersee, mallnitz, heiligenblut,
villach, woerthersee, lavanttal, klopeinersee, hohetauern und weitere (Runde 14).

## Wetter

GeoSphere-Stationen mit Schneehöhe (sh oder sh_manu) je neuem Gebiet, Abrufe `klima-v2-1d_steiermark.json` und
`klima-v2-1d_steiermark2.json`. Ohne Schneehöhe und daher nicht genutzt: Gröbming 12811, Murau 15920, Mariapfarr 15721,
Rottenmann 9925, Präbichl 10111, Oberwölz 15901, Kalwang 13120.

## Offen

- Lungau und übriges Kärnten: nur bergfex (siehe E-22). Entweder bergfex um Erlaubnis fragen oder vorerst ohne.
- Vor dem Öffentlichschalten: Nutzungsbedingungen von Steiermark Tourismus (steiermark.com) prüfen (Backlog).
- Dezember: Status im Betrieb prüfen (Mitte November fast alles geschlossen).
