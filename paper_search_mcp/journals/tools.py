"""
journals/tools.py
=================
Werkzeug für das Kennzahlenprofil einer Zeitschrift.

Ein Tool, das über `register_journal_tools(mcp)` auf eine bestehende
FastMCP-Instanz gehängt wird — analog zu `register_citation_tools`.

Einbindung im Haupt-Server (paper_search_mcp/server.py), direkt nach
der Zitations-Registrierung:

    from paper_search_mcp.journals.tools import register_journal_tools
    register_journal_tools(mcp)

Bewusste Grenze: Der Journal Impact Factor (Clarivate/JCR) wird nicht
abgebildet und darf nirgends so genannt werden — siehe openalex_sources.py.
"""

import asyncio
import logging
from typing import Any, Dict

from ..citations import openalex_graph as graph
from . import openalex_sources as quellen

logger = logging.getLogger(__name__)


def _fehler(kennung: str, exc: Exception) -> Dict[str, Any]:
    return {"kennung": kennung, "quelle": {}, "errors": {"openalex": str(exc)}}


def _quelle_id_aus_work(kennung: str) -> str:
    """Holt die Source-ID der publizierenden Zeitschrift zu einer DOI/Work-ID."""
    work = graph.hole_json(
        f"{graph.OPENALEX_BASE}/{graph.normalisiere_kennung(kennung)}",
        {"select": "id,primary_location"},
    )
    quelle_obj = (work.get("primary_location") or {}).get("source") or {}
    return graph.kurz_id(quelle_obj.get("id", ""))


def _profil(kennung: str) -> Dict[str, Any]:
    """Erkennt die Art der Kennung und holt das passende Profil.

    Reihenfolge: Source-ID -> ISSN -> DOI/Work-ID -> unscharfe Namenssuche.
    """
    roh = (kennung or "").strip()
    if not roh:
        raise quellen.OpenAlexFehler(
            "Keine Kennung übergeben (ISSN, Source-ID, Zeitschriftenname oder DOI erforderlich)."
        )

    if quellen.ist_source_id(roh):
        gefunden = quellen.hole_quellen([roh.upper()])
        return {"quelle": gefunden.get(roh.upper(), {}), "zuordnung": "eindeutig"}

    if quellen.ist_issn(roh):
        return {"quelle": quellen.quelle_per_issn(roh) or {}, "zuordnung": "eindeutig"}

    if roh.startswith("10.") or "doi.org" in roh.lower() or roh.upper().startswith("W"):
        quelle_id = _quelle_id_aus_work(roh)
        if not quelle_id:
            return {
                "quelle": {},
                "zuordnung": "eindeutig",
                "hinweis": (
                    "Zu dieser Arbeit ist in OpenAlex keine publizierende Zeitschrift "
                    "hinterlegt — typisch für Preprints und Repositoriumskopien."
                ),
            }
        gefunden = quellen.hole_quellen([quelle_id])
        return {"quelle": gefunden.get(quelle_id, {}), "zuordnung": "eindeutig"}

    return {"quelle": quellen.quelle_per_name(roh) or {}, "zuordnung": "unscharf"}


def register_journal_tools(mcp) -> None:
    """Hängt das Zeitschriften-Werkzeug an die übergebene FastMCP-Instanz."""

    @mcp.tool()
    async def zeitschrift_profil(kennung: str) -> Dict[str, Any]:
        """Kennzahlen und Zugangsstatus einer Zeitschrift.

        Nimmt eine ISSN, einen Zeitschriftennamen, eine OpenAlex-Source-ID oder die
        DOI eines Aufsatzes entgegen und liefert das Profil der publizierenden
        Zeitschrift: Verlag, Open-Access-Status, DOAJ-Eintrag, Zahl der erfassten
        Arbeiten, h-Index und den Zitationsschnitt der letzten zwei Jahre.

        Der Journal Impact Factor (Clarivate/JCR) ist proprietär und wird hier nicht
        geliefert. 'zit_schnitt_2j' ist die frei verfügbare OpenAlex-Entsprechung
        (2yr_mean_citedness) und mit dem JIF nicht zahlengleich.

        Args:
            kennung: ISSN ('0005-1098'), OpenAlex-Source-ID ('S51360982'),
                Zeitschriftenname ('Automatica') oder Aufsatz-DOI.

        Returns:
            Dict mit 'quelle' (Kennzahlen), 'zuordnung' ('eindeutig' bei ISSN/ID,
            'unscharf' bei Namenssuche) und ggf. 'errors'.
        """
        try:
            ergebnis = await asyncio.to_thread(_profil, kennung)
        except Exception as exc:
            logger.warning("zeitschrift_profil: Abruf fehlgeschlagen (%s): %s", kennung, exc)
            return _fehler(kennung, exc)

        if not ergebnis.get("quelle") and "hinweis" not in ergebnis:
            ergebnis["hinweis"] = (
                f"Keine Zeitschrift zu '{kennung}' gefunden. Mit der ISSN erneut "
                "versuchen — die ist eindeutig, der Name nicht."
            )
        return {"kennung": kennung, **ergebnis}
