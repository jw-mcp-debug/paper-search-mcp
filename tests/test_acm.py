"""ACM Digital Library ohne Key, über OpenAlex mit DOI-Präfix 10.1145.

Der Request ist gemockt. Geprüft wird, dass der Präfixfilter immer gesetzt ist
und ein zusätzlicher Filter ihn ergänzt statt ersetzt, dass Treffer als ACM
gekennzeichnet sind, und dass ACM ohne jede Konfiguration registriert ist —
ohne die Download- und Lesetools, die der alte Connector anbot.
"""
import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from paper_search_mcp import server
from paper_search_mcp.academic_platforms.acm import ACMSearcher

WERK = {
    "id": "https://openalex.org/W1",
    "title": "Teach AI How to Code",
    "doi": "https://doi.org/10.1145/3613904.3642349",
    "abstract_inverted_index": {"Teachable": [0], "agents": [1]},
    "open_access": {},
}


def _sucher():
    antwort = MagicMock(status_code=200)
    antwort.json.return_value = {"results": [WERK]}
    sucher = ACMSearcher()
    sucher.session = MagicMock()
    sucher.session.get.return_value = antwort
    return sucher


class TestACMSearcher(unittest.TestCase):
    def test_praefixfilter_immer_gesetzt(self):
        sucher = _sucher()
        sucher.search("llm programming education", max_results=5)
        self.assertEqual(sucher.session.get.call_args.kwargs["params"]["filter"],
                         "doi_starts_with:10.1145")

    def test_zusatzfilter_ergaenzt_den_praefix(self):
        sucher = _sucher()
        sucher.search("q", filter="publication_year:>2020")
        self.assertEqual(sucher.session.get.call_args.kwargs["params"]["filter"],
                         "doi_starts_with:10.1145,publication_year:>2020")

    def test_treffer_sind_acm_mit_dl_link(self):
        paper = _sucher().search("q")[0]
        self.assertEqual(paper.source, "acm")
        self.assertEqual(paper.url, "https://dl.acm.org/doi/10.1145/3613904.3642349")
        self.assertTrue(paper.abstract)


class TestRegistrierung(unittest.TestCase):
    def test_ohne_key_registriert_und_in_all(self):
        namen = {t.name for t in asyncio.run(server.mcp.list_tools())}
        self.assertIn("search_acm", namen)
        self.assertNotIn("download_acm", namen)
        self.assertNotIn("read_acm_paper", namen)
        self.assertIn("acm", server.ALL_SOURCES)

    def test_search_papers_gibt_openalex_filter_an_acm(self):
        with patch.object(server, "search_acm", AsyncMock(return_value=[])) as gemockt:
            asyncio.run(server.search_papers("q", sources="acm", openalex_filter="language:en"))
        self.assertEqual(gemockt.call_args.kwargs["filter"], "language:en")


if __name__ == "__main__":
    unittest.main()
