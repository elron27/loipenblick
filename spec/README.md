# spec/ – Anforderungen von Loipenblick

Dieser Ordner ist ein [ReqSeq](https://github.com/ThomasBirkmaier/ReqSeq)-Workspace (getestet mit ReqSeq 0.8.3). Jede Anforderung ist eine Markdown-Datei mit Eigenschaften im Kopf. ReqSeq prüft die Dateien, verfolgt die Beziehungen und zeigt, was abgedeckt und nachgewiesen ist.

Der Inhalt stammt aus dem [Anforderungsdokument](https://claude.ai/artifact/RWrftfaPcM8nDDuxnN5MDA), der [Produktdefinition](https://claude.ai/artifact/WVMQVo2gnzPbrdqTBGUWWT) und dem [Plan Version 1](https://claude.ai/artifact/61MjfbbRGU1kt2km3ELSr7). Ab jetzt gilt dieser Ordner als Quelle der Wahrheit für die Anforderungen.

## Aufbau

| Ordner | Typ | Inhalt |
|---|---|---|
| `need/` | Bedürfnis (N) | Was Langläufer und Betreiber wollen, in ihren Worten: N-01 bis N-44 (N-05 ersetzt durch N-09; N-41 bis N-44 für die Schneekarte) |
| `system-requirement/` | Systemanforderung (SR) | Was das System können muss, mit Akzeptanzkriterien: P1–P43, D1–D25, U1–U49, N1–N12, B1–B33, S1–S26 (Schneekarte); P41–P43, D21–D24, U49, B32, B33 und D9/D10 = Mehr Daten je Loipe (24.11.2026); D25 = Hunderegel und beleuchtete Loipen (27.11.2026) |
| `decision/` | Entscheidung (D) | Getroffene Festlegungen: E-01 bis E-45 (u. a. E-45: Seefeld-Loipenbericht freigegeben, tourinfra bleibt ausstehend; E-43: Achensee nach endgültiger Ablehnung nur auf der Testseite; E-42: Besucherzähler selbst gehostet ohne Cookies; E-41: Kaiserwinkl freigegeben, Widget-Klärung abwarten; E-40: nur Fakten übernehmen, keine Beschreibungstexte, kein Outdooractive; E-39: keine fremden Bewertungen, kein Google-Link; E-38: Schneefall flächig aus ERA5-Land, Stationen als Referenz; E-37: tirol.at freigegeben, Achensee über tirol.at wieder zeigen; E-31 bis E-36: Schneekarte als Modul, keine eigene Lawinenbewertung, kein Open-Meteo, zuerst sammeln, Warnregionen als Zuschnitt, Abgrenzung zu Skitourenguru; E-30: Achensee nach Absage ganz ausblenden, auch die tirol.at-Daten; E-28: Spenden nur über einen einfachen Link; E-25: Push ohne Konto über öffentliche ntfy-Themen je Loipe und Gebiet; E-24: Quellen ohne Zustimmung erst testen, dann fragen; E-23: unplausible Offen-Meldungen als geschlossen zeigen; E-22: Steiermark über das Tourenportal von Steiermark Tourismus; E-19: Südtirol über Dolomiti NordicSki und Open Data Hub; E-18: E-Mail-Abo und Fehlermeldungen über PHP im Ordner abo/; E-17: Livegang mit deutschem Webspace; E-16: regionale Loipenberichte vor tirol.at; E-15: Ausbaustufe 1 Tirol und Salzburg; E-10: NAS parst, statische Website extern; E-11: Version 1 zuerst lokal testen) |
| `package/` | Paket (PKG) | Themen: Datenerfassung, Datenmodell, Oberfläche, Benachrichtigung, Betrieb, Schneekarte |
| `filters/` | gespeicherte Filter | `version-1`, `ausbau-1`, `ausbau-2`, `ausbau-3`, `livegang`, `schneekarte-sammeln`, `schneekarte-v1`, `loipendetails` und `spaeter` |
| `metamodel/` | Metamodell | Standardmodell plus `loipen.yaml` |

Beziehungen: Jede Systemanforderung *leitet sich ab von* (`derives-from`) einem oder mehreren Bedürfnissen und *beruht auf* (`based-on`) den Entscheidungen, die sie betreffen.

Eigene Eigenschaften (`metamodel/loipen.yaml`):

- `kennung`: lesbare ID wie `P1`, `U5`, `N-01`, `E-05`. Jeder Befehl nimmt sie als Verweis.
- `prio`: `muss`, `soll`, `kann` wie im Anforderungsdokument.
- `umfang`: `v1`, `ausbau1` (Kufstein/Tirol und Salzburg, Plan vom 12.11.2026), `ausbau2` (Südtirol und Cortina/Comelico, 13.11.2026), `livegang` (öffentlicher Betrieb im Winter 2026/27, [docs/livegang.md](../docs/livegang.md)), `schnee0` (Schneekarte: Sammel-Job, Quellen, Lizenzen und Datenmodell, sofort), `schnee1` (Schneekarte Version 1: Karte, Zeitachse, Lawinenanzeige), `details` (mehr Daten je Loipe, Plan vom 24.11.2026) oder `spaeter`.

Alle Elemente stehen auf `draft`. Den Status setzt nur ein Mensch, ReqSeq berechnet ihn nie.

## Bedienung (Kommandozeile)

Aus dem Ordner `spec/` heraus, oder überall mit `--workspace spec`:

```sh
reqseq workspace check                          # alles prüfen, Exit-Code 1 bei Fehlern
reqseq element get U5                           # eine Anforderung mit Text und Beziehungen
reqseq element list --filter version-1          # alles für Version 1
reqseq element list --package Oberfläche --where-type system-requirement --sort kennung
reqseq element search "Push"                    # Volltextsuche
reqseq trace chain N-03                         # vom Bedürfnis zu Anforderungen und Nachweisen

reqseq element create system-requirement "Titel" --text "Das System muss …" \
  --set kennung=U14 --set prio=soll --set umfang=v1 --set requirement-type=functional \
  --set 'acceptance-criteria=["Kriterium 1"]' --set 'packages=[{"id":"Oberfläche"}]' \
  --relations derives-from=N-01
reqseq element update U5 --set umfang=spaeter   # ändern
reqseq relation add U14 based-on E-07           # Beziehung ergänzen
reqseq element set-status approved --refs U5    # freigeben (nur durch Stefan)
reqseq element supersede U9 obsolete            # ungültig setzen statt löschen
```

Wird ein Bedürfnis geändert, zeigt ReqSeq die Beziehungen der davon abgeleiteten Anforderungen als „outdated“, bis jemand sie geprüft hat.

## Tests mit Anforderungen verknüpfen

Ein Test nennt die Anforderung in seinem Namen, z. B. `test_p6_datum_parsen` oder `[P6] parst das Datum`. Aus dem JUnit-XML von pytest (`pytest --junitxml=…`) macht `reqseq evidence enrich-junit` Nachweise, und `reqseq evidence without-passed-test` listet die Anforderungen, die noch kein Test zeigt.

## Desktop-App

Die App gibt es für macOS, Windows und Linux in den [Releases](https://github.com/ThomasBirkmaier/ReqSeq/releases/latest). Ordner `spec/` öffnen, dann Strg+Umschalt+P (⌘⇧P) für die Befehlsliste: Element anlegen, Beziehung anlegen, Nachbarschaft zeigen (Strg+J), Workspace prüfen.

## Bekannte Grenze

Der Workspace liegt in einem Unterordner des Git-Repositorys. ReqSeq sieht dort kein Git: Versionen haben kein Datum, und `workspace check --changed-since` geht nicht.
