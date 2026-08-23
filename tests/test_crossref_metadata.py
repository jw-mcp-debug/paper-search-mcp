"""CrossRef metadata must not carry placeholders or markup.

A missing date used to be filled with 1970-01-01, which corrupts every year
filter and sort, and abstracts arrive as JATS XML.
"""
import unittest

from paper_search_mcp.academic_platforms.crossref import CrossRefSearcher, _strip_jats


class TestCrossRefDates(unittest.TestCase):
    def setUp(self):
        self.searcher = CrossRefSearcher()

    def test_missing_date_stays_empty(self):
        paper = self.searcher._parse_crossref_item(
            {"DOI": "10.1000/x", "type": "journal-article", "title": ["No date here"]}
        )
        self.assertIsNone(paper.published_date)
        self.assertNotIn("published_date", paper.to_dict())

    def test_a_yearless_field_falls_through_to_the_next_one(self):
        """The placeholder used to hide the real date.

        _extract_date returned 1970-01-01 for a `published` entry without a
        year, which is truthy, so the fallback to `issued` never ran and the
        real publication date was lost.
        """
        paper = self.searcher._parse_crossref_item({
            "DOI": "10.1000/w", "type": "journal-article", "title": ["Partial date"],
            "published": {"date-parts": [[None]]},
            "issued": {"date-parts": [[2018, 10, 4]]},
        })
        self.assertEqual(paper.published_date.year, 2018)

    def test_present_date_is_used(self):
        paper = self.searcher._parse_crossref_item({
            "DOI": "10.1000/y", "type": "journal-article", "title": ["Dated"],
            "issued": {"date-parts": [[2021, 5, 4]]},
        })
        self.assertEqual(paper.published_date.year, 2021)


class TestJatsStripping(unittest.TestCase):
    def test_jats_markup_is_removed(self):
        raw = ("<jats:title>Abstract</jats:title><jats:p>The growing need for "
               "<jats:italic>sustainable</jats:italic> materials &amp; methods.</jats:p>")
        self.assertEqual(_strip_jats(raw), "The growing need for sustainable materials & methods.")

    def test_plain_text_is_untouched(self):
        self.assertEqual(_strip_jats("Plain abstract."), "Plain abstract.")

    def test_empty_stays_empty(self):
        self.assertEqual(_strip_jats(""), "")
        self.assertEqual(_strip_jats(None), "")

    def test_abstracts_are_stripped_while_parsing(self):
        paper = CrossRefSearcher()._parse_crossref_item({
            "DOI": "10.1000/z", "type": "journal-article", "title": ["Marked up"],
            "abstract": "<jats:p>Some <jats:sup>2</jats:sup> text.</jats:p>",
        })
        self.assertEqual(paper.abstract, "Some 2 text.")


if __name__ == "__main__":
    unittest.main()
