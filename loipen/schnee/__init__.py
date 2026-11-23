"""Schneekarte (E-31): Sammeln von Schnee-, Wetter- und Lawinendaten auf der Loipenblick-Infrastruktur.

Grundsaetze:
- E-34: zuerst sammeln, dann zeigen. Jeder Rohwert wird unveraendert gespeichert, die Antwort der Quelle
  zusaetzlich gepackt mit Pruefsumme (rohablage.py).
- E-32: keine eigene Bewertung der Lawinenlage. Gespeichert wird nur, was der Warndienst veroeffentlicht.
- E-33: nur Quellen mit Lizenzeintrag in config/schnee.yaml (S6), kein Open-Meteo.
"""
