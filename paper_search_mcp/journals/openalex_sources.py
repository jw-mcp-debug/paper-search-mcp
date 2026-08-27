"""
journals/openalex_sources.py
============================
Kennzahlen zu Zeitschriften aus dem OpenAlex-/sources-Endpoint.

Bewusste Grenze: Der Journal Impact Factor (Clarivate, JCR) wird hier NICHT
abgebildet — er ist proprietär und ohne Lizenz nicht zugänglich. Geliefert wird
'2yr_mean_citedness': der mittlere Zitationsschnitt der Arbeiten der letzten
zwei Jahre auf OpenAlex-Datenbasis. Ähnliches Konzept, andere Datengrundlage,
andere Zahl. Nirgends als 'Impact Factor' bezeichnen.

Kreditverbrauch: /sources kostet dasselbe wie /works — 1 Credit je Request,
unabhängig davon, wie viele IDs in einem Batch stecken. Ein Batch von 50
Zeitschriften ist also so teuer wie ein einzelner Work-Abruf.

HTTP-Schicht, API-Key und Fehlerübersetzung kommen aus
``citations/openalex_graph.py``; hier wird nichts davon dupliziert.
"""

from __future__ import annotations

import logging
import re
from typing import Dict, List, Optional

from ..citations.openalex_graph import OpenAlexFehler, hole_json, kurz_id
from ..paper import Paper

logger = logging.getLogger(__name__)

OPENALEX_SOURCES = "https://api.openalex.org/sources"

# select= erlaubt auf /sources keine verschachtelten Felder — 'summary_stats'
# muss als ganzes Objekt geholt werden (geprüft am 27.08.2026).
_SELECT_QUELLE = (
    "id,display_name,issn_l,issn,type,is_oa,is_in_doaj,"
    "host_organization_name,apc_usd,works_count,summary_stats"
)

# OpenAlex erlaubt bis zu 50 mit "|" verknüpfte Werte je Filter.
_BATCH_GROESSE = 50

# Prozessweiter Cache. Zeitschriften wiederholen sich innerhalb einer
# Recherchesitzung stark. Kein TTL: der Prozess läuft nicht lange genug, als
# dass sich Jahreskennzahlen ändern könnten.
_CACHE: Dict[str, Dict] = {}

_ISSN_MUSTER = re.compile(r"^\d{4}-\d{3}[\dxX]$")
_SOURCE_ID_MUSTER = re.compile(r"^S\d+$")


def cache_leeren() -> None:
    """Nur für Tests und für einen erzwungenen Neuabruf."""
    _CACHE.clear()


def ist_issn(text: str) -> bool:
    """True für '0005-1098' und '1748-0221X'."""
    return bool(_ISSN_MUSTER.match((text or "").strip()))


def ist_source_id(text: str) -> bool:
    """True für 'S51360982'."""
    return bool(_SOURCE_ID_MUSTER.match((text or "").strip().upper()))


def _zu_kennzahlen(quelle: Dict) -> Dict:
    """Flacht ein OpenAlex-Source-Objekt auf die Felder ab, die gebraucht werden.

    Fehlende Werte werden weggelassen statt mit 0 gefüllt: eine 0 in einer
    Kennzahlenspalte liest sich als Aussage über die Zeitschrift, ist aber
    fast immer eine Datenlücke.
    """
    stats = quelle.get("summary_stats") or {}
    kennzahlen = {
        "quelle_id": kurz_id(quelle.get("id", "")),
        "name": quelle.get("display_name") or "",
        "issn_l": quelle.get("issn_l") or "",
        "typ": quelle.get("type") or "",
        "verlag": quelle.get("host_organization_name") or "",
        "zeitschrift_oa": bool(quelle.get("is_oa")),
        "in_doaj": bool(quelle.get("is_in_doaj")),
    }

    for ziel, wert in (
        ("zit_schnitt_2j", stats.get("2yr_mean_citedness")),
        ("h_index", stats.get("h_index")),
        ("i10_index", stats.get("i10_index")),
        ("arbeiten_gesamt", quelle.get("works_count")),
        ("apc_usd", quelle.get("apc_usd")),
    ):
        if wert:
            kennzahlen[ziel] = round(wert, 3) if isinstance(wert, float) else wert

    return {schluessel: wert for schluessel, wert in kennzahlen.items() if wert != ""}


def hole_quellen(source_ids: List[str]) -> Dict[str, Dict]:
    """Batch-Abruf von Zeitschriftenkennzahlen.

    Kostet 1 Request je angefangene 50 IDs; bereits gecachte IDs kosten nichts.
    Liefert ein Dict source_id -> Kennzahlen-Dict. Unbekannte IDs fehlen im
    Ergebnis (kein Fehler, keine Platzhalter-Nullen).
    """
    ids = []
    for eintrag in source_ids:
        kurz = kurz_id(eintrag).upper()
        if kurz and ist_source_id(kurz) and kurz not in ids:
            ids.append(kurz)

    ergebnis = {kennung: _CACHE[kennung] for kennung in ids if kennung in _CACHE}
    offen = [kennung for kennung in ids if kennung not in _CACHE]

    for start in range(0, len(offen), _BATCH_GROESSE):
        block = offen[start : start + _BATCH_GROESSE]
        daten = hole_json(
            OPENALEX_SOURCES,
            {
                "filter": "ids.openalex:" + "|".join(block),
                "select": _SELECT_QUELLE,
                "per-page": len(block),
            },
        )
        for quelle in daten.get("results", []):
            kennzahlen = _zu_kennzahlen(quelle)
            kennung = kennzahlen.get("quelle_id")
            if kennung:
                _CACHE[kennung] = kennzahlen
                ergebnis[kennung] = kennzahlen

    return ergebnis


def quelle_per_issn(issn: str) -> Optional[Dict]:
    """Einzelabruf über ISSN oder ISSN-L. Kostet 1 Request."""
    kennung = (issn or "").strip()
    if not kennung:
        return None
    daten = hole_json(
        OPENALEX_SOURCES,
        {"filter": f"issn:{kennung}", "select": _SELECT_QUELLE, "per-page": 1},
    )
    treffer = daten.get("results") or []
    if not treffer:
        return None
    kennzahlen = _zu_kennzahlen(treffer[0])
    if kennzahlen.get("quelle_id"):
        _CACHE[kennzahlen["quelle_id"]] = kennzahlen
    return kennzahlen


def quelle_per_name(name: str) -> Optional[Dict]:
    """Unscharfe Suche über den Zeitschriftennamen. Kostet 1 Request.

    Nur als Fallback, wenn weder Source-ID noch ISSN vorliegen — die Zuordnung
    ist nicht eindeutig und muss in der Ausgabe als unsicher gekennzeichnet
    werden.
    """
    suchbegriff = (name or "").strip()
    if not suchbegriff:
        return None
    daten = hole_json(
        OPENALEX_SOURCES,
        {"search": suchbegriff, "select": _SELECT_QUELLE, "per-page": 1},
    )
    treffer = daten.get("results") or []
    if not treffer:
        return None
    kennzahlen = _zu_kennzahlen(treffer[0])
    if kennzahlen.get("quelle_id"):
        _CACHE[kennzahlen["quelle_id"]] = kennzahlen
    return kennzahlen


def _extras_anreichern(extras: List[Dict]) -> None:
    """Trägt die Kennzahlen in eine Liste von ``extra``-Dicts ein.

    Gemeinsamer Kern von :func:`reichere_an` (Paper-Objekte) und
    :func:`reichere_dicts_an` (bereits serialisierte Treffer). Sammelt die
    distinkten quelle_id und holt sie in einem einzigen Batch — nicht ein
    Request pro Treffer. Fehler werden geloggt und geschluckt: Die Anreicherung
    ist Zusatzinformation und darf eine funktionierende Trefferliste nie kippen.
    """
    ids = []
    for extra in extras:
        kennung = (extra or {}).get("quelle_id") or ""
        if kennung and kennung not in ids:
            ids.append(kennung)
    if not ids:
        return

    try:
        kennzahlen_je_quelle = hole_quellen(ids)
    except OpenAlexFehler as exc:
        logger.warning("Zeitschriftenkennzahlen nicht abrufbar: %s", exc)
        return
    except Exception as exc:  # pragma: no cover - defensiv
        logger.warning("Zeitschriftenkennzahlen unerwartet fehlgeschlagen: %s", exc)
        return

    for extra in extras:
        kennzahlen = kennzahlen_je_quelle.get((extra or {}).get("quelle_id") or "")
        if not kennzahlen:
            continue
        if "zit_schnitt_2j" in kennzahlen:
            extra["zit_schnitt_2j"] = kennzahlen["zit_schnitt_2j"]
        if "h_index" in kennzahlen:
            extra["zeitschrift_h_index"] = kennzahlen["h_index"]


def reichere_an(papers: List[Paper]) -> List[Paper]:
    """Ergänzt paper.extra um die Kennzahlen der publizierenden Zeitschrift.

    Papers ohne quelle_id (Preprints, Quellen ohne OpenAlex-Anbindung) bleiben
    unverändert. Kostet 1 Request je angefangene 50 distinkte Zeitschriften.
    """
    for paper in papers:
        if paper.extra is None:
            paper.extra = {}
    _extras_anreichern([paper.extra for paper in papers])
    return papers


def reichere_dicts_an(treffer: List[Dict]) -> List[Dict]:
    """Wie :func:`reichere_an`, aber für bereits serialisierte Treffer.

    ``Paper.to_dict()`` liefert ``extra`` als Dict, das ``quelle_id`` trägt —
    damit lässt sich die Trefferliste des Servers ohne Umweg über die
    Paper-Objekte anreichern.
    """
    extras = [eintrag.get("extra") for eintrag in treffer]
    extras = [extra if isinstance(extra, dict) else {} for extra in extras]
    _extras_anreichern(extras)

    for eintrag, extra in zip(treffer, extras):
        # Ein leeres extra nicht neu anlegen - to_dict() laesst es bewusst weg.
        if extra:
            eintrag["extra"] = extra
    return treffer
