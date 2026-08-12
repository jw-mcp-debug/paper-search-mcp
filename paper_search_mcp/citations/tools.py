"""
citations/tools.py
==================
Werkzeuge zur Zitationsverfolgung (Schneeballsystem).

Drei Tools, die über `register_citation_tools(mcp)` auf eine bestehende
FastMCP-Instanz gehängt werden — analog zu `register_opac_tools`.

Einbindung im Haupt-Server (paper_search_mcp/server.py), direkt nach
der OPAC-Registrierung:

    from paper_search_mcp.citations.tools import register_citation_tools
    register_citation_tools(mcp)

Bewusste Grenze: Diese Tools werten ausschliesslich strukturierte
Metadaten aus. Es werden keine Volltexte geladen und keine
Literaturverzeichnisse aus PDFs geparst.
"""

import asyncio
import logging
from typing import Any, Dict, Optional

from . import openalex_graph as graph

logger = logging.getLogger(__name__)


def _fehler(kennung: str, exc: Exception) -> Dict[str, Any]:
    return {
        "kennung": kennung,
        "papers": [],
        "total": 0,
        "errors": {"openalex": str(exc)},
    }


def register_citation_tools(mcp) -> None:
    """Hängt die Zitations-Werkzeuge an die übergebene FastMCP-Instanz."""

    @mcp.tool()
    async def paper_referenzen(
        kennung: str,
        max_treffer: int = 25,
        mit_abstract: bool = False,
    ) -> Dict[str, Any]:
        """Rückwärtssuche: Welche Arbeiten zitiert dieses Paper?

        Liest das Literaturverzeichnis aus den strukturierten OpenAlex-Metadaten
        (Feld referenced_works) und lädt die Metadaten der zitierten Arbeiten
        nach. Das ist der Rückwärtsschritt im Schneeballsystem und führt
        zuverlässig zu den Grundlagenarbeiten eines Themas.

        Kein Volltextzugriff: Es wird kein PDF geladen und kein
        Literaturverzeichnis aus einem Dokument geparst.

        Args:
            kennung: DOI (z. B. '10.1038/nature12373') oder OpenAlex-Work-ID
                (z. B. 'W2741809807'). URLs beider Formen werden akzeptiert.
            max_treffer: Höchstzahl zurückgegebener Referenzen (Standard 25, hart begrenzt auf 50).
            mit_abstract: Abstracts mitliefern. Standard False, weil Abstracts die
                Antwort stark verlängern. Für Begriffsernte (Pearl Growing) auf True setzen.

        Returns:
            Dict mit 'ausgangspaper' (Titel/Jahr der Ausgangsarbeit),
            'referenzen_gesamt' (Zahl der Einträge im Literaturverzeichnis),
            'papers' (nach Zitationszahl absteigend) und ggf. 'errors'.
        """
        try:
            work = await asyncio.to_thread(graph.hole_work, kennung, mit_abstract)
        except Exception as exc:
            logger.warning("paper_referenzen: Work-Abruf fehlgeschlagen (%s): %s", kennung, exc)
            return _fehler(kennung, exc)

        referenz_ids = work.get("referenced_works") or []
        if not referenz_ids:
            return {
                "kennung": kennung,
                "ausgangspaper": {
                    "titel": work.get("display_name") or "",
                    "jahr": work.get("publication_year"),
                },
                "referenzen_gesamt": 0,
                "papers": [],
                "total": 0,
                "hinweis": (
                    "OpenAlex kennt zu dieser Arbeit keine Referenzliste. Das kommt vor, "
                    "wenn der Verlag seine Referenzen nicht offen hinterlegt hat. "
                    "Vorwärtssuche über paper_zitiert_von versuchen."
                ),
            }

        try:
            papers = await asyncio.to_thread(
                graph.hydratisiere, referenz_ids, mit_abstract, max_treffer
            )
        except Exception as exc:
            logger.warning("paper_referenzen: Hydratisierung fehlgeschlagen (%s): %s", kennung, exc)
            return _fehler(kennung, exc)

        return {
            "kennung": kennung,
            "ausgangspaper": {
                "titel": work.get("display_name") or "",
                "jahr": work.get("publication_year"),
            },
            "referenzen_gesamt": len(referenz_ids),
            "papers": [paper.to_dict() for paper in papers],
            "total": len(papers),
        }

    @mcp.tool()
    async def paper_zitiert_von(
        kennung: str,
        max_treffer: int = 25,
        ab_jahr: Optional[int] = None,
        mit_abstract: bool = False,
    ) -> Dict[str, Any]:
        """Vorwärtssuche: Welche Arbeiten zitieren dieses Paper?

        Der Vorwärtsschritt im Schneeballsystem. Führt von einer bekannten
        Grundlagenarbeit zum aktuellen Forschungsstand — genau die Richtung, die
        eine reine Stichwortsuche nicht abbildet. Sortiert nach Zitationszahl,
        die einflussreichsten zitierenden Arbeiten stehen oben.

        Args:
            kennung: DOI oder OpenAlex-Work-ID der Ausgangsarbeit.
            max_treffer: Höchstzahl zurückgegebener Arbeiten (Standard 25, hart begrenzt auf 50).
            ab_jahr: Nur Arbeiten ab diesem Erscheinungsjahr. Für den aktuellen
                Forschungsstand sinnvoll, z. B. 2022.
            mit_abstract: Abstracts mitliefern (Standard False).

        Returns:
            Dict mit 'gesamt' (Gesamtzahl zitierender Arbeiten in OpenAlex),
            'papers' (die max_treffer meistzitierten davon) und ggf. 'errors'.
        """
        try:
            ergebnis = await asyncio.to_thread(
                graph.zitierende_werke, kennung, max_treffer, ab_jahr, mit_abstract
            )
        except Exception as exc:
            logger.warning("paper_zitiert_von: Abruf fehlgeschlagen (%s): %s", kennung, exc)
            return _fehler(kennung, exc)

        papers = ergebnis["papers"]
        return {
            "kennung": kennung,
            "work_id": ergebnis["work_id"],
            "ausgangspaper": {"titel": ergebnis["titel"]},
            "gesamt": ergebnis["gesamt"],
            "ab_jahr": ab_jahr,
            "papers": [paper.to_dict() for paper in papers],
            "total": len(papers),
        }

    @mcp.tool()
    async def paper_verwandte(
        kennung: str,
        max_treffer: int = 15,
        mit_abstract: bool = False,
    ) -> Dict[str, Any]:
        """Seitwärtssuche: thematisch verwandte Arbeiten zu diesem Paper.

        Nutzt die von OpenAlex algorithmisch berechneten related_works — aktuelle
        Arbeiten mit den meisten gemeinsamen Konzepten. Nützlich, wenn die
        Stichwortsuche stockt, weil ein Feld mit uneinheitlicher Terminologie
        arbeitet: Die Verwandtschaft wird über Konzepte bestimmt, nicht über
        Wortgleichheit.

        Args:
            kennung: DOI oder OpenAlex-Work-ID.
            max_treffer: Höchstzahl zurückgegebener Arbeiten (Standard 15).
            mit_abstract: Abstracts mitliefern (Standard False).

        Returns:
            Dict mit 'papers' und ggf. 'errors'.
        """
        try:
            work = await asyncio.to_thread(graph.hole_work, kennung, False)
        except Exception as exc:
            logger.warning("paper_verwandte: Work-Abruf fehlgeschlagen (%s): %s", kennung, exc)
            return _fehler(kennung, exc)

        verwandte_ids = work.get("related_works") or []
        if not verwandte_ids:
            return {
                "kennung": kennung,
                "ausgangspaper": {"titel": work.get("display_name") or ""},
                "papers": [],
                "total": 0,
                "hinweis": "OpenAlex hat zu dieser Arbeit keine verwandten Werke berechnet.",
            }

        try:
            papers = await asyncio.to_thread(
                graph.hydratisiere, verwandte_ids, mit_abstract, max_treffer
            )
        except Exception as exc:
            logger.warning("paper_verwandte: Hydratisierung fehlgeschlagen (%s): %s", kennung, exc)
            return _fehler(kennung, exc)

        return {
            "kennung": kennung,
            "ausgangspaper": {"titel": work.get("display_name") or ""},
            "papers": [paper.to_dict() for paper in papers],
            "total": len(papers),
        }
