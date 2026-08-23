"""Regression tests: Paper.published_date must be a datetime.

Paper.to_dict() calls .isoformat() on published_date, so a source that
passes a raw string makes every one of its results fail to serialize.
"""
import unittest
from datetime import datetime

from paper_search_mcp.academic_platforms.hal import HALSearcher
from paper_search_mcp.academic_platforms.zenodo import ZenodoSearcher


class TestHALDates(unittest.TestCase):
    def setUp(self):
        self.searcher = HALSearcher()

    def test_year_only_document(self):
        paper = self.searcher._parse_doc({
            "halId_s": "hal-123",
            "title_s": ["A HAL paper"],
            "publicationDateY_i": 2025,
        })
        self.assertEqual(paper.published_date, datetime(2025, 1, 1))
        self.assertEqual(paper.to_dict()["published_date"], "2025-01-01T00:00:00")

    def test_full_submitted_date(self):
        paper = self.searcher._parse_doc({
            "halId_s": "hal-124",
            "title_s": ["Another HAL paper"],
            "submittedDate_s": "2024-03-04 11:22:33",
        })
        self.assertEqual(paper.published_date, datetime(2024, 3, 4))

    def test_missing_date(self):
        paper = self.searcher._parse_doc({"halId_s": "hal-125", "title_s": ["No date"]})
        self.assertIsNone(paper.published_date)
        self.assertEqual(paper.to_dict()["published_date"], "")


class TestZenodoDates(unittest.TestCase):
    def setUp(self):
        self.searcher = ZenodoSearcher()

    def _record(self, publication_date):
        return {
            "id": 42,
            "metadata": {
                "title": "A Zenodo record",
                "publication_date": publication_date,
                "creators": [{"name": "Example, Alice"}],
            },
        }

    def test_full_date(self):
        paper = self.searcher._parse_record(self._record("2025-11-17"))
        self.assertEqual(paper.published_date, datetime(2025, 11, 17))
        self.assertEqual(paper.to_dict()["published_date"], "2025-11-17T00:00:00")

    def test_partial_dates(self):
        self.assertEqual(
            self.searcher._parse_record(self._record("2025-11")).published_date,
            datetime(2025, 11, 1),
        )
        self.assertEqual(
            self.searcher._parse_record(self._record("2025")).published_date,
            datetime(2025, 1, 1),
        )

    def test_missing_date(self):
        paper = self.searcher._parse_record(self._record(""))
        self.assertIsNone(paper.published_date)


if __name__ == "__main__":
    unittest.main()
