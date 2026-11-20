---
id: 3f8eb6aa-35f7-486a-a2a6-c24cbdcb228e
type: decision
status: draft
title: Spenden nur über einen einfachen Link, Adresse aus der .env
kennung: "E-25"
rationale: "Stefan am 20.11.2026 wünscht einen Buy-me-a-coffee- oder PayPal-Spendenlink. Datenschutz-Ziel aus E-17: keine Drittanbieter beim Aufruf."
---

Der Spendenlink ist ein gewöhnlicher Link auf Buy Me a Coffee, PayPal.Me oder einen anderen Anbieter. Die Adresse steht in LOIPEN_SPENDEN_URL in der .env auf dem NAS; leer heißt, die Seite zeigt nichts. Es gibt kein eingebettetes Widget, keinen Knopf und kein Skript des Anbieters, damit beim Aufruf keine Daten an Dritte gehen (B23) und kein Cookie-Banner nötig wird. Empfehlung: PayPal.Me, weil Stefan dort nur ein Privatkonto braucht und keine Plattformgebühr anfällt; Buy Me a Coffee nimmt zusätzlich 5 % und braucht Stripe.
