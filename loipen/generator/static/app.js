/* Loipenblick: statische Seite, liest nur die JSON-Dateien (B7). Kein Server, keine Datenbank. */
(function () {
"use strict";
var WORT = {offen: "Offen", eingeschraenkt: "Eingeschränkt", geschlossen: "Geschlossen", unbekannt: "Unbekannt"};
var SYM = {
  offen: '<path d="M20 6 9 17l-5-5"/>',
  eingeschraenkt: '<path d="M12 8v5M12 17h.01"/><circle cx="12" cy="12" r="9"/>',
  geschlossen: '<path d="M18 6 6 18M6 6l12 12"/>',
  unbekannt: '<path d="M9.5 9a2.5 2.5 0 1 1 3.5 2.3c-.7.4-1 1-1 1.7M12 17h.01"/>'
};
var FARBE = {offen: "#4ade80", eingeschraenkt: "#fbbf24", geschlossen: "#9fb3c2", unbekannt: "#c7d2da"};
var RANG = {offen: 0, eingeschraenkt: 1, unbekannt: 2, geschlossen: 3};
var TAGE = ["So", "Mo", "Di", "Mi", "Do", "Fr", "Sa"];
var S = {idx: null, regionen: {}, strecken: {}, gebiete: [], loipen: [], demo: false, ort: null, orte: []};
var view = document.getElementById("view");

function esc(s) { return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) { return {"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"}[c]; }); }
function safeUrl(u) { return /^https?:\/\//i.test(u || "") ? u : "#"; }
function zahl(x, n) { return x == null ? "unbekannt" : String(Number(x).toFixed(n == null ? 1 : n)).replace(".", ","); }
function km(x) { return x == null ? "Länge unbekannt" : zahl(x) + " km"; }
function chip(s) { return '<span class="st ' + s + '"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' + SYM[s] + "</svg>" + WORT[s] + "</span>"; }
function jetztMs() { return Date.now(); }
function alter(iso) {
  if (!iso) return "unbekannt";
  var min = Math.max(0, Math.round((jetztMs() - new Date(iso).getTime()) / 60000));
  if (min < 60) return "vor " + min + " Min.";
  if (min < 48 * 60) return "vor " + Math.round(min / 60) + " Std.";
  return "vor " + Math.round(min / 1440) + " Tagen";
}
function datum(iso) { if (!iso) return "unbekannt"; var d = new Date(iso); return d.toLocaleDateString("de-DE", {day: "2-digit", month: "2-digit", year: "numeric"}) + (iso.length > 10 ? ", " + d.toLocaleTimeString("de-DE", {hour: "2-digit", minute: "2-digit"}) + " Uhr" : ""); }
function dist(a, b) {
  if (!a || !b || a.lat == null || b.lat == null) return null;
  var r = Math.PI / 180, dl = (b.lat - a.lat) * r, dn = (b.lon - a.lon) * r;
  var h = Math.sin(dl / 2) * Math.sin(dl / 2) + Math.cos(a.lat * r) * Math.cos(b.lat * r) * Math.sin(dn / 2) * Math.sin(dn / 2);
  return 12742 * Math.asin(Math.sqrt(h));
}
function speicher(k, v) { try { if (v === undefined) return JSON.parse(localStorage.getItem(k)); localStorage.setItem(k, JSON.stringify(v)); } catch (e) { return null; } }
function navLink(lat, lon) { return "https://www.google.com/maps/dir/?api=1&destination=" + lat + "," + lon; }
function oevLink(lat, lon) { return "https://www.google.com/maps/dir/?api=1&destination=" + lat + "," + lon + "&travelmode=transit"; }

/* ---------- Daten laden ---------- */
function holeJson(url) { return fetch(url).then(function (r) { if (!r.ok) throw new Error(url + ": " + r.status); return r.json(); }); }
function mache(gebiete) {
  S.gebiete = []; S.loipen = [];
  gebiete.forEach(function (g) {
    S.gebiete.push(g);
    g.loipen.forEach(function (l) { l.gebiet = g; S.loipen.push(l); });
  });
}
function demoAnwenden() {
  S.loipen.forEach(function (l, i) {
    if (l.status === "geschlossen" || l.status === "unbekannt") {
      var r = (l.id * 7 + i) % 9;
      if (r < 2) { l.status = "offen"; l.gespurt_km = l.laenge_km; l.veraltet = false; l.abgerufen = new Date().toISOString(); l.quelle_stand = l.abgerufen; }
      else if (r === 2) { l.status = "eingeschraenkt"; l.veraltet = false; l.abgerufen = new Date().toISOString(); }
    }
  });
  S.gebiete.forEach(function (g) { g.schnee.schneehoehe_cm = 28; g.schnee.neuschnee_48h_cm = 6; g.schnee.neuschnee_24h_cm = 3; g.schnee.neuschnee_72h_cm = 9; g.schnee.station_name = g.schnee.station_name || "Beispiel"; });
}
function laden() {
  return holeJson("daten.json").then(function (idx) {
    S.idx = idx; S.orte = idx.orte || [];
    var jobs = idx.regionen.map(function (r) { return holeJson(r.datei); });
    return Promise.all(jobs);
  }).then(function (regs) {
    var alle = [];
    regs.forEach(function (r) { S.regionen[r.region.slug] = r; alle = alle.concat(r.gebiete); });
    mache(alle);
    var q = parseQuery(location.hash);
    try { if (q.demo === "1") sessionStorage.setItem("demo", "1"); if (q.demo === "0") sessionStorage.removeItem("demo"); S.demo = sessionStorage.getItem("demo") === "1"; } catch (e) { S.demo = q.demo === "1"; }
    if (S.demo) demoAnwenden();
    S.ort = ortAusName(q.ort) || speicher("ort") || ortAusName(S.idx.standardort) || (S.gebiete[0] && {name: S.gebiete[0].name, lat: S.gebiete[0].lat, lon: S.gebiete[0].lon});
  });
}
function ladeStrecken() {
  var offen = S.idx.regionen.filter(function (r) { return !S.strecken[r.slug]; });
  return Promise.all(offen.map(function (r) { return holeJson(r.strecken).then(function (s) { S.strecken[r.slug] = s; }); }));
}
function ortAusName(n) {
  if (!n) return null;
  var k = n.toLowerCase(), t = null;
  S.orte.forEach(function (o) { if (o.name.toLowerCase() === k) t = o; });
  S.gebiete.forEach(function (g) { if (!t && g.name.toLowerCase() === k && g.lat != null) t = {name: g.name, lat: g.lat, lon: g.lon}; });
  return t;
}

/* ---------- Filter, Sortierung, URL (U2, U3, U4, U24) ---------- */
function parseQuery(h) {
  var i = h.indexOf("?"), q = {};
  if (i < 0) return q;
  h.slice(i + 1).split("&").forEach(function (p) { var kv = p.split("="); if (kv[0]) q[decodeURIComponent(kv[0])] = decodeURIComponent((kv[1] || "").replace(/\+/g, " ")); });
  return q;
}
function pfad(h) { var p = h.replace(/^#/, ""); var i = p.indexOf("?"); return i < 0 ? p : p.slice(0, i); }
function queryStr(q) { var t = []; Object.keys(q).forEach(function (k) { if (q[k] !== "" && q[k] != null) t.push(encodeURIComponent(k) + "=" + encodeURIComponent(q[k])); }); return t.length ? "?" + t.join("&") : ""; }
function ortFuer(q) { return ortAusName(q.ort) || S.ort; }
function filtere(q) {
  var o = ortFuer(q), max = q.max ? parseFloat(q.max.replace(",", ".")) : null, r = q.r ? parseFloat(q.r) : null;
  var liste = S.loipen.filter(function (l) {
    if (q.offen === "1" && !(l.status === "offen" || l.status === "eingeschraenkt")) return false;
    if (q.technik === "klassisch" && l.technik === "skating") return false;
    if (q.technik === "skating" && l.technik === "klassisch") return false;
    if (q.leicht === "1" && l.schwierigkeit !== "leicht") return false;
    if (q.rund === "1" && l.rundkurs !== true) return false;
    if (q.nacht === "1" && l.nachtloipe !== true) return false;
    if (max != null && !(l.laenge_km != null && l.laenge_km <= max)) return false;
    if (q.region && l.gebiet.region !== q.region) return false;
    if (q.gebiet && l.gebiet.slug !== q.gebiet) return false;
    if (q.text && l.name.toLowerCase().indexOf(q.text.toLowerCase()) < 0) return false;
    return true;
  });
  liste.forEach(function (l) { l.entf = dist(o, l.lat != null ? l : l.gebiet); });
  if (r != null) liste = liste.filter(function (l) { return l.entf != null && l.entf <= r; });
  var sort = q.sort || "status";
  liste.sort(function (a, b) {
    if (sort === "entfernung") return (a.entf == null) - (b.entf == null) || a.entf - b.entf;
    if (sort === "gespurt") return (b.gespurt_km || 0) - (a.gespurt_km || 0);
    if (sort === "praeparierung") return (b.quelle_stand || "").localeCompare(a.quelle_stand || "");
    return RANG[a.status] - RANG[b.status] || (a.entf == null) - (b.entf == null) || a.entf - b.entf || a.name.localeCompare(b.name);
  });
  return liste;
}
function go(q, basis) { location.hash = "#" + (basis || "/loipen") + queryStr(q); }

/* ---------- Bausteine ---------- */
function loipeKarte(l, mitGebiet) {
  var teile = [km(l.laenge_km), l.schwierigkeit !== "unbekannt" ? l.schwierigkeit : null, l.technik === "beides" ? "klassisch und Skating" : (l.technik !== "unbekannt" ? l.technik : null), l.nachtloipe ? "Flutlicht" : null, l.gespurt_km != null && l.gespurt_km > 0 ? "gespurt " + zahl(l.gespurt_km) + " km" : null];
  if (l.entf != null) teile.unshift(zahl(l.entf, 0) + " km entfernt");
  var frisch = l.veraltet ? '<span class="badge">veraltet</span> ' : "";
  var stand = l.abgerufen ? "Stand " + alter(l.abgerufen) : "noch kein Abruf";
  return '<a class="lp glass" href="#/loipe/' + l.id + '"><span class="n">' + esc(l.name) + (mitGebiet ? ' <span class="fine">· ' + esc(l.gebiet.name) + "</span>" : "") + "</span>" + chip(l.status) +
    '<span class="d">' + esc(teile.filter(Boolean).join(" · ")) + " · " + frisch + esc(stand) + (l.quelle_fehler ? " · letzter Abruf fehlgeschlagen" : "") + "</span></a>";
}
function neuschneeBadge(g) { return g.schnee && g.schnee.neuschnee_48h_cm >= 1 ? ' <span class="badge neu">Neuschnee ' + zahl(g.schnee.neuschnee_48h_cm, 0) + " cm in 48 h</span>" : ""; }
function istWochenende(iso) { var d = new Date(iso + "T12:00:00").getDay(); return d === 0 || d === 6; }
function vorhersageHtml(g) {
  var v = g.vorhersage || [];
  if (!v.length) return '<p class="fine">Noch keine Vorhersage.</p>';
  return '<p class="fine">Vorhersage (keine Messung), Quelle Bright Sky mit Daten des Deutschen Wetterdienstes</p><div class="wx">' + v.map(function (t) {
    var d = new Date(t.datum + "T12:00:00");
    return '<div class="' + (istWochenende(t.datum) ? "we" : "") + '"><b>' + TAGE[d.getDay()] + " " + d.getDate() + "." + (d.getMonth() + 1) + ".</b><span>" + (t.tmin == null ? "–" : Math.round(t.tmin)) + " / " + (t.tmax == null ? "–" : Math.round(t.tmax)) + " °C</span><small class=\"fine\">" + (t.niederschlag_mm == null ? "" : zahl(t.niederschlag_mm) + " mm") + "</small></div>";
  }).join("") + "</div>";
}
function schneeHtml(g) {
  var s = g.schnee || {};
  if (s.messtag == null) return '<p class="fine">Noch keine Messwerte für dieses Gebiet.</p>';
  return '<div class="kv"><div class="glass"><small>Schneehöhe</small><b>' + (s.schneehoehe_cm == null ? "unbekannt" : zahl(s.schneehoehe_cm, 0) + " cm") + "</b></div>" +
    ["24", "48", "72"].map(function (h) { var x = s["neuschnee_" + h + "h_cm"]; return '<div class="glass"><small>Neuschnee ' + h + " h</small><b>" + (x == null ? "unbekannt" : zahl(x, 0) + " cm") + "</b></div>"; }).join("") +
    '</div><p class="fine">Gemessen am ' + esc(datum(s.messtag)) + " an der Station " + esc(s.station_name || s.station_id || "unbekannt") + ", Quelle " + esc(s.quelle || "unbekannt") + ".</p>";
}
function nahesterOrt() { return S.ort; }

/* ---------- Talprofil ---------- */
function ridge(x) { return 235 - 38 * Math.sin(x / 70) - 26 * Math.sin(x / 31 + 1) - 14 * Math.sin(x / 13 + 2) + (x > 600 ? -18 * Math.sin((x - 600) / 90) : 0); }
function far(x) { return 190 - 45 * Math.sin(x / 95 + 2) - 24 * Math.sin(x / 37); }
function talprofil(gebiete, schnee) {
  var sorted = gebiete.filter(function (g) { return g.lon != null; }).sort(function (a, b) { return a.lon - b.lon; });
  if (!sorted.length) return "";
  var min = sorted[0].lon, max = sorted[sorted.length - 1].lon, span = Math.max(max - min, 0.05), s = "";
  s += '<defs><linearGradient id="rg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="var(--ridge1)"/><stop offset="1" stop-color="var(--ridge2)"/></linearGradient></defs>';
  var f = "M0 340"; for (var x = 0; x <= 900; x += 10) f += "L" + x + " " + far(x); s += '<path class="s-far" d="' + f + 'L900 340Z" opacity=".85"/>';
  var q = "M0 340", rim = "M0 " + ridge(0); for (x = 0; x <= 900; x += 6) { q += "L" + x + " " + ridge(x); rim += "L" + x + " " + ridge(x); }
  s += '<path class="s-ridge" d="' + q + 'L900 340Z"/><path class="s-rim" d="' + rim + '"/>';
  sorted.forEach(function (g, i) {
    var px = sorted.length === 1 ? 450 : 60 + i * (780 / (sorted.length - 1)), y = ridge(px);
    var best = g.loipen.reduce(function (a, l) { return RANG[l.status] < RANG[a] ? l.status : a; }, "geschlossen");
    s += '<a href="#/gebiet/' + esc(g.slug) + '"><line class="s-l" x1="' + px + '" y1="' + y + '" x2="' + px + '" y2="' + (y - 40) + '" stroke-width="1.5"/><circle cx="' + px + '" cy="' + (y - 44) + '" r="10" fill="' + FARBE[best] + '" stroke="var(--ink)" stroke-width="2"/><text class="s-t" x="' + px + '" y="' + (y - 64 - (i % 3) * 22) + '" text-anchor="middle">' + esc(g.name) + "</text><title>" + esc(g.name) + ": " + WORT[best] + "</title></a>";
  });
  return '<div class="scr"><svg viewBox="0 0 900 340" preserveAspectRatio="xMidYMax meet" role="img" aria-label="Talprofil mit den Loipengebieten von West nach Ost">' + s + "</svg></div>";
}

/* ---------- Seiten ---------- */
function seiteHeute(q) {
  var o = S.ort, nah = S.gebiete.slice().sort(function (a, b) { return (dist(o, a) == null) - (dist(o, b) == null) || dist(o, a) - dist(o, b); });
  var zeig = nah.slice(0, 10);
  var offene = S.loipen.filter(function (l) { return l.status === "offen" || l.status === "eingeschraenkt"; });
  offene.forEach(function (l) { l.entf = dist(o, l.lat != null ? l : l.gebiet); });
  offene.sort(function (a, b) { return RANG[a.status] - RANG[b.status] || (a.entf || 1e9) - (b.entf || 1e9); });
  var reco = offene[0], kz = S.idx.kennzahlen;
  var fehler = S.idx.quellen.filter(function (x) { return x.status === "fehler"; }).length;
  var h = (S.demo ? '<p class="demo">Vorschau mit Beispielwerten, keine echten Daten.</p>' : "") +
    '<section class="sky"><div class="herotxt"><div class="eyebrow">' + esc(new Date().toLocaleDateString("de-DE", {weekday: "long", day: "numeric", month: "long"})) + " · " + esc(o ? o.name : "") + "</div><h1>" +
    (reco ? "Heute lohnt sich <em>" + esc(reco.name) + "</em>" : "Heute keine <em>offene Loipe</em>") + "</h1><p>" +
    (reco ? esc(km(reco.laenge_km) + (reco.entf != null ? ", " + zahl(reco.entf, 0) + " km von " + o.name : "") + ", Stand " + alter(reco.abgerufen)) : "Alle Quellen melden die Loipen als geschlossen oder ohne Angabe. Wir prüfen in der Saison dreimal täglich.") +
    "</p></div>" + talprofil(zeig) + "</section>" +
    '<div class="cols" style="margin-top:14px"><div class="reco glass"><h2>Heute in deiner Nähe</h2><div class="big">' + (reco ? esc(reco.name) : "Heute keine offene Loipe") + "</div><p>" +
    (reco ? esc(reco.gebiet.name) + " · " + WORT[reco.status] : "Wir sagen es dir hier, sobald etwas gespurt ist.") + '</p><div class="facts">' +
    (nah[0] && nah[0].schnee && nah[0].schnee.schneehoehe_cm != null ? '<span class="chip">Schnee ' + esc(nah[0].name) + ": " + zahl(nah[0].schnee.schneehoehe_cm, 0) + " cm</span>" : '<span class="chip">Schneehöhe: noch keine Messung</span>') +
    (reco ? '<a class="btn prim" href="#/loipe/' + reco.id + '">Zur Loipe</a>' : "") + "</div></div>" +
    '<div class="stats"><div class="stat glass"><b>' + (kz.offen + kz.eingeschraenkt) + "</b><span>befahrbar</span></div><div class=\"stat glass\"><b>" + kz.loipen + "</b><span>Loipen im Blick</span></div><div class=\"stat glass\"><b>" + (S.idx.quellen.length - fehler) + "/" + S.idx.quellen.length + "</b><span>Quellen ohne Fehler</span></div></div></div>";
  if (nah[0] && nah[0].vorhersage.length) h += '<h2 class="sec">Ausblick für ' + esc(nah[0].name) + "</h2>" + vorhersageHtml(nah[0]);
  h += '<h2 class="sec">Gebiete in deiner Nähe</h2><div class="cards">' + zeig.map(function (g) {
    var best = g.loipen.slice().sort(function (a, b) { return RANG[a.status] - RANG[b.status]; }).slice(0, 3);
    var d = dist(o, g);
    return '<a class="gc glass" href="#/gebiet/' + esc(g.slug) + '"><h3>' + esc(g.name) + neuschneeBadge(g) + "</h3><p>" + (d != null ? zahl(d, 0) + " km entfernt · " : "") + g.loipen.length + " Loipen</p>" + best.map(function (l) { return '<div class="r"><span>' + esc(l.name) + "</span>" + chip(l.status) + "</div>"; }).join("") + "</a>";
  }).join("") + '</div><p><a class="btn" href="#/loipen">Alle ' + kz.loipen + " Loipen ansehen</a></p>";
  view.innerHTML = h;
}

function filterLeiste(q, basis) {
  function tog(k, v, text) { var an = q[k] === v; return '<button type="button" class="tog" data-k="' + k + '" data-v="' + (an ? "" : v) + '" aria-pressed="' + an + '">' + text + "</button>"; }
  var regs = S.idx.regionen.map(function (r) { return '<option value="' + esc(r.slug) + '"' + (q.region === r.slug ? " selected" : "") + ">" + esc(r.name) + "</option>"; }).join("");
  return '<div class="filter" role="group" aria-label="Filter">' + tog("offen", "1", "Nur offene") + tog("technik", "klassisch", "Klassisch") + tog("technik", "skating", "Skating") + tog("leicht", "1", "Leicht") + tog("rund", "1", "Rundkurs") + tog("nacht", "1", "Nachtloipe") +
    '<label class="vh" for="f-max">Höchstlänge in km</label><input id="f-max" type="number" inputmode="decimal" min="0" step="0.5" placeholder="max. km" value="' + esc(q.max || "") + '">' +
    '<label class="vh" for="f-r">Umkreis</label><select id="f-r"><option value="">Umkreis: alle</option>' + [10, 25, 50, 100].map(function (r) { return '<option value="' + r + '"' + (q.r == r ? " selected" : "") + ">bis " + r + " km</option>"; }).join("") + "</select>" +
    '<label class="vh" for="f-reg">Region</label><select id="f-reg"><option value="">Alle Regionen</option>' + regs + "</select>" +
    '<label class="vh" for="f-sort">Sortierung</label><select id="f-sort">' + [["status", "Status"], ["entfernung", "Entfernung"], ["gespurt", "Gespurte km"], ["praeparierung", "Letzte Präparierung"]].map(function (s) { return '<option value="' + s[0] + '"' + ((q.sort || "status") === s[0] ? " selected" : "") + ">Sortiert nach " + s[1] + "</option>"; }).join("") + "</select>" +
    '<button type="button" class="btn" id="teilen">Teilen</button></div>';
}
function filterBinden(q, basis) {
  view.querySelectorAll(".tog").forEach(function (b) { b.addEventListener("click", function () { var n = Object.assign({}, q); n[b.dataset.k] = b.dataset.v; go(n, basis); }); });
  function sel(id, k) { var e = document.getElementById(id); if (e) e.addEventListener("change", function () { var n = Object.assign({}, q); n[k] = e.value; go(n, basis); }); }
  sel("f-max", "max"); sel("f-r", "r"); sel("f-reg", "region"); sel("f-sort", "sort");
  var t = document.getElementById("teilen");
  if (t) t.addEventListener("click", function () {
    var url = location.href;
    if (navigator.share) navigator.share({title: "Loipenblick", url: url}).catch(function () {});
    else if (navigator.clipboard) navigator.clipboard.writeText(url).then(function () { t.textContent = "Link kopiert"; });
  });
}
function seiteListe(q) {
  var o = ortFuer(q), liste = filtere(q);
  if (q.ort && !q.sort) q.sort = "entfernung";
  var h = (S.demo ? '<p class="demo">Vorschau mit Beispielwerten, keine echten Daten.</p>' : "") + "<h1>Loipen" + (q.r ? " im Umkreis von " + esc(q.r) + " km um " + esc(o ? o.name : "") : "") + '</h1><p class="fine">' + liste.length + " von " + S.loipen.length + " Loipen" + (o ? ", Entfernung von " + esc(o.name) : "") + "</p>" + filterLeiste(q, "/loipen");
  h += liste.length ? '<div class="lg">' + liste.map(function (l) { return loipeKarte(l, true); }).join("") + "</div>" : '<p class="leer glass">Keine Loipe passt zu diesen Filtern. Lockere einen Filter oder vergrößere den Umkreis.</p>';
  view.innerHTML = h; filterBinden(q, "/loipen");
}

function seiteGebiet(slug) {
  var g = S.gebiete.filter(function (x) { return x.slug === slug; })[0];
  if (!g) { view.innerHTML = '<p class="leer glass">Dieses Gebiet gibt es nicht. <a href="#/loipen">Zur Liste</a></p>'; return; }
  var gesamt = g.loipen.reduce(function (a, l) { return a + (l.laenge_km || 0); }, 0);
  var gebuehr = g.loipengebuehr || {};
  var h = "<h1>" + esc(g.name) + neuschneeBadge(g) + '</h1><p class="fine">' + g.loipen.length + " Loipen, zusammen " + zahl(gesamt) + " km · <a href=\"" + esc(safeUrl(g.tourist_url)) + '" rel="noopener">Touristeninformation</a></p>' +
    '<h2 class="sec">Schnee</h2>' + schneeHtml(g) + '<h2 class="sec">Vorhersage</h2>' + vorhersageHtml(g) +
    '<h2 class="sec">Anreise</h2><ul class="plain">' +
    '<li class="glass"><span>Loipengebühr</span><b>' + (gebuehr.text ? esc(gebuehr.text) : gebuehr.eur != null ? zahl(gebuehr.eur, 2) + " €" : "unbekannt") + "</b></li>" +
    (g.parkplaetze.length ? g.parkplaetze.map(function (p) { return '<li class="glass"><span><b>' + esc(p.name) + "</b><br><span class=\"fine\">Gebühr: " + esc(p.gebuehr_text || (p.gebuehr_eur_tag != null ? zahl(p.gebuehr_eur_tag, 2) + " € pro Tag" : "unbekannt")) + (p.geschaetzt ? " · Lage ungefähr (Loipenstart)" : "") + '</span></span><a class="btn" href="' + esc(navLink(p.lat, p.lon)) + '" rel="noopener">Navigation</a></li>'; }).join("") : '<li class="glass"><span>Parkplätze</span><b>noch nicht erfasst</b></li>') +
    (g.haltestellen.length ? g.haltestellen.map(function (s) { return '<li class="glass"><span><b>' + esc(s.name) + '</b><br><span class="fine">Haltestelle (' + esc(s.art || "ÖPNV") + ')</span></span><a class="btn" href="' + esc(oevLink(s.lat, s.lon)) + '" rel="noopener">Fahrplan</a></li>'; }).join("") : '<li class="glass"><span>Haltestelle</span><b>keine bekannt</b></li>') +
    '</ul><h2 class="sec">Loipen</h2><div class="lg">' + g.loipen.map(function (l) { l.entf = dist(S.ort, l.lat != null ? l : g); return loipeKarte(l, false); }).join("") + "</div>";
  view.innerHTML = h;
}

function miniKarte(l) {
  var reg = l.gebiet.region, pts = ((S.strecken[reg] || {})[String(l.id)] || []);
  if (!pts.length && l.lat != null) pts = [[l.lat, l.lon]];
  if (!pts.length) return "";
  var la = pts.map(function (p) { return p[0]; }), lo = pts.map(function (p) { return p[1]; });
  var k = Math.cos(la[0] * Math.PI / 180), w = 320, hgt = 200, mnx = Math.min.apply(0, lo), mxx = Math.max.apply(0, lo), mny = Math.min.apply(0, la), mxy = Math.max.apply(0, la);
  var sc = Math.min((w - 40) / Math.max((mxx - mnx) * k, 1e-4), (hgt - 40) / Math.max(mxy - mny, 1e-4)); if (pts.length === 1) sc = 4000;
  function P(p) { return [(w / 2 + ((p[1] - (mnx + mxx) / 2) * k) * sc).toFixed(1), (hgt / 2 - (p[0] - (mny + mxy) / 2) * sc).toFixed(1)]; }
  var line = pts.map(function (p) { return P(p).join(","); }).join(" "), a = P(pts[0]);
  return '<svg viewBox="0 0 ' + w + " " + hgt + '" role="img" aria-label="Mini-Karte der Loipe" style="width:100%;max-width:520px;border-radius:18px;border:1px solid var(--line);background:var(--unk-bg)">' + (pts.length > 1 ? '<polyline class="tr" points="' + line + '" stroke="' + FARBE[l.status] + '" stroke-width="4"/>' : "") + '<circle cx="' + a[0] + '" cy="' + a[1] + '" r="8" fill="' + FARBE[l.status] + '" stroke="var(--ink)" stroke-width="2"/></svg>';
}
function seiteLoipe(id) {
  var l = S.loipen.filter(function (x) { return String(x.id) === id; })[0];
  if (!l) { view.innerHTML = '<p class="leer glass">Diese Loipe gibt es nicht. <a href="#/loipen">Zur Liste</a></p>'; return; }
  ladeStrecken().then(function () {
    var g = l.gebiet, ziel = g.parkplaetze[0] || (l.lat != null ? {lat: l.lat, lon: l.lon, name: "Start der Loipe"} : null);
    var hist = l.historie.map(function (t) { return '<span class="' + (t.status ? "" : "keine ") + '" style="' + (t.status ? "background:var(--" + ({offen: "ok", eingeschraenkt: "mid", geschlossen: "bad", unbekannt: "unk"}[t.status]) + "-bg);color:var(--" + ({offen: "ok", eingeschraenkt: "mid", geschlossen: "bad", unbekannt: "unk"}[t.status]) + ')"' : "") + ' title="' + esc(t.tag + ": " + (t.status ? WORT[t.status] : "noch keine Daten")) + '">' + (t.status ? {offen: "✓", eingeschraenkt: "!", geschlossen: "✕", unbekannt: "?"}[t.status] : "·") + "</span>"; }).join("");
    view.innerHTML = '<p><a href="#/gebiet/' + esc(g.slug) + '">← ' + esc(g.name) + "</a></p><h1>" + esc(l.name) + "</h1><p>" + chip(l.status) + (l.veraltet ? ' <span class="badge">veraltet</span>' : "") + (l.quelle_fehler ? ' <span class="badge">letzter Abruf fehlgeschlagen</span>' : "") + "</p>" +
      '<div class="kv"><div class="glass"><small>Länge</small><b>' + km(l.laenge_km) + '</b></div><div class="glass"><small>Gespurt</small><b>' + (l.gespurt_km == null ? "unbekannt" : zahl(l.gespurt_km) + " km") + '</b></div><div class="glass"><small>Klassisch</small><b>' + (l.status_klassisch ? WORT[l.status_klassisch] : "keine Angabe") + '</b></div><div class="glass"><small>Skating</small><b>' + (l.status_skating ? WORT[l.status_skating] : "keine Angabe") + '</b></div><div class="glass"><small>Schwierigkeit</small><b>' + esc(l.schwierigkeit) + '</b></div><div class="glass"><small>Technik</small><b>' + esc(l.technik) + '</b></div><div class="glass"><small>Rundkurs</small><b>' + (l.rundkurs == null ? "unbekannt" : l.rundkurs ? "ja" : "nein") + '</b></div><div class="glass"><small>Flutlicht</small><b>' + (l.nachtloipe == null ? "unbekannt" : l.nachtloipe ? "ja" : "nein") + "</b></div></div>" +
      miniKarte(l) + '<h2 class="sec">Letzte 14 Tage</h2><div class="hist" role="img" aria-label="Status der letzten 14 Tage">' + hist + "</div>" +
      '<h2 class="sec">Quelle und Stand</h2><ul class="plain"><li class="glass"><span>Quelle</span><a href="' + esc(safeUrl(l.quelle.url)) + '" rel="noopener">' + esc(l.quelle.name) + "</a></li><li class=\"glass\"><span>Stand laut Quelle</span><b>" + esc(l.quelle_stand ? datum(l.quelle_stand) : "nicht angegeben") + '</b></li><li class="glass"><span>Zuletzt von uns geprüft</span><b>' + esc(l.abgerufen ? datum(l.abgerufen) + " (" + alter(l.abgerufen) + ")" : "noch nie") + "</b></li></ul>" +
      (ziel ? '<p style="margin-top:18px"><a class="btn prim" href="' + esc(navLink(ziel.lat, ziel.lon)) + '" rel="noopener">Navigation zu ' + esc(ziel.name) + "</a></p>" : "");
  });
}

/* ---------- Karte (U1) ---------- */
var MV = {cx: 0, cy: 0, sc: 1};
function seiteKarte(q) {
  ladeStrecken().then(function () {
    var liste = filtere(q).filter(function (l) { return l.lat != null; });
    view.innerHTML = (S.demo ? '<p class="demo">Vorschau mit Beispielwerten, keine echten Daten.</p>' : "") + filterLeiste(q, "/karte") + '<div class="mapw" id="mapw"><svg id="map" role="img" aria-label="Karte der Loipen"></svg><div class="zoom"><button type="button" id="zi" aria-label="Hineinzoomen">+</button><button type="button" id="zo" aria-label="Herauszoomen">−</button><button type="button" id="zf" aria-label="Alles zeigen">⌖</button></div><div class="sel glass" id="sel"><span class="fine">Tippe auf einen Marker oder eine Strecke. ' + liste.length + " Loipen mit Standort.</span></div></div>";
    filterBinden(q, "/karte");
    var el = document.getElementById("mapw"), svg = document.getElementById("map");
    var k = Math.cos(47.7 * Math.PI / 180);
    var pts = liste.map(function (l) { return {l: l, x: l.lon * k, y: -l.lat}; });
    function fit() {
      if (!pts.length) { MV = {cx: 0, cy: 0, sc: 1000}; return; }
      var xs = pts.map(function (p) { return p.x; }), ys = pts.map(function (p) { return p.y; });
      var mnx = Math.min.apply(0, xs), mxx = Math.max.apply(0, xs), mny = Math.min.apply(0, ys), mxy = Math.max.apply(0, ys);
      MV = {cx: (mnx + mxx) / 2, cy: (mny + mxy) / 2, sc: Math.min((el.clientWidth - 90) / Math.max(mxx - mnx, 0.01), (el.clientHeight - 110) / Math.max(mxy - mny, 0.01))};
    }
    function sx(x) { return el.clientWidth / 2 + (x - MV.cx) * MV.sc; }
    function sy(y) { return el.clientHeight / 2 + (y - MV.cy) * MV.sc; }
    function draw() {
      var W = el.clientWidth, H = el.clientHeight, out = "";
      svg.setAttribute("viewBox", "0 0 " + W + " " + H);
      for (var i = 1; i <= 7; i++) out += '<ellipse class="topo" cx="' + (W * .35) + '" cy="' + (H * .45) + '" rx="' + (i * W * .08) + '" ry="' + (i * H * .07) + '"/>';
      // Strecken
      var ids = {}; liste.forEach(function (l) { ids[l.id] = l; });
      S.idx.regionen.forEach(function (r) {
        var st = S.strecken[r.slug] || {};
        Object.keys(st).forEach(function (id) {
          var l = ids[id]; if (!l) return;
          var p = st[id].map(function (c) { return sx(c[1] * k).toFixed(1) + "," + sy(-c[0]).toFixed(1); }).join(" ");
          out += '<polyline class="tr" points="' + p + '" stroke="' + FARBE[l.status] + '" stroke-width="' + (l.status === "geschlossen" ? 2 : 4) + '" opacity="' + (l.status === "geschlossen" ? .55 : 1) + '"/>';
        });
      });
      // Marker, nahe beieinander liegende gebuendelt (Raster 46 px)
      var zellen = {};
      pts.forEach(function (p) { var gx = Math.floor(sx(p.x) / 46), gy = Math.floor(sy(p.y) / 46), key = gx + ":" + gy; (zellen[key] = zellen[key] || []).push(p); });
      Object.keys(zellen).forEach(function (key, n) {
        var gr = zellen[key], best = gr.reduce(function (a, p) { return RANG[p.l.status] < RANG[a] ? p.l.status : a; }, "geschlossen");
        var cx = gr.reduce(function (a, p) { return a + sx(p.x); }, 0) / gr.length, cy = gr.reduce(function (a, p) { return a + sy(p.y); }, 0) / gr.length;
        out += '<g class="mk" data-k="' + key + '" tabindex="0" role="button" aria-label="' + (gr.length > 1 ? gr.length + " Loipen, bester Status " + WORT[best] : esc(gr[0].l.name) + ", " + WORT[best]) + '"><circle cx="' + cx.toFixed(1) + '" cy="' + cy.toFixed(1) + '" r="' + (gr.length > 1 ? 16 : 9) + '" fill="' + FARBE[best] + '" stroke="#0b2231" stroke-width="2"/>' + (gr.length > 1 ? '<text x="' + cx.toFixed(1) + '" y="' + (cy + 4).toFixed(1) + '" text-anchor="middle">' + gr.length + "</text>" : "") + "</g>";
      });
      svg.innerHTML = out;
      svg.querySelectorAll(".mk").forEach(function (m) {
        function wahl() {
          var gr = zellen[m.dataset.k];
          if (gr.length > 1) { zoomAuf(gr); return; }
          var l = gr[0].l;
          document.getElementById("sel").innerHTML = '<b>' + esc(l.name) + '</b><div class="fine">' + esc(l.gebiet.name) + " · " + km(l.laenge_km) + " · Stand " + esc(alter(l.abgerufen)) + '</div><div style="margin:8px 0">' + chip(l.status) + '</div><a class="btn prim" href="#/loipe/' + l.id + '">Details</a>';
        }
        m.addEventListener("click", wahl); m.addEventListener("keydown", function (e) { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); wahl(); } });
      });
    }
    function zoomAuf(gr) {
      var xs = gr.map(function (p) { return p.x; }), ys = gr.map(function (p) { return p.y; });
      MV.cx = (Math.min.apply(0, xs) + Math.max.apply(0, xs)) / 2; MV.cy = (Math.min.apply(0, ys) + Math.max.apply(0, ys)) / 2; MV.sc *= 3; draw();
    }
    fit(); draw();
    document.getElementById("zi").onclick = function () { MV.sc *= 1.6; draw(); };
    document.getElementById("zo").onclick = function () { MV.sc /= 1.6; draw(); };
    document.getElementById("zf").onclick = function () { fit(); draw(); };
    el.addEventListener("wheel", function (e) { e.preventDefault(); MV.sc *= e.deltaY < 0 ? 1.2 : 1 / 1.2; draw(); }, {passive: false});
    var ptr = {}, last = null;
    svg.addEventListener("pointerdown", function (e) { ptr[e.pointerId] = {x: e.clientX, y: e.clientY}; last = null; });
    svg.addEventListener("pointermove", function (e) {
      if (!ptr[e.pointerId]) return;
      var ids = Object.keys(ptr), prev = ptr[e.pointerId];
      if (ids.length === 2) {
        var a = ptr[ids[0]], b = ptr[ids[1]], d0 = Math.hypot(a.x - b.x, a.y - b.y);
        ptr[e.pointerId] = {x: e.clientX, y: e.clientY};
        var a2 = ptr[ids[0]], b2 = ptr[ids[1]], d1 = Math.hypot(a2.x - b2.x, a2.y - b2.y);
        if (d0 > 0) { MV.sc *= d1 / d0; draw(); }
      } else {
        MV.cx -= (e.clientX - prev.x) / MV.sc; MV.cy -= (e.clientY - prev.y) / MV.sc; ptr[e.pointerId] = {x: e.clientX, y: e.clientY}; draw();
      }
    });
    function ende(e) { delete ptr[e.pointerId]; }
    svg.addEventListener("pointerup", ende); svg.addEventListener("pointercancel", ende);
  });
}

/* ---------- Suche (U21) und Ort ---------- */
function setzeOrt(o) { S.ort = o; speicher("ort", o); beschrifteOrt(); }
function beschrifteOrt() { var b = document.getElementById("ort"); b.textContent = (S.ort ? S.ort.name : "Ort wählen") + " ▾"; b.setAttribute("aria-label", "Standort: " + (S.ort ? S.ort.name : "keiner") + ", ändern"); }
function sucheBinden() {
  var q = document.getElementById("q"), ul = document.getElementById("vorschlaege"), aktiv = -1, items = [];
  function zu() { ul.hidden = true; q.setAttribute("aria-expanded", "false"); aktiv = -1; }
  function zeige() {
    var t = q.value.trim().toLowerCase();
    if (t.length < 3) { zu(); return; }
    items = [];
    S.gebiete.forEach(function (g) { if (g.name.toLowerCase().indexOf(t) >= 0) items.push({art: "Gebiet", name: g.name, ziel: "#/gebiet/" + g.slug}); });
    S.loipen.forEach(function (l) { if (l.name.toLowerCase().indexOf(t) >= 0 && items.length < 40) items.push({art: "Loipe", name: l.name, extra: l.gebiet.name, ziel: "#/loipe/" + l.id}); });
    S.orte.forEach(function (o) { if (o.name.toLowerCase().indexOf(t) >= 0) items.push({art: "Ort", name: o.name, ziel: "#/loipen?ort=" + encodeURIComponent(o.name) + "&sort=entfernung", ort: o}); });
    items = items.slice(0, 12);
    ul.innerHTML = items.length ? items.map(function (it, i) { return '<li role="option" id="v' + i + '" data-i="' + i + '"><span>' + esc(it.name) + (it.extra ? ' <small>' + esc(it.extra) + "</small>" : "") + "</span><small>" + it.art + "</small></li>"; }).join("") : '<li role="option" aria-disabled="true">Nichts gefunden</li>';
    ul.hidden = false; q.setAttribute("aria-expanded", "true"); aktiv = -1;
  }
  function wahl(i) { var it = items[i]; if (!it) return; zu(); q.value = ""; if (it.ort) setzeOrt(it.ort); location.hash = it.ziel; }
  q.addEventListener("input", zeige);
  q.addEventListener("keydown", function (e) {
    if (e.key === "ArrowDown" || e.key === "ArrowUp") { e.preventDefault(); aktiv = Math.max(0, Math.min(items.length - 1, aktiv + (e.key === "ArrowDown" ? 1 : -1))); ul.querySelectorAll("li").forEach(function (li, i) { li.setAttribute("aria-selected", i === aktiv); }); q.setAttribute("aria-activedescendant", "v" + aktiv); }
    else if (e.key === "Enter") { e.preventDefault(); wahl(aktiv >= 0 ? aktiv : 0); }
    else if (e.key === "Escape") zu();
  });
  ul.addEventListener("mousedown", function (e) { var li = e.target.closest("li[data-i]"); if (li) { e.preventDefault(); wahl(+li.dataset.i); } });
  q.addEventListener("blur", function () { setTimeout(zu, 120); });
}
function ortDialog() {
  var d = document.getElementById("ortwahl");
  var optionen = S.orte.concat(S.gebiete.filter(function (g) { return g.lat != null; }).map(function (g) { return {name: g.name, lat: g.lat, lon: g.lon}; }));
  var gesehen = {}; optionen = optionen.filter(function (o) { if (gesehen[o.name]) return false; gesehen[o.name] = 1; return true; }).sort(function (a, b) { return a.name.localeCompare(b.name); });
  d.innerHTML = '<div class="box"><h2 style="margin-top:0">Standort wählen</h2><button type="button" class="o" id="geo"><span>Mein Standort verwenden</span><span>⌖</span></button>' + optionen.map(function (o, i) { return '<button type="button" class="o" data-i="' + i + '"><span>' + esc(o.name) + "</span></button>"; }).join("") + '<p><button type="button" class="btn" id="zu">Schließen</button></p></div>';
  d.hidden = false;
  d.querySelector("#zu").focus();
  d.querySelector("#zu").onclick = function () { d.hidden = true; };
  d.onclick = function (e) { if (e.target === d) d.hidden = true; };
  d.onkeydown = function (e) { if (e.key === "Escape") d.hidden = true; };
  d.querySelectorAll("button.o[data-i]").forEach(function (b) { b.onclick = function () { setzeOrt(optionen[+b.dataset.i]); d.hidden = true; route(); }; });
  d.querySelector("#geo").onclick = function () {
    if (!navigator.geolocation) { alert("Dein Gerät kann den Standort nicht bestimmen."); return; }
    navigator.geolocation.getCurrentPosition(function (p) { setzeOrt({name: "Mein Standort", lat: p.coords.latitude, lon: p.coords.longitude}); d.hidden = true; route(); }, function () { alert("Der Standort wurde nicht freigegeben."); });
  };
}

/* ---------- Routing ---------- */
function route() {
  var q = parseQuery(location.hash), p = pfad(location.hash) || "/";
  var tab = p.indexOf("/karte") === 0 ? "karte" : p.indexOf("/loipen") === 0 || p.indexOf("/loipe/") === 0 || p.indexOf("/gebiet/") === 0 ? "loipen" : "heute";
  document.querySelectorAll(".tabs a").forEach(function (a) { if (a.dataset.tab === tab) a.setAttribute("aria-current", "page"); else a.removeAttribute("aria-current"); });
  if (q.demo && (q.demo === "1") !== S.demo) { location.reload(); return; }
  view.dataset.r = (+view.dataset.r || 0) + 1; // Zaehler: Tests warten damit auf das Neuzeichnen
  if (p === "/karte") seiteKarte(q);
  else if (p === "/loipen") seiteListe(q);
  else if (p.indexOf("/gebiet/") === 0) seiteGebiet(p.slice(8));
  else if (p.indexOf("/loipe/") === 0) seiteLoipe(p.slice(7));
  else seiteHeute(q);
  if (p.indexOf("/loipe/") !== 0 && p !== "/karte") window.scrollTo(0, 0);
}

function start() {
  laden().then(function () {
    document.getElementById("stand").textContent = "Stand der Daten: " + datum(S.idx.erzeugt) + " · Wetter: Deutscher Wetterdienst, Bright Sky";
    beschrifteOrt(); sucheBinden();
    document.getElementById("ort").addEventListener("click", ortDialog);
    var dk = document.getElementById("demo-knopf");
    dk.textContent = S.demo ? "Beispielansicht beenden" : "Beispielansicht mit Schnee (erfundene Werte)";
    dk.addEventListener("click", function () { try { if (S.demo) sessionStorage.removeItem("demo"); else sessionStorage.setItem("demo", "1"); } catch (e) {} location.reload(); });
    window.addEventListener("hashchange", route);
    route();
    if ("serviceWorker" in navigator && location.protocol.indexOf("http") === 0) navigator.serviceWorker.register("sw.js").catch(function () {});
  }).catch(function (e) {
    view.innerHTML = '<p class="leer glass">Die Daten konnten nicht geladen werden (' + esc(e.message) + "). Bitte später noch einmal versuchen.</p>";
  });
}
start();
})();
