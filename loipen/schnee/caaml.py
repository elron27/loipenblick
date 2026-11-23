"""Lawinenlageberichte im Format CAAML v6 (EAWS), als XML oder JSON (S4).

Uebernommen wird nur, was der Bericht sagt (E-32): Stufe je Hoehenband und Tageszeit, Probleme mit Exposition
und Hoehe, Tendenz, Gueltigkeit, Ausgabezeit und Link. Unbekannte Felder werden uebergangen (S4 AK 4).
"""

import json
from datetime import datetime

from lxml import etree

from loipen.schnee.daten import BerichtDaten, Problem, Stufe

TAGESZEIT = {"earlier": "vormittag", "later": "nachmittag", "all_day": "ganztags", None: "ganztags", "": "ganztags"}
STUFEN = {"low", "moderate", "considerable", "high", "very_high", "no_snow", "no_rating"}


def _zeit(text: str | None) -> datetime | None:
    if not text:
        return None
    return datetime.fromisoformat(text.strip().replace("Z", "+00:00"))


def _grenze(wert) -> int | str | None:
    """Hoehe in m oder "treeline" (Waldgrenze), genau wie im Bericht."""
    if wert is None or wert == "":
        return None
    text = str(wert).strip().lower()
    if text == "treeline":
        return "treeline"
    try:
        return int(float(text))
    except ValueError:
        return None


def _hoehen(elev: dict | None) -> tuple[int | str | None, int | str | None]:
    elev = elev or {}
    return _grenze(elev.get("lowerBound")), _grenze(elev.get("upperBound"))


def _liste(b: dict, *namen) -> list:
    """CAAML-v6-Dateien schreiben Listen mal im Plural (dangerRatings), mal im Singular (dangerRating)."""
    for n in namen:
        v = b.get(n)
        if v:
            return v if isinstance(v, list) else [v]
    return []


def _bericht(b: dict, sprache: str | None) -> BerichtDaten | None:
    gueltig = b.get("validTime") or {}
    von, bis = _zeit(gueltig.get("startTime")), _zeit(gueltig.get("endTime"))
    ausgabe = _zeit(b.get("publicationTime"))
    regionen = [r.get("regionID") for r in _liste(b, "regions") if r.get("regionID")]
    if not (von and bis and ausgabe and regionen):
        return None
    stufen = []
    for d in _liste(b, "dangerRatings", "dangerRating"):
        wert = d.get("mainValue")
        if wert not in STUFEN:
            continue
        unten, oben = _hoehen(d.get("elevation"))
        stufen.append(Stufe(stufe=wert, tageszeit=TAGESZEIT.get(d.get("validTimePeriod"), "ganztags"),
                            hoehe_unten=unten, hoehe_oben=oben,
                            expositionen=list(_liste(d, "aspects", "aspect"))))
    probleme = []
    for p in _liste(b, "avalancheProblems", "avalancheProblem"):
        if not p.get("problemType"):
            continue
        unten, oben = _hoehen(p.get("elevation"))
        probleme.append(Problem(art=p["problemType"], expositionen=list(_liste(p, "aspects", "aspect")),
                                hoehe_unten=unten, hoehe_oben=oben,
                                tageszeit=TAGESZEIT.get(p.get("validTimePeriod"), "ganztags")))
    tendenz = None
    t = b.get("tendency")
    if isinstance(t, list) and t:
        tendenz = t[0].get("tendencyType")
    elif isinstance(t, dict):
        tendenz = t.get("tendencyType")
    link = None
    for ext in (b.get("metaData") or {}).get("extFiles") or []:
        if ext.get("fileType") == "linkToWebPage" and ext.get("fileReferenceURI"):
            link = ext["fileReferenceURI"]
            break
    return BerichtDaten(bulletin_id=str(b.get("bulletinID") or "|".join(regionen))[:100], ausgabe_at=ausgabe,
                        gueltig_von=von, gueltig_bis=bis, regionen=regionen, stufen=stufen, probleme=probleme,
                        sprache=b.get("lang") or sprache, link=link, tendenz=tendenz)


# ------------------------------------------------------------------------------------------------ XML nach dict
def _ohne_ns(tag) -> str:
    return etree.QName(tag).localname if isinstance(tag, str) else ""


def _text(el, name):
    for k in el:
        if _ohne_ns(k.tag) == name:
            return (k.text or "").strip()
    return None


def _kind(el, name):
    for k in el:
        if _ohne_ns(k.tag) == name:
            return k
    return None


def _elevation(el):
    e = _kind(el, "elevation")
    if e is None:
        return None
    return {"lowerBound": _text(e, "lowerBound"), "upperBound": _text(e, "upperBound")}


def _xml_bulletin(el) -> dict:
    d: dict = {"bulletinID": el.get("bulletinID") or el.get("id"), "lang": el.get("lang") or el.get("{http://www.w3.org/XML/1998/namespace}lang"),
               "publicationTime": _text(el, "publicationTime"), "regions": [], "dangerRatings": [],
               "avalancheProblems": [], "metaData": {"extFiles": []}}
    vt = _kind(el, "validTime")
    if vt is not None:
        d["validTime"] = {"startTime": _text(vt, "startTime"), "endTime": _text(vt, "endTime")}
    for k in el:
        name = _ohne_ns(k.tag)
        if name == "region":
            d["regions"].append({"regionID": k.get("regionID") or k.get("id"), "name": _text(k, "name")})
        elif name == "dangerRating":
            d["dangerRatings"].append({"mainValue": _text(k, "mainValue"), "elevation": _elevation(k),
                                       "validTimePeriod": _text(k, "validTimePeriod"),
                                       "aspects": [(a.text or "").strip() for a in k if _ohne_ns(a.tag) == "aspect"]})
        elif name == "avalancheProblem":
            d["avalancheProblems"].append({
                "problemType": _text(k, "problemType"), "elevation": _elevation(k),
                "aspects": [(a.text or "").strip() for a in k if _ohne_ns(a.tag) == "aspect"],
                "validTimePeriod": _text(k, "validTimePeriod")})
        elif name == "tendency":
            d["tendency"] = [{"tendencyType": _text(k, "tendencyType")}]
        elif name == "metaData":
            for ext in k.iter():
                if _ohne_ns(ext.tag) == "extFile":
                    d["metaData"]["extFiles"].append({"fileType": _text(ext, "fileType"),
                                                      "fileReferenceURI": _text(ext, "fileReferenceURI")})
    return d


def lies(inhalt: bytes) -> list[BerichtDaten]:
    """Alle Berichte einer CAAML-v6-Datei (XML oder JSON)."""
    kopf = inhalt.lstrip()[:1]
    if kopf in (b"{", b"["):
        daten = json.loads(inhalt)
        bulletins = daten.get("bulletins", []) if isinstance(daten, dict) else daten
    else:
        wurzel = etree.fromstring(inhalt, parser=etree.XMLParser(resolve_entities=False, no_network=True))
        bulletins = [_xml_bulletin(el) for el in wurzel.iter() if _ohne_ns(el.tag) == "bulletin"]
    berichte = []
    for b in bulletins:
        bericht = _bericht(b, None)
        if bericht:
            berichte.append(bericht)
    return berichte
