import unittest
from unittest.mock import MagicMock, patch

import requests

from paper_search_mcp.academic_platforms.arxiv import ArxivSearcher


def _response(text: str, status_code: int = 200):
    response = MagicMock()
    response.text = text
    response.status_code = status_code
    response.content = text.encode()
    return response


class TestArxivRateLimit(unittest.TestCase):
    def test_soft_rate_limit_is_retried_then_raised(self):
        searcher = ArxivSearcher()
        limited = _response("Rate exceeded.")

        with patch.object(searcher.session, "get", return_value=limited) as get, \
             patch("paper_search_mcp.academic_platforms.arxiv.time.sleep"):
            with self.assertRaises(requests.RequestException):
                searcher.search("machine learning", max_results=1)

        self.assertEqual(get.call_count, 3)

    def test_soft_rate_limit_recovers_on_retry(self):
        searcher = ArxivSearcher()
        feed = "<?xml version='1.0'?><feed xmlns='http://www.w3.org/2005/Atom'></feed>"

        with patch.object(
            searcher.session,
            "get",
            side_effect=[_response("Rate exceeded."), _response(feed)],
        ), patch("paper_search_mcp.academic_platforms.arxiv.time.sleep"):
            self.assertEqual(searcher.search("machine learning", max_results=1), [])

    def test_pacing_waits_between_calls(self):
        searcher = ArxivSearcher()
        feed = "<?xml version='1.0'?><feed xmlns='http://www.w3.org/2005/Atom'></feed>"

        with patch.object(searcher.session, "get", return_value=_response(feed)), \
             patch("paper_search_mcp.academic_platforms.arxiv.time.sleep") as sleep:
            searcher.search("first", max_results=1)
            self.assertEqual(sleep.call_count, 0)  # no wait before the first request
            searcher.search("second", max_results=1)

        self.assertEqual(sleep.call_count, 1)
        self.assertLessEqual(sleep.call_args[0][0], ArxivSearcher.MIN_INTERVAL_SEC)


if __name__ == "__main__":
    unittest.main()
