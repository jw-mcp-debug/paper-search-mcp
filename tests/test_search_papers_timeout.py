import asyncio
import unittest
from unittest.mock import AsyncMock, patch

from paper_search_mcp import server


class TestSearchPapersTimeout(unittest.IsolatedAsyncioTestCase):
    async def test_slow_source_does_not_block_the_other_sources(self):
        async def slow_search(*args, **kwargs):
            await asyncio.sleep(0.5)
            return [{"title": "slow", "paper_id": "slow-1"}]

        with (
            patch.object(server, "SOURCE_TIMEOUT_SECONDS", 0.01),
            patch.object(server, "search_arxiv", AsyncMock(side_effect=slow_search)),
            patch.object(
                server,
                "search_pubmed",
                AsyncMock(return_value=[{"title": "fast", "paper_id": "fast-1"}]),
            ),
        ):
            result = await server.search_papers(
                "test query",
                max_results_per_source=2,
                sources="arxiv,pubmed",
            )

        self.assertEqual(result["source_results"]["arxiv"], 0)
        self.assertEqual(result["source_results"]["pubmed"], 1)
        self.assertIn("timed out", result["errors"]["arxiv"])
        self.assertEqual(result["total"], 1)
        self.assertEqual(result["papers"][0]["paper_id"], "fast-1")

    async def test_results_are_kept_when_no_source_times_out(self):
        with (
            patch.object(server, "SOURCE_TIMEOUT_SECONDS", 5),
            patch.object(
                server,
                "search_arxiv",
                AsyncMock(return_value=[{"title": "paper a", "paper_id": "a"}]),
            ),
        ):
            result = await server.search_papers(
                "test query",
                max_results_per_source=1,
                sources="arxiv",
            )

        self.assertEqual(result["source_results"]["arxiv"], 1)
        self.assertEqual(result["errors"], {})
        self.assertEqual(result["total"], 1)


if __name__ == "__main__":
    unittest.main()
