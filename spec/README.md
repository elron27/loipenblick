# spec/ – Anforderungen von Loipenblick

Dieser Ordner ist ein [ReqSeq](https://github.com/ThomasBirkmaier/ReqSeq)-Workspace (getestet mit ReqSeq 0.8.3). Jede Anforderung ist eine Markdown-Datei mit Eigenschaften im Kopf. ReqSeq prüft die Dateien, verfolgt die Beziehungen und zeigt, was abgedeckt und nachgewiesen ist.

Der Inhalt stammt aus dem [Anforderungsdokument](https://claude.ai/artifact/RWrftfaPcM8nDDuxnN5MDA), der [Produktdefinition](https://claude.ai/artifact/WVMQVo2gnzPbrdqTBGUWWT) und dem [Plan Version 1](https://claude.ai/artifact/61MjfbbRGU1kt2km3ELSr7). Ab jetzt gilt dieser Ordner als Quelle der Wahrheit für die Anforderungen.

## Aufbau

| Ordner | Typ | Inhalt |
|---|---|---|
| `need/` | Bedürfnis (N) | Was Langläufer und Betreiber wollen, in ihren Worten: N-01 bis N-19 (N-05 ersetzt durch N-09) |
| `system-requirement/` | Systemanforderung (SR) | Was das System können muss, mit Akzeptanzkriterien: P1–P13, D1–D13, U1–U20, N1–N4, B1–B11 |
| `decision/` | Entscheidung (D) | Getroffene Festlegungen: E-01 bis E-12 (u. a. E-10: NAS parst, statische Website extern; E-11: Version 1 zuerst lokal testen) |
| `package/` | Paket (PKG) | Themen: Datenerfassung, Datenmodell, Oberfläche, Benachrichtigung, Betrieb |
| `filters/` | gespeicherte Filter | `version-1` und `spaeter` |
| `metamodel/` | Metamodell | Standardmodell plus `loipen.yaml` |

Beziehungen: Jede Systemanforderung *leitet sich ab von* (`derives-from`) einem oder mehreren Bedürfnissen und *beruht auf* (`based-on`) den Entscheidungen, die sie betreffen.

Eigene Eigenschaften (`metamodel/loipen.yaml`):

- `kennung`: lesbare ID wie `P1`, `U5`, `N-01`, `E-05`. Jeder Befehl nimmt sie als Verweis.
- `prio`: `muss`, `soll`, `kann` wie im Anforderungsdokument.
- `umfang`: `v1` oder `spaeter`, abgeleitet aus Produktdefinition und Plan V1.

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
