/* B13: Wer sich auf der Auswertung anmeldet, wird in diesem Browser nicht mehr mitgezaehlt.
   Der Merker liegt nur im lokalen Speicher dieses Browsers und geht nirgends hin. */
(function () {
  "use strict";
  var KEY = "loipen_nicht_zaehlen";
  var p = document.getElementById("dieser");
  var text = document.getElementById("dieser-text");
  var knopf = document.getElementById("dieser-knopf");
  function lies() { try { return localStorage.getItem(KEY) === "1"; } catch (e) { return false; } }
  function setze(an) { try { if (an) localStorage.setItem(KEY, "1"); else localStorage.removeItem(KEY); } catch (e) {} zeige(); }
  function zeige() {
    var aus = lies();
    text.textContent = aus ? "Dieser Browser wird nicht mitgezählt." : "Dieser Browser wird mitgezählt.";
    knopf.textContent = aus ? "Wieder mitzählen" : "Nicht mehr mitzählen";
    p.hidden = false;
  }
  function gewaehlt() { try { return sessionStorage.getItem("zaehler_gewaehlt") === "1"; } catch (e) { return false; } }
  if (p.dataset.angemeldet !== "1") return;
  if (gewaehlt()) zeige(); else setze(true);
  knopf.addEventListener("click", function () { try { sessionStorage.setItem("zaehler_gewaehlt", "1"); } catch (e) {} setze(!lies()); });
})();
