/* Loipenblick: Saisonstatistik (U19, U37, U38, U39). Liest nur die fertige Statistik-Datei aus daten.json;
   gerechnet wird auf dem NAS (loipen/statistik.py). Haengt sich ueber window.LB an app.js. */
(function () {
"use strict";
var LB = window.LB;
if (!LB) return;
var esc = LB.esc, zahl = LB.zahl;
var MONAT = ["Jan", "Feb", "Mär", "Apr", "Mai", "Jun", "Jul", "Aug", "Sep", "Okt", "Nov", "Dez"];
var WTAG = ["So", "Mo", "Di", "Mi", "Do", "Fr", "Sa"];
var cache = {};

function datei() { var s = LB.S.idx.statistik || {}; return LB.S.demo ? s.beispiel : s.datei; }
function lade() {
  var d = datei();
  if (!d) return Promise.resolve(null);
  if (!cache[d]) cache[d] = LB.holeJson(d).catch(function (e) { delete cache[d]; throw e; });
  return cache[d];
}
function tag(startIso, i) { var d = new Date(startIso + "T12:00:00"); d.setDate(d.getDate() + i); return d; }
function kurz(iso) { if (!iso) return "–"; var p = iso.split("-"); return p[2] + "." + p[1] + "."; }
function lang(d) { return WTAG[d.getDay()] + ", " + ("0" + d.getDate()).slice(-2) + "." + ("0" + (d.getMonth() + 1)).slice(-2) + "." + d.getFullYear(); }
function prozent(a, b) { return b ? Math.round(100 * a / b) + " %" : "–"; }
function link(q) { return "#/statistik" + LB.queryStr(q); }

/* ---------- Verlaufsdiagramm: eine Reihe, eine Achse, Luecken bleiben Luecken ---------- */
function schoen(max) {
  if (max <= 4) return 4;
  var p = Math.pow(10, Math.floor(Math.log10(max))), f = max / p;
  return (f <= 2 ? 2 : f <= 5 ? 5 : 10) * p;
}
function diagramm(box, w, reihe, art) {
  var breite = Math.max(280, box.clientWidth || 600), hoehe = breite < 560 ? 190 : 230;
  /* die Achse zeigt immer den ganzen Winter, auch wenn er noch laeuft */
  var L = 40, R = 12, O = 14, U = 26, n = Math.round((new Date(w.ende + "T12:00:00") - new Date(w.start + "T12:00:00")) / 864e5) + 1, iw = breite - L - R, ih = hoehe - O - U;
  var max = schoen(Math.max.apply(null, reihe.map(function (v) { return v || 0; }).concat([1])));
  function x(i) { return L + (n <= 1 ? iw / 2 : i * iw / (n - 1)); }
  function y(v) { return O + ih - v * ih / max; }
  var g = "";
  for (var k = 0; k <= 4; k++) {
    var v = max * k / 4, yy = y(v);
    g += '<line x1="' + L + '" x2="' + (breite - R) + '" y1="' + yy + '" y2="' + yy + '" class="gl"/><text x="' + (L - 6) + '" y="' + (yy + 4) + '" class="ax" text-anchor="end">' + (Math.round(v * 10) / 10) + "</text>";
  }
  for (var i = 0; i < n; i++) {
    var d = tag(w.start, i);
    if (d.getDate() === 1) g += '<line x1="' + x(i) + '" x2="' + x(i) + '" y1="' + O + '" y2="' + (O + ih) + '" class="gl"/><text x="' + (x(i) + 4) + '" y="' + (hoehe - 8) + '" class="ax">' + MONAT[d.getMonth()] + "</text>";
  }
  /* zusammenhaengende Abschnitte ohne Luecke */
  var flaeche = "", linie = "", punkte = "", seg = [];
  function schliesse() {
    if (!seg.length) return;
    if (seg.length === 1) { punkte += '<circle class="pt" r="4" cx="' + x(seg[0][0]).toFixed(1) + '" cy="' + y(seg[0][1]).toFixed(1) + '"/>'; seg = []; return; }
    var p = seg.map(function (s) { return (s === seg[0] ? "M" : "L") + x(s[0]).toFixed(1) + " " + y(s[1]).toFixed(1); }).join("");
    linie += p;
    flaeche += p + "L" + x(seg[seg.length - 1][0]).toFixed(1) + " " + y(0) + "L" + x(seg[0][0]).toFixed(1) + " " + y(0) + "Z";
    seg = [];
  }
  reihe.forEach(function (v, i) { if (v == null) schliesse(); else seg.push([i, v]); });
  schliesse();
  var leer = reihe.every(function (v) { return v == null; });
  var svg = '<svg class="dg ' + art.klasse + '" width="' + breite + '" height="' + hoehe + '" viewBox="0 0 ' + breite + " " + hoehe + '" role="img" aria-label="' + esc(art.aria) + '">' + g +
    '<line x1="' + L + '" x2="' + (breite - R) + '" y1="' + y(0) + '" y2="' + y(0) + '" class="bl"/>' +
    '<path d="' + flaeche + '" class="fl"/><path d="' + linie + '" class="ln"/>' + punkte +
    (leer ? '<text x="' + (L + iw / 2) + '" y="' + (O + ih / 2) + '" class="ax" text-anchor="middle">Noch keine Werte in diesem Winter</text>' : "") +
    '<line class="hx" y1="' + O + '" y2="' + (O + ih) + '" x1="0" x2="0" visibility="hidden"/><circle class="hp" r="5" cx="0" cy="0" visibility="hidden"/>' +
    '<rect class="hit" x="' + L + '" y="0" width="' + iw + '" height="' + hoehe + '" fill="transparent"/></svg><div class="tip" hidden></div>';
  box.innerHTML = svg;
  var el = box.querySelector("svg"), tip = box.querySelector(".tip"), hx = el.querySelector(".hx"), hp = el.querySelector(".hp");
  function zeige(ev) {
    var r = el.getBoundingClientRect(), px = (ev.touches ? ev.touches[0].clientX : ev.clientX) - r.left;
    var i = Math.max(0, Math.min(n - 1, Math.round((px - L) / (iw / Math.max(1, n - 1)))));
    var v = i < reihe.length ? reihe[i] : undefined;
    hx.setAttribute("x1", x(i)); hx.setAttribute("x2", x(i)); hx.setAttribute("visibility", "visible");
    if (v != null) { hp.setAttribute("cx", x(i)); hp.setAttribute("cy", y(v)); hp.setAttribute("visibility", "visible"); } else { hp.setAttribute("visibility", "hidden"); }
    tip.innerHTML = "<b>" + lang(tag(w.start, i)) + "</b><br>" + (i >= reihe.length ? "noch nicht erreicht" : v == null ? "keine Daten" : art.wert(v));
    tip.hidden = false;
    var tw = tip.offsetWidth, left = Math.min(Math.max(0, x(i) - tw / 2), breite - tw);
    tip.style.left = left + "px";
  }
  function weg() { tip.hidden = true; hx.setAttribute("visibility", "hidden"); hp.setAttribute("visibility", "hidden"); }
  var hit = el.querySelector(".hit");
  hit.addEventListener("mousemove", zeige); hit.addEventListener("mouseleave", weg);
  hit.addEventListener("touchstart", zeige, {passive: true}); hit.addEventListener("touchmove", zeige, {passive: true});
}
/* Tabellenansicht zum Diagramm: je Monat (Barrierefreiheit, auch zum Nachlesen) */
function monatsTabelle(w, reihe, art) {
  var m = {};
  reihe.forEach(function (v, i) {
    var d = tag(w.start, i), k = d.getFullYear() + "-" + d.getMonth();
    var e = m[k] || (m[k] = {name: MONAT[d.getMonth()] + " " + d.getFullYear(), tage: 0, beob: 0, max: null});
    if (v != null) { e.beob++; if (v > 0) e.tage++; e.max = e.max == null ? v : Math.max(e.max, v); }
  });
  return '<details class="werte"><summary>Werte als Tabelle</summary><div class="tabw"><table class="tab"><thead><tr><th scope="col">Monat</th><th scope="col">' + art.spalte + '</th><th scope="col">Tage mit Daten</th><th scope="col">Höchstwert</th></tr></thead><tbody>' +
    Object.keys(m).map(function (k) { var e = m[k]; return '<tr><th scope="row">' + e.name + "</th><td>" + e.tage + "</td><td>" + e.beob + "</td><td>" + (e.max == null ? "–" : e.max) + "</td></tr>"; }).join("") + "</tbody></table></div></details>";
}

/* ---------- Seite #/statistik ---------- */
function seite(q) {
  var view = LB.view;
  view.innerHTML = '<h1>Statistik</h1><p class="fine">Lädt …</p>';
  var r0 = view.dataset.r;
  lade().then(function (st) {
    if (view.dataset.r !== r0) return; /* inzwischen andere Seite */
    if (!st || !st.winter.length) {
      view.innerHTML = '<h1>Statistik</h1><p class="leer glass">Noch keine Saisondaten. Gezählt wird ab dem ersten Abruf im Winter (1. November bis 30. April).</p>';
      return;
    }
    zeichne(q, st);
  }).catch(function (e) {
    view.innerHTML = '<h1>Statistik</h1><p class="leer glass">Die Statistik konnte nicht geladen werden (' + esc(e.message) + ").</p>";
  });
}

function zeichne(q, st) {
  var view = LB.view;
  var wi = 0;
  st.winter.forEach(function (w, i) { if (w.name === q.winter) wi = i; });
  var w = st.winter[wi], vor = st.winter[wi + 1] || null;
  var g = q.gebiet && w.gebiete[q.gebiet] ? q.gebiet : null;
  var region = g ? w.gebiete[g].region : (q.region && LB.S.regionen[q.region] ? q.region : null);
  var auswahl = g ? w.gebiete[g] : region ? w.regionen[region] : w.gesamt;
  var name = g ? w.gebiete[g].name : region ? LB.S.regionen[region].region.name : "alle Gebiete";
  var reihe = auswahl ? auswahl.befahrbar : [];
  var tage = auswahl ? auswahl.tage : 0, beob = reihe.filter(function (v) { return v != null; }).length;
  var spitze = Math.max.apply(null, reihe.map(function (v) { return v || 0; }).concat([0]));
  var befIdx = []; reihe.forEach(function (v, i) { if (v) befIdx.push(i); });
  var erster = befIdx.length ? tag(w.start, befIdx[0]) : null, letzter = befIdx.length ? tag(w.start, befIdx[befIdx.length - 1]) : null;
  var laufend = w.bis < w.ende;

  var regs = LB.gruppen().map(function (gr) {
    var opts = gr.regionen.filter(function (r) { return w.regionen[r.slug]; }).map(function (r) { return '<option value="' + esc(r.slug) + '"' + (region === r.slug ? " selected" : "") + ">" + esc(r.name) + "</option>"; }).join("");
    return opts ? '<optgroup label="' + esc(gr.name) + '">' + opts + "</optgroup>" : "";
  }).join("");
  var h = (st.beispiel ? '<p class="demo">Beispielwinter mit erfundenen Werten, keine echten Daten.</p>' : "") +
    "<h1>Statistik</h1>" +
    '<p class="fine">Wie viele Tage die Loipen befahrbar waren, wie der Winter verlief und wie verlässlich die Quellen melden. ' + esc(st.regel) + "</p>" +
    '<div class="filter" role="group" aria-label="Auswahl">' +
    '<label class="vh" for="s-winter">Winter</label><select id="s-winter">' + st.winter.map(function (x) { return '<option value="' + esc(x.name) + '"' + (x === w ? " selected" : "") + ">Winter " + esc(x.name) + "</option>"; }).join("") + "</select>" +
    '<label class="vh" for="s-region">Region</label><select id="s-region"><option value="">Alle Regionen</option>' + regs + "</select>" +
    (g ? '<a class="tog" aria-pressed="true" href="' + link({winter: q.winter, region: region}) + '">' + esc(name) + ' <span aria-hidden="true">×</span><span class="vh"> Gebiet abwählen</span></a>' : "") + "</div>";

  h += '<h2 class="sec">Winter ' + esc(w.name) + " · " + esc(name) + "</h2>" +
    (laufend ? '<p class="fine">Laufender Winter, Stand ' + esc(kurz(w.bis)) + (beob ? ", " + beob + (beob === 1 ? " Tag" : " Tage") + " mit Daten" : ", noch keine Tage mit Daten") + ".</p>" : "") +
    '<div class="kv s-kz"><div class="glass"><small>Tage mit befahrbarer Loipe</small><b id="s-tage">' + tage + '</b></div><div class="glass"><small>Tage mit Daten</small><b>' + beob + " von " + Math.min(w.tage, reihe.length) + '</b></div><div class="glass"><small>Erster befahrbarer Tag</small><b>' + (erster ? esc(kurz(iso(erster))) : "–") + '</b></div><div class="glass"><small>Letzter befahrbarer Tag</small><b>' + (letzter ? esc(kurz(iso(letzter))) : "–") + '</b></div><div class="glass"><small>Höchstens gleichzeitig befahrbar</small><b>' + spitze + " Loipen</b></div>" +
    (vor && vorWert(vor, g, region) != null ? '<div class="glass"><small>Vorwinter ' + esc(vor.name) + "</small><b>" + vorWert(vor, g, region) + " Tage</b></div>" : "") + "</div>";

  var artLoipen = {klasse: "befahrbar", aria: "Befahrbare Loipen pro Tag, Winter " + w.name + ", " + name + ": " + tage + " Tage mit befahrbarer Loipe", spalte: "Tage mit befahrbarer Loipe",
    wert: function (v) { return v + (v === 1 ? " Loipe" : " Loipen") + " befahrbar"; }};
  h += '<h3 class="s-titel">Befahrbare Loipen pro Tag</h3><div class="dgbox" id="s-verlauf"></div>' + monatsTabelle(w, reihe, artLoipen);
  var schnee = g ? w.gebiete[g].schnee : null, hatSchnee = schnee && schnee.some(function (v) { return v != null; });
  var artSchnee = {klasse: "schnee", aria: "Schneehöhe in Zentimetern, " + name, spalte: "Tage mit Schnee",
    wert: function (v) { return v + " cm Schnee"; }};
  if (g) h += '<h3 class="s-titel">Schneehöhe an der Messstation (cm)</h3>' + (hatSchnee ? '<div class="dgbox" id="s-schnee"></div>' + monatsTabelle(w, schnee, artSchnee) : '<p class="fine">Für dieses Gebiet gibt es in diesem Winter keine Schneemessung.</p>') +
    '<p><a href="#/gebiet/' + esc(g) + '">Zum Gebiet ' + esc(name) + "</a></p>";

  /* U38: Rangliste der Gebiete */
  var gebiete = Object.keys(w.gebiete).filter(function (s) { return !region || w.gebiete[s].region === region; })
    .map(function (s) { return Object.assign({slug: s}, w.gebiete[s]); }).filter(function (x) { return x.beobachtet > 0; })
    .sort(function (a, b) { return b.tage - a.tage || b.loipen - a.loipen || a.name.localeCompare(b.name, "de"); });
  if (!g) {
    h += '<h2 class="sec">Gebiete nach befahrbaren Tagen</h2>' + (gebiete.length ? '<div class="tabw"><table class="tab" id="s-gebiete"><thead><tr><th scope="col">Gebiet</th><th scope="col">Tage</th><th scope="col" title="Tage mit Daten">Daten</th><th scope="col">erster</th><th scope="col">letzter</th>' + (vor ? '<th scope="col">' + esc(vor.name) + "</th>" : "") + "</tr></thead><tbody>" +
      gebiete.slice(0, 30).map(function (x) {
        var v = vor && vor.gebiete[x.slug];
        return '<tr><th scope="row"><a href="' + link({winter: q.winter, gebiet: x.slug}) + '">' + esc(x.name) + '</a><br><span class="fine">' + esc((LB.S.regionen[x.region] || {region: {name: ""}}).region.name) + "</span></th><td><b>" + x.tage + "</b></td><td>" + x.beobachtet + "</td><td>" + esc(kurz(x.erster)) + "</td><td>" + esc(kurz(x.letzter)) + "</td>" + (vor ? "<td>" + (v ? v.tage : "–") + "</td>" : "") + "</tr>";
      }).join("") + "</tbody></table></div>" + (gebiete.length > 30 ? '<p class="fine">' + (gebiete.length - 30) + " weitere Gebiete, Auswahl über die Region.</p>" : "") : '<p class="fine">Noch kein Gebiet mit Daten in diesem Winter.</p>');
  }

  /* U19/U38: Loipen der Auswahl */
  var loipen = LB.S.loipen.filter(function (l) { return w.loipen[l.id] && (!g || l.gebiet.slug === g) && (!region || l.gebiet.region === region); })
    .map(function (l) { return {l: l, s: w.loipen[l.id]}; }).filter(function (e) { return g || e.s.tage > 0; })
    .sort(function (a, b) { return b.s.tage - a.s.tage || b.s.offen - a.s.offen || a.l.name.localeCompare(b.l.name, "de"); });
  var zeig = loipen.slice(0, g ? 200 : 20);
  h += '<h2 class="sec">' + (g ? "Loipen in " + esc(name) : "Loipen mit den meisten befahrbaren Tagen") + "</h2>" + (zeig.length ? '<div class="tabw"><table class="tab" id="s-loipen"><thead><tr><th scope="col">Loipe</th><th scope="col">Tage</th><th scope="col" title="davon offen, nicht nur eingeschränkt">offen</th><th scope="col">erster</th><th scope="col">letzter</th></tr></thead><tbody>' +
    zeig.map(function (e) {
      return '<tr><th scope="row"><a href="#/loipe/' + e.l.id + '">' + esc(e.l.name) + "</a>" + (g ? "" : '<br><span class="fine">' + esc(e.l.gebiet.name) + "</span>") + (e.s.unbestaetigt ? ' <span class="badge abw">nur ' + esc(e.l.quelle.name) + "</span>" : "") + "</th><td><b>" + e.s.tage + "</b></td><td>" + e.s.offen + "</td><td>" + esc(kurz(e.s.erster)) + "</td><td>" + esc(kurz(e.s.letzter)) + "</td></tr>";
    }).join("") + "</tbody></table></div>" : '<p class="fine">Noch keine Loipe mit Daten.</p>');

  /* U39: Zuverlaessigkeit der Quellen */
  h += '<h2 class="sec">Wie verlässlich die Quellen melden</h2><p class="fine"><b>Tage mit Daten</b>: an wie vielen Tagen seit dem ersten Abruf die Quelle erreichbar war und Loipen lieferte. <b>Übereinstimmung</b>: Führen zwei Quellen dieselbe Loipe, wird pro Tag verglichen, ob beide sie als befahrbar melden oder beide nicht. Gezählt werden Loipentage.</p>' +
    '<div class="tabw"><table class="tab" id="s-quellen"><thead><tr><th scope="col">Quelle</th><th scope="col">Tage mit Daten</th><th scope="col">Übereinstimmung</th></tr></thead><tbody>' +
    w.quellen.map(function (x) {
      var v = x.vergleich, p = x.paare.slice(0, 3);
      return '<tr><th scope="row">' + esc(x.name) + (p.length ? '<br><span class="fine">verglichen mit ' + p.map(function (y) { return esc(y.mit) + " " + prozent(y.gleich, y.tage); }).join(", ") + "</span>" : "") + "</th><td>" + prozent(x.tage_mit_daten, x.tage_moeglich) + '<br><span class="fine">' + x.tage_mit_daten + " von " + x.tage_moeglich + "</span></td><td>" + (v.tage ? "<b>" + prozent(v.gleich, v.tage) + '</b><br><span class="fine">' + v.tage + " Loipentage</span>" : '<span class="fine">kein Vergleich, keine gemeinsame Loipe</span>') + "</td></tr>";
    }).join("") + "</tbody></table></div>";
  view.innerHTML = h;

  function malen() {
    var b = document.getElementById("s-verlauf");
    if (b) diagramm(b, w, reihe, artLoipen);
    var s = document.getElementById("s-schnee");
    if (s) diagramm(s, w, schnee, artSchnee);
  }
  malen();
  var breite = view.clientWidth;
  if (LB.beiGroesse) window.removeEventListener("resize", LB.beiGroesse);
  LB.beiGroesse = function () { if (!document.getElementById("s-verlauf")) return; if (Math.abs(view.clientWidth - breite) > 20) { breite = view.clientWidth; malen(); } };
  window.addEventListener("resize", LB.beiGroesse);
  function sel(id, k) {
    var e = document.getElementById(id);
    e.addEventListener("change", function () { var n = {winter: q.winter, region: region}; n[k] = e.value; if (k === "region") delete n.gebiet; location.hash = link(n); });
  }
  sel("s-winter", "winter"); sel("s-region", "region");
}
function iso(d) { return d.getFullYear() + "-" + ("0" + (d.getMonth() + 1)).slice(-2) + "-" + ("0" + d.getDate()).slice(-2); }
function vorWert(vor, g, region) {
  if (g) return vor.gebiete[g] ? vor.gebiete[g].tage : null;
  if (region) return vor.regionen[region] ? vor.regionen[region].tage : null;
  return vor.gesamt.beobachtet ? vor.gesamt.tage : null;
}

/* ---------- Abschnitt auf der Loipen-Seite (U19) ---------- */
function saisonLoipe(l, box) {
  lade().then(function (st) {
    if (!box.isConnected) return;
    var zeilen = (st ? st.winter : []).filter(function (w) { return w.loipen[l.id]; });
    if (!zeilen.length) { box.innerHTML = '<p class="fine">Noch keine Saisondaten für diese Loipe. Gezählt wird ab dem ersten Abruf im Winter. <a href="#/statistik">Zur Statistik</a></p>'; return; }
    box.innerHTML = (st.beispiel ? '<p class="demo">Beispielwinter mit erfundenen Werten.</p>' : "") +
      '<div class="tabw"><table class="tab" id="saison-tab"><thead><tr><th scope="col">Winter</th><th scope="col">befahrbar</th><th scope="col">davon offen</th><th scope="col" title="Tage mit Daten">Daten</th><th scope="col">erster</th><th scope="col">letzter</th></tr></thead><tbody>' +
      zeilen.map(function (w, i) {
        var s = w.loipen[l.id], v = zeilen[i + 1] && zeilen[i + 1].loipen[l.id], diff = v ? s.tage - v.tage : null;
        return '<tr><th scope="row">' + esc(w.name) + (w.bis < w.ende ? ' <span class="fine">läuft</span>' : "") + "</th><td><b>" + s.tage + " Tage</b>" + (diff != null ? '<br><span class="fine">' + (diff >= 0 ? "+" : "−") + Math.abs(diff) + " zum Vorwinter</span>" : "") + "</td><td>" + s.offen + "</td><td>" + s.beobachtet + "</td><td>" + esc(kurz(s.erster)) + "</td><td>" + esc(kurz(s.letzter)) + "</td></tr>";
      }).join("") + '</tbody></table></div><p class="fine">' + esc(st.regel) + ' <a href="' + link({gebiet: l.gebiet.slug}) + '">Statistik für ' + esc(l.gebiet.name) + "</a></p>";
  }).catch(function () { if (box.isConnected) box.innerHTML = '<p class="fine">Die Saisonstatistik konnte nicht geladen werden.</p>'; });
}

LB.seiten["/statistik"] = seite;
LB.saisonLoipe = saisonLoipe;
})();
