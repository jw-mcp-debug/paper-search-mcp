"""dblp must report an outage instead of returning an empty result list.

dblp throttles per IP with 429 and then 503. The previous implementation did
not retry 429 at all, fell through to an HTML fallback against the same
throttled host and swallowed its failure, so an outage was indistinguishable
from "no hits".
"""
import unittest
from unittest.mock import MagicMock, patch

import requests

from paper_search_mcp.academic_platforms.dblp import DBLPSearcher, DBLPUnavailable

XML_ONE_HIT = """<?xml version="1.0"?>
<result><hits><hit><info>
  <title>A dblp paper</title>
  <authors><author>Ada Lovelace</author></authors>
  <year>2024</year>
  <venue>ICSE</venue>
</info></hit></hits></result>"""

XML_NO_HITS = """<?xml version="1.0"?><result><hits></hits></result>"""


def _response(status_code=200, text="", headers=None):
    headers = {"Content-Type": "application/xml"} | (headers or {})
    response = MagicMock()
    response.status_code = status_code
    response.text = text
    response.content = text.encode()
    response.headers = headers
    return response


class TestDBLPErrorPropagation(unittest.TestCase):
    def setUp(self):
        self.searcher = DBLPSearcher()
        self.sleep = patch("paper_search_mcp.academic_platforms.dblp.time.sleep").start()
        self.addCleanup(patch.stopall)

    def test_persistent_rate_limit_raises(self):
        with patch.object(self.searcher.session, "get",
                          return_value=_response(429, headers={"Retry-After": "2"})) as get:
            with self.assertRaises(DBLPUnavailable) as ctx:
                self.searcher.search("microservices", max_results=3)

        self.assertEqual(get.call_count, 3)
        self.assertIn("429", str(ctx.exception))

    def test_rate_limit_recovers_on_retry(self):
        with patch.object(self.searcher.session, "get", side_effect=[
            _response(429, headers={"Retry-After": "1"}),
            _response(200, XML_ONE_HIT),
        ]):
            papers = self.searcher.search("microservices", max_results=3)

        self.assertEqual(len(papers), 1)
        self.assertEqual(papers[0].title, "A dblp paper")
        self.assertIn(1.0, [call.args[0] for call in self.sleep.call_args_list])

    def test_long_retry_after_is_not_waited_out(self):
        with patch.object(self.searcher.session, "get",
                          return_value=_response(429, headers={"Retry-After": "600"})) as get:
            with self.assertRaises(DBLPUnavailable):
                self.searcher.search("microservices", max_results=3)

        self.assertEqual(get.call_count, 1)
        self.sleep.assert_not_called()

    def test_server_error_raises(self):
        with patch.object(self.searcher.session, "get", return_value=_response(503, "<html>503</html>")):
            with self.assertRaises(DBLPUnavailable):
                self.searcher.search("microservices", max_results=3)

    def test_dropped_connection_raises(self):
        with patch.object(self.searcher.session, "get",
                          side_effect=requests.ConnectionError("Remote end closed connection")):
            with self.assertRaises(DBLPUnavailable):
                self.searcher.search("microservices", max_results=3)

    def test_unparseable_body_raises(self):
        with patch.object(self.searcher.session, "get",
                          return_value=_response(200, "429 Too Many Requests")):
            with self.assertRaises(DBLPUnavailable):
                self.searcher.search("microservices", max_results=3)

    def test_html_error_page_raises(self):
        """A throttling page can be well-formed XML — the content type gives it away."""
        with patch.object(self.searcher.session, "get", return_value=_response(
            200, "<html><body>throttled</body></html>", {"Content-Type": "text/html"}
        )):
            with self.assertRaises(DBLPUnavailable):
                self.searcher.search("microservices", max_results=3)

    def test_empty_result_is_not_an_error(self):
        with patch.object(self.searcher.session, "get", return_value=_response(200, XML_NO_HITS)), \
             patch.object(self.searcher, "_search_html_fallback", return_value=[]) as fallback:
            self.assertEqual(self.searcher.search("no such thing", max_results=3), [])

        fallback.assert_called_once()


class TestDBLPPacing(unittest.TestCase):
    def test_requests_are_paced(self):
        searcher = DBLPSearcher()
        with patch.object(searcher.session, "get", return_value=_response(200, XML_ONE_HIT)), \
             patch("paper_search_mcp.academic_platforms.dblp.time.sleep") as sleep:
            searcher.search("first", max_results=1)
            self.assertEqual(sleep.call_count, 0)  # no wait before the first request
            searcher.search("second", max_results=1)

        self.assertEqual(sleep.call_count, 1)
        self.assertLessEqual(sleep.call_args[0][0], DBLPSearcher.MIN_INTERVAL_SEC)


if __name__ == "__main__":
    unittest.main()
