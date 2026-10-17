"""Regression tests: Paper.authors must be a list of names.

Zenodo and HAL joined the names into one string. _format_authors iterates the
list, so a string came out one character per "author":
"Mausberg, Samuel" became "M; a; u u. a. (n=16)".
"""
import unittest

from paper_search_mcp.academic_platforms.hal import HALSearcher
from paper_search_mcp.academic_platforms.zenodo import ZenodoSearcher
from paper_search_mcp.paper import Paper


class TestZenodoAuthors(unittest.TestCase):
    def test_creators_become_one_entry_each(self):
        paper = ZenodoSearcher()._parse_record({
            "id": 1,
            "metadata": {
                "title": "Ein Datensatz",
                "creators": [
                    {"name": "Mausberg, Samuel"},
                    {"given_name": "Ada", "family_name": "Lovelace"},
                    {"name": ""},
                ],
            },
        })
        self.assertEqual(paper.authors, ["Mausberg, Samuel", "Ada Lovelace"])
        self.assertEqual(paper.to_dict()["authors"], "Mausberg, Samuel; Ada Lovelace")


class TestHALAuthors(unittest.TestCase):
    def test_author_list_is_kept_as_list(self):
        paper = HALSearcher()._parse_doc({
            "halId_s": "hal-00000001",
            "title_s": ["Un article"],
            "authFullName_s": ["Redeer Avdal Saleh", "Hajar Maseeh Yasin"],
        })
        self.assertEqual(paper.authors, ["Redeer Avdal Saleh", "Hajar Maseeh Yasin"])
        self.assertEqual(
            paper.to_dict()["authors"], "Redeer Avdal Saleh; Hajar Maseeh Yasin"
        )

    def test_single_string_author(self):
        paper = HALSearcher()._parse_doc({
            "halId_s": "hal-00000002",
            "title_s": "Un article",
            "authFullName_s": "Marie Curie",
        })
        self.assertEqual(paper.authors, ["Marie Curie"])


class TestPaperGuard(unittest.TestCase):
    def _paper(self, authors):
        return Paper(
            paper_id="x", title="t", authors=authors, abstract="", doi="",
            published_date=None, pdf_url="", url="", source="test",
        )

    def test_string_is_wrapped_not_split(self):
        self.assertEqual(self._paper("Mausberg, Samuel").authors, ["Mausberg, Samuel"])

    def test_blank_string_is_empty(self):
        self.assertEqual(self._paper("  ").authors, [])


if __name__ == "__main__":
    unittest.main()
