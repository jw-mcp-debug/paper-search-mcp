"""The serialized result carries only what helps judge a paper.

Every field is paid for in the model's context on every call, and the result
of a search accumulates over a session, so empty fields, restatements of the
DOI and runaway author lists are dropped.
"""
import unittest
from datetime import datetime

from paper_search_mcp import server
from paper_search_mcp.paper import Paper


def _paper(**overrides):
    fields = dict(
        paper_id="w123", title="A paper", authors=["Ada Lovelace"], abstract="An abstract.",
        doi="10.1000/abc", published_date=datetime(2022, 6, 17), pdf_url="", url="",
        source="openalex",
    )
    fields.update(overrides)
    return Paper(**fields)


class TestPaperSerialization(unittest.TestCase):
    def test_empty_fields_are_omitted(self):
        data = _paper().to_dict()
        for absent in ("pdf_url", "url", "updated_date", "keywords", "references", "extra", "citations"):
            self.assertNotIn(absent, data)
        self.assertEqual(data["title"], "A paper")

    def test_published_date_is_the_year(self):
        self.assertEqual(_paper().to_dict()["published_date"], "2022")

    def test_doi_resolver_url_is_dropped(self):
        for url in ("https://doi.org/10.1000/abc", "http://dx.doi.org/10.1000/ABC"):
            with self.subTest(url=url):
                self.assertNotIn("url", _paper(url=url).to_dict())

    def test_other_urls_are_kept(self):
        data = _paper(url="https://example.org/record/1").to_dict()
        self.assertEqual(data["url"], "https://example.org/record/1")

    def test_paper_id_equal_to_doi_is_dropped(self):
        self.assertNotIn("paper_id", _paper(paper_id="10.1000/abc").to_dict())
        self.assertIn("paper_id", _paper(paper_id="w123").to_dict())

    def test_author_list_is_capped(self):
        authors = [f"Author {i}" for i in range(47)]
        self.assertEqual(
            _paper(authors=authors).to_dict()["authors"],
            "Author 0; Author 1; Author 2 u. a. (n=47)",
        )

    def test_short_author_list_is_untouched(self):
        self.assertEqual(_paper(authors=["A", "B"]).to_dict()["authors"], "A; B")

    def test_categories_are_capped(self):
        data = _paper(categories=["a", "b", "c", "d", "e"]).to_dict()
        self.assertEqual(data["categories"], "a; b; c")

    def test_extra_is_a_dict_limited_to_useful_keys(self):
        data = _paper(extra={"journal": "Nature", "venue": "", "pages": "1-9", "type": "article"}).to_dict()
        self.assertEqual(data["extra"], {"journal": "Nature"})

    def test_journal_metric_keys_survive_the_whitelist(self):
        """Die Kennzahlen wären ohne Eintrag in EXTRA_KEYS stumm verschwunden."""
        extra = {
            "journal": "Automatica", "quelle_id": "S51360982", "issn_l": "0005-1098",
            "quelle_typ": "journal", "zeitschrift_oa": True, "in_doaj": True,
            "zit_schnitt_2j": 5.477, "zeitschrift_h_index": 401,
            "irgendwas_anderes": "wird verworfen",
        }
        data = _paper(extra=extra).to_dict()
        self.assertNotIn("irgendwas_anderes", data["extra"])
        for key in ("quelle_id", "issn_l", "quelle_typ", "zeitschrift_oa",
                    "in_doaj", "zit_schnitt_2j", "zeitschrift_h_index"):
            self.assertIn(key, data["extra"])


class TestSearchResponseShape(unittest.TestCase):
    def test_redundant_response_fields_are_gone(self):
        import asyncio
        from unittest.mock import AsyncMock, patch

        with patch.object(server, "search_crossref", AsyncMock(return_value=[{"title": "t", "doi": "10.1/a"}])):
            result = asyncio.run(server.search_papers("q", max_results_per_source=1, sources="crossref"))

        self.assertEqual(set(result), {"query", "source_results", "errors", "papers", "total"})


class TestDeduplication(unittest.TestCase):
    def test_case_and_plural_differences_still_match(self):
        crossref = {"title": "Stepwise Migration of a Monolith to a Microservices Architecture",
                    "published_date": "2024", "source": "crossref", "abstract": "The full abstract."}
        dblp = {"title": "Stepwise migration of a monolith to a microservice architecture",
                "published_date": "2024", "source": "dblp", "citations": 12}

        deduped = server._dedupe_papers([crossref, dblp])

        self.assertEqual(len(deduped), 1)
        self.assertEqual(deduped[0]["abstract"], "The full abstract.")
        self.assertEqual(deduped[0]["citations"], 12)

    def test_same_title_in_different_years_is_not_merged(self):
        a = {"title": "Annual report", "published_date": "2023"}
        b = {"title": "Annual report", "published_date": "2024"}
        self.assertEqual(len(server._dedupe_papers([a, b])), 2)

    def test_the_richer_record_wins_field_by_field(self):
        first = {"doi": "10.1/x", "title": "T", "abstract": "", "citations": 3,
                 "extra": {"publisher": "P"}}
        second = {"doi": "10.1/x", "title": "T", "abstract": "A real abstract", "citations": 9,
                  "extra": {"journal": "J"}}

        merged = server._dedupe_papers([first, second])[0]

        self.assertEqual(merged["abstract"], "A real abstract")
        self.assertEqual(merged["citations"], 9)
        self.assertEqual(merged["extra"], {"publisher": "P", "journal": "J"})


if __name__ == "__main__":
    unittest.main()
