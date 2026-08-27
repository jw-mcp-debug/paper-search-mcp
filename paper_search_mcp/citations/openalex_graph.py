"""
citations/openalex_graph.py
===========================
HTTP-Schicht für die Zitationsverfolgung über OpenAlex.

Rückwärts (welche Arbeiten zitiert dieses Paper?) kommt aus dem Feld
``referenced_works`` des Work-Objekts. Vorwärts (wer zitiert dieses Paper?)
erfordert eine gefilterte Abfrage an /works mit ``cites:<id>`` — OpenAlex
liefert eingehende Zitationen bewusst nicht inline, weil eine Arbeit
zehntausendfach zitiert sein kann.

Kreditverbrauch beachten: Seit dem 13.02.2026 verlangt die OpenAlex-API einen
(kostenlosen) API-Key; der frühere "polite pool" über den mailto-Parameter
existiert nicht mehr. Ohne Key sind es ca. 100 Credits/Tag. Jede Funktion hier
kostet 1–3 Requests — siehe die Docstrings.

Der Key wird über dieselben Umgebungsvariablen gelesen wie in
``academic_platforms/openalex.py``:
``PAPER_SEARCH_MCP_OPENALEX_API_KEY`` oder ``OPENALEX_API_KEY``.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import Dict, List, Optional

import requests

from ..paper import Paper
from ..utils import quelle_felder

logger = logging.getLogger(__name__)

OPENALEX_BASE = "https://api.openalex.org/works"

# Nur die Felder holen, die gebraucht werden. Ohne select= liefert OpenAlex das
# volle Work-Objekt inklusive abstract_inverted_index und concepts — bei 40
# Referenzen sprengt das den Kontext des aufrufenden Modells.
_SELECT_BASIS = (
    "id,doi,display_name,publication_year,publication_date,cited_by_count,"
    "authorships,primary_location,open_access,type"
)
_SELECT_MIT_GRAPH = _SELECT_BASIS + ",referenced_works,related_works"
_ABSTRACT_FELD = ",abstract_inverted_index"

# OpenAlex erlaubt bis zu 50 mit "|" verknüpfte Werte je Filter.
_BATCH_GROESSE = 50

# Harte Obergrenze, damit ein Aufruf nicht unbemerkt 20 Requests auslöst.
MAX_TREFFER_HART = 50


class OpenAlexFehler(RuntimeError):
    """Fachlicher Fehler beim Zugriff auf die OpenAlex-API."""


_session: Optional[requests.Session] = None


def _hole_session() -> requests.Session:
    global _session
    if _session is None:
        _session = requests.Session()
        _session.headers.update({"User-Agent": "paper-search-mcp/1.0 (BHT Campusbibliothek)"})
    return _session


def _api_key() -> str:
    return (
        os.environ.get("PAPER_SEARCH_MCP_OPENALEX_API_KEY")
        or os.environ.get("OPENALEX_API_KEY")
        or ""
    ).strip()


def hole_json(url: str, params: Dict) -> Dict:
    """Ein GET gegen OpenAlex mit einheitlicher Fehlerübersetzung.

    Öffentlich, weil ``journals/openalex_sources.py`` dieselbe Session, denselben
    API-Key und dieselbe Fehlerübersetzung braucht.
    """
    key = _api_key()
    if key:
        params = {**params, "api_key": key}

    try:
        antwort = _hole_session().get(url, params=params, timeout=30)
    except requests.RequestException as exc:
        raise OpenAlexFehler(f"OpenAlex nicht erreichbar: {exc}") from exc

    if antwort.status_code == 404:
        raise OpenAlexFehler("Kein OpenAlex-Datensatz zu dieser Kennung gefunden.")
    if antwort.status_code == 409:
        raise OpenAlexFehler(
            "OpenAlex-Kreditkontingent erschöpft (HTTP 409). Ohne API-Key sind es "
            "ca. 100 Credits pro Tag. Key in PAPER_SEARCH_MCP_OPENALEX_API_KEY setzen."
        )
    if antwort.status_code == 429:
        raise OpenAlexFehler("OpenAlex-Rate-Limit erreicht (HTTP 429). Später erneut versuchen.")
    if antwort.status_code >= 400:
        raise OpenAlexFehler(f"OpenAlex antwortete mit HTTP {antwort.status_code}.")

    try:
        return antwort.json()
    except ValueError as exc:
        raise OpenAlexFehler(f"OpenAlex lieferte kein gültiges JSON: {exc}") from exc


def normalisiere_kennung(kennung: str) -> str:
    """
    Nimmt DOI, OpenAlex-ID oder URL entgegen und liefert die Form, die im
    OpenAlex-Pfad funktioniert.

    Beispiele:
        '10.1038/nature12373'                  -> 'doi:10.1038/nature12373'
        'https://doi.org/10.1038/nature12373'  -> 'doi:10.1038/nature12373'
        'W2741809807'                          -> 'W2741809807'
        'https://openalex.org/W2741809807'     -> 'W2741809807'
    """
    roh = (kennung or "").strip()
    if not roh:
        raise OpenAlexFehler("Keine Kennung übergeben (DOI oder OpenAlex-ID erforderlich).")

    if roh.lower().startswith("doi:"):
        roh = roh[4:].strip()

    for praefix in ("https://openalex.org/", "http://openalex.org/", "https://api.openalex.org/works/"):
        if roh.lower().startswith(praefix):
            roh = roh[len(praefix):].strip()

    if roh.upper().startswith("W") and roh[1:].isdigit():
        return roh.upper()

    for praefix in ("https://doi.org/", "http://doi.org/", "https://dx.doi.org/", "doi.org/"):
        if roh.lower().startswith(praefix):
            roh = roh[len(praefix):].strip()

    if roh.startswith("10."):
        return f"doi:{roh}"

    raise OpenAlexFehler(
        f"Kennung '{kennung}' ist weder eine DOI (beginnt mit '10.') noch eine "
        "OpenAlex-Work-ID (beginnt mit 'W')."
    )


def kurz_id(openalex_url: str) -> str:
    """'https://openalex.org/W123' -> 'W123'; auch für Source-IDs ('S123')."""
    return (openalex_url or "").rstrip("/").rsplit("/", 1)[-1]


def _rekonstruiere_abstract(inverted_index: Optional[dict]) -> str:
    """OpenAlex liefert Abstracts als invertierten Index; hier zurückgedreht."""
    if not inverted_index:
        return ""
    try:
        positionen = [
            (pos, wort)
            for wort, stellen in inverted_index.items()
            for pos in stellen
        ]
        positionen.sort(key=lambda paar: paar[0])
        return " ".join(wort for _, wort in positionen)
    except Exception as exc:  # pragma: no cover - defensiv
        logger.warning("Abstract-Rekonstruktion fehlgeschlagen: %s", exc)
        return ""


def _zu_paper(work: Dict) -> Paper:
    """Wandelt ein OpenAlex-Work in die Paper-Datenklasse des Projekts."""
    doi_url = work.get("doi") or ""
    doi = doi_url.replace("https://doi.org/", "").replace("http://doi.org/", "")

    autoren = [
        (eintrag.get("author") or {}).get("display_name", "")
        for eintrag in (work.get("authorships") or [])
    ]
    autoren = [name for name in autoren if name]

    veroeffentlicht = None
    datum = work.get("publication_date")
    if datum:
        try:
            veroeffentlicht = datetime.strptime(datum, "%Y-%m-%d")
        except ValueError:
            veroeffentlicht = None
    if veroeffentlicht is None and work.get("publication_year"):
        try:
            veroeffentlicht = datetime(int(work["publication_year"]), 1, 1)
        except (TypeError, ValueError):
            veroeffentlicht = None

    fundort = work.get("primary_location") or {}
    quelle_obj = fundort.get("source") or {}
    oa = work.get("open_access") or {}
    oa_url = oa.get("oa_url") or ""

    return Paper(
        paper_id=kurz_id(work.get("id", "")),
        title=work.get("display_name") or "",
        authors=autoren,
        abstract=_rekonstruiere_abstract(work.get("abstract_inverted_index")),
        doi=doi,
        published_date=veroeffentlicht,
        pdf_url=oa_url,
        url=doi_url or work.get("id", ""),
        source="openalex",
        citations=work.get("cited_by_count") or 0,
        references=[kurz_id(ref) for ref in (work.get("referenced_works") or [])],
        extra={
            **quelle_felder(quelle_obj),
            "typ": work.get("type") or "",
            "open_access": bool(oa.get("is_oa")),
            "oa_status": oa.get("oa_status") or "",
        },
    )


def hole_work(kennung: str, mit_abstract: bool = False) -> Dict:
    """
    Holt ein einzelnes Work inklusive referenced_works und related_works.
    Kostet 1 Request.
    """
    pfad_id = normalisiere_kennung(kennung)
    select = _SELECT_MIT_GRAPH + (_ABSTRACT_FELD if mit_abstract else "")
    return hole_json(f"{OPENALEX_BASE}/{pfad_id}", {"select": select})


def hydratisiere(
    work_ids: List[str],
    mit_abstract: bool = False,
    max_treffer: int = 25,
) -> List[Paper]:
    """
    Lädt Metadaten zu einer Liste von OpenAlex-Work-IDs.
    Kostet 1 Request je angefangene 50 IDs.
    """
    ids = [kurz_id(eintrag) for eintrag in work_ids if eintrag]
    ids = ids[: min(max_treffer, MAX_TREFFER_HART)]
    if not ids:
        return []

    select = _SELECT_BASIS + (_ABSTRACT_FELD if mit_abstract else "")
    gesammelt: List[Paper] = []

    for start in range(0, len(ids), _BATCH_GROESSE):
        block = ids[start : start + _BATCH_GROESSE]
        daten = hole_json(
            OPENALEX_BASE,
            {
                "filter": "openalex_id:" + "|".join(block),
                "select": select,
                "per-page": len(block),
            },
        )
        gesammelt.extend(_zu_paper(work) for work in daten.get("results", []))

    # Reihenfolge der Referenzliste ist bedeutungslos; nach Zitationszahl
    # sortieren macht die einflussreichen Arbeiten oben sichtbar.
    gesammelt.sort(key=lambda paper: paper.citations, reverse=True)
    return gesammelt


def zitierende_werke(
    kennung: str,
    max_treffer: int = 25,
    ab_jahr: Optional[int] = None,
    mit_abstract: bool = False,
) -> Dict:
    """
    Vorwärtssuche: Arbeiten, die die angegebene Arbeit zitieren.
    Kostet 1 Request (bzw. 2, wenn erst eine DOI aufgelöst werden muss).
    """
    pfad_id = normalisiere_kennung(kennung)

    if pfad_id.startswith("doi:"):
        work = hole_json(f"{OPENALEX_BASE}/{pfad_id}", {"select": "id,display_name,cited_by_count"})
        work_id = kurz_id(work.get("id", ""))
        titel = work.get("display_name") or ""
        gesamt_bekannt = work.get("cited_by_count") or 0
    else:
        work_id = pfad_id
        titel = ""
        gesamt_bekannt = None

    filter_teile = [f"cites:{work_id}"]
    if ab_jahr:
        filter_teile.append(f"from_publication_date:{int(ab_jahr)}-01-01")

    select = _SELECT_BASIS + (_ABSTRACT_FELD if mit_abstract else "")
    daten = hole_json(
        OPENALEX_BASE,
        {
            "filter": ",".join(filter_teile),
            "select": select,
            "sort": "cited_by_count:desc",
            "per-page": min(max(int(max_treffer), 1), MAX_TREFFER_HART),
        },
    )

    treffer = [_zu_paper(work) for work in daten.get("results", [])]
    gesamt = (daten.get("meta") or {}).get("count", len(treffer))

    return {
        "work_id": work_id,
        "titel": titel,
        "gesamt": gesamt,
        "cited_by_count": gesamt_bekannt,
        "papers": treffer,
    }
