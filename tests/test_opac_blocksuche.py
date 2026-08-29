"""Die Blocksuche bildet eine Suchbegriffstabelle in einer Anfrage ab.

Der KOBV-Katalog kennt kein Relevanzranking: jedes Wort einer Anfrage ist ein
harter UND-Filter. Wer drei Konzepte in eine Anfrage schreibt, bekommt deshalb
regelmäßig null Treffer, obwohl der Bestand zum Thema etwas hergibt. Die
Blocksuche trennt Konzepte (';') von ihren Synonymen (' OR '), sodass die
Synonyme die Treffermenge vergrößern statt sie zu verkleinern.

Alle Tests hier kommen ohne Netz aus — geprüft wird der erzeugte PQF-Ausdruck.
"""
import unittest
from unittest.mock import patch

from paper_search_mcp.opac import tools
from paper_search_mcp.opac.z3950_client import (
    BHT_ISIL, BIB1_ATTR, _pqf, suche_bht_sync, zerlege_bloecke,
)

ANY = BIB1_ATTR["any"]
SUBJ = BIB1_ATTR["subject"]


class TestZerlegung(unittest.TestCase):
    def test_ein_begriff_bleibt_ein_block(self):
        self.assertEqual(zerlege_bloecke("Gamification"), [["Gamification"]])

    def test_oder_trennt_alternativen(self):
        self.assertEqual(zerlege_bloecke("Deskilling OR Dequalifizierung"),
                         [["Deskilling", "Dequalifizierung"]])

    def test_semikolon_trennt_bloecke(self):
        self.assertEqual(zerlege_bloecke("KI OR Intelligenz; Bildung"),
                         [["KI", "Intelligenz"], ["Bildung"]])

    def test_oder_ist_case_insensitive(self):
        self.assertEqual(zerlege_bloecke("a or b"), [["a", "b"]])

    def test_oder_als_wortbestandteil_trennt_nicht(self):
        """'Ordnung' und 'Sensor' enthalten 'or', sind aber keine Operatoren."""
        self.assertEqual(zerlege_bloecke("Ordnung Sensor"), [["Ordnung Sensor"]])


class TestRueckwaertskompatibilitaet(unittest.TestCase):
    """Eingaben ohne ';' und ' OR ' müssen exakt dasselbe PQF ergeben wie zuvor."""

    def test_einzelwort(self):
        self.assertEqual(_pqf(ANY, "Gamification", None),
                         "@attr 1=1016 Gamification")

    def test_mehrwort_wird_und_verknuepft(self):
        self.assertEqual(_pqf(ANY, "Beton Nachhaltigkeit", None),
                         "@and @attr 1=1016 Beton @attr 1=1016 Nachhaltigkeit")

    def test_subject_bleibt_phrase(self):
        self.assertEqual(_pqf(SUBJ, "Nachhaltiges Bauen", None),
                         '@attr 1=21 "Nachhaltiges Bauen"')

    def test_isil_filter_umschliesst_die_anfrage(self):
        self.assertEqual(_pqf(ANY, "Gamification", BHT_ISIL),
                         "@and @attr 1=1044 DE-B768 @attr 1=1016 Gamification")


class TestBlocksuche(unittest.TestCase):
    def test_synonyme_werden_oder_verknuepft(self):
        self.assertEqual(_pqf(ANY, "Deskilling OR Dequalifizierung", None),
                         "@or @attr 1=1016 Deskilling @attr 1=1016 Dequalifizierung")

    def test_bloecke_werden_und_verknuepft(self):
        self.assertEqual(
            _pqf(ANY, "Deskilling OR Dequalifizierung; Bildung", None),
            "@and @or @attr 1=1016 Deskilling @attr 1=1016 Dequalifizierung "
            "@attr 1=1016 Bildung")

    def test_anfuehrungszeichen_erzwingen_eine_phrase(self):
        """Ohne sie würde 'Cognitive Offloading' in zwei UND-Terme zerfallen."""
        self.assertEqual(_pqf(ANY, '"Cognitive Offloading" OR Auslagerung', None),
                         '@or @attr 1=1016 "Cognitive Offloading" '
                         '@attr 1=1016 Auslagerung')

    def test_block_mit_mehreren_woertern_bleibt_und(self):
        self.assertEqual(_pqf(ANY, "Beton Nachhaltigkeit; Bildung", None),
                         "@and @and @attr 1=1016 Beton @attr 1=1016 Nachhaltigkeit "
                         "@attr 1=1016 Bildung")

    def test_drei_synonyme(self):
        self.assertEqual(_pqf(ANY, "a OR b OR c", None),
                         "@or @attr 1=1016 a @or @attr 1=1016 b @attr 1=1016 c")


class TestFreitextFallback(unittest.TestCase):
    def test_fallback_sucht_zusaetzlich_im_freitextfeld(self):
        self.assertEqual(_pqf(SUBJ, "Deskilling", None, auch_freitext=True),
                         "@or @attr 1=21 Deskilling @attr 1=1016 Deskilling")

    def test_fallback_ist_bei_any_wirkungslos(self):
        """'any' IST das Freitextfeld — ein @or mit sich selbst wäre Ballast."""
        self.assertEqual(_pqf(ANY, "Deskilling", None, auch_freitext=True),
                         "@attr 1=1016 Deskilling")

    def test_schlagwortsuche_ohne_treffer_faellt_auf_freitext_zurueck(self):
        with patch("paper_search_mcp.opac.z3950_client._suche_einmal") as einmal:
            einmal.side_effect = [
                {"treffer_gesamt": 0, "treffer": []},
                {"treffer_gesamt": 115, "treffer": [{"titel": "x"}]},
            ]
            ergebnis = suche_bht_sync(SUBJ, "Deskilling", None, 10)
        self.assertEqual(ergebnis["treffer_gesamt"], 115)
        self.assertTrue(ergebnis["freitext_fallback"])
        self.assertTrue(einmal.call_args.kwargs["auch_freitext"])

    def test_erfolgreiche_schlagwortsuche_bleibt_unangetastet(self):
        """Die Präzision der GND-Suche darf nicht durch Freitext verwässert werden."""
        with patch("paper_search_mcp.opac.z3950_client._suche_einmal") as einmal:
            einmal.return_value = {"treffer_gesamt": 531, "treffer": []}
            ergebnis = suche_bht_sync(SUBJ, "Künstliche Intelligenz", None, 10)
        self.assertEqual(einmal.call_count, 1)
        self.assertNotIn("freitext_fallback", ergebnis)

    def test_kein_fallback_wenn_auch_der_freitext_leer_bleibt(self):
        with patch("paper_search_mcp.opac.z3950_client._suche_einmal") as einmal:
            einmal.return_value = {"treffer_gesamt": 0, "treffer": []}
            ergebnis = suche_bht_sync(SUBJ, "Kognitive Delegation", None, 10)
        self.assertNotIn("freitext_fallback", ergebnis)

    def test_verbindungsfehler_loest_keinen_fallback_aus(self):
        with patch("paper_search_mcp.opac.z3950_client._suche_einmal") as einmal:
            einmal.return_value = {"fehler": "Verbindungsfehler",
                                   "treffer_gesamt": 0, "treffer": []}
            suche_bht_sync(SUBJ, "Deskilling", None, 10)
        self.assertEqual(einmal.call_count, 1)


class TestPlatzhalter(unittest.TestCase):
    """Der Server liest * und ? stumm als Wortbestandteil statt als Trunkierung."""

    def test_platzhalter_wird_gemeldet(self):
        with patch("paper_search_mcp.opac.z3950_client._suche_einmal") as einmal:
            einmal.return_value = {"treffer_gesamt": 612, "treffer": []}
            ergebnis = suche_bht_sync(ANY, "Bildung*", None, 10)
        self.assertTrue(ergebnis["platzhalter"])

    def test_ohne_platzhalter_keine_meldung(self):
        with patch("paper_search_mcp.opac.z3950_client._suche_einmal") as einmal:
            einmal.return_value = {"treffer_gesamt": 612, "treffer": []}
            ergebnis = suche_bht_sync(ANY, "Bildung", None, 10)
        self.assertNotIn("platzhalter", ergebnis)


class TestAusgabe(unittest.TestCase):
    def test_fallback_wird_im_ergebnis_ausgewiesen(self):
        text = tools._formatiere_ergebnisse(
            {"treffer_gesamt": 1, "treffer": [{"titel": "T"}], "freitext_fallback": True},
            "Deskilling", "BHT-OPAC")
        self.assertIn("nicht angesetzt", text)

    def test_platzhalter_warnung_erscheint(self):
        text = tools._formatiere_ergebnisse(
            {"treffer_gesamt": 1, "treffer": [{"titel": "T"}], "platzhalter": True},
            "Bildung*", "BHT-OPAC")
        self.assertIn("Trunkierung", text)

    def test_nullresultat_erklaert_die_und_verknuepfung(self):
        text = tools._formatiere_ergebnisse(
            {"treffer_gesamt": 0, "treffer": []}, "a b c", "KOBV-Verbund")
        self.assertIn("UND", text)
        self.assertIn(" OR ", text)

    def test_nullresultat_warnt_vor_wirkungslosem_platzhalter(self):
        text = tools._formatiere_ergebnisse(
            {"treffer_gesamt": 0, "treffer": [], "platzhalter": True},
            "Bildung*", "KOBV-Verbund")
        self.assertIn("Trunkierung", text)


if __name__ == "__main__":
    unittest.main()
