"""bioRxiv und medRxiv listen eine Kategorie, sie suchen nicht.

Beide APIs kennen keine Stichwortsuche. Sie filtern über exakte Kategorienamen
und ignorieren alles andere stillschweigend: `machine learning` und
`voelliger unsinn xyz` lieferten dieselben fünf Sätze — die zuletzt
eingestellten Preprints, ausgewiesen als Treffer zur Anfrage. Über
`search_papers(sources="all")` landete das in jeder Sammelsuche.

Die netzfreien Tests hier prüfen beides: dass ein Begriff, der keine Kategorie
ist, als solcher gemeldet wird, und dass fremde Kategorien auch dann nicht
durchrutschen, wenn der Serverfilter nicht greift.
"""
import unittest
from unittest.mock import patch

import requests

from paper_search_mcp.academic_platforms.biorxiv import BioRxivSearcher
from paper_search_mcp.academic_platforms.medrxiv import MedRxivSearcher
from paper_search_mcp.server import ALL_SOURCES, OPT_IN_SOURCES, _parse_sources


def eintrag(doi: str, kategorie: str) -> dict:
    return {
        "doi": doi,
        "title": f"Preprint {doi}",
        "authors": "Doe, Jane; Roe, Richard",
        "abstract": "…",
        "date": "2026-08-15",
        "version": "1",
        "category": kategorie,
    }


class FakeAntwort:
    def __init__(self, collection):
        self._collection = collection

    def raise_for_status(self):
        pass

    def json(self):
        return {"collection": self._collection}


def mit_antwort(searcher, collection):
    """Ersetzt die HTTP-Sitzung durch eine feste Antwort."""
    return patch.object(searcher.session, "get",
                        return_value=FakeAntwort(collection))


class TestKategorielisten(unittest.TestCase):
    """Gilt für beide Server — sie teilen sich die Implementierung."""

    def setUp(self):
        self.searcher = BioRxivSearcher()

    def test_passende_kategorie_kommt_durch(self):
        with mit_antwort(self.searcher, [eintrag("10.1101/1", "bioinformatics")]):
            papers = self.searcher.search("bioinformatics", max_results=5)
        self.assertEqual(len(papers), 1)
        self.assertEqual(papers[0].categories, ["bioinformatics"])

    def test_leerzeichen_und_grossschreibung(self):
        with mit_antwort(self.searcher, [eintrag("10.1101/1", "cell biology")]):
            papers = self.searcher.search("Cell Biology", max_results=5)
        self.assertEqual(len(papers), 1)

    def test_kein_kategoriename_wird_gemeldet(self):
        """Der Fall, der bisher Zufallstreffer lieferte."""
        collection = [eintrag("10.1101/1", "ecology"),
                      eintrag("10.1101/2", "biochemistry")]
        with mit_antwort(self.searcher, collection):
            with self.assertRaises(ValueError) as ctx:
                self.searcher.search("machine learning", max_results=5)
        meldung = str(ctx.exception)
        self.assertIn("machine learning", meldung)
        self.assertIn("ecology", meldung)      # nennt, was es tatsächlich gibt
        self.assertIn("europepmc", meldung)    # und den Weg zur Stichwortsuche

    def test_fremde_kategorien_rutschen_nicht_durch(self):
        """Auch wenn der Serverfilter nicht greift, wird clientseitig gefiltert."""
        collection = [eintrag("10.1101/1", "ecology"),
                      eintrag("10.1101/2", "bioinformatics")]
        with mit_antwort(self.searcher, collection):
            papers = self.searcher.search("bioinformatics", max_results=5)
        self.assertEqual([p.categories for p in papers], [["bioinformatics"]])

    def test_leere_antwort_meldet_keine_falsche_kategorie(self):
        """Ohne Daten lässt sich nichts über den Begriff aussagen."""
        with mit_antwort(self.searcher, []):
            self.assertEqual(self.searcher.search("bioinformatics"), [])

    def test_netzfehler_bleibt_ein_leeres_ergebnis(self):
        with patch.object(self.searcher.session, "get",
                          side_effect=requests.exceptions.ConnectionError("kein Netz")):
            self.assertEqual(self.searcher.search("bioinformatics"), [])

    def test_medrxiv_verhaelt_sich_gleich(self):
        m = MedRxivSearcher()
        with mit_antwort(m, [eintrag("10.1101/9", "oncology")]):
            self.assertEqual(len(m.search("oncology", max_results=5)), 1)
        with mit_antwort(m, [eintrag("10.1101/9", "oncology")]):
            with self.assertRaises(ValueError):
                m.search("machine learning", max_results=5)


class TestQuellenwahl(unittest.TestCase):
    def test_nicht_in_der_sammelsuche(self):
        self.assertNotIn("biorxiv", ALL_SOURCES)
        self.assertNotIn("medrxiv", ALL_SOURCES)
        self.assertNotIn("biorxiv", _parse_sources("all"))

    def test_auf_ausdrueckliche_nennung_weiter_waehlbar(self):
        self.assertEqual(_parse_sources("biorxiv,medrxiv"), ["biorxiv", "medrxiv"])
        self.assertEqual(OPT_IN_SOURCES, ["biorxiv", "medrxiv"])

    def test_unbekannte_quelle_faellt_weiterhin_weg(self):
        self.assertEqual(_parse_sources("biorxiv,gibtsnicht"), ["biorxiv"])


if __name__ == "__main__":
    unittest.main()
