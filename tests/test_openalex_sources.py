"""Zeitschriftenkennzahlen aus dem OpenAlex-/sources-Endpoint.

Alle Requests sind gemockt. Geprüft wird vor allem, dass eine fehlende Kennzahl
als fehlend ankommt und nicht als 0 — eine 0 in einer Kennzahlenspalte liest
sich als Aussage über die Zeitschrift, ist aber fast immer eine Datenlücke.
"""
import unittest
from datetime import datetime
from unittest.mock import patch

from paper_search_mcp.citations.openalex_graph import OpenAlexFehler
from paper_search_mcp.journals import openalex_sources as quellen
from paper_search_mcp.paper import Paper


def _quelle(kennung="S1", name="Automatica", stats=None, **overrides):
    daten = {
        "id": f"https://openalex.org/{kennung}",
        "display_name": name,
        "issn_l": "0005-1098",
        "type": "journal",
        "is_oa": False,
        "is_in_doaj": False,
        "host_organization_name": "Elsevier BV",
        "apc_usd": 3760,
        "works_count": 15823,
        "summary_stats": {"2yr_mean_citedness": 5.4768, "h_index": 401, "i10_index": 10366},
    }
    if stats is not None:
        daten["summary_stats"] = stats
    daten.update(overrides)
    return daten


def _paper(extra=None):
    return Paper(
        paper_id="W1", title="A paper", authors=["Ada Lovelace"], abstract="",
        doi="10.1000/abc", published_date=datetime(2022, 1, 1), pdf_url="", url="",
        source="openalex", extra=extra,
    )


class TestHoleQuellen(unittest.TestCase):
    def setUp(self):
        quellen.cache_leeren()

    def test_batch_mit_drei_ids_kostet_einen_request(self):
        antwort = {"results": [_quelle(f"S{i}", f"Journal {i}") for i in (1, 2, 3)]}
        with patch.object(quellen, "hole_json", return_value=antwort) as gemockt:
            ergebnis = quellen.hole_quellen(["S1", "S2", "S3"])

        self.assertEqual(gemockt.call_count, 1)
        self.assertEqual(sorted(ergebnis), ["S1", "S2", "S3"])
        self.assertEqual(ergebnis["S2"]["name"], "Journal 2")

    def test_batch_mit_120_ids_wird_in_dreier_bloecke_geteilt(self):
        ids = [f"S{i}" for i in range(1, 121)]
        with patch.object(quellen, "hole_json", return_value={"results": []}) as gemockt:
            quellen.hole_quellen(ids)

        self.assertEqual(gemockt.call_count, 3)
        groessen = [
            len(aufruf.args[1]["filter"].split(":", 1)[1].split("|"))
            for aufruf in gemockt.call_args_list
        ]
        self.assertEqual(groessen, [50, 50, 20])

    def test_gecachte_id_loest_keinen_request_aus(self):
        antwort = {"results": [_quelle("S1")]}
        with patch.object(quellen, "hole_json", return_value=antwort) as gemockt:
            quellen.hole_quellen(["S1"])
            quellen.hole_quellen(["S1"])

        self.assertEqual(gemockt.call_count, 1)

    def test_fehlende_summary_stats_liefert_kein_null(self):
        antwort = {"results": [_quelle("S1", stats={})]}
        with patch.object(quellen, "hole_json", return_value=antwort):
            ergebnis = quellen.hole_quellen(["S1"])

        self.assertNotIn("zit_schnitt_2j", ergebnis["S1"])
        self.assertNotIn("h_index", ergebnis["S1"])
        self.assertEqual(ergebnis["S1"]["name"], "Automatica")

    def test_zitationsschnitt_null_wird_weggelassen(self):
        antwort = {"results": [_quelle("S1", stats={"2yr_mean_citedness": 0, "h_index": 12})]}
        with patch.object(quellen, "hole_json", return_value=antwort):
            ergebnis = quellen.hole_quellen(["S1"])

        self.assertNotIn("zit_schnitt_2j", ergebnis["S1"])
        self.assertEqual(ergebnis["S1"]["h_index"], 12)

    def test_unbekannte_id_fehlt_im_ergebnis_ohne_exception(self):
        antwort = {"results": [_quelle("S1")]}
        with patch.object(quellen, "hole_json", return_value=antwort):
            ergebnis = quellen.hole_quellen(["S1", "S999"])

        self.assertIn("S1", ergebnis)
        self.assertNotIn("S999", ergebnis)

    def test_kreditfehler_wird_durchgereicht(self):
        fehler = OpenAlexFehler("OpenAlex-Kreditkontingent erschöpft (HTTP 409).")
        with patch.object(quellen, "hole_json", side_effect=fehler):
            with self.assertRaises(OpenAlexFehler) as gefangen:
                quellen.hole_quellen(["S1"])

        self.assertIn("409", str(gefangen.exception))

    def test_zitationsschnitt_wird_gerundet(self):
        with patch.object(quellen, "hole_json", return_value={"results": [_quelle("S1")]}):
            ergebnis = quellen.hole_quellen(["S1"])

        self.assertEqual(ergebnis["S1"]["zit_schnitt_2j"], 5.477)


class TestAnreicherung(unittest.TestCase):
    def setUp(self):
        quellen.cache_leeren()

    def test_paper_ohne_quelle_id_loest_keinen_request_aus(self):
        papers = [_paper({"journal": "Ein Preprint-Server"})]
        with patch.object(quellen, "hole_json") as gemockt:
            ergebnis = quellen.reichere_an(papers)

        gemockt.assert_not_called()
        self.assertNotIn("zit_schnitt_2j", ergebnis[0].extra)

    def test_api_fehler_laesst_die_trefferliste_stehen(self):
        papers = [_paper({"quelle_id": "S1", "journal": "Automatica"})]
        with patch.object(quellen, "hole_json", side_effect=OpenAlexFehler("HTTP 429")):
            ergebnis = quellen.reichere_an(papers)

        self.assertEqual(len(ergebnis), 1)
        self.assertEqual(ergebnis[0].extra["journal"], "Automatica")
        self.assertNotIn("zit_schnitt_2j", ergebnis[0].extra)

    def test_kennzahlen_landen_im_extra(self):
        papers = [_paper({"quelle_id": "S1"})]
        with patch.object(quellen, "hole_json", return_value={"results": [_quelle("S1")]}):
            ergebnis = quellen.reichere_an(papers)

        self.assertEqual(ergebnis[0].extra["zit_schnitt_2j"], 5.477)
        self.assertEqual(ergebnis[0].extra["zeitschrift_h_index"], 401)

    def test_zwei_treffer_derselben_zeitschrift_kosten_einen_request(self):
        papers = [_paper({"quelle_id": "S1"}), _paper({"quelle_id": "S1"})]
        with patch.object(quellen, "hole_json", return_value={"results": [_quelle("S1")]}) as gemockt:
            quellen.reichere_an(papers)

        self.assertEqual(gemockt.call_count, 1)

    def test_dict_variante_reichert_serialisierte_treffer_an(self):
        treffer = [{"title": "A", "extra": {"quelle_id": "S1"}}, {"title": "B"}]
        with patch.object(quellen, "hole_json", return_value={"results": [_quelle("S1")]}):
            ergebnis = quellen.reichere_dicts_an(treffer)

        self.assertEqual(ergebnis[0]["extra"]["zit_schnitt_2j"], 5.477)
        self.assertNotIn("extra", ergebnis[1])


class TestKennungserkennung(unittest.TestCase):
    def test_issn_muster(self):
        for issn in ("0005-1098", "2041-1723", "1748-022X"):
            self.assertTrue(quellen.ist_issn(issn), issn)

    def test_keine_issn(self):
        for text in ("Automatica", "S51360982", "10.1000/abc", "0005-109"):
            self.assertFalse(quellen.ist_issn(text), text)

    def test_source_id_muster(self):
        self.assertTrue(quellen.ist_source_id("S51360982"))
        self.assertFalse(quellen.ist_source_id("W2741809807"))
        self.assertFalse(quellen.ist_source_id("Science"))


if __name__ == "__main__":
    unittest.main()
