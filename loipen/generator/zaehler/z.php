<?php
/*
 * Nimmt einen Seitenaufruf von der App entgegen (navigator.sendBeacon) und zaehlt ihn (B13).
 * Antwortet immer mit 204 ohne Inhalt; setzt keine Cookies.
 */
declare(strict_types=1);
require __DIR__ . '/_kern.php';

header('Cache-Control: no-store');
http_response_code(204);
if (($_SERVER['REQUEST_METHOD'] ?? '') !== 'POST') {
    exit;
}
// Nur Aufrufe von der eigenen Seite (Browser schicken Sec-Fetch-Site mit)
$herkunft = $_SERVER['HTTP_SEC_FETCH_SITE'] ?? 'same-origin';
if ($herkunft !== 'same-origin') {
    exit;
}
try {
    z_zaehle(
        substr((string) ($_POST['s'] ?? ''), 0, 20),
        substr((string) ($_POST['g'] ?? ''), 0, 80),
        substr((string) ($_POST['l'] ?? ''), 0, 12),
        (string) ($_SERVER['REMOTE_ADDR'] ?? ''),
        (string) ($_SERVER['HTTP_USER_AGENT'] ?? '')
    );
} catch (Throwable $e) {
    error_log('Loipenblick-Zaehler: ' . $e->getMessage());
}
