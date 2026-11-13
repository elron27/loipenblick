<?php
/*
 * Abmelden vom E-Mail-Abo (N2). Geht nur mit ID und Token aus der Mail, nie mit der Adresse allein.
 * GET zeigt einen Knopf, POST meldet ab. Ein POST mit "List-Unsubscribe=One-Click" (RFC 8058)
 * kommt vom Mailprogramm und meldet direkt ab.
 */
declare(strict_types=1);
require __DIR__ . '/_kern.php';

$id = (string)($_GET['id'] ?? $_POST['id'] ?? '');
$t = (string)($_GET['t'] ?? $_POST['t'] ?? '');
if (!preg_match('/^[0-9a-f]{24}$/', $id) || !hash_equals(substr(abo_hmac('abmelden', $id), 0, 32), $t)) {
    abo_antwort(400, 'Link ungültig', 'Dieser Abmeldelink ist ungültig. Bitte nimm den Link aus der letzten Mail.');
}

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    abo_antwort(200, 'Abo beenden', 'Möchtest du keine E-Mails mehr von uns bekommen? Deine Adresse wird dann beim nächsten Lauf gelöscht.',
        '<form method="post"><input type="hidden" name="id" value="' . abo_h($id) . '">'
        . '<input type="hidden" name="t" value="' . abo_h($t) . '"><button type="submit">Abmelden</button></form>');
}

abo_warteschlange_anhaengen(['typ' => 'abgemeldet', 'id' => $id, 'zeit' => gmdate('c')]);
abo_antwort(200, 'Abgemeldet', 'Du bekommst keine E-Mails mehr. Deine Adresse wird beim nächsten Lauf gelöscht.');
