<?php
/*
 * Abgleich mit dem NAS (N6). Das NAS ruft das Skript per HTTPS auf, nicht umgekehrt.
 *
 *   POST schluessel=<LOIPEN_ABO_SCHLUESSEL>               -> {"eintraege": [...], "anzahl": n}
 *   POST schluessel=<...>&quittung=<n>                    -> loescht die ersten n Eintraege
 *
 * Auf dem Webspace liegt nur der SHA-256-Wert des Schluessels (einstellungen.php).
 * Der Schluessel steht im POST-Rumpf, weil manche Webspaces den Authorization-Kopf nicht an PHP geben.
 */
declare(strict_types=1);
require __DIR__ . '/_kern.php';

header('Content-Type: application/json; charset=utf-8');
header('Cache-Control: no-store');
header('X-Robots-Tag: noindex');

function export_ende(int $code, array $daten): never
{
    http_response_code($code);
    echo json_encode($daten, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
    exit;
}

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    export_ende(405, ['fehler' => 'nur POST']);
}
$soll = (string)(abo_einstellungen()['schluessel_sha256'] ?? '');
$ist = hash('sha256', (string)($_POST['schluessel'] ?? ''));
if ($soll === '' || !hash_equals($soll, $ist)) {
    sleep(1);
    export_ende(403, ['fehler' => 'Schluessel falsch']);
}

if (isset($_POST['quittung'])) {
    $n = max(0, (int)$_POST['quittung']);
    $rest = abo_datei('warteschlange', function (array $zeilen) use ($n) {
        $rest = array_slice($zeilen, $n);
        return [$rest, count($rest)];
    });
    export_ende(200, ['geloescht' => $n, 'rest' => $rest]);
}

// "anzahl" zaehlt alle Zeilen, auch unlesbare, damit die Quittung genau diese Zeilen loescht.
[$eintraege, $anzahl] = abo_datei('warteschlange', function (array $zeilen) {
    $gelesen = array_values(array_filter(array_map(fn($z) => json_decode($z, true), $zeilen), 'is_array'));
    return [null, [$gelesen, count($zeilen)]];
});
export_ende(200, ['eintraege' => $eintraege, 'anzahl' => $anzahl]);
