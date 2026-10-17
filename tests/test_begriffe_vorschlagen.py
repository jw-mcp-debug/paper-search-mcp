"""Englisches Suchvokabular aus den OpenAlex-Keywords.

Alle Requests sind gemockt. Geprüft wird vor allem, was Geld oder Kontext
kostet: kein /text-Aufruf für zu kurze Texte, keiner für ein bereits gefragtes
Thema, keine Plural- und Schreibvarianten als „Synonyme", und dass ein Ausfall
der Anreicherung die schon bezahlten Begriffe nicht verwirft.
"""
import asyncio
import json
import unittest
from unittest.mock import patch

from paper_search_mcp.begriffe import openalex_keywords as kw
from paper_search_mcp.citations.openalex_graph import OpenAlexFehler
from paper_search_mcp.server import mcp

TEXT = "Wärmepumpen im Altbau"


def _kw(slug, name, score):
    return {"id": f"https://openalex.org/keywords/{slug}", "display_name": name, "score": score}


TAGS = {"keywords": [
    _kw("old-buildings", "old buildings", 0.833),
    _kw("heat-pumps", "heat pumps", 0.999),
    _kw("building-retrofitting", "building retrofit", 0.418),
]}
KENNZAHLEN = {"results": [
    {"id": "https://openalex.org/keywords/heat-pumps", "works_count": 37705,
     "display_name_alternatives": ["heat pump", "Heat-Pumps", "heat pump technology", "heat pump systems"]},
    {"id": "https://openalex.org/keywords/old-buildings", "works_count": 2272,
     "display_name_alternatives": ["old building", "older buildings"]},
    {"id": "https://openalex.org/keywords/building-retrofitting", "works_count": 10002,
     "display_name_alternatives": []},
]}
AUTOCOMPLETE = {"results": [
    {"id": "https://openalex.org/keywords/heat-pumps", "display_name": "heat pumps", "works_count": 37705},
    {"id": "https://openalex.org/keywords/air-to-water-heat-pump", "display_name": "air-to-water heat pump", "works_count": 2300},
    {"id": "https://openalex.org/keywords/x", "display_name": "leer", "works_count": 0},
]}


def _antworten(url, params):
    if url == kw.TEXT_KEYWORDS:
        return TAGS
    if url == kw.KEYWORDS:
        return KENNZAHLEN
    return AUTOCOMPLETE if params["q"] == "heat pumps" else {"results": []}


class TestVorschlagen(unittest.TestCase):
    def setUp(self):
        kw.cache_leeren()

    def test_begriffe_nach_relevanz_mit_werkzahl(self):
        with patch.object(kw, "hole_json", side_effect=_antworten):
            ergebnis = kw.vorschlagen(TEXT)
        self.assertEqual([b["begriff"] for b in ergebnis["begriffe"]],
                         ["heat pumps", "old buildings", "building retrofit"])
        self.assertEqual(ergebnis["begriffe"][0]["werke"], 37705)
        self.assertNotIn("id", ergebnis["begriffe"][0])

    def test_synonyme_ohne_plural_und_schreibweise(self):
        with patch.object(kw, "hole_json", side_effect=_antworten):
            ergebnis = kw.vorschlagen(TEXT)
        begriffe = {b["begriff"]: b for b in ergebnis["begriffe"]}
        self.assertEqual(begriffe["heat pumps"]["synonyme"],
                         ["heat pump technology", "heat pump systems"])
        # 'old building' und 'older buildings': nur das zweite ist ein anderes Wort.
        self.assertEqual(begriffe["old buildings"]["synonyme"], ["older buildings"])
        self.assertNotIn("synonyme", begriffe["building retrofit"])

    def test_varianten_ohne_bekannte_und_leere(self):
        with patch.object(kw, "hole_json", side_effect=_antworten):
            ergebnis = kw.vorschlagen(TEXT)
        self.assertEqual(ergebnis["varianten"], [
            {"begriff": "air-to-water heat pump", "werke": 2300, "zu": "heat pumps"},
        ])

    def test_keine_varianten_zu_allerweltsbegriffen(self):
        breit = {"results": [dict(KENNZAHLEN["results"][0], works_count=571466)]
                 + KENNZAHLEN["results"][1:]}

        def antworten(url, params):
            return breit if url == kw.KEYWORDS else _antworten(url, params)

        with patch.object(kw, "hole_json", side_effect=antworten) as gemockt:
            ergebnis = kw.vorschlagen(TEXT)
        gefragt = [c.args[1]["q"] for c in gemockt.call_args_list if c.args[0] == kw.AUTOCOMPLETE]
        self.assertEqual(gefragt, ["old buildings", "building retrofit"])
        self.assertEqual(ergebnis["varianten"], [])

    def test_zu_kurzer_text_kostet_keinen_request(self):
        with patch.object(kw, "hole_json") as gemockt:
            with self.assertRaises(OpenAlexFehler):
                kw.vorschlagen("Wärmepumpe")
        gemockt.assert_not_called()

    def test_zweite_anfrage_kommt_aus_dem_cache(self):
        with patch.object(kw, "hole_json", side_effect=_antworten) as gemockt:
            kw.vorschlagen(TEXT)
            erste = gemockt.call_count
            kw.vorschlagen("  Wärmepumpen   im Altbau ")
        self.assertEqual(gemockt.call_count, erste)

    def test_ausfall_der_anreicherung_behaelt_die_begriffe(self):
        def nur_text(url, params):
            if url == kw.TEXT_KEYWORDS:
                return TAGS
            raise OpenAlexFehler("OpenAlex-Rate-Limit erreicht (HTTP 429).")

        with patch.object(kw, "hole_json", side_effect=nur_text):
            ergebnis = kw.vorschlagen(TEXT)
        self.assertEqual(len(ergebnis["begriffe"]), 3)
        self.assertIn("429", ergebnis["errors"]["openalex"])
        self.assertNotIn("werke", ergebnis["begriffe"][0])

    def test_langer_text_wird_gekuerzt(self):
        with patch.object(kw, "hole_json", return_value={"keywords": []}) as gemockt:
            kw.vorschlagen("Wort " * 1000)
        self.assertLessEqual(len(gemockt.call_args.args[1]["title"]), kw.MAX_ZEICHEN)


class TestTool(unittest.TestCase):
    def setUp(self):
        kw.cache_leeren()

    def test_tool_ist_registriert_und_meldet_fehler_als_errors(self):
        namen = [t.name for t in asyncio.run(mcp.list_tools())]
        self.assertIn("begriffe_vorschlagen", namen)
        with patch.object(kw, "hole_json") as gemockt:
            inhalt = asyncio.run(mcp.call_tool("begriffe_vorschlagen", {"text": "kurz"}))
        # Ohne outputSchema (siehe test_tool_schema_diet) kommt nur der Text zurück.
        ergebnis = json.loads(inhalt[0].text)
        gemockt.assert_not_called()
        self.assertEqual(ergebnis["begriffe"], [])
        self.assertIn("zu kurz", ergebnis["errors"]["openalex"])


if __name__ == "__main__":
    unittest.main()
