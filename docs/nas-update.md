# Update auf der Synology (Container Manager)

**Warum „Stoppen und neu erstellen“ nicht reicht:** Der Container Manager nimmt dabei das Image, das schon
auf dem NAS liegt. Die neue Version holt er nur, wenn das alte Image weg ist oder ausdrücklich
`docker compose pull` läuft. GitHub baut nach jedem Merge ein neues Image (`ghcr.io/elron27/loipenblick:latest`).

Die Daten (Ordner `data/`, `site/`, `backup/` neben der `docker-compose.yml`) bleiben bei beiden Wegen erhalten.

## Weg A: nur Container Manager (ohne Einrichtung)

1. **Container Manager → Projekt →** Projekt „loipenblick“ anklicken **→ Aktion → Stoppen.**
2. **Aktion → Bereinigen.** Das entfernt nur die Container, nicht die Daten.
3. **Image** (links) **→** `ghcr.io/elron27/loipenblick` (Tag `latest`) anklicken **→ Löschen.**
   Das Image `postgres` und `nginx` stehen lassen.
4. **Projekt → loipenblick → Aktion → Erstellen.** Weil das Image fehlt, lädt er das neueste von GitHub.
   Der Container `migrate` spielt danach die neuen Datenbank-Tabellen ein und beendet sich (das ist richtig so).

## Weg B: Aufgabenplaner (einmal einrichten, danach ein Klick)

1. **Systemsteuerung → Aufgabenplaner → Erstellen → Geplante Aufgabe → Benutzerdefiniertes Script.**
2. Reiter **Allgemein:** Name „Loipenblick aktualisieren“, Benutzer **root**, Haken bei „Aktiviert“ entfernen
   (dann läuft sie nur, wenn du sie startest).
3. Reiter **Aufgabeneinstellungen**, Feld „Benutzerdefiniertes Script“:

   ```sh
   cd /volume1/docker/loipenblick && docker compose pull && docker compose up -d
   ```

   Den Pfad auf den Ordner mit der `docker-compose.yml` anpassen. Er steht im Container Manager unter
   **Projekt → loipenblick → Allgemein → Pfad**. Auf älteren DSM-Versionen heißt der Befehl `docker-compose`.
4. **OK**, dann die Aufgabe anklicken **→ Ausführen.**

## Prüfen, ob das Update angekommen ist

1. **Container Manager → Container →** `…-worker-1` **→ Details → Protokoll.** Oben steht
   `Loipenblick Version 1234abc startet`. Die sieben Zeichen sind der Stand auf GitHub.
2. Der erste Lauf ruft alle Quellen ab und dauert einige Minuten, bei allen Regionen bis etwa eine halbe Stunde.
   Erst wenn im Protokoll `Seite erzeugt in /app/site` steht, ändert sich die Seite.
3. Die Seite im Heimnetz (`http://<NAS-IP>:<VORSCHAU_PORT>`) **zweimal neu laden.** Beim ersten Mal zeigt der
   Browser noch die gespeicherte alte Fassung. Unten in der Fußzeile steht dann `Version 1234abc`.

## .env

Für den Test im Heimnetz ist **keine neue Variable nötig.** Alle neuen Werte gehören zum Livegang:

| Variable | Wofür | Ohne Wert |
|---|---|---|
| `LOIPEN_IMPRESSUM_NAME`, `…_ANSCHRIFT`, `…_EMAIL` | Impressum, Pflicht vor dem Upload | Impressum bleibt unvollständig, kein Upload |
| `LOIPEN_ABO_*`, `LOIPEN_SMTP_*` | E-Mail-Abo und „Angabe falsch? Melden“ | keine Formulare auf der Seite |
| `LOIPEN_WAECHTER_MAIL` | Mail, wenn eine Quelle kaputt wirkt | Wächter meldet nur per Push (`LOIPEN_NTFY_URL`) |

Vorlage mit Erklärungen: [`.env.example`](../.env.example).
