# Benachrichtigung für einzelne Loipen

Stand 20.11.2026 (E-25, U7, N10–N12). Wer eine bestimmte Loipe beobachten will, hat drei Wege. Alle melden
dieselben Ereignisse: **öffnet**, **frisch gespurt**, **schließt**.

| Weg | Für wen | Einstellung | Was gespeichert wird |
| --- | --- | --- | --- |
| E-Mail-Abo je Loipe, Gebiet oder für alle gemerkten Loipen | Besucher | `LOIPEN_ABO_*`, `LOIPEN_SMTP_*` (E-18) | Adresse und Auswahl auf dem NAS, nach Double-Opt-In |
| Push über öffentliche ntfy-Themen je Loipe und Gebiet | Besucher, ohne Konto | `LOIPEN_PUSH_PRAEFIX` | nichts: wir senden nur ans Thema |
| Push über das eigene geheime Thema | Stefan | `LOIPEN_NTFY_URL`, `config/abos.yaml` (E-05) | nichts |

## Merkliste „Meine Loipen“ (U7, N12)

- Auf jeder Loipenseite steht **Merken**. Die Liste liegt nur im Browser (`localStorage`), ohne Konto.
- Die Startseite zeigt die gemerkten Loipen mit Status ganz oben, darunter der Link zu **Meine Loipen** (`#/meine`, auch in der Fußzeile).
- Auf „Meine Loipen“ gibt es ein E-Mail-Abo für alle gemerkten Loipen auf einmal (höchstens 20, wie `ABO_MAX_ZIELE` in `abo/_kern.php`) und die Push-Themen jeder gemerkten Loipe.

## Push ohne Konto (N10)

- Themen: `<praefix>-l<loipen-id>` und `<praefix>-g-<gebiet>`. Die Loipen-ID ist dieselbe wie in der Adresse `#/loipe/<id>`.
- Besucher installieren die App **ntfy** (Android, iPhone) oder nutzen den Browser und abonnieren das Thema. Der Link auf der Seite führt zu `https://ntfy.sh/<thema>`. Die Seite selbst lädt nichts von ntfy.
- Je Thema und Lauf höchstens eine Nachricht. Das Gebietsthema bündelt alle Ereignisse des Gebiets. Ein Tippen auf die Nachricht öffnet die Loipe bzw. das Gebiet auf der Seite.
- **Tagesgrenze:** ntfy.sh erlaubt ohne Konto 250 Nachrichten am Tag je Absender. Der öffentliche Push nutzt höchstens `LOIPEN_PUSH_MAX_TAG` (Standard 150), Gebietsthemen zuerst; der Rest bleibt für Stefans eigene Meldungen. Wird die Grenze erreicht, kommt einmal am Tag eine Meldung über `LOIPEN_NTFY_URL`. Reicht das nicht (z. B. am ersten Schneetag mit vielen Öffnungen), hilft ein ntfy-Konto: Token in `LOIPEN_PUSH_TOKEN`, Grenze hochsetzen.
- **Öffentliche Themen kann jeder beschreiben.** Das Präfix steht auf der Seite. Ein schwer erratbares Präfix hält Zufallstreffer fern, gegen Absicht hilft nur ein ntfy-Konto mit reservierten Themen. Unsere Nachrichten verweisen immer auf die Seite; das steht so auch in der Datenschutzerklärung.

## Keine doppelten Nachrichten (N11)

Das Meldeprotokoll (Tabelle `meldeprotokoll`, Migration 0008) merkt sich je Loipe, was zuletzt gemeldet wurde. Es gilt für alle drei Wege und greift nach der Plausibilitätsprüfung (D19):

- „öffnet“ und „schließt“ gehen nicht noch einmal raus, wenn dieselbe Art schon zuletzt gemeldet wurde und das weniger als 48 Stunden her ist. Typischer Fall: Die Quelle meldet kurz „unbekannt“ und danach wieder „offen“.
- „frisch gespurt“ höchstens einmal in 18 Stunden je Loipe, und nicht in den 18 Stunden nach „öffnet“.
- Ein gegenläufiger Wechsel (schließt nach öffnet) geht immer durch.
- Eingetragen wird vor dem Versand. Scheitert ein Versand, wird er nicht nachgeholt; sonst kämen nach einer Störung Doppelte.

Weiterhin gilt: höchstens eine Mail je Abonnent und Lauf (N3), eine Nachricht je Abo in `abos.yaml` und Lauf (N4), und eine unplausible Offen-Meldung löst keine Nachricht aus (D19).
