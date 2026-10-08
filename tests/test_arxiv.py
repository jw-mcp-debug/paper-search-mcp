# tests/test_arxiv.py
import unittest

import requests

from paper_search_mcp.academic_platforms.arxiv import ArxivSearcher

class TestArxivSearcher(unittest.TestCase):
    def test_search(self):
        searcher = ArxivSearcher()
        try:
            papers = searcher.search("machine learning", max_results=10)
        except requests.RequestException as exc:
            self.skipTest(f"arXiv API is unavailable or rate-limited: {exc}")
        print(f"Found {len(papers)} papers for query 'machine learning':")
        for i, paper in enumerate(papers, 1):
            print(f"{i}. {paper.title} (ID: {paper.paper_id})")
        self.assertEqual(len(papers), 10)
        self.assertTrue(papers[0].title)

if __name__ == '__main__':
    unittest.main()