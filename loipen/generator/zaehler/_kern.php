<?php
/*
 * Besucherzaehler von Loipenblick, Teil auf dem Webspace (B13, E-42).
 *
 * Zaehlt Seitenaufrufe und Besucher pro Tag, Seite, Gebiet und Loipe, ohne Cookies und ohne etwas
 * im Browser zu speichern. Gespeichert werden nur Summen pro Tag.
 *
 * Besucher: Aus IP-Adresse und Browserkennung entsteht ein Pruefwert mit einem Zufallssalz, das
 * jeden Tag neu gewuerfelt und am naechsten Tag mit allen Pruefwerten verworfen wird. Die IP-Adresse
 * selbst wird nie gespeichert. Ein Besucher, der an zwei Tagen kommt, zaehlt zweimal; Besuche an
 * verschiedenen Tagen lassen sich nicht verbinden.
 *
 * Dateien im Datenordner beginnen mit "<?php exit; ?>", damit sie auch dann nicht lesbar sind,
 * wenn der Webserver .htaccess nicht beachtet.
 */
declare(strict_types=1);

const Z_SPERRE = "<?php exit; ?>\n";
const Z_SEITEN = ['heute', 'karte', 'loipen', 'gebiet', 'loipe', 'statistik', 'abdeckung', 'meine', 'sonst'];
const Z_MAX_BESUCHER_TAG = 100000;   // Obergrenze der Pruefwerte pro Tag (Schutz vor Flut)
const Z_BOTS = '/bot|crawl|spider|slurp|curl|wget|python|httpx|aiohttp|java\/|go-http|okhttp|libwww|headless|'
    . 'phantom|selenium|playwright|puppeteer|lighthouse|pagespeed|gtmetrix|pingdom|uptime|monitor|statuscake|'
    . 'preview|facebookexternalhit|whatsapp|telegram|discord|slack|embedly|scan|check|feed|fetch/i';
const Z_LOGIN_VERSUCHE = 5;          // falsche Passwoerter je Anschluss und Stunde
const Z_LOGIN_VERSUCHE_ALLE = 30;    // falsche Passwoerter insgesamt je Stunde
const Z_SITZUNG_S = 3600;            // so lange gilt die Anmeldung auf der Auswertungsseite

function z_einstellungen(): array
{
    static $e = null;
    if ($e === null) {
        $datei = __DIR__ . '/einstellungen.php';
        $e = is_file($datei) ? require $datei : [];
    }
    return $e;
}

function z_ziele(): array
{
    static $z = null;
    if ($z === null) {
        $datei = __DIR__ . '/ziele.php';
        $z = is_file($datei) ? require $datei : ['gebiete' => [], 'loipen' => []];
    }
    return $z;
}

function z_datenordner(): string
{
    $o = z_einstellungen()['datenordner'] ?? '';
    if ($o === '') {
        $o = __DIR__ . '/daten';
    } elseif ($o[0] !== '/') {
        $o = __DIR__ . '/' . $o;
    }
    if (!is_dir($o) && !@mkdir($o, 0700, true) && !is_dir($o)) {
        throw new RuntimeException('Datenordner des Zaehlers fehlt');
    }
    return $o;
}

function z_heute(?int $zeit = null): string
{
    $d = new DateTimeImmutable('@' . ($zeit ?? time()));
    return $d->setTimezone(new DateTimeZone('Europe/Berlin'))->format('Y-m-d');
}

/** JSON aus einer gesperrten Datei lesen. */
function z_lies(string $datei): ?array
{
    if (!is_file($datei)) {
        return null;
    }
    $roh = (string) file_get_contents($datei);
    if (str_starts_with($roh, Z_SPERRE)) {
        $roh = substr($roh, strlen(Z_SPERRE));
    }
    $d = json_decode($roh, true);
    return is_array($d) ? $d : null;
}

/** JSON in eine gesperrte Datei schreiben, per Umbenennen, damit nie eine halbe Datei entsteht. */
function z_schreibe(string $datei, array $daten): void
{
    $tmp = $datei . '.tmp' . bin2hex(random_bytes(4));
    file_put_contents($tmp, Z_SPERRE . json_encode($daten, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES | JSON_FORCE_OBJECT));
    @chmod($tmp, 0600);
    rename($tmp, $datei);
}

/** Fuehrt $f unter einer exklusiven Sperre aus, damit gleichzeitige Aufrufe nichts verlieren. */
function z_gesperrt(callable $f): mixed
{
    $sperre = fopen(z_datenordner() . '/.sperre', 'c');
    if ($sperre === false) {
        throw new RuntimeException('Sperre nicht moeglich');
    }
    try {
        flock($sperre, LOCK_EX);
        return $f();
    } finally {
        flock($sperre, LOCK_UN);
        fclose($sperre);
    }
}

function z_ist_bot(string $ua): bool
{
    return $ua === '' || strlen($ua) > 512 || preg_match(Z_BOTS, $ua) === 1;
}

/** Pruefwert des Besuchers fuer heute. Das Salz wechselt taeglich, alte Pruefwerte verfallen. */
function z_tagesdaten(string $heute): array
{
    $datei = z_datenordner() . '/heute.php';
    $d = z_lies($datei);
    if (!$d || ($d['tag'] ?? '') !== $heute) {
        $d = ['tag' => $heute, 'salz' => bin2hex(random_bytes(32)), 'besucher' => []];
    }
    return $d;
}

/**
 * Einen Aufruf zaehlen. $seite ist eine der Z_SEITEN, $gebiet ein Gebiets-Slug, $loipe eine Loipen-ID.
 * Unbekannte Werte werden verworfen, damit niemand beliebige Eintraege erzeugen kann.
 * Gibt true zurueck, wenn gezaehlt wurde.
 */
function z_zaehle(string $seite, string $gebiet, string $loipe, string $ip, string $ua, ?int $zeit = null): bool
{
    if (z_ist_bot($ua) || !in_array($seite, Z_SEITEN, true)) {
        return false;
    }
    $ziele = z_ziele();
    $gebiet = isset($ziele['gebiete'][$gebiet]) ? $gebiet : '';
    $loipe = isset($ziele['loipen'][$loipe]) ? $loipe : '';
    if ($loipe !== '' && $gebiet === '') {
        $gebiet = (string) ($ziele['loipen'][$loipe][1] ?? '');  // Loipenseite zaehlt auch fuer ihr Gebiet
    }
    $heute = z_heute($zeit);
    return z_gesperrt(function () use ($seite, $gebiet, $loipe, $ip, $ua, $heute) {
        $ordner = z_datenordner();
        $tag = z_tagesdaten($heute);
        $pruefwert = substr(hash_hmac('sha256', $ip . '|' . $ua, hex2bin($tag['salz'])), 0, 16);
        $neu = !isset($tag['besucher'][$pruefwert]);
        if ($neu && count($tag['besucher']) < Z_MAX_BESUCHER_TAG) {
            $tag['besucher'][$pruefwert] = 1;
        }
        z_schreibe($ordner . '/heute.php', $tag);

        $monat = $ordner . '/monat-' . substr($heute, 0, 7) . '.php';
        $m = z_lies($monat) ?? [];
        $t = $m[$heute] ?? ['aufrufe' => 0, 'besucher' => 0, 'seiten' => [], 'gebiete' => [], 'loipen' => []];
        $t['aufrufe']++;
        if ($neu) {
            $t['besucher']++;
        }
        $t['seiten'][$seite] = ($t['seiten'][$seite] ?? 0) + 1;
        if ($gebiet !== '') {
            $t['gebiete'][$gebiet] = ($t['gebiete'][$gebiet] ?? 0) + 1;
        }
        if ($loipe !== '') {
            $t['loipen'][$loipe] = ($t['loipen'][$loipe] ?? 0) + 1;
        }
        $m[$heute] = $t;
        ksort($m);
        z_schreibe($monat, $m);
        return true;
    });
}

/** Alle Monate mit Daten, neueste zuerst. */
function z_monate(): array
{
    $monate = [];
    foreach (glob(z_datenordner() . '/monat-*.php') ?: [] as $f) {
        if (preg_match('/monat-(\d{4}-\d{2})\.php$/', $f, $treffer)) {
            $monate[] = $treffer[1];
        }
    }
    rsort($monate);
    return $monate;
}

function z_monat(string $monat): array
{
    if (!preg_match('/^\d{4}-\d{2}$/', $monat)) {
        return [];
    }
    return z_lies(z_datenordner() . '/monat-' . $monat . '.php') ?? [];
}

/** Summen eines Monats: Aufrufe, Besucher (Summe der Tagesbesucher) und Ranglisten. */
function z_auswerten(array $tage): array
{
    $s = ['aufrufe' => 0, 'besucher' => 0, 'tage' => count($tage), 'seiten' => [], 'gebiete' => [], 'loipen' => []];
    foreach ($tage as $t) {
        $s['aufrufe'] += $t['aufrufe'] ?? 0;
        $s['besucher'] += $t['besucher'] ?? 0;
        foreach (['seiten', 'gebiete', 'loipen'] as $feld) {
            foreach ($t[$feld] ?? [] as $k => $n) {
                $s[$feld][$k] = ($s[$feld][$k] ?? 0) + $n;
            }
        }
    }
    foreach (['seiten', 'gebiete', 'loipen'] as $feld) {
        arsort($s[$feld]);
    }
    return $s;
}

/* ---------- Anmeldung fuer die Auswertung ---------- */

function z_geheimnis(): string
{
    $datei = z_datenordner() . '/geheimnis.php';
    if (!is_file($datei)) {
        $f = @fopen($datei, 'x');
        if ($f !== false) {
            fwrite($f, Z_SPERRE . bin2hex(random_bytes(32)) . "\n");
            fclose($f);
            @chmod($datei, 0600);
        }
    }
    $zeilen = file($datei, FILE_IGNORE_NEW_LINES) ?: [];
    $g = hex2bin(trim($zeilen[1] ?? ''));
    if ($g === false || strlen($g) !== 32) {
        throw new RuntimeException('Geheimnis des Zaehlers beschaedigt');
    }
    return $g;
}

function z_passwort_ok(string $passwort): bool
{
    $e = z_einstellungen();
    if (($e['passwort_pbkdf2'] ?? '') === '' || $passwort === '') {
        return false;
    }
    $h = hash_pbkdf2('sha256', $passwort, (string) $e['passwort_salz'], (int) $e['passwort_runden'], 64);
    return hash_equals((string) $e['passwort_pbkdf2'], $h);
}

/** Falsche Passwoerter begrenzen. true = noch erlaubt. $zaehlen = true traegt einen Fehlversuch ein. */
function z_login_erlaubt(string $ip, bool $zaehlen = false, ?int $zeit = null): bool
{
    $stunde = intdiv($zeit ?? time(), 3600);
    return z_gesperrt(function () use ($ip, $zaehlen, $stunde) {
        $datei = z_datenordner() . '/login.php';
        $d = z_lies($datei);
        if (!$d || ($d['stunde'] ?? 0) !== $stunde) {
            $d = ['stunde' => $stunde, 'alle' => 0, 'je' => []];
        }
        $k = substr(hash_hmac('sha256', $ip, z_geheimnis()), 0, 16);
        $ok = $d['alle'] < Z_LOGIN_VERSUCHE_ALLE && ($d['je'][$k] ?? 0) < Z_LOGIN_VERSUCHE;
        if ($zaehlen) {
            $d['alle']++;
            $d['je'][$k] = ($d['je'][$k] ?? 0) + 1;
            z_schreibe($datei, $d);
        }
        return $ok;
    });
}

/** Signierte Anmeldung fuer eine Stunde, steckt nur im Formular (kein Cookie). */
function z_sitzung(?int $zeit = null): string
{
    $bis = ($zeit ?? time()) + Z_SITZUNG_S;
    return $bis . '.' . hash_hmac('sha256', 'auswertung:' . $bis, z_geheimnis());
}

function z_sitzung_ok(string $s, ?int $zeit = null): bool
{
    $teile = explode('.', $s, 2);
    if (count($teile) !== 2 || !ctype_digit($teile[0]) || (int) $teile[0] < ($zeit ?? time())) {
        return false;
    }
    return hash_equals(hash_hmac('sha256', 'auswertung:' . $teile[0], z_geheimnis()), $teile[1]);
}

function z_h(string|int $s): string
{
    return htmlspecialchars((string) $s, ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8');
}
