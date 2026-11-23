"""GeoSphere SNOWGRID-CL (snowgrid_cl-v2-1d-1km, CC BY 4.0): modellierte Schneehoehe im 1-km-Raster fuer Oesterreich.

In dieser Stufe wird die Schneehoehe an den Punkten der Loipenblick-Gebiete in Oesterreich gesammelt (je Gebiet
ein Punkt mit dessen Hoehe, Messart "modell"); das Mittel je Warnregion und Hoehenband folgt mit S10.
Weil GeoSphere das Archiv ab 1961 anbietet, geht nichts verloren, wenn ein Tag ausfaellt.
Die Daten haben einen Tag Verzug. snow_depth kommt in Metern und wird in cm gespeichert.
"""

from datetime import datetime, timedelta

from sqlalchemy import select

from loipen.schnee.adapter._hilfe import antwort, json_aus, zahl
from loipen.schnee.daten import Ergebnis, MesswertDaten, StationDaten


def punkte(session) -> list[dict]:
    from loipen.models import Gebiet, Region
    if session is None:
        return []
    zeilen = session.execute(select(Gebiet.slug, Gebiet.name, Gebiet.lat, Gebiet.lon, Gebiet.hoehe_m)
                             .join(Region).where(Region.land == "AT", Gebiet.lat.is_not(None))).all()
    return [{"kennung": f"gebiet:{s}", "name": n, "lat": la, "lon": lo, "hoehe": h} for s, n, la, lo, h in zeilen]


def abrufe(q, fetcher, jetzt, session=None):
    o = q.optionen
    p = punkte(session)
    bis = jetzt.date() - timedelta(days=1)
    von = bis - timedelta(days=o.get("tage", 3))
    paket = o.get("paket", 40)
    for i in range(0, len(p), paket):
        teil = p[i:i + paket]
        lat_lon = "&".join(f"lat_lon={x['lat']:.4f},{x['lon']:.4f}" for x in teil)
        url = o["url"].format(von=von.isoformat(), bis=bis.isoformat(), lat_lon=lat_lon)
        yield antwort(fetcher, url, punkte=teil)


def verarbeite(antwort, q) -> Ergebnis:
    daten = json_aus(antwort.inhalt)
    erg = Ergebnis()
    zeiten = [datetime.fromisoformat(t) for t in daten.get("timestamps", [])]
    punkte_ = antwort.meta.get("punkte") or []
    for i, f in enumerate(daten.get("features", [])):
        lon, lat = f["geometry"]["coordinates"][:2]
        if i < len(punkte_):
            p = punkte_[i]
        else:  # ohne Zuordnung (z. B. Fixture-Test): Punkt nach Lage benennen
            p = {"kennung": f"punkt:{lat:.3f},{lon:.3f}", "name": f"{lat:.3f}, {lon:.3f}", "lat": lat, "lon": lon,
                 "hoehe": q.optionen.get("hoehe_unbekannt")}
        erg.stationen.append(StationDaten(kennung=p["kennung"], name=f"SNOWGRID {p['name']}", lat=p["lat"],
                                          lon=p["lon"], hoehe_m=p.get("hoehe"), betreiber="GeoSphere Austria",
                                          land="AT", messart="modell", messgroessen=["hs"]))
        reihe = ((f.get("properties") or {}).get("parameters") or {}).get("snow_depth", {}).get("data", [])
        for zeit, w in zip(zeiten, reihe):
            w = zahl(w)
            if w is not None:
                erg.messwerte.append(MesswertDaten(station=p["kennung"], zeitpunkt=zeit, groesse="hs",
                                                   wert=round(w * 100, 1), einheit="cm"))
    return erg
