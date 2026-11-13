<?php
/*
 * Anmeldung zum E-Mail-Abo (N5). Speichert nichts ausser kurzlebigen Zaehlern gegen Missbrauch (N8)
 * und schickt die Bestaetigungsmail (Double-Opt-In, N2).
 */
declare(strict_types=1);
require __DIR__ . '/_kern.php';

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    header('Allow: POST');
    abo_antwort(405, 'Nur über das Formular', 'Bitte melde dich über das Formular bei einer Loipe oder einem Gebiet an.');
}
abo_einstellungen();

// Honigtopf: Das Feld ist fuer Menschen unsichtbar. Bots fuellen es aus und bekommen dieselbe Antwort.
$erfolg_titel = 'Fast geschafft';
$erfolg_text = 'Wir haben dir eine E-Mail geschickt. Erst wenn du den Link darin öffnest, ist das Abo aktiv. Der Link gilt 48 Stunden.';
if (trim((string)($_POST['webseite'] ?? '')) !== '') {
    abo_antwort(200, $erfolg_titel, $erfolg_text);
}

$email = trim((string)($_POST['email'] ?? ''));
if (strlen($email) > 254 || filter_var($email, FILTER_VALIDATE_EMAIL) === false || preg_match('/[\r\n,;]/', $email)) {
    abo_antwort(400, 'Adresse prüfen', 'Das sieht nicht nach einer gültigen E-Mail-Adresse aus.');
}
if (($_POST['einwilligung'] ?? '') !== 'ja') {
    abo_antwort(400, 'Einwilligung fehlt', 'Bitte bestätige, dass wir dir die Benachrichtigungen schicken dürfen.');
}

$bekannt = abo_ziele();
$ziele = array_values(array_unique(array_filter((array)($_POST['ziel'] ?? []), 'is_string')));
$ziele = array_values(array_filter($ziele, fn($z) => isset($bekannt[$z])));
if (!$ziele || count($ziele) > ABO_MAX_ZIELE) {
    abo_antwort(400, 'Keine Loipe gewählt', 'Bitte wähle mindestens eine Loipe oder ein Gebiet.');
}
$arten = array_values(array_intersect(array_keys(ABO_ARTEN), (array)($_POST['ereignis'] ?? [])));
if (!$arten) {
    abo_antwort(400, 'Kein Ereignis gewählt', 'Bitte wähle, wann du eine Nachricht bekommen möchtest.');
}

$ip = $_SERVER['REMOTE_ADDR'] ?? '';
if (!abo_limit('ip', $ip, ABO_LIMIT_IP, 3600)) {
    abo_antwort(429, 'Zu viele Anfragen', 'Bitte versuche es in einer Stunde noch einmal.');
}
if (!abo_limit('mail', strtolower($email), ABO_LIMIT_MAIL, 86400)) {
    // Gleiche Antwort wie bei Erfolg: verraet nicht, ob die Adresse schon angefragt wurde.
    abo_antwort(200, $erfolg_titel, $erfolg_text);
}

$token = abo_versiegeln(['e' => $email, 'z' => $ziele, 'a' => $arten, 't' => time()]);
$link = abo_link('bestaetigen.php', ['t' => $token]);
$e = abo_einstellungen();
$namen = array_map(fn($z) => '- ' . $bekannt[$z], $ziele);
$text = "Hallo,\n\n"
    . "jemand, hoffentlich du, möchte unter dieser Adresse eine E-Mail von {$e['seitenname']} bekommen, "
    . "wenn sich bei diesen Loipen etwas tut:\n\n"
    . implode("\n", $namen) . "\n\n"
    . 'Benachrichtigen, wenn eine Loipe: ' . abo_arten_text($arten) . "\n\n"
    . "Zum Bestätigen bitte diesen Link öffnen (48 Stunden gültig):\n{$link}\n\n"
    . "Warst du das nicht? Dann ignoriere diese Mail einfach. Ohne Bestätigung speichern wir deine Adresse nicht.\n\n"
    . "Datenschutz: " . rtrim($e['seite_url'], '/') . '/' . ($e['datenschutz'] ?? 'datenschutz.html') . "\n";

if (!abo_mail($email, "{$e['seitenname']}: Bitte E-Mail-Abo bestätigen", $text)) {
    abo_antwort(500, 'Mail nicht verschickt', 'Die Bestätigungsmail konnte gerade nicht verschickt werden. Bitte später noch einmal versuchen.');
}
abo_antwort(200, $erfolg_titel, $erfolg_text);
