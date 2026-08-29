# tests/test_server.py
import unittest
import asyncio
from paper_search_mcp import server

class TestPaperSearchServer(unittest.TestCase):
    def test_all_sources_include_new_platforms(self):
        self.assertIn("dblp", server.ALL_SOURCES)
        self.assertIn("openaire", server.ALL_SOURCES)
        self.assertIn("doaj", server.ALL_SOURCES)
        self.assertIn("base", server.ALL_SOURCES)
        self.assertIn("zenodo", server.ALL_SOURCES)
        self.assertIn("hal", server.ALL_SOURCES)
        self.assertIn("unpaywall", server.ALL_SOURCES)

    def test_retired_platforms_stay_out_of_all_sources(self):
        """CiteSeerX and SSRN are not part of the aggregated search.

        Both connector modules still exist and are unit-tested against
        recorded HTML, but neither returns live results: CiteSeerX 404s /
        redirects to an archive, and SSRN's search endpoints sit behind a
        Cloudflare challenge (the documented result page 404s, the alternate
        answers 403). Listing them in ALL_SOURCES only adds a guaranteed
        per-source error to every search_papers call.
        """
        self.assertNotIn("citeseerx", server.ALL_SOURCES)
        self.assertNotIn("ssrn", server.ALL_SOURCES)

    def test_parse_sources_with_new_platforms(self):
        parsed = server._parse_sources("dblp,doaj,base,zenodo,hal,unpaywall,invalid")
        self.assertEqual(parsed, ["dblp", "doaj", "base", "zenodo", "hal", "unpaywall"])

    def test_parse_sources_drops_retired_platforms(self):
        """An explicit ssrn/citeseerx request is filtered out, not passed through."""
        self.assertEqual(server._parse_sources("dblp,ssrn,citeseerx"), ["dblp"])

    def test_search_arxiv(self):
        """Test the search_arxiv tool returns 10 results."""
        result = asyncio.run(server.search_arxiv("machine learning", max_results=10))
        self.assertIsInstance(result, list, "Result should be a list")
        self.assertEqual(len(result), 10, "Should return exactly 10 results")
        for paper in result:
            self.assertIn('title', paper, "Each result should contain a title")
            self.assertIn('paper_id', paper, "Each result should contain a paper_id")

if __name__ == "__main__":
    unittest.main()