<?php
/*
 * Falsche Angabe zu einer Loipe melden (N9). Die Meldung geht per Mail an den Betreiber der Seite
 * und ueber die Warteschlange als Push (ntfy) vom NAS. Sie aendert nie den angezeigten Status.
 * Gespeichert wird nur, was in der Warteschlange bis zur Abholung durch das NAS liegt.
 * Eine E-Mail-Adresse ist freiwillig und nur fuer Rueckfragen.
 */
declare(strict_types=1);
require __DIR__ . '/_kern.php';

const MELDE_ARTEN = [
    'offen' => 'Loipe ist in Wirklichkeit offen',
    'geschlossen' => 'Loipe ist in Wirklichkeit geschlossen',
    'nicht_gespurt' => 'Loipe ist nicht gespurt',
    'daten' => 'Länge, Lage oder andere Angaben stimmen nicht',
    'sonstiges' => 'Sonstiges',
];

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    header('Allow: POST');
    abo_antwort(405, 'Nur über das Formular', 'Bitte melde Fehler über den Knopf bei der Loipe.');
}
$e = abo_einstellungen();
$danke_titel = 'Danke für den Hinweis';
$danke_text = 'Wir prüfen die Meldung. Der angezeigte Status kommt weiter von der Quelle, bis sie ihn selbst ändert.';
if (trim((string)($_POST['webseite'] ?? '')) !== '') {
    abo_antwort(200, $danke_titel, $danke_text);
}

$ziel = (string)($_POST['ziel'] ?? '');
$bekannt = abo_ziele();
if (!str_starts_with($ziel, 'l:') || !isset($bekannt[$ziel])) {
    abo_antwort(400, 'Loipe unbekannt', 'Diese Loipe kennen wir nicht.');
}
$art = (string)($_POST['art'] ?? '');
if (!isset(MELDE_ARTEN[$art])) {
    abo_antwort(400, 'Was stimmt nicht?', 'Bitte wähle aus, was nicht stimmt.');
}
$text = trim(str_replace("\r", '', (string)($_POST['text'] ?? '')));
$text = mb_substr(preg_replace('/[^\P{C}\n]/u', '', $text) ?? '', 0, 500);
$kontakt = trim((string)($_POST['email'] ?? ''));
if ($kontakt !== '' && (strlen($kontakt) > 254 || filter_var($kontakt, FILTER_VALIDATE_EMAIL) === false || preg_match('/[\r\n,;]/', $kontakt))) {
    abo_antwort(400, 'Adresse prüfen', 'Die E-Mail-Adresse ist freiwillig, sieht aber nicht gültig aus.');
}
if (!abo_limit('melden', $_SERVER['REMOTE_ADDR'] ?? '', ABO_LIMIT_IP, 3600)) {
    abo_antwort(429, 'Zu viele Meldungen', 'Bitte versuche es in einer Stunde noch einmal.');
}

$eintrag = [
    'typ' => 'meldung',
    'ziel' => $ziel,
    'name' => $bekannt[$ziel],
    'art' => $art,
    'text' => $text,
    'kontakt' => $kontakt,
    'zeit' => gmdate('c'),
];
abo_warteschlange_anhaengen($eintrag);

$an = (string)($e['meldungen_an'] ?? '');
if ($an !== '') {
    $mail = "Neue Meldung auf {$e['seitenname']}\n\n"
        . "Loipe: {$bekannt[$ziel]} ({$ziel})\n"
        . 'Was: ' . MELDE_ARTEN[$art] . "\n"
        . ($text !== '' ? "Text:\n{$text}\n" : "Kein Text.\n")
        . ($kontakt !== '' ? "Rückfragen an: {$kontakt}\n" : "Keine Kontaktadresse angegeben.\n")
        . "\nDer Status auf der Seite ändert sich dadurch nicht.\n";
    $kopf = $kontakt !== '' ? ['Reply-To' => $kontakt] : [];
    abo_mail($an, "{$e['seitenname']}: Meldung zu {$bekannt[$ziel]}", $mail, $kopf);
}
abo_antwort(200, $danke_titel, $danke_text);
