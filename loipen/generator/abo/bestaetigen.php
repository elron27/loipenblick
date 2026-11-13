<?php
/*
 * Bestaetigung des E-Mail-Abos (Double-Opt-In, N2). Der Link zeigt zuerst nur einen Knopf, damit
 * Virenscanner, die Links in Mails vorab aufrufen, kein Abo bestaetigen. Erst das Absenden
 * (POST) traegt das Abo in die Warteschlange fuer das NAS ein.
 */
declare(strict_types=1);
require __DIR__ . '/_kern.php';

$token = (string)($_POST['t'] ?? $_GET['t'] ?? '');
$daten = $token !== '' && strlen($token) < 4096 ? abo_entsiegeln($token) : null;
if ($daten === null || !isset($daten['e'], $daten['z'], $daten['a'], $daten['t'])) {
    abo_antwort(400, 'Link ungültig', 'Dieser Bestätigungslink ist ungültig. Bitte melde dich noch einmal an.');
}
if (time() - (int)$daten['t'] > ABO_GUELTIG_S) {
    abo_antwort(410, 'Link abgelaufen', 'Der Bestätigungslink war 48 Stunden gültig und ist abgelaufen. Bitte melde dich noch einmal an.');
}

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    abo_antwort(200, 'Abo bestätigen', 'Bitte bestätige, dass du an ' . $daten['e'] . ' eine E-Mail bekommen möchtest, wenn sich bei diesen Loipen etwas tut (' . abo_arten_text($daten['a']) . '):',
        '<div class="feld">' . abo_ziel_liste($daten['z']) . '</div>'
        . '<form method="post"><input type="hidden" name="t" value="' . abo_h($token) . '"><button type="submit">Abo bestätigen</button></form>');
}

// Dieselbe Bestaetigung ergibt dieselbe ID: doppeltes Klicken legt kein zweites Abo an.
$id = substr(abo_hmac('id', $token), 0, 24);
abo_warteschlange_anhaengen([
    'typ' => 'bestaetigt',
    'id' => $id,
    'email' => $daten['e'],
    'ziele' => $daten['z'],
    'ereignisse' => $daten['a'],
    'angefragt' => gmdate('c', (int)$daten['t']),
    'bestaetigt' => gmdate('c'),
    'abmelden' => substr(abo_hmac('abmelden', $id), 0, 32),
]);
abo_antwort(200, 'Abo ist aktiv', 'Danke! Ab dem nächsten Lauf bekommst du eine E-Mail, sobald sich bei deinen Loipen etwas tut. In jeder Mail steht ein Link zum Abmelden.');
