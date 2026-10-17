import threading
import time
import unittest
from unittest.mock import MagicMock, patch

import requests

from paper_search_mcp.academic_platforms.arxiv import ArxivSearcher


EMPTY_FEED = "<?xml version='1.0'?><feed xmlns='http://www.w3.org/2005/Atom'></feed>"

ONE_ENTRY_FEED = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom"
      xmlns:opensearch="http://a9.com/-/spec/opensearch/1.1/"
      xmlns:arxiv="http://arxiv.org/schemas/atom">
  <id>https://arxiv.org/api/abc123</id>
  <title>arXiv Query</title>
  <updated>2026-10-08T00:00:00Z</updated>
  <opensearch:totalResults>1</opensearch:totalResults>
  <entry>
    <id>http://arxiv.org/abs/hep-th/9901001v1</id>
    <updated>1999-01-01T00:00:00Z</updated>
    <published>1999-01-01T00:00:00Z</published>
    <title>A legacy paper</title>
    <summary>Abstract text.</summary>
    <author><name>Jane Doe</name></author>
    <link href="http://arxiv.org/pdf/hep-th/9901001v1" rel="related" type="application/pdf"/>
    <category term="hep-th" scheme="http://arxiv.org/schemas/atom"/>
  </entry>
</feed>"""


def _response(text: str, status_code: int = 200):
    response = MagicMock()
    response.text = text
    response.status_code = status_code
    response.content = text.encode()
    return response


class _ArxivTestCase(unittest.TestCase):
    def setUp(self):
        # Pacing state is shared across the process; start every test clean.
        ArxivSearcher._last_request_at = 0.0


class TestArxivRateLimit(_ArxivTestCase):
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

        with patch.object(
            searcher.session,
            "get",
            side_effect=[_response("Rate exceeded."), _response(EMPTY_FEED)],
        ), patch("paper_search_mcp.academic_platforms.arxiv.time.sleep"):
            self.assertEqual(searcher.search("machine learning", max_results=1), [])

    def test_pacing_waits_between_calls(self):
        searcher = ArxivSearcher()

        with patch.object(searcher.session, "get", return_value=_response(EMPTY_FEED)), \
             patch("paper_search_mcp.academic_platforms.arxiv.time.sleep") as sleep:
            searcher.search("first", max_results=1)
            self.assertEqual(sleep.call_count, 0)  # no wait before the first request
            searcher.search("second", max_results=1)

        self.assertEqual(sleep.call_count, 1)
        self.assertLessEqual(sleep.call_args[0][0], ArxivSearcher.MIN_INTERVAL_SEC)

    def test_pacing_is_shared_between_instances(self):
        first, second = ArxivSearcher(), ArxivSearcher()

        with patch.object(first.session, "get", return_value=_response(EMPTY_FEED)), \
             patch.object(second.session, "get", return_value=_response(EMPTY_FEED)), \
             patch("paper_search_mcp.academic_platforms.arxiv.time.sleep") as sleep:
            first.search("first", max_results=1)
            second.search("second", max_results=1)

        self.assertEqual(sleep.call_count, 1)

    def test_concurrent_requests_do_not_overlap(self):
        """Two threads must not be inside a request at the same time."""
        searcher = ArxivSearcher()
        active, overlaps = [0], []
        guard = threading.Lock()

        def slow_get(*args, **kwargs):
            with guard:
                active[0] += 1
                if active[0] > 1:
                    overlaps.append(True)
            time.sleep(0.05)
            with guard:
                active[0] -= 1
            return _response(EMPTY_FEED)

        with patch.object(searcher.session, "get", side_effect=slow_get), \
             patch.object(ArxivSearcher, "MIN_INTERVAL_SEC", 0.0):
            threads = [
                threading.Thread(target=searcher.search, args=(f"q{i}",))
                for i in range(4)
            ]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join()

        self.assertEqual(overlaps, [])


class TestArxivFailuresAreReported(_ArxivTestCase):
    """A failed request must not look like an empty result set."""

    def _search_with(self, *responses):
        searcher = ArxivSearcher()
        with patch.object(searcher.session, "get", side_effect=list(responses)) as get, \
             patch("paper_search_mcp.academic_platforms.arxiv.time.sleep"):
            try:
                return searcher.search("machine learning", max_results=1), get
            except requests.RequestException as exc:
                return exc, get

    def test_persistent_server_error_raises(self):
        result, get = self._search_with(*[_response("", 503)] * 3)
        self.assertIsInstance(result, requests.RequestException)
        self.assertIn("HTTP 503", str(result))
        self.assertEqual(get.call_count, 3)

    def test_non_retryable_status_raises_at_once(self):
        result, get = self._search_with(_response("bad query", 400))
        self.assertIsInstance(result, requests.RequestException)
        self.assertIn("HTTP 400", str(result))
        self.assertEqual(get.call_count, 1)

    def test_network_errors_raise(self):
        searcher = ArxivSearcher()
        with patch.object(
            searcher.session, "get", side_effect=requests.ConnectionError("down")
        ), patch("paper_search_mcp.academic_platforms.arxiv.time.sleep"):
            with self.assertRaises(requests.RequestException):
                searcher.search("machine learning", max_results=1)

    def test_transient_error_recovers(self):
        result, _ = self._search_with(_response("", 502), _response(ONE_ENTRY_FEED))
        self.assertEqual(len(result), 1)

    def test_406_with_valid_feed_is_accepted(self):
        result, get = self._search_with(_response(ONE_ENTRY_FEED, 406))
        self.assertEqual([p.title for p in result], ["A legacy paper"])
        self.assertEqual(get.call_count, 1)

    def test_406_without_feed_raises(self):
        result, get = self._search_with(*[_response("<html>Not Acceptable</html>", 406)] * 3)
        self.assertIsInstance(result, requests.RequestException)
        self.assertIn("406", str(result))
        self.assertEqual(get.call_count, 3)

    def test_406_with_empty_feed_is_not_success(self):
        result, _ = self._search_with(*[_response(EMPTY_FEED, 406)] * 3)
        self.assertIsInstance(result, requests.RequestException)


class TestArxivQuery(_ArxivTestCase):
    def test_plain_words_are_anded(self):
        self.assertEqual(
            ArxivSearcher._build_search_query("machine  learning"),
            "all:machine AND all:learning",
        )

    def test_single_word(self):
        self.assertEqual(ArxivSearcher._build_search_query("transformer"), "all:transformer")

    def test_structured_queries_pass_through(self):
        for query in (
            'ti:"graph neural" AND au:smith',
            "cat:cs.LG",
            '"deep learning"',
            "bert OR roberta",
        ):
            self.assertEqual(ArxivSearcher._build_search_query(query), query)

    def test_lowercase_or_is_a_word(self):
        self.assertEqual(
            ArxivSearcher._build_search_query("black or white"),
            "all:black AND all:or AND all:white",
        )

    def test_request_uses_https_and_and(self):
        searcher = ArxivSearcher()
        with patch.object(searcher.session, "get", return_value=_response(EMPTY_FEED)) as get:
            searcher.search("machine learning", max_results=1)
        url = get.call_args[0][0]
        params = get.call_args[1]["params"]
        self.assertTrue(url.startswith("https://"))
        self.assertEqual(params["search_query"], "all:machine AND all:learning")


class TestArxivEntry(_ArxivTestCase):
    def test_legacy_id_keeps_archive(self):
        searcher = ArxivSearcher()
        with patch.object(searcher.session, "get", return_value=_response(ONE_ENTRY_FEED)):
            papers = searcher.search("legacy", max_results=1)
        self.assertEqual(papers[0].paper_id, "hep-th/9901001v1")


if __name__ == "__main__":
    unittest.main()
