"""
begriffe/tools.py
=================
Werkzeug für englisches Suchvokabular aus den OpenAlex-Keywords.

Ein Tool, das über `register_begriffe_tools(mcp)` auf eine bestehende
FastMCP-Instanz gehängt wird — analog zu `register_journal_tools`.
"""

import asyncio
import logging
from typing import Any, Dict

from . import openalex_keywords as kw

logger = logging.getLogger(__name__)


def register_begriffe_tools(mcp) -> None:
    """Hängt das Vokabular-Werkzeug an die übergebene FastMCP-Instanz."""

    @mcp.tool()
    async def begriffe_vorschlagen(text: str) -> Dict[str, Any]:
        """Englische Fachbegriffe zu einem Thema aus dem OpenAlex-Schlagwortbestand.

        Nimmt eine Themenbeschreibung in beliebiger Sprache (auch Deutsch) und
        liefert die englischen Schlagwörter, die OpenAlex Arbeiten zu diesem
        Thema zuordnet — für die Englisch-Spalte der Suchbegriffstabelle.
        Je Begriff: Relevanz für den Text (0–1), Zahl der Arbeiten mit diesem
        Schlagwort ('werke') und Schreibvarianten ('synonyme', für ODER im Block).
        'varianten' sind verwandte, meist engere Begriffe zu den zwei stärksten.

        Ein ganzer Satz trifft besser als ein Stichwort; mindestens 20 Zeichen.
        Ein Aufruf je Thema genügt. Die Begriffe sind Vorschläge eines Modells,
        keine Thesaurusauskunft — fachfremde Treffer verwerfen.

        Args:
            text: Thema als Satz, z. B. 'Wärmepumpen im Altbau' oder
                'Fachkräftemangel im Sanitär- und Heizungshandwerk'.

        Returns:
            Dict mit 'begriffe' (nach Relevanz), 'varianten' und ggf. 'errors'.
        """
        try:
            ergebnis = await asyncio.to_thread(kw.vorschlagen, text)
        except Exception as exc:
            logger.warning("begriffe_vorschlagen: Abruf fehlgeschlagen: %s", exc)
            return {"begriffe": [], "varianten": [], "errors": {"openalex": str(exc)}}
        return ergebnis
