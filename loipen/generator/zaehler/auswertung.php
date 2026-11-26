<?php
/*
 * Private Auswertung des Besucherzaehlers (B13). Nur mit dem Passwort aus LOIPEN_ZAEHLER_PASSWORT.
 * Kein Cookie: Die Anmeldung steckt eine Stunde lang signiert im Formular.
 * Nach der Anmeldung nimmt auswertung.js diesen Browser von der Zaehlung aus.
 */
declare(strict_types=1);
require __DIR__ . '/_kern.php';

header('Cache-Control: no-store');
header('X-Robots-Tag: noindex, nofollow');
header('Referrer-Policy: no-referrer');

$e = z_einstellungen();
$ip = (string) ($_SERVER['REMOTE_ADDR'] ?? '');
$fehler = '';
$sitzung = '';
if (($e['passwort_pbkdf2'] ?? '') === '') {
    $fehler = 'Die Auswertung ist nicht eingerichtet: LOIPEN_ZAEHLER_PASSWORT fehlt in der .env auf dem NAS.';
} elseif (($_SERVER['REQUEST_METHOD'] ?? '') === 'POST') {
    if (z_sitzung_ok((string) ($_POST['sitzung'] ?? ''))) {
        $sitzung = (string) $_POST['sitzung'];
    } elseif (isset($_POST['passwort'])) {
        if (!z_login_erlaubt($ip)) {
            $fehler = 'Zu viele falsche Versuche. Bitte in einer Stunde noch einmal.';
        } elseif (z_passwort_ok((string) $_POST['passwort'])) {
            $sitzung = z_sitzung();
        } else {
            z_login_erlaubt($ip, true);
            $fehler = 'Das Passwort stimmt nicht.';
        }
    } else {
        $fehler = 'Die Anmeldung ist abgelaufen. Bitte neu anmelden.';
    }
}

$monate = $sitzung !== '' ? z_monate() : [];
$monat = (string) ($_POST['monat'] ?? '');
if (!in_array($monat, $monate, true)) {
    $monat = $monate[0] ?? substr(z_heute(), 0, 7);
}
$tage = $sitzung !== '' ? z_monat($monat) : [];
$s = z_auswerten($tage);
$ziele = z_ziele();
$seitennamen = ['heute' => 'Heute', 'karte' => 'Karte', 'loipen' => 'Loipenliste', 'gebiet' => 'Gebietsseiten',
    'loipe' => 'Loipenseiten', 'statistik' => 'Statistik', 'abdeckung' => 'Abdeckung', 'meine' => 'Meine Loipen',
    'sonst' => 'Sonstige'];
$monatsnamen = ['01' => 'Januar', '02' => 'Februar', '03' => 'März', '04' => 'April', '05' => 'Mai', '06' => 'Juni',
    '07' => 'Juli', '08' => 'August', '09' => 'September', '10' => 'Oktober', '11' => 'November', '12' => 'Dezember'];
$monatsname = fn(string $m) => ($monatsnamen[substr($m, 5, 2)] ?? '') . ' ' . substr($m, 0, 4);
$zahl = fn(int $n) => number_format($n, 0, ',', '.');

function z_rangliste(array $werte, callable $name, int $max = 10, string $spalte = 'Aufrufe'): string
{
    if (!$werte) {
        return '<p class="fine">Noch keine Aufrufe.</p>';
    }
    $h = '<div class="tabw"><table class="tab"><thead><tr><th>Name</th><th>' . z_h($spalte) . '</th></tr></thead><tbody>';
    foreach (array_slice($werte, 0, $max, true) as $k => $n) {
        $h .= '<tr><td>' . z_h($name((string) $k)) . '</td><td>' . number_format($n, 0, ',', '.') . '</td></tr>';
    }
    return $h . '</tbody></table></div>';
}
?>
<!doctype html>
<html lang="de">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="robots" content="noindex, nofollow">
<title>Besucherzähler · Loipenblick</title>
<link rel="icon" href="../icon-192.png" type="image/png">
<link rel="stylesheet" href="../app.css">
<style>
.zbar{display:block;height:8px;border-radius:4px;background:var(--cy);min-width:2px}
.zt td.bar{width:45%;text-align:left}
.anmeldung{display:grid;gap:12px;max-width:360px;padding:20px}
.monatwahl{display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin:12px 0}
.monatwahl select{min-height:44px;padding:0 12px;border-radius:12px;border:1px solid var(--line);background:var(--solid);color:var(--ink);font:inherit}
.dieser{padding:12px 14px;margin:16px 0}
.dieser button{margin-left:8px}
</style>
</head>
<body class="textseite">
<header class="top">
  <div class="wrap in">
    <a class="logo" href="../#/" aria-label="Loipenblick, Startseite"><i aria-hidden="true"><svg viewBox="0 0 24 24" fill="none" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="M3 18c4-9 6-9 9-3s6 3 9-8"/></svg></i><span>Loipenblick</span></a>
  </div>
</header>
<main id="view" class="wrap text">
<h1>Besucherzähler<?php if (empty($e['oeffentlich'])): ?> <span class="badge">Testseite</span><?php endif; ?></h1>
<?php if ($fehler !== ''): ?><p class="hinweis glass" id="fehler"><?= z_h($fehler) ?></p><?php endif; ?>
<?php if ($sitzung === ''): ?>
<?php if (($e['passwort_pbkdf2'] ?? '') !== ''): ?>
<form method="post" class="anmeldung glass" id="anmeldung">
  <label class="feld">Passwort<input type="password" name="passwort" autocomplete="current-password" required autofocus></label>
  <button class="btn prim" type="submit">Anmelden</button>
  <p class="fine">Das Passwort steht als LOIPEN_ZAEHLER_PASSWORT in der .env auf dem NAS.</p>
</form>
<?php endif; ?>
<?php else: ?>
<form method="post" class="monatwahl" id="monatwahl">
  <input type="hidden" name="sitzung" value="<?= z_h($sitzung) ?>">
  <label class="vh" for="monat">Monat</label>
  <select name="monat" id="monat">
<?php foreach ($monate ?: [$monat] as $m): ?>    <option value="<?= z_h($m) ?>"<?= $m === $monat ? ' selected' : '' ?>><?= z_h($monatsname($m)) ?></option>
<?php endforeach; ?>
  </select>
  <button class="btn" type="submit">Anzeigen</button>
</form>
<div class="stats" id="summen">
  <div class="stat glass"><b><?= $zahl($s['besucher']) ?></b><span>Besucher (Summe der Tage)</span></div>
  <div class="stat glass"><b><?= $zahl($s['aufrufe']) ?></b><span>Seitenaufrufe</span></div>
  <div class="stat glass"><b><?= $s['tage'] ? $zahl((int) round($s['besucher'] / $s['tage'])) : '0' ?></b><span>Besucher pro Tag im Schnitt</span></div>
</div>
<p class="fine">Gezählt wird ohne Cookies. Wer an zwei Tagen kommt, zählt zweimal, darum ist „Besucher“ die Summe der Tagesbesucher. Bots, automatische Browser und Browser, in denen du angemeldet warst, zählen nicht.</p>

<h2>Woher die Besucher kommen</h2>
<p class="fine">Gezählt wird beim ersten Aufruf, nur der Name der Seite, von der jemand kam. „direkt“ heißt: Adresse eingetippt, Lesezeichen, App vom Startbildschirm oder eine Seite, die die Herkunft nicht verrät.</p>
<?= z_rangliste($s['herkunft'], fn($k) => $k, 15, 'Einstiege') ?>

<h2>Geräte</h2>
<?= z_rangliste($s['geraete'], fn($k) => ['handy' => 'Handy', 'tablet' => 'Tablet', 'pc' => 'PC oder Laptop', 'app' => 'Als App installiert'][$k] ?? $k, 10, 'Einstiege') ?>

<h2>Meistgesehene Gebiete</h2>
<?= z_rangliste($s['gebiete'], fn($k) => (string) ($ziele['gebiete'][$k] ?? $k)) ?>

<h2>Meistgesehene Loipen</h2>
<?= z_rangliste($s['loipen'], fn($k) => isset($ziele['loipen'][$k]) ? $ziele['loipen'][$k][0] . ' (' . ($ziele['gebiete'][$ziele['loipen'][$k][1]] ?? $ziele['loipen'][$k][1]) . ')' : 'Loipe ' . $k) ?>

<h2>Seiten</h2>
<?= z_rangliste($s['seiten'], fn($k) => $seitennamen[$k] ?? $k, 20) ?>

<h2>Tage</h2>
<?php if (!$tage): ?><p class="fine">In diesem Monat wurde noch nichts gezählt.</p>
<?php else: $max = max(array_map(fn($t) => $t['besucher'] ?? 0, $tage)) ?: 1; ?>
<div class="tabw"><table class="tab zt" id="tage"><thead><tr><th>Tag</th><th>Besucher</th><th>Aufrufe</th><th class="vh">Verlauf</th></tr></thead><tbody>
<?php foreach (array_reverse($tage, true) as $tag => $t): ?>
<tr><td><?= z_h(substr($tag, 8, 2) . '.' . substr($tag, 5, 2) . '.') ?></td><td><?= $zahl($t['besucher'] ?? 0) ?></td><td><?= $zahl($t['aufrufe'] ?? 0) ?></td><td class="bar"><span class="zbar" style="width:<?= round(100 * ($t['besucher'] ?? 0) / $max) ?>%"></span></td></tr>
<?php endforeach; ?>
</tbody></table></div>
<?php endif; ?>
<?php endif; ?>
<p class="dieser glass" id="dieser" hidden data-angemeldet="<?= $sitzung !== '' ? '1' : '' ?>"><span id="dieser-text"></span><button class="btn" type="button" id="dieser-knopf"></button></p>
</main>
<script src="auswertung.js"></script>
</body>
</html>
