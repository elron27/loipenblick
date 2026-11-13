<?php
/*
 * E-Mail-Abo von Loipenblick, Teil auf dem Webspace (E-18).
 *
 * Der Webspace nimmt Anmeldungen an, verschickt die Bestaetigungsmail (Double-Opt-In, N2) und
 * merkt sich bestaetigte Abos und Abmeldungen in einer Warteschlange. Das NAS holt die
 * Warteschlange bei jedem Lauf ab (export.php), uebernimmt sie in seine Datenbank und schickt
 * die Alarme selbst per SMTP. Das NAS oeffnet dafuer keinen Port.
 *
 * Datensparsamkeit (N7): Eine unbestaetigte Anmeldung wird nirgends gespeichert. Alles, was der
 * Bestaetigungslink braucht, steckt verschluesselt im Link selbst. Nach der Abholung durch das NAS
 * loescht der Webspace die Eintraege wieder.
 *
 * Dateien im Datenordner beginnen mit "<?php exit; ?>", damit sie auch dann nicht lesbar sind,
 * wenn der Webserver .htaccess nicht beachtet.
 */
declare(strict_types=1);

const ABO_ARTEN = ['oeffnet' => 'öffnet', 'frisch_gespurt' => 'frisch gespurt', 'schliesst' => 'schließt'];
const ABO_GUELTIG_S = 48 * 3600;      // Bestaetigungslink
const ABO_MAX_ZIELE = 20;
const ABO_LIMIT_IP = 5;               // Anmeldungen je Anschluss und Stunde
const ABO_LIMIT_MAIL = 3;             // Bestaetigungsmails je Adresse und Tag
const ABO_SPERRE = "<?php exit; ?>\n";

function abo_einstellungen(): array
{
    static $e = null;
    if ($e === null) {
        $datei = __DIR__ . '/einstellungen.php';
        if (!is_file($datei)) {
            abo_antwort(503, 'Abo nicht eingerichtet', 'Das E-Mail-Abo ist auf dieser Seite nicht eingerichtet.');
        }
        $e = require $datei;
    }
    return $e;
}

function abo_datenordner(): string
{
    $o = abo_einstellungen()['datenordner'] ?? '';
    if ($o === '') {
        $o = __DIR__ . '/daten';
    } elseif ($o[0] !== '/') {
        $o = __DIR__ . '/' . $o;
    }
    if (!is_dir($o) && !mkdir($o, 0700, true) && !is_dir($o)) {
        abo_antwort(500, 'Fehler', 'Der Datenordner des Abos fehlt.');
    }
    return $o;
}

/** Zufaelliges Geheimnis, beim ersten Aufruf auf dem Webspace erzeugt. Verlaesst den Webspace nie. */
function abo_geheimnis(): string
{
    static $g = null;
    if ($g !== null) {
        return $g;
    }
    $datei = abo_datenordner() . '/geheimnis.php';
    if (!is_file($datei)) {
        $f = @fopen($datei, 'x');
        if ($f !== false) {
            fwrite($f, ABO_SPERRE . bin2hex(random_bytes(32)) . "\n");
            fclose($f);
            @chmod($datei, 0600);
        }
    }
    $zeilen = file($datei, FILE_IGNORE_NEW_LINES);
    $g = hex2bin(trim($zeilen[1] ?? ''));
    if ($g === false || strlen($g) !== 32) {
        abo_antwort(500, 'Fehler', 'Das Geheimnis des Abos ist beschädigt.');
    }
    return $g;
}

function abo_b64(string $s): string
{
    return rtrim(strtr(base64_encode($s), '+/', '-_'), '=');
}

function abo_unb64(string $s): string|false
{
    return base64_decode(strtr($s, '-_', '+/'), true);
}

function abo_hmac(string $zweck, string $daten): string
{
    return hash_hmac('sha256', $zweck . ':' . $daten, abo_geheimnis());
}

/** Verschluesselt und signiert (AES-256-GCM), damit die Adresse auch im Server-Log nicht lesbar ist. */
function abo_versiegeln(array $daten): string
{
    $iv = random_bytes(12);
    $tag = '';
    $schluessel = hash_hmac('sha256', 'siegel', abo_geheimnis(), true);
    $c = openssl_encrypt(json_encode($daten), 'aes-256-gcm', $schluessel, OPENSSL_RAW_DATA, $iv, $tag);
    return abo_b64($iv . $tag . $c);
}

function abo_entsiegeln(string $token): ?array
{
    $roh = abo_unb64($token);
    if ($roh === false || strlen($roh) < 29) {
        return null;
    }
    $schluessel = hash_hmac('sha256', 'siegel', abo_geheimnis(), true);
    $json = openssl_decrypt(substr($roh, 28), 'aes-256-gcm', $schluessel, OPENSSL_RAW_DATA, substr($roh, 0, 12), substr($roh, 12, 16));
    if ($json === false) {
        return null;
    }
    $d = json_decode($json, true);
    return is_array($d) ? $d : null;
}

function abo_ziele(): array
{
    static $z = null;
    if ($z === null) {
        $datei = __DIR__ . '/ziele.php';
        $z = is_file($datei) ? require $datei : [];
    }
    return $z;
}

/** Datei im Datenordner unter Sperre lesen und aendern. $aendern bekommt die Zeilen ohne Kopf. */
function abo_datei(string $name, callable $aendern): mixed
{
    $datei = abo_datenordner() . '/' . $name . '.php';
    $f = fopen($datei, 'c+');
    if ($f === false || !flock($f, LOCK_EX)) {
        abo_antwort(500, 'Fehler', 'Die Abo-Daten sind gerade nicht erreichbar.');
    }
    $inhalt = stream_get_contents($f);
    $zeilen = array_values(array_filter(explode("\n", $inhalt), fn($z) => $z !== '' && !str_starts_with($z, '<?php')));
    [$neu, $ergebnis] = $aendern($zeilen);
    if ($neu !== null) {
        ftruncate($f, 0);
        rewind($f);
        fwrite($f, ABO_SPERRE . implode('', array_map(fn($z) => $z . "\n", $neu)));
        fflush($f);
    }
    flock($f, LOCK_UN);
    fclose($f);
    @chmod($datei, 0600);
    return $ergebnis;
}

function abo_warteschlange_anhaengen(array $eintrag): void
{
    abo_datei('warteschlange', function (array $zeilen) use ($eintrag) {
        $zeilen[] = json_encode($eintrag, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
        return [$zeilen, null];
    });
}

/**
 * Begrenzt Anfragen je Schluessel (nur als HMAC gespeichert, nach 24 h geloescht).
 * Gibt false zurueck, wenn das Limit erreicht ist.
 */
function abo_limit(string $art, string $wert, int $max, int $fenster_s): bool
{
    $schluessel = $art . ':' . substr(abo_hmac('limit', $art . $wert), 0, 24);
    $jetzt = time();
    return abo_datei('limits', function (array $zeilen) use ($schluessel, $max, $fenster_s, $jetzt) {
        $daten = json_decode($zeilen[0] ?? '{}', true) ?: [];
        foreach ($daten as $k => $zeiten) {
            $daten[$k] = array_values(array_filter($zeiten, fn($t) => $t > $jetzt - 86400));
            if (!$daten[$k]) {
                unset($daten[$k]);
            }
        }
        $treffer = array_filter($daten[$schluessel] ?? [], fn($t) => $t > $jetzt - $fenster_s);
        $frei = count($treffer) < $max;
        if ($frei) {
            $daten[$schluessel][] = $jetzt;
        }
        return [[json_encode($daten)], $frei];
    });
}

function abo_link(string $datei, array $parameter): string
{
    $basis = rtrim(abo_einstellungen()['seite_url'] ?? '', '/');
    return $basis . '/abo/' . $datei . '?' . http_build_query($parameter);
}

function abo_mail(string $an, string $betreff, string $text, array $kopf = []): bool
{
    $e = abo_einstellungen();
    $absender = $e['absender'];
    $kopfzeilen = array_merge([
        'From' => '=?UTF-8?B?' . base64_encode($e['seitenname'] ?? 'Loipenblick') . '?= <' . $absender . '>',
        'MIME-Version' => '1.0',
        'Content-Type' => 'text/plain; charset=UTF-8',
        'Content-Transfer-Encoding' => '8bit',
        'Auto-Submitted' => 'auto-generated',
    ], $kopf);
    return mail($an, '=?UTF-8?B?' . base64_encode($betreff) . '?=', $text, $kopfzeilen, '-f' . $absender);
}

function abo_h(string $s): string
{
    return htmlspecialchars($s, ENT_QUOTES | ENT_HTML5, 'UTF-8');
}

function abo_will_json(): bool
{
    return str_contains($_SERVER['HTTP_ACCEPT'] ?? '', 'application/json');
}

/** Antwort als kleine HTML-Seite im Stil der Website oder als JSON fuer das Formular. Beendet das Skript. */
function abo_antwort(int $code, string $titel, string $text, string $html_zusatz = ''): never
{
    http_response_code($code);
    header('Cache-Control: no-store');
    header('X-Robots-Tag: noindex');
    header('Referrer-Policy: no-referrer');
    if (abo_will_json()) {
        header('Content-Type: application/json; charset=utf-8');
        echo json_encode(['ok' => $code < 400, 'titel' => $titel, 'text' => $text], JSON_UNESCAPED_UNICODE);
        exit;
    }
    header('Content-Type: text/html; charset=utf-8');
    header("Content-Security-Policy: default-src 'none'; style-src 'unsafe-inline'; form-action 'self'; base-uri 'none'; frame-ancestors 'none'");
    $name = 'Loipenblick';
    $datenschutz = 'datenschutz.html';
    if (is_file(__DIR__ . '/einstellungen.php')) {
        $e = require __DIR__ . '/einstellungen.php';
        $name = $e['seitenname'] ?? $name;
        $datenschutz = $e['datenschutz'] ?? $datenschutz;
    }
    echo '<!doctype html><html lang="de"><head><meta charset="utf-8">'
        . '<meta name="viewport" content="width=device-width,initial-scale=1">'
        . '<meta name="robots" content="noindex">'
        . '<title>' . abo_h($titel) . ' · ' . abo_h($name) . '</title><style>'
        . ':root{--grund:#0f1d2b;--flaeche:#16283a;--linie:#2b4560;--text:#e8f1f8;--leise:#9fb6c9;--eis:#7fd3f0;--fehler:#ff9c8a}'
        . '@media (prefers-color-scheme:light){:root{--grund:#e9f1f7;--flaeche:#f7fbfe;--linie:#b9cddd;--text:#10202f;--leise:#4a6378;--eis:#0f6f96;--fehler:#a3341e}}'
        . 'body{margin:0;background:var(--grund);color:var(--text);font:16px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif}'
        . 'main{max-width:34rem;margin:12vh auto 2rem;padding:1.5rem 1rem}'
        . '.marke{color:var(--eis);font-weight:700;letter-spacing:.04em;text-decoration:none}'
        . 'h1{font-size:1.5rem;margin:.8rem 0 .6rem}p{color:var(--leise)}'
        . '.feld{background:var(--flaeche);border:1px solid var(--linie);border-radius:10px;padding:1rem 1.1rem;margin:1.2rem 0}'
        . 'ul{margin:.3rem 0 0;padding-left:1.2rem}'
        . 'button{font:inherit;font-weight:600;background:var(--eis);color:var(--grund);border:0;border-radius:8px;padding:.7rem 1.2rem;cursor:pointer}'
        . 'a{color:var(--eis)}.fehler{color:var(--fehler)}footer{margin-top:2rem;font-size:.9rem}'
        . '</style></head><body><main>'
        . '<a class="marke" href="../">' . abo_h($name) . '</a>'
        . '<h1' . ($code >= 400 ? ' class="fehler"' : '') . '>' . abo_h($titel) . '</h1>'
        . '<p>' . abo_h($text) . '</p>' . $html_zusatz
        . '<footer><a href="../">Zur Übersicht</a> · <a href="../' . abo_h($datenschutz) . '">Datenschutz</a></footer>'
        . '</main></body></html>';
    exit;
}

function abo_ziel_liste(array $ziele): string
{
    $namen = abo_ziele();
    return '<ul>' . implode('', array_map(fn($z) => '<li>' . abo_h($namen[$z] ?? $z) . '</li>', $ziele)) . '</ul>';
}

function abo_arten_text(array $arten): string
{
    return implode(', ', array_map(fn($a) => ABO_ARTEN[$a] ?? $a, $arten));
}
