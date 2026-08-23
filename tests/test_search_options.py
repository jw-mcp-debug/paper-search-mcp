"""Abstract truncation and the CrossRef filter passthrough.

Abstracts are the largest field of a result, so they are shortened by default —
but term harvesting needs them whole, which is what abstract_chars=0 is for.
The CrossRef filter works inside the aggregation, so deduplication and error
handling still apply.
"""
import asyncio
import unittest
from unittest.mock import AsyncMock, patch

from paper_search_mcp import server

LONG = ("Cross-laminated timber behaves predictably in fire. " * 40).strip()


def _search(**kwargs):
    return asyncio.run(server.search_papers("q", max_results_per_source=1, **kwargs))


class TestAbstractTruncation(unittest.TestCase):
    def test_truncates_on_a_word_boundary_with_a_marker(self):
        result = server._truncate_abstract("one two three four five", 12)
        self.assertTrue(result.endswith(" […]"))
        self.assertNotIn("thre […]", result)
        self.assertLessEqual(len(result) - len(" […]"), 12)

    def test_short_abstracts_are_untouched(self):
        self.assertEqual(server._truncate_abstract("short one", 600), "short one")

    def test_zero_disables_truncation(self):
        self.assertEqual(server._truncate_abstract(LONG, 0), LONG)

    def test_search_papers_truncates_by_default(self):
        with patch.object(server, "search_crossref",
                          AsyncMock(return_value=[{"title": "t", "doi": "10.1/a", "abstract": LONG}])):
            papers = _search(sources="crossref")["papers"]

        self.assertTrue(papers[0]["abstract"].endswith(" […]"))
        self.assertLess(len(papers[0]["abstract"]), len(LONG))

    def test_search_papers_keeps_full_abstracts_on_request(self):
        with patch.object(server, "search_crossref",
                          AsyncMock(return_value=[{"title": "t", "doi": "10.1/a", "abstract": LONG}])):
            papers = _search(sources="crossref", abstract_chars=0)["papers"]

        self.assertEqual(papers[0]["abstract"], LONG)


class TestCrossrefFilterPassthrough(unittest.TestCase):
    def test_filter_reaches_the_crossref_search(self):
        crossref = AsyncMock(return_value=[])
        with patch.object(server, "search_crossref", crossref):
            _search(sources="crossref", crossref_filter="type:journal-article")

        self.assertEqual(crossref.await_args.kwargs["filter"], "type:journal-article")

    def test_no_filter_is_passed_as_none(self):
        crossref = AsyncMock(return_value=[])
        with patch.object(server, "search_crossref", crossref):
            _search(sources="crossref")

        self.assertIsNone(crossref.await_args.kwargs["filter"])

    def test_filtering_happens_inside_the_aggregation(self):
        """Errors and deduplication must still apply to the filtered source."""
        with patch.object(server, "search_crossref", AsyncMock(side_effect=RuntimeError("boom"))), \
             patch.object(server, "search_arxiv",
                          AsyncMock(return_value=[{"title": "t", "doi": "10.1/a"}])):
            result = _search(sources="crossref,arxiv", crossref_filter="type:journal-article")

        self.assertIn("crossref", result["errors"])
        self.assertEqual(result["source_results"]["arxiv"], 1)


if __name__ == "__main__":
    unittest.main()
