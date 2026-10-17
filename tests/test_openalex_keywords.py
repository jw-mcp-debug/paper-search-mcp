"""OpenAlex-Schlagwörter statt Concepts.

Der Request ist gemockt. Geprüft wird die Auswahl: nach Score sortiert, höchstens
fünf, und ein Werk ohne Keywords bekommt keine erfundenen Ersatzbegriffe.
"""
import unittest
from unittest.mock import MagicMock

from paper_search_mcp.academic_platforms.openalex import OpenAlexSearcher


def _werk(keywords, concepts=None):
    return {
        "id": "https://openalex.org/W1",
        "title": "A paper",
        "keywords": keywords,
        "concepts": concepts or [{"display_name": "Christian ministry"}],
        "open_access": {},
    }


def _suche(werk):
    antwort = MagicMock(status_code=200)
    antwort.json.return_value = {"results": [werk]}
    sucher = OpenAlexSearcher()
    sucher.session = MagicMock()
    sucher.session.get.return_value = antwort
    return sucher.search("rdm", max_results=5)[0]


class TestOpenAlexKeywords(unittest.TestCase):
    def test_best_keywords_first_and_capped_at_five(self):
        kws = [{"display_name": f"k{i}", "score": i / 10} for i in range(8)]
        paper = _suche(_werk(kws))
        self.assertEqual(paper.keywords, ["k7", "k6", "k5", "k4", "k3"])

    def test_concepts_are_no_longer_reported(self):
        paper = _suche(_werk([{"display_name": "saturation", "score": 0.9}]))
        self.assertEqual(paper.categories, [])
        self.assertNotIn("Christian ministry", paper.to_dict().get("categories", ""))

    def test_work_without_keywords_gets_none(self):
        for fehlend in ([], None):
            with self.subTest(keywords=fehlend):
                self.assertEqual(_suche(_werk(fehlend)).keywords, [])

    def test_missing_score_sorts_last(self):
        paper = _suche(_werk([{"display_name": "ohne"}, {"display_name": "mit", "score": 0.5}]))
        self.assertEqual(paper.keywords, ["mit", "ohne"])


if __name__ == "__main__":
    unittest.main()
