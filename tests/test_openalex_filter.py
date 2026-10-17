"""OpenAlex-Filter und Fehlermeldungen statt leerer Listen.

Der Request ist gemockt. Geprüft wird, dass der Filter beim Request ankommt —
auch aus search_papers heraus — und dass OpenAlex nicht mehr still mit null
Treffern antwortet, wenn es gar nicht geantwortet hat: erschöpftes Budget,
Drosselung, ein vertippter Filter und ein Verbindungsfehler werden gemeldet.
"""
import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

import requests

from paper_search_mcp import server
from paper_search_mcp.academic_platforms.openalex import OpenAlexSearcher


def _sucher(status=200, json=None, fehler=None):
    antwort = MagicMock(status_code=status)
    antwort.json.return_value = json if json is not None else {"results": []}
    sucher = OpenAlexSearcher()
    sucher.session = MagicMock()
    if fehler:
        sucher.session.get.side_effect = fehler
    else:
        sucher.session.get.return_value = antwort
    return sucher


class TestFilter(unittest.TestCase):
    def test_filter_geht_in_den_request(self):
        sucher = _sucher()
        sucher.search("heat pumps", max_results=5, filter=" language:de,publication_year:>2020 ")
        params = sucher.session.get.call_args.kwargs["params"]
        self.assertEqual(params["filter"], "language:de,publication_year:>2020")
        self.assertEqual(params["search"], "heat pumps")

    def test_ohne_filter_kein_filterparameter(self):
        sucher = _sucher()
        sucher.search("heat pumps", max_results=5)
        self.assertNotIn("filter", sucher.session.get.call_args.kwargs["params"])

    def test_search_papers_reicht_den_filter_durch(self):
        with patch.object(server, "search_openalex", AsyncMock(return_value=[])) as gemockt:
            asyncio.run(server.search_papers(
                "q", sources="openalex", max_results_per_source=3,
                openalex_filter="publication_year:>2020"))
        self.assertEqual(gemockt.call_args.kwargs["filter"], "publication_year:>2020")


class TestFehler(unittest.TestCase):
    def _meldung(self, **kwargs):
        with self.assertRaises(requests.RequestException) as kontext:
            _sucher(**kwargs).search("q")
        return str(kontext.exception)

    def test_budget_erschoepft(self):
        meldung = self._meldung(status=409)
        self.assertIn("HTTP 409", meldung)
        self.assertIn("PAPER_SEARCH_MCP_OPENALEX_API_KEY", meldung)

    def test_drosselung(self):
        self.assertIn("HTTP 429", self._meldung(status=429))

    def test_vertippter_filter_nennt_den_grund_ohne_feldliste(self):
        meldung = self._meldung(status=403, json={
            "error": "Invalid query parameters error.",
            "message": "languag is not a valid field. Valid fields are " + "x, " * 500,
        })
        self.assertIn("languag is not a valid field", meldung)
        self.assertNotIn("Valid fields", meldung)

    def test_verbindungsfehler(self):
        self._meldung(fehler=requests.ConnectionError("down"))

    def test_kein_json(self):
        sucher = _sucher()
        sucher.session.get.return_value.json.side_effect = ValueError("bad")
        with self.assertRaises(requests.RequestException):
            sucher.search("q")

    def test_search_papers_meldet_den_ausfall_unter_errors(self):
        sucher = _sucher(status=409)
        with patch.object(server, "openalex_searcher", sucher):
            ergebnis = asyncio.run(server.search_papers("q", sources="openalex"))
        self.assertEqual(ergebnis["source_results"]["openalex"], 0)
        self.assertIn("HTTP 409", ergebnis["errors"]["openalex"])


if __name__ == "__main__":
    unittest.main()
