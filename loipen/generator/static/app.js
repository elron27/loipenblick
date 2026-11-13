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
var LAND = {DE: "Deutschland", AT: "Österreich", IT: "Italien"};
var TAGE = ["So", "Mo", "Di", "Mi", "Do", "Fr", "Sa"];
var S = {idx: null, regionen: {}, strecken: {}, gebiete: [], loipen: [], demo: false, ort: null, orte: []};
var view = document.getElementById("view");

function esc(s) { return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) { return {"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"}[c]; }); }
function safeUrl(u) { return /^https?:\/\//i.test(u || "") ? u : "#"; }
function zahl(x, n) { return x == null ? "unbekannt" : String(Number(x).toFixed(n == null ? 1 : n)).replace(".", ","); }
function km(x) { return x == null ? "Länge unbekannt" : zahl(x) + " km"; }
function chip(s) { return '<span class="st ' + s + '"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' + SYM[s] + "</svg>" + WORT[s] + "</span>"; }
function jetztMs() { return Date.now(); }
/* D16: Gruppe "Land · Bundesland", z. B. "Österreich · Tirol" */
function gruppeName(r) { return (LAND[r.land] || r.land || "") + (r.bundesland ? " · " + r.bundesland : ""); }
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
function namensZahl(t) { var h = 0; for (var k = 0; k < t.length; k++) h = (h * 31 + t.charCodeAt(k)) % 100003; return h; }
function demoAnwenden() {
  S.loipen.forEach(function (l, i) {
    if (l.status === "geschlossen" || l.status === "unbekannt") {
      var r = (namensZahl(l.name) + i) % 9;  // nicht l.id: die haengt von der Datenbank ab
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
    regs.forEach(function (r) { S.regionen[r.region.slug] = r; r.gebiete.forEach(function (g) { g.region = r.region.slug; g.region_name = r.region.name; }); alle = alle.concat(r.gebiete); });
    mache(alle);
    var q = parseQuery(location.hash);
    try { if (q.demo === "1") sessionStorage.setItem("demo", "1"); if (q.demo === "0") sessionStorage.removeItem("demo"); S.demo = sessionStorage.getItem("demo") === "1"; } catch (e) { S.demo = q.demo === "1"; }
    if (S.demo) demoAnwenden();
    S.ort = ortAusName(q.ort) || speicher("ort") || ortAusName(S.idx.standardort) || (S.gebiete[0] && {name: S.gebiete[0].name, lat: S.gebiete[0].lat, lon: S.gebiete[0].lon});
  });
}
/* U32: Streckenverlaeufe nur fuer die Regionen laden, die gerade gebraucht werden */
function ladeStrecken(slugs) {
  var offen = S.idx.regionen.filter(function (r) { return slugs.indexOf(r.slug) >= 0 && !S.strecken[r.slug]; });
  return Promise.all(offen.map(function (r) { return holeJson(r.strecken).then(function (s) { S.strecken[r.slug] = s; }); }));
}
function regionenNahe(punkt, km) {
  return S.idx.regionen.filter(function (r) { return r.mitte && punkt && dist(punkt, {lat: r.mitte[0], lon: r.mitte[1]}) <= km; }).map(function (r) { return r.slug; });
}
function ortAusName(n) {
  if (!n) return null;
  var k = n.toLowerCase(), t = null;
  S.orte.forEach(function (o) { if (o.name.toLowerCase() === k) t = o; });
  S.gebiete.forEach(function (g) { if (!t && g.name.toLowerCase() === k && g.lat != null) t = {name: g.name, lat: g.lat, lon: g.lon}; });
  return t;
}

/* ---------- Filter, Sortierung, URL (U2, U3, U4, U16, U24) ---------- */
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
    if (sort === "praeparierung") return (a.ohne_datum - b.ohne_datum) || (b.quelle_stand || "").localeCompare(a.quelle_stand || "");  // U30: ohne Datum hinten
    if (sort === "neuschnee") return neu48(b) - neu48(a) || RANG[a.status] - RANG[b.status] || a.name.localeCompare(b.name);
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
  // U30, P16: Quelle ohne Praeparierdatum oder ganz ohne Zustand
  var stand = !l.abgerufen ? "noch kein Abruf" : (l.ohne_zustand ? "Quelle meldet keinen Zustand · " : l.ohne_datum ? "Status ohne Datum · " : "") + "Stand " + alter(l.abgerufen);
  return '<a class="lp glass" href="#/loipe/' + l.id + '"><span class="n">' + esc(l.name) + (mitGebiet ? ' <span class="fine">· ' + esc(l.gebiet.name) + "</span>" : "") + "</span>" + chip(l.status) +
    '<span class="d">' + esc(teile.filter(Boolean).join(" · ")) + " · " + frisch + esc(stand) + (l.quelle_fehler ? " · letzter Abruf fehlgeschlagen" : "") + "</span></a>";
}
function neu48(l) { var s = l.gebiet && l.gebiet.schnee; return s && s.neuschnee_48h_cm != null ? s.neuschnee_48h_cm : -1; }
function neuschneeBadge(g) { return g.schnee && g.schnee.neuschnee_48h_cm >= 1 ? ' <span class="badge neu">Neuschnee ' + zahl(g.schnee.neuschnee_48h_cm, 0) + " cm in 48 h</span>" : ""; }
function istWochenende(iso) { var d = new Date(iso + "T12:00:00").getDay(); return d === 0 || d === 6; }
var WX_NAME = {sonne: "Sonnig", wolkig: "Wolkig", bedeckt: "Bedeckt", regen: "Regen", schneeregen: "Schneeregen", schnee: "Schnee", gewitter: "Gewitter"};
var WX_SONNE = '<circle cx="24" cy="24" r="8" fill="#fbbf24" stroke="#f59e0b"/><path d="M24 7v5M24 36v5M7 24h5M36 24h5M12 12l3.5 3.5M32.5 32.5L36 36M12 36l3.5-3.5M32.5 15.5L36 12" stroke="#f59e0b"/>';
var WX_WOLKE = function (f) { return '<path d="M15 36h19a7 7 0 0 0 .6-13.97A10 10 0 0 0 15.4 20.6 7.7 7.7 0 0 0 15 36z" fill="' + f + '" stroke="#7b93a8"/>'; };
var WX_SVG = {
  sonne: WX_SONNE,
  wolkig: '<g transform="translate(-4 -6) scale(.8)">' + WX_SONNE + "</g>" + '<g transform="translate(5 3) scale(.85)">' + WX_WOLKE("#e8f1f8") + "</g>",
  bedeckt: WX_WOLKE("#cfdce8"),
  regen: WX_WOLKE("#cfdce8") + '<path d="M17 40l-2 5M25 40l-2 5M33 40l-2 5" stroke="#2f89d8"/>',
  schneeregen: WX_WOLKE("#cfdce8") + '<path d="M16 41l-1.5 4M34 41l-1.5 4" stroke="#2f89d8"/><circle cx="24" cy="43" r="1.6" fill="#7dd3fc" stroke="none"/>',
  schnee: WX_WOLKE("#e8f1f8") + '<g stroke="none" fill="#38bdf8"><circle cx="17" cy="42" r="2"/><circle cx="25" cy="44" r="2"/><circle cx="33" cy="42" r="2"/></g>',
  gewitter: WX_WOLKE("#b6c6d6") + '<path d="M26 33l-5 8h5l-3 7 8-10h-5l3-5z" fill="#fbbf24" stroke="#f59e0b" stroke-width="1.4"/>'
};
function wxIcon(symbol) {
  if (!symbol || !WX_SVG[symbol]) return "";
  return '<svg class="wxi" viewBox="0 0 48 48" width="40" height="40" fill="none" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" role="img" aria-label="' + WX_NAME[symbol] + '">' + WX_SVG[symbol] + "</svg>";
}
function vorhersageHtml(g) {
  var v = g.vorhersage || [];
  if (!v.length) return '<p class="fine">Noch keine Vorhersage.</p>';
  return '<p class="fine">Vorhersage (keine Messung), Quelle Bright Sky mit Daten des Deutschen Wetterdienstes</p><div class="wx">' + v.map(function (t) {
    var d = new Date(t.datum + "T12:00:00");
    var info = [];
    if (t.niederschlag_mm != null) info.push(zahl(t.niederschlag_mm) + " mm");
    if (t.sonne_h != null && t.sonne_h >= 0.5) info.push(zahl(t.sonne_h) + " h Sonne");
    return '<div class="' + (istWochenende(t.datum) ? "we" : "") + '"><b>' + TAGE[d.getDay()] + " " + d.getDate() + "." + (d.getMonth() + 1) + ".</b>" + wxIcon(t.symbol) +
      (t.symbol ? '<em class="wxn">' + WX_NAME[t.symbol] + "</em>" : "") + "<span>" + (t.tmin == null ? "–" : Math.round(t.tmin)) + " / " + (t.tmax == null ? "–" : Math.round(t.tmax)) + " °C</span><small class=\"fine\">" + info.join(" · ") + "</small></div>";
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
/* Talprofil-Beschriftung (U33): je Name eine Position, die keinen anderen Namen und keinen Nadelkopf
   ueberdeckt. Eingabe [{name, x, kopf}] (kopf = Mitte des Nadelkopfs), Ausgabe [{x, y, hoch, box}]. */
var ZEICHEN_PX = 7.4, ZEILE_PX = 17;
/* Textbreite echt messen (Schrift des Geraets), sonst schaetzen: geschaetzte Breiten passten nicht zu
   jeder Schrift, auf manchen Systemen ragte ein Name dann in eine Nachbarnadel (U33). */
var messer = null;
function textBreite(t) {
  try {
    if (!messer) {
      messer = document.createElement("canvas").getContext("2d");
      messer.font = "700 13px " + getComputedStyle(document.body).fontFamily;
    }
    var w = messer.measureText(t).width;
    if (w > 0) return Math.max(w, t.length * ZEICHEN_PX) + 8;
  } catch (e) { /* ohne Canvas schaetzen */ }
  return t.length * ZEICHEN_PX + 8;
}
function beschriftung(punkte) {
  var boxen = [], koepfe = punkte.map(function (p) { return {l: p.x - 11, r: p.x + 11, o: p.kopf - 11, u: p.kopf + 11}; });
  function frei(b, eigen) {
    return boxen.every(function (a) { return b.r <= a.l || b.l >= a.r || b.u <= a.o || b.o >= a.u; }) &&
      koepfe.every(function (k, j) { return j === eigen || b.r <= k.l || b.l >= k.r || b.u <= k.o || b.o >= k.u; });
  }
  /* Nadeln mit tiefem Kopf zuerst: sie haben unten am wenigsten Platz */
  var reihe = punkte.map(function (p, i) { return i; }).sort(function (a, b) { return punkte[b].kopf - punkte[a].kopf || punkte[a].x - punkte[b].x; });
  var aus = [];
  reihe.forEach(function (i) {
    var p = punkte[i], w = textBreite(p.name), y0 = p.kopf - 18, wahl = null;
    var x = Math.max(w / 2 + 2, Math.min(900 - w / 2 - 2, p.x));
    for (var y = y0; y >= 14 && !wahl; y -= 6) {
      [0, -1, 1].forEach(function (seite) {
        if (wahl) return;
        var xx = Math.max(w / 2 + 2, Math.min(900 - w / 2 - 2, x + seite * w * 0.3));
        var b = {l: xx - w / 2, r: xx + w / 2, o: y - ZEILE_PX + 4, u: y + 4};
        if (frei(b, i)) wahl = {x: xx, y: y, box: b};
      });
    }
    if (!wahl) { var b = {l: x - w / 2, r: x + w / 2, o: 14 - ZEILE_PX + 4, u: 18}; wahl = {x: x, y: 14, box: b}; }
    wahl.hoch = wahl.y < y0 - 1 || Math.abs(wahl.x - p.x) > 1;
    boxen.push(wahl.box); aus[i] = wahl;
  });
  return aus;
}
window.__beschriftung = beschriftung;  // fuer den Kollisionstest
function far(x) { return 190 - 45 * Math.sin(x / 95 + 2) - 24 * Math.sin(x / 37); }
function talprofil(gebiete, schnee) {
  var sorted = gebiete.filter(function (g) { return g.lon != null; }).sort(function (a, b) { return a.lon - b.lon; });
  if (!sorted.length) return "";
  var s = "", n = sorted.length;
  /* Die Nadeln stehen nach Laengengrad von West nach Ost; der Bergruecken verlaeuft durch die echten Hoehen der Orte. */
  var hs = sorted.map(function (g) { return g.hoehe_m; }).filter(function (h) { return h != null; });
  var hmin = hs.length ? Math.min.apply(null, hs) : 0, hmax = hs.length ? Math.max.apply(null, hs) : 1, hspan = Math.max(hmax - hmin, 150);
  var mitte = hs.length ? (hmin + hmax) / 2 : 0;
  function hy(g) { var h = g.hoehe_m == null ? mitte : g.hoehe_m; return 250 - 95 * (h - hmin) / hspan; }
  var px = sorted.map(function (g, i) { return n === 1 ? 450 : 60 + i * (780 / (n - 1)); });
  var py = sorted.map(hy);
  function grund(x) {
    if (n === 1) return py[0];
    if (x <= px[0]) return py[0];
    if (x >= px[n - 1]) return py[n - 1];
    var i = 0; while (x > px[i + 1]) i++;
    var t = (x - px[i]) / (px[i + 1] - px[i]), k = (1 - Math.cos(t * Math.PI)) / 2;
    return py[i] + (py[i + 1] - py[i]) * k;
  }
  function ridgeH(x) { var w = Math.sin(x / 31 + 1) * 7 + Math.sin(x / 13 + 2) * 4, nahe = 1; for (var i = 0; i < n; i++) nahe = Math.min(nahe, Math.abs(x - px[i]) / 25); return grund(x) + w * Math.min(nahe, 1); }
  s += '<defs><linearGradient id="rg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="var(--ridge1)"/><stop offset="1" stop-color="var(--ridge2)"/></linearGradient></defs>';
  var f = "M0 340"; for (var x = 0; x <= 900; x += 10) f += "L" + x + " " + (far(x) - 20 + (hy({hoehe_m: mitte}) - 250) * 0.3); s += '<path class="s-far" d="' + f + 'L900 340Z" opacity=".85"/>';
  var q = "M0 340", rim = "M0 " + ridgeH(0); for (x = 0; x <= 900; x += 6) { q += "L" + x + " " + ridgeH(x); rim += "L" + x + " " + ridgeH(x); }
  s += '<path class="s-ridge" d="' + q + 'L900 340Z"/><path class="s-rim" d="' + rim + '"/>';
  /* Namen so tief wie moeglich direkt ueber der Nadel. Kollision wird zweidimensional geprueft (Breite
     und Hoehe des Textes, Nadelkoepfe), weil die Nadeln je nach Ortshoehe verschieden hoch stehen. Wer
     ausweichen muss, rueckt nach oben und bekommt eine duenne Linie zur Nadel (U33). */
  var lage = beschriftung(sorted.map(function (g, i) { return {name: g.name, x: px[i], kopf: py[i] - 44}; }));
  sorted.forEach(function (g, i) {
    var y = py[i], X = px[i], b = lage[i];
    var best = g.loipen.reduce(function (a, l) { return RANG[l.status] < RANG[a] ? l.status : a; }, "geschlossen");
    var hoehe = g.hoehe_m == null ? "" : " (" + g.hoehe_m + " m)";
    s += '<a href="#/gebiet/' + esc(g.slug) + '"><line class="s-l" x1="' + X + '" y1="' + y + '" x2="' + X + '" y2="' + (y - 40) + '" stroke-width="1.5"/>' +
      (b.hoch ? '<line class="s-l s-f" x1="' + X + '" y1="' + (y - 55) + '" x2="' + b.x + '" y2="' + (b.y + 4) + '" stroke-width="1"/>' : "") +
      '<circle cx="' + X + '" cy="' + (y - 44) + '" r="10" fill="' + FARBE[best] + '" stroke="var(--ink)" stroke-width="2"/><text class="s-t" x="' + b.x + '" y="' + b.y + '" text-anchor="middle">' + esc(g.name) + "</text><title>" + esc(g.name) + hoehe + ": " + WORT[best] + "</title></a>";
  });
  return '<div class="scr"><svg viewBox="0 0 900 340" preserveAspectRatio="xMidYMax meet" role="img" aria-label="Talprofil: die Loipengebiete von West nach Ost, die Höhe der Nadeln folgt der Höhe der Orte">' + s + "</svg></div>";
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
    (reco ? 'Heute lohnt sich <span class="akz">' + esc(reco.name) + "</span>" : 'Heute keine <span class="akz">offene Loipe</span>') + "</h1><p>" +
    (reco ? esc(km(reco.laenge_km) + (reco.entf != null ? ", " + zahl(reco.entf, 0) + " km von " + o.name : "") + ", Stand " + alter(reco.abgerufen)) : "Alle Quellen melden die Loipen als geschlossen oder ohne Angabe. Wir prüfen in der Saison dreimal täglich.") +
    "</p></div>" + talprofil(zeig) + "</section>" +
    '<div class="cols" style="margin-top:14px"><div class="reco glass"><h2>Heute in deiner Nähe</h2><div class="big">' + (reco ? esc(reco.name) : "Heute keine offene Loipe") + "</div><p>" +
    (reco ? esc(reco.gebiet.name) + " · " + WORT[reco.status] : "Wir sagen es dir hier, sobald etwas gespurt ist.") + '</p><div class="facts">' +
    (nah[0] && nah[0].schnee && nah[0].schnee.schneehoehe_cm != null ? '<span class="chip">Schnee ' + esc(nah[0].name) + ": " + zahl(nah[0].schnee.schneehoehe_cm, 0) + " cm</span>" : '<span class="chip">Schneehöhe: noch keine Messung</span>') +
    (reco ? '<a class="btn prim" href="#/loipe/' + reco.id + '">Zur Loipe</a>' : "") + "</div></div>" +
    /* U34: die Kennzahlen fuehren direkt zur passend gefilterten Liste */
    '<div class="stats"><a class="stat glass" id="k-offen" href="#/loipen?offen=1&amp;sort=entfernung"><b>' + offene.length + '</b><span>befahrbar</span></a><a class="stat glass" href="#/loipen"><b>' + kz.loipen + '</b><span>Loipen im Blick</span></a><a class="stat glass" href="#/abdeckung"><b>' + (S.idx.quellen.length - fehler) + "/" + S.idx.quellen.length + "</b><span>Quellen ohne Fehler</span></a></div></div>";
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
  var regs = gruppen().map(function (gr) { return '<optgroup label="' + esc(gr.name) + '">' + gr.regionen.map(function (r) { return '<option value="' + esc(r.slug) + '"' + (q.region === r.slug ? " selected" : "") + ">" + esc(r.name) + "</option>"; }).join("") + "</optgroup>"; }).join("");
  return '<div class="filter" role="group" aria-label="Filter">' + tog("offen", "1", "Nur offene") + tog("technik", "klassisch", "Klassisch") + tog("technik", "skating", "Skating") + tog("leicht", "1", "Leicht") + tog("rund", "1", "Rundkurs") + tog("nacht", "1", "Nachtloipe") +
    '<label class="vh" for="f-max">Höchstlänge in km</label><input id="f-max" type="number" inputmode="decimal" min="0" step="0.5" placeholder="max. km" value="' + esc(q.max || "") + '">' +
    '<label class="vh" for="f-r">Umkreis</label><select id="f-r"><option value="">Umkreis: alle</option>' + [10, 25, 50, 100].map(function (r) { return '<option value="' + r + '"' + (q.r == r ? " selected" : "") + ">bis " + r + " km</option>"; }).join("") + "</select>" +
    '<label class="vh" for="f-reg">Region</label><select id="f-reg"><option value="">Alle Regionen</option>' + regs + "</select>" +
    '<label class="vh" for="f-sort">Sortierung</label><select id="f-sort">' + [["region", "Land und Region"], ["status", "Status"], ["entfernung", "Entfernung"], ["gespurt", "Gespurte km"], ["praeparierung", "Letzte Präparierung"], ["neuschnee", "Neuschnee 48 h"]].map(function (s) { return '<option value="' + s[0] + '"' + ((q.sort || "region") === s[0] ? " selected" : "") + ">Sortiert nach " + s[1] + "</option>"; }).join("") + "</select>" +
    '<button type="button" class="btn" id="teilen">Teilen</button></div>';
}
function gruppen() {
  var g = [], akt = null;
  S.idx.regionen.forEach(function (r) { var n = gruppeName(r); if (!akt || akt.name !== n) { akt = {name: n, regionen: []}; g.push(akt); } akt.regionen.push(r); });
  return g;
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
  if (q.ort && !q.sort) q.sort = "entfernung";
  var o = ortFuer(q), liste = filtere(q);
  var h = (S.demo ? '<p class="demo">Vorschau mit Beispielwerten, keine echten Daten.</p>' : "") + "<h1>Loipen" + (q.r ? " im Umkreis von " + esc(q.r) + " km um " + esc(o ? o.name : "") : "") + '</h1><p class="fine">' + liste.length + " von " + S.loipen.length + " Loipen" + (o ? ", Entfernung von " + esc(o.name) : "") + "</p>" + filterLeiste(q, "/loipen");
  h += !liste.length ? '<p class="leer glass">Keine Loipe passt zu diesen Filtern. Lockere einen Filter oder vergrößere den Umkreis.</p>' :
    (q.sort || "region") === "region" ? listeGruppiert(liste) : '<div class="lg">' + liste.map(function (l) { return loipeKarte(l, true); }).join("") + "</div>";
  view.innerHTML = h; filterBinden(q, "/loipen");
}
/* D16 AK 2: Liste nach Land/Bundesland und Region, innerhalb der Region nach Status */
function listeGruppiert(liste) {
  var je = {};
  liste.forEach(function (l) { (je[l.gebiet.region] = je[l.gebiet.region] || []).push(l); });
  return gruppen().map(function (gr) {
    var teile = gr.regionen.filter(function (r) { return je[r.slug]; }).map(function (r) {
      return '<section class="rg" data-region="' + esc(r.slug) + '"><h3 class="reg">' + esc(r.name) + ' <span class="fine">' + je[r.slug].length + " Loipen</span></h3><div class=\"lg\">" + je[r.slug].map(function (l) { return loipeKarte(l, true); }).join("") + "</div></section>";
    });
    return teile.length ? '<h2 class="sec land">' + esc(gr.name) + "</h2>" + teile.join("") : "";
  }).join("");
}

function seiteGebiet(slug) {
  var g = S.gebiete.filter(function (x) { return x.slug === slug; })[0];
  if (!g) { view.innerHTML = '<p class="leer glass">Dieses Gebiet gibt es nicht. <a href="#/loipen">Zur Liste</a></p>'; return; }
  var gesamt = g.loipen.reduce(function (a, l) { return a + (l.laenge_km || 0); }, 0);
  var gebuehr = g.loipengebuehr || {};
  var andere = Object.keys(g.namen || {}).map(function (k) { return g.namen[k]; }).filter(function (n) { return n && n !== g.name; });
  var ohneZustand = g.loipen.length && g.loipen.every(function (l) { return l.ohne_zustand; });
  var h = "<h1>" + esc(g.name) + neuschneeBadge(g) + "</h1>" + (andere.length ? '<p class="fine">auch: ' + esc(andere.join(", ")) + "</p>" : "") +
    '<p class="fine">' + esc([g.region_name, gruppeName(g)].filter(Boolean).join(" · ")) + " · " + g.loipen.length + " Loipen" + (gesamt > 0 ? ", zusammen " + zahl(gesamt) + " km" : ", Länge noch unbekannt") + " · <a href=\"" + esc(safeUrl(g.tourist_url)) + '" rel="noopener">Touristeninformation</a></p>' +
    '<h2 class="sec">Schnee</h2>' + schneeHtml(g) + '<h2 class="sec">Vorhersage</h2>' + vorhersageHtml(g) +
    (ohneZustand ? '<p class="hinweis glass">Die Quelle für dieses Gebiet meldet keinen Loipenzustand, nur Lage und Länge. Den aktuellen Zustand kennt die Touristeninformation.</p>' : "") +
    '<h2 class="sec">Anreise</h2><ul class="plain">' +
    (g.grenzinfo ? '<li class="glass vignette"><span>Vignette</span><b>' + esc(g.grenzinfo) + "</b></li>" : "") +
    '<li class="glass"><span>Loipengebühr</span><b>' + (gebuehr.text ? esc(gebuehr.text) : gebuehr.eur != null ? zahl(gebuehr.eur, 2) + " €" : "unbekannt") + "</b></li>" +
    (g.parkplaetze.length ? g.parkplaetze.map(function (p) { return '<li class="glass"><span><b>' + esc(p.name) + "</b><br><span class=\"fine\">Gebühr: " + esc(p.gebuehr_text || (p.gebuehr_eur_tag != null ? zahl(p.gebuehr_eur_tag, 2) + " € pro Tag" : "unbekannt")) + (p.geschaetzt ? " · Lage ungefähr (Loipenstart)" : "") + '</span></span><a class="btn" href="' + esc(navLink(p.lat, p.lon)) + '" rel="noopener">Navigation</a></li>'; }).join("") : '<li class="glass"><span>Parkplätze</span><b>noch nicht erfasst</b></li>') +
    (g.haltestellen.length ? g.haltestellen.map(function (s) { return '<li class="glass"><span><b>' + esc(s.name) + '</b><br><span class="fine">Haltestelle (' + esc(s.art || "ÖPNV") + ')</span></span><a class="btn" href="' + esc(oevLink(s.lat, s.lon)) + '" rel="noopener">Fahrplan</a></li>'; }).join("") : '<li class="glass"><span>Haltestelle</span><b>keine bekannt</b></li>') +
    '</ul><h2 class="sec">Loipen</h2><div class="lg">' + g.loipen.map(function (l) { l.entf = dist(S.ort, l.lat != null ? l : g); return loipeKarte(l, false); }).join("") + "</div>";
  view.innerHTML = h;
}

/* ---------- Leaflet-Karten (Grundkarte OpenStreetMap) ---------- */
var KARTEN = [];
function kartenAbbauen() { KARTEN.forEach(function (m) { try { m.remove(); } catch (e) {} }); KARTEN = []; window.__map = null; }
function grundkarte(el, opts) {
  var m = L.map(el, Object.assign({zoomControl: true, attributionControl: true, scrollWheelZoom: true}, opts || {}));
  L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {maxZoom: 18, attribution: '© <a href="https://www.openstreetmap.org/copyright" rel="noopener">OpenStreetMap-Mitwirkende</a>'}).addTo(m);
  KARTEN.push(m); window.__map = m;
  return m;
}
function punktIcon(status, text, titel) {
  var gross = text != null;
  return L.divIcon({className: "", iconSize: gross ? [34, 34] : [22, 22], iconAnchor: gross ? [17, 17] : [11, 11],
    html: '<span class="' + (gross ? "mkc" : "mk") + '" data-s="' + status + '" role="button" tabindex="0" aria-label="' + esc(titel) + '" style="background:' + FARBE[status] + '">' + (gross ? esc(text) : "") + "</span>"});
}
function miniKarte(l) {
  var reg = l.gebiet.region, pts = ((S.strecken[reg] || {})[String(l.id)] || []);
  if (!pts.length && l.lat == null) return '<p class="fine glass" style="padding:12px 14px">Für diese Loipe ist noch keine Position bekannt.</p>';
  /* U36 AK 2: ohne Streckenverlauf steht der Grund dabei */
  var grund = pts.length ? "" : '<p class="fine" id="ohne-strecke">Nur Startpunkt, kein Streckenverlauf' + (l.strecke_hinweis ? ": " + esc(l.strecke_hinweis) : ".") + "</p>";
  return '<div id="minimap" class="minimap" role="region" aria-label="Karte der Loipe"></div>' + grund;
}
function miniKarteZeichnen(l) {
  var el = document.getElementById("minimap"); if (!el) return;
  var reg = l.gebiet.region, pts = ((S.strecken[reg] || {})[String(l.id)] || []);
  var m = grundkarte(el, {scrollWheelZoom: false}), gruppe = [];
  if (pts.length > 1) gruppe.push(L.polyline(pts, {color: FARBE[l.status], weight: 6, opacity: .95}).addTo(m));
  var start = pts.length ? pts[0] : [l.lat, l.lon];
  gruppe.push(L.marker(start, {icon: punktIcon(l.status, null, l.name + ", Start")}).addTo(m));
  l.gebiet.parkplaetze.forEach(function (p) {
    gruppe.push(L.marker([p.lat, p.lon], {icon: L.divIcon({className: "", iconSize: [24, 24], iconAnchor: [12, 12], html: '<span class="pk" title="' + esc(p.name) + '">P</span>'})}).addTo(m).bindTooltip(p.name));
  });
  var gr = L.featureGroup(gruppe), b = gr.getBounds();
  setTimeout(function () { m.invalidateSize(); m.fitBounds(b.pad(.25), {maxZoom: 15}); }, 0);
}
function seiteLoipe(id) {
  var l = S.loipen.filter(function (x) { return String(x.id) === id; })[0];
  if (!l) { view.innerHTML = '<p class="leer glass">Diese Loipe gibt es nicht. <a href="#/loipen">Zur Liste</a></p>'; return; }
  ladeStrecken([l.gebiet.region]).then(function () {
    var g = l.gebiet, ziel = g.parkplaetze[0] || (l.lat != null ? {lat: l.lat, lon: l.lon, name: "Start der Loipe"} : null);
    var hist = l.historie.map(function (t) { return '<span class="' + (t.status ? "" : "keine ") + '" style="' + (t.status ? "background:var(--" + ({offen: "ok", eingeschraenkt: "mid", geschlossen: "bad", unbekannt: "unk"}[t.status]) + "-bg);color:var(--" + ({offen: "ok", eingeschraenkt: "mid", geschlossen: "bad", unbekannt: "unk"}[t.status]) + ')"' : "") + ' title="' + esc(t.tag + ": " + (t.status ? WORT[t.status] : "noch keine Daten")) + '">' + (t.status ? {offen: "✓", eingeschraenkt: "!", geschlossen: "✕", unbekannt: "?"}[t.status] : "·") + "</span>"; }).join("");
    view.innerHTML = '<p><a href="#/gebiet/' + esc(g.slug) + '">← ' + esc(g.name) + "</a></p><h1>" + esc(l.name) + "</h1><p>" + chip(l.status) + (l.veraltet ? ' <span class="badge">veraltet</span>' : "") + (l.quelle_fehler ? ' <span class="badge">letzter Abruf fehlgeschlagen</span>' : "") + "</p>" +
      '<div class="kv"><div class="glass"><small>Länge</small><b>' + km(l.laenge_km) + '</b></div><div class="glass"><small>Gespurt</small><b>' + (l.gespurt_km == null ? "unbekannt" : zahl(l.gespurt_km) + " km") + '</b></div><div class="glass"><small>Klassisch</small><b>' + (l.status_klassisch ? WORT[l.status_klassisch] : "keine Angabe") + '</b></div><div class="glass"><small>Skating</small><b>' + (l.status_skating ? WORT[l.status_skating] : "keine Angabe") + '</b></div><div class="glass"><small>Schwierigkeit</small><b>' + esc(l.schwierigkeit) + '</b></div><div class="glass"><small>Technik</small><b>' + esc(l.technik) + '</b></div><div class="glass"><small>Rundkurs</small><b>' + (l.rundkurs == null ? "unbekannt" : l.rundkurs ? "ja" : "nein") + '</b></div><div class="glass"><small>Flutlicht</small><b>' + (l.nachtloipe == null ? "unbekannt" : l.nachtloipe ? "ja" : "nein") + "</b></div></div>" +
      miniKarte(l) + '<h2 class="sec">Letzte 14 Tage</h2><div class="hist" role="img" aria-label="Status der letzten 14 Tage">' + hist + "</div>" +
      '<h2 class="sec">Quelle und Stand</h2><ul class="plain"><li class="glass"><span>Quelle</span><a href="' + esc(safeUrl(l.quelle.url)) + '" rel="noopener">' + esc(l.quelle.name) + "</a></li><li class=\"glass\"><span>Stand laut Quelle</span><b>" + esc(l.ohne_zustand ? "Quelle meldet keinen Zustand" : l.quelle_stand ? datum(l.quelle_stand) : l.ohne_datum ? "Quelle nennt nur den Status, kein Präparierdatum" : "nicht angegeben") + '</b></li><li class="glass"><span>Zuletzt von uns geprüft</span><b>' + esc(l.abgerufen ? datum(l.abgerufen) + " (" + alter(l.abgerufen) + ")" : "noch nie") + "</b></li>" +
      (l.auch_bei && l.auch_bei.length ? '<li class="glass"><span>Auch gemeldet von</span><span>' + l.auch_bei.map(function (a) {
        /* D18: weicht die verdeckte Quelle ab, steht ihr Status dabei; es zaehlt die oben gezeigte, genauere Quelle */
        var ab = a.status && a.status !== l.status && a.status !== "unbekannt";
        return '<a href="' + esc(safeUrl(a.url)) + '" rel="noopener">' + esc(a.quelle) + "</a>" + (ab ? ' <span class="badge abw">meldet ' + esc(WORT[a.status]) + ", abweichend</span>" : "");
      }).join(", ") + "</span></li>" : "") + "</ul>" +
      (ziel ? '<p style="margin-top:18px"><a class="btn prim" href="' + esc(navLink(ziel.lat, ziel.lon)) + '" rel="noopener">Navigation zu ' + esc(ziel.name) + "</a></p>" : "");
    miniKarteZeichnen(l);
  });
}

/* ---------- Karte (U1) ---------- */
function seiteKarte(q) {
  (function () {
    var liste = filtere(q).filter(function (l) { return l.lat != null; });
    view.innerHTML = (S.demo ? '<p class="demo">Vorschau mit Beispielwerten, keine echten Daten.</p>' : "") + filterLeiste(q, "/karte") + '<div class="mapw" id="mapw"><div id="map" role="region" aria-label="Karte der Loipen"></div><div class="sel glass" id="sel"><span class="fine">Tippe auf einen Marker oder eine Strecke. ' + liste.length + " Loipen mit Standort.</span></div></div>";
    filterBinden(q, "/karte");
    var m = grundkarte(document.getElementById("map"));
    var ids = {}; liste.forEach(function (l) { ids[l.id] = l; });
    function waehle(l) {
      document.getElementById("sel").innerHTML = '<b>' + esc(l.name) + '</b><div class="fine">' + esc(l.gebiet.name) + " · " + km(l.laenge_km) + " · Stand " + esc(alter(l.abgerufen)) + '</div><div style="margin:8px 0">' + chip(l.status) + '</div><a class="btn prim" href="#/loipe/' + l.id + '">Details</a>';
    }
    // Strecken; geschlossene dezent, offene kraeftig. U32 AK 2: nur fuer die gewaehlte Region laden,
    // ohne Wahl fuer die Regionen um den Ort und spaeter fuer die, in die hineingezoomt wird
    var gezeichnet = {};
    function zeichne(slug) {
      if (gezeichnet[slug] || KARTEN.indexOf(m) < 0) return;
      gezeichnet[slug] = true;
      var st = S.strecken[slug] || {};
      Object.keys(st).forEach(function (id) {
        var l = ids[id]; if (!l || st[id].length < 2) return;
        L.polyline(st[id], {color: FARBE[l.status], weight: l.status === "geschlossen" ? 4 : 6, opacity: l.status === "geschlossen" ? .75 : 1}).addTo(m).on("click", function () { waehle(l); });
      });
    }
    function streckenFuer(slugs) { ladeStrecken(slugs).then(function () { slugs.forEach(zeichne); }).catch(function () {}); }
    var gebietWahl = q.gebiet && S.gebiete.filter(function (g) { return g.slug === q.gebiet; })[0];
    // P21: ohne Wahl die Strecken aller Regionen, die welche haben (sonst blieben sie ausserhalb von 40 km unsichtbar)
    var mitStrecken = S.idx.regionen.filter(function (r) { return r.strecken_anzahl > 0; }).map(function (r) { return r.slug; });
    var start = q.region ? [q.region] : gebietWahl ? [gebietWahl.region] : (S.idx.regionen.some(function (r) { return "strecken_anzahl" in r; }) ? mitStrecken : regionenNahe(ortFuer(q), 40));
    streckenFuer(start);
    if (!q.region && !q.gebiet) m.on("moveend", function () {
      if (m.getZoom() < 10) return;
      var b = m.getBounds().pad(.5);
      streckenFuer(S.idx.regionen.filter(function (r) { return r.mitte && b.contains(r.mitte); }).map(function (r) { return r.slug; }));
    });
    // Marker; nahe beieinander liegende werden gebuendelt, Farbe des Buendels = bester Status darin
    var cluster = L.markerClusterGroup({
      showCoverageOnHover: false, animate: false, maxClusterRadius: 44, spiderfyOnMaxZoom: true,
      iconCreateFunction: function (c) {
        var ch = c.getAllChildMarkers(), best = ch.reduce(function (a, mk) { return RANG[mk.options.status] < RANG[a] ? mk.options.status : a; }, "geschlossen");
        return punktIcon(best, String(ch.length), ch.length + " Loipen, bester Status " + WORT[best]);
      }
    });
    liste.forEach(function (l) {
      var mk = L.marker([l.lat, l.lon], {icon: punktIcon(l.status, null, l.name + ", " + WORT[l.status]), status: l.status, title: l.name});
      mk.on("click", function () { waehle(l); });
      cluster.addLayer(mk);
    });
    m.addLayer(cluster);
    function passend() {
      m.invalidateSize();
      if (liste.length) m.fitBounds(L.latLngBounds(liste.map(function (l) { return [l.lat, l.lon]; })).pad(.12), {maxZoom: 13});
      else m.setView([47.7, 11.9], 9);
    }
    setTimeout(passend, 0);
    var Alles = L.Control.extend({onAdd: function () { var b = L.DomUtil.create("button", "alles leaflet-bar"); b.type = "button"; b.setAttribute("aria-label", "Alles zeigen"); b.textContent = "⌖"; L.DomEvent.disableClickPropagation(b); b.onclick = passend; return b; }});
    new Alles({position: "topright"}).addTo(m);
  })();
}

/* ---------- Abdeckung (P13 AK 2) ---------- */
function seiteAbdeckung() {
  var je = {};
  S.gebiete.forEach(function (g) { if (g.loipen.some(function (l) { return l.status === "offen" || l.status === "eingeschraenkt"; })) je[g.region] = (je[g.region] || 0) + 1; });
  var zeilen = {};
  (S.idx.abdeckung || []).forEach(function (a) { zeilen[a.region] = a; });
  var h = '<h1>Abdeckung</h1><p class="fine">Wie viele Gebiete jeder Region eine Online-Quelle mit Loipenzustand haben. Neue Regionen kommen in Stufen dazu.</p><p class="fine">Spalten: Gebiete gesamt · mit Loipenzustand · davon mit offener Loipe · nur Stammdaten ohne Zustand · ohne Online-Quelle.</p>';
  gruppen().forEach(function (gr) {
    h += '<h2 class="sec">' + esc(gr.name) + '</h2><div class="tabw"><table class="tab"><thead><tr><th scope="col">Region</th><th scope="col">Gebiete</th><th scope="col" title="mit Loipenzustand">Zustand</th><th scope="col" title="mit offener Loipe">offen</th><th scope="col" title="nur Stammdaten">Stamm</th><th scope="col" title="ohne Online-Quelle">ohne</th></tr></thead><tbody>' +
      gr.regionen.map(function (r) { var a = zeilen[r.name] || {}; return "<tr><th scope=\"row\"><a href=\"#/loipen?region=" + esc(r.slug) + "\">" + esc(r.name) + "</a></th><td>" + r.gebiete + "</td><td>" + (a.angebunden || 0) + "</td><td>" + (je[r.slug] || 0) + "</td><td>" + (a.nur_stammdaten || 0) + "</td><td>" + (a.ohne_quelle || 0) + "</td></tr>"; }).join("") + "</tbody></table></div>";
  });
  h += '<h2 class="sec">Quellen</h2><ul class="plain">' + S.idx.quellen.map(function (x) {
    return '<li class="glass"><span><b>' + esc(x.name) + '</b><br><span class="fine">' + (x.anzahl == null ? "noch kein Lauf" : x.anzahl + " Loipen") + " · letzter Lauf " + esc(datum(x.letzter_lauf)) + "</span></span><b>" + esc({ok: "in Ordnung", warnung: "mit Warnung", fehler: "Fehler"}[x.status] || "noch nicht gelaufen") + "</b></li>";
  }).join("") + "</ul>";
  view.innerHTML = h;
}

/* ---------- Suche (U21) und Ort (U4, U35) ---------- */
/* Ein Ort ist {name, lat, lon, art}; art "gps" = vom Geraet bestimmt, "ort" = gewaehlt oder gesucht. */
function setzeOrt(o) { S.ort = o; speicher("ort", o); beschrifteOrt(); }
function nahName(lat, lon) {
  var p = {lat: lat, lon: lon}, best = null, bd = 1e9;
  S.orte.concat(S.gebiete).forEach(function (o) { var d = dist(p, o); if (d != null && d < bd) { bd = d; best = o; } });
  return best && bd < 25 ? best.name : null;
}
function gpsOrt(pos) {
  var lat = Math.round(pos.coords.latitude * 1000) / 1000, lon = Math.round(pos.coords.longitude * 1000) / 1000, n = nahName(lat, lon);
  return {name: n ? "Mein Standort · bei " + n : "Mein Standort", lat: lat, lon: lon, art: "gps"};
}
/* Standort per Geraet geht nur auf https oder localhost; auf http://<NAS-IP> sperrt der Browser ihn. */
function gpsMoeglich() { return !!(navigator.geolocation && window.isSecureContext); }
function gpsHolen(ok, fehler) {
  if (!gpsMoeglich()) { fehler(window.isSecureContext === false ? "unsicher" : "fehlt"); return; }
  navigator.geolocation.getCurrentPosition(function (p) { ok(gpsOrt(p)); }, function (e) { fehler(e && e.code === 1 ? "verweigert" : "fehler"); },
    {enableHighAccuracy: false, timeout: 10000, maximumAge: 15 * 60000});
}
/* Beim Oeffnen: gespeicherter GPS-Standort wird still aufgefrischt; beim ersten Besuch wird einmal gefragt. */
function gpsBeimStart(q) {
  if (q.ort || !gpsMoeglich()) return;
  var gespeichert = speicher("ort"), gefragt = speicher("gps_gefragt");
  if (gespeichert && gespeichert.art !== "gps") return;
  if (!gespeichert && gefragt) return;
  speicher("gps_gefragt", true);
  gpsHolen(function (o) { var alt = S.ort; setzeOrt(o); if (!alt || dist(alt, o) > 1) route(); }, function () {});
}
var GEO_URL = "https://photon.komoot.io/api/";
function ortSucheOnline(text) {
  var url = GEO_URL + "?q=" + encodeURIComponent(text) + "&lang=de&limit=8&bbox=5.8,45.8,17.2,55.1&osm_tag=place";
  return holeJson(url).then(function (r) {
    return (r.features || []).map(function (f) {
      var pr = f.properties || {}, c = (f.geometry || {}).coordinates || [];
      var zusatz = [pr.postcode, pr.county || pr.state, pr.countrycode].filter(Boolean).join(", ");
      return c.length === 2 ? {name: pr.name, zusatz: zusatz, lat: Math.round(c[1] * 1000) / 1000, lon: Math.round(c[0] * 1000) / 1000, art: "ort"} : null;
    }).filter(function (o) { return o && o.name; });
  });
}
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
  var optionen = S.orte.concat(S.gebiete.filter(function (g) { return g.lat != null; }).map(function (g) { return {name: g.name, lat: g.lat, lon: g.lon, zusatz: g.region_name}; }));
  var gesehen = {}; optionen = optionen.filter(function (o) { if (gesehen[o.name]) return false; gesehen[o.name] = 1; return true; }).sort(function (a, b) { return a.name.localeCompare(b.name, "de"); });
  var treffer = [];
  var gpsText = gpsMoeglich() ? "Mein Standort verwenden" : "Mein Standort (nur über https)";
  d.innerHTML = '<div class="box"><h2 style="margin-top:0">Standort wählen</h2>' +
    '<button type="button" class="o gps" id="geo"' + (gpsMoeglich() ? "" : ' aria-describedby="geo-info"') + '><span>' + gpsText + '</span><span aria-hidden="true">⌖</span></button>' +
    '<p class="fine" id="geo-info" role="status">' + (gpsMoeglich() ? "" : "Der Browser gibt den Standort nur auf sicheren Seiten (https) frei. Suche deinen Ort einfach unten.") + "</p>" +
    '<form id="ortsuche" class="ortsuche" role="search"><label class="vh" for="ortq">Ort oder Postleitzahl</label><input id="ortq" type="search" autocomplete="off" placeholder="Ort oder PLZ, z. B. Holzkirchen"><button type="submit" class="btn">Suchen</button></form>' +
    '<div id="ortliste" role="listbox" aria-label="Orte"></div><p><button type="button" class="btn" id="zu">Schließen</button></p></div>';
  d.hidden = false;
  var ein = d.querySelector("#ortq"), liste = d.querySelector("#ortliste"), info = d.querySelector("#geo-info");
  function zeichne(online, hinweis) {
    var t = ein.value.trim().toLowerCase();
    var lokal = optionen.filter(function (o) { return !t || o.name.toLowerCase().indexOf(t) >= 0; });
    treffer = lokal.concat(online || []);
    liste.innerHTML = (hinweis ? '<p class="fine">' + esc(hinweis) + "</p>" : "") + (treffer.length ? treffer.map(function (o, i) {
      return '<button type="button" class="o" role="option" data-i="' + i + '"><span>' + esc(o.name) + (o.zusatz ? ' <small class="fine">' + esc(o.zusatz) + "</small>" : "") + "</span>" + (i >= lokal.length ? '<small class="fine">Online</small>' : "") + "</button>";
    }).join("") : '<p class="fine">Kein bekannter Ort. Mit „Suchen“ wird online gesucht.</p>');
    liste.querySelectorAll("button.o[data-i]").forEach(function (b) { b.onclick = function () { var o = treffer[+b.dataset.i]; setzeOrt({name: o.name, lat: o.lat, lon: o.lon, art: "ort"}); d.hidden = true; route(); }; });
  }
  zeichne();
  ein.addEventListener("input", function () { zeichne(); });
  d.querySelector("#ortsuche").onsubmit = function (e) {
    e.preventDefault();
    var t = ein.value.trim();
    if (t.length < 2) return;
    zeichne([], "Suche läuft …");
    ortSucheOnline(t).then(function (r) { zeichne(r, r.length ? "" : "Online nichts gefunden."); }, function () { zeichne([], "Online-Suche gerade nicht erreichbar, nur bekannte Orte."); });
  };
  ein.focus();
  d.querySelector("#zu").onclick = function () { d.hidden = true; };
  d.onclick = function (e) { if (e.target === d) d.hidden = true; };
  d.onkeydown = function (e) { if (e.key === "Escape") d.hidden = true; };
  d.querySelector("#geo").onclick = function () {
    info.textContent = "Standort wird bestimmt …";
    gpsHolen(function (o) { setzeOrt(o); d.hidden = true; route(); }, function (grund) {
      info.textContent = {unsicher: "Der Browser gibt den Standort nur auf sicheren Seiten (https) frei. Suche deinen Ort einfach unten.",
        verweigert: "Der Standort wurde nicht freigegeben. Du kannst ihn in den Browser-Einstellungen erlauben oder unten einen Ort suchen.",
        fehlt: "Dein Gerät kann den Standort nicht bestimmen. Suche deinen Ort unten.",
        fehler: "Der Standort ließ sich gerade nicht bestimmen. Suche deinen Ort unten."}[grund];
    });
  };
}

/* ---------- Routing ---------- */
function route() {
  var q = parseQuery(location.hash), p = pfad(location.hash) || "/";
  var tab = p.indexOf("/karte") === 0 ? "karte" : p.indexOf("/loipen") === 0 || p.indexOf("/loipe/") === 0 || p.indexOf("/gebiet/") === 0 ? "loipen" : "heute";
  document.querySelectorAll(".tabs a").forEach(function (a) { if (a.dataset.tab === tab) a.setAttribute("aria-current", "page"); else a.removeAttribute("aria-current"); });
  if (q.demo && (q.demo === "1") !== S.demo) { location.reload(); return; }
  kartenAbbauen();
  view.dataset.r = (+view.dataset.r || 0) + 1; // Zaehler: Tests warten damit auf das Neuzeichnen
  if (p === "/karte") seiteKarte(q);
  else if (p === "/loipen") seiteListe(q);
  else if (p === "/abdeckung") seiteAbdeckung();
  else if (p.indexOf("/gebiet/") === 0) seiteGebiet(p.slice(8));
  else if (p.indexOf("/loipe/") === 0) seiteLoipe(p.slice(7));
  else seiteHeute(q);
  if (p.indexOf("/loipe/") !== 0 && p !== "/karte") window.scrollTo(0, 0);
}

function start() {
  laden().then(function () {
    document.getElementById("stand").textContent = "Stand der Daten: " + datum(S.idx.erzeugt) + " · Wetter: Deutscher Wetterdienst, Bright Sky, GeoSphere Austria";
    beschrifteOrt(); sucheBinden();
    document.getElementById("ort").addEventListener("click", ortDialog);
    var dk = document.getElementById("demo-knopf");
    dk.textContent = S.demo ? "Beispielansicht beenden" : "Beispielansicht mit Schnee (erfundene Werte)";
    dk.addEventListener("click", function () { try { if (S.demo) sessionStorage.removeItem("demo"); else sessionStorage.setItem("demo", "1"); } catch (e) {} location.reload(); });
    window.addEventListener("hashchange", route);
    route();
    gpsBeimStart(parseQuery(location.hash));
    if ("serviceWorker" in navigator && location.protocol.indexOf("http") === 0) navigator.serviceWorker.register("sw.js").catch(function () {});
  }).catch(function (e) {
    view.innerHTML = '<p class="leer glass">Die Daten konnten nicht geladen werden (' + esc(e.message) + "). Bitte später noch einmal versuchen.</p>";
  });
}
start();
})();
