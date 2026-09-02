"""Bestandslabel, Volltextlink und Fernleih-Nachsatz der OPAC-Tools.

Hintergrund: Die Trefferausgabe konnte einen Titel ganz ohne Bestandszeile
zeigen — `bht_bestand` wurde nie `False`, und in der Verbundsuche wurde der
Besitznachweis mangels ISIL überhaupt nicht ausgewertet. Darunter stand
trotzdem ein pauschaler Fernleih-Nachsatz. Aus der Lücke plus der Werbung
wurde eine Fernleihbestellung für Bücher im eigenen Regal.

Alle Tests kommen ohne Netz aus: MARC-Sätze werden synthetisch gebaut und
durch denselben Parser geschickt, den der Z39.50-Client verwendet.
"""
import asyncio
import unittest
from unittest.mock import patch

from pymarc import Field, Record, Subfield

from paper_search_mcp.opac import tools
from paper_search_mcp.opac.z3950_client import BHT_ISIL, _parse_marc

# 008 mit 'o' (online) bzw. ' ' (kein besonderer Träger) auf Position 23
F008_ONLINE = "230101s2023    gw      o    000 0 ger d"
F008_PRINT  = "230101s2023    gw           000 0 ger d"


def satz(*, isils=(), online=False, mit_856=None, lizenz=None,
         freie_schlagworte=(), f924=True) -> bytes:
    """Baut einen MARC21-Satz und gibt ihn als Rohdaten zurück."""
    r = Record(force_utf8=True)
    r.add_field(Field(tag="001", data="BV000000001"))
    r.add_field(Field(tag="008", data=F008_ONLINE if online else F008_PRINT))
    r.add_field(Field(tag="245", indicators=[" ", " "],
                      subfields=[Subfield("a", "Kosie /")]))
    if f924:
        for isil in isils:
            r.add_field(Field(tag="924", indicators=[" ", " "],
                              subfields=[Subfield("b", isil)]))
    if mit_856:
        ind2, subfields = mit_856
        r.add_field(Field(tag="856", indicators=["4", ind2],
                          subfields=[Subfield(c, v) for c, v in subfields]))
    if lizenz:
        r.add_field(Field(tag="540", indicators=[" ", " "],
                          subfields=[Subfield("a", lizenz)]))
    for wort in freie_schlagworte:
        r.add_field(Field(tag="653", indicators=[" ", " "],
                          subfields=[Subfield("a", wort)]))
    return r.as_marc()


class TestBestandsauswertung(unittest.TestCase):
    def test_bht_besitz_ist_true(self):
        t = _parse_marc(satz(isils=[BHT_ISIL]), BHT_ISIL)
        self.assertIs(t["bht_bestand"], True)

    def test_fremder_besitz_ist_false(self):
        """Der Zweig, der vorher toter Code war: 924 da, aber nicht die BHT."""
        t = _parse_marc(satz(isils=["DE-11"]), BHT_ISIL)
        self.assertIs(t["bht_bestand"], False)

    def test_ohne_924_bleibt_unbekannt(self):
        """Kein Besitznachweis ist kein Nachweis der Nichtverfügbarkeit."""
        t = _parse_marc(satz(f924=False), BHT_ISIL)
        self.assertIsNone(t["bht_bestand"])

    def test_bht_neben_anderen_haeusern(self):
        t = _parse_marc(satz(isils=["DE-11", BHT_ISIL, "DE-83"]), BHT_ISIL)
        self.assertIs(t["bht_bestand"], True)


class TestVolltextUndTraeger(unittest.TestCase):
    def test_freier_volltext_wird_erkannt(self):
        t = _parse_marc(satz(online=True, mit_856=("0", [
            ("u", "https://repo.example/1"), ("z", "kostenfrei")])), BHT_ISIL)
        self.assertEqual(t["volltext_url"], "https://repo.example/1")
        self.assertTrue(t["volltext_frei"])
        self.assertTrue(t["ist_online"])

    def test_inhaltsverzeichnis_ist_kein_volltext(self):
        t = _parse_marc(satz(mit_856=("2", [
            ("u", "https://d-nb.info/toc.pdf"),
            ("3", "Inhaltsverzeichnis")])), BHT_ISIL)
        self.assertEqual(t["volltext_url"], "")

    def test_lizenzpflichtiger_link_ohne_frei_marker(self):
        t = _parse_marc(satz(online=True, mit_856=("0", [
            ("u", "https://verlag.example/ebook")])), BHT_ISIL)
        self.assertEqual(t["volltext_url"], "https://verlag.example/ebook")
        self.assertFalse(t["volltext_frei"])

    def test_druckwerk_ist_nicht_online(self):
        self.assertFalse(_parse_marc(satz(isils=[BHT_ISIL]), BHT_ISIL)["ist_online"])

    def test_lizenz_und_freie_schlagworte(self):
        t = _parse_marc(satz(lizenz="CC BY 4.0",
                             freie_schlagworte=["Kosie", "Pflege"]), BHT_ISIL)
        self.assertEqual(t["lizenz"], "CC BY 4.0")
        self.assertIn("Kosie", t["schlagwoerter"])


class TestLabelkaskade(unittest.TestCase):
    def label(self, **kwargs):
        return tools._bestandszeile(kwargs)

    def test_jeder_treffer_bekommt_ein_label(self):
        """Auch der unklare Fall — eine fehlende Zeile lädt zum Raten ein."""
        for zustand in ({}, {"bht_bestand": None}, {"bht_bestand": False},
                        {"bht_bestand": True}, {"ist_online": True},
                        {"volltext_frei": True}):
            self.assertTrue(self.label(**zustand).startswith("**Bestand:**"))

    def test_besitz_schlaegt_fernleihe(self):
        self.assertIn("✅", self.label(bht_bestand=True))

    def test_verbundtreffer_verweist_auf_fernleihe(self):
        self.assertIn("Fernleihe", self.label(bht_bestand=False))

    def test_freier_volltext_statt_fernleihe(self):
        zeile = self.label(bht_bestand=False, volltext_frei=True, ist_online=True)
        self.assertIn("Frei zugänglicher Volltext", zeile)
        self.assertNotIn("Fernleihe", zeile)

    def test_lizenzpflichtige_eressource_ist_nicht_fernleihfaehig(self):
        zeile = self.label(bht_bestand=False, ist_online=True)
        self.assertIn("nicht fernleihfähig", zeile)

    def test_unbekannter_bestand_wird_als_ungeklaert_ausgewiesen(self):
        self.assertIn("ungeklärt", self.label(bht_bestand=None))


class TestFernleihkandidat(unittest.TestCase):
    def test_bht_bestand_ist_kein_kandidat(self):
        self.assertFalse(tools.ist_fernleihkandidat({"bht_bestand": True}))

    def test_online_ist_kein_kandidat(self):
        self.assertFalse(tools.ist_fernleihkandidat(
            {"bht_bestand": False, "ist_online": True}))

    def test_gedruckt_und_fremd_ist_kandidat(self):
        self.assertTrue(tools.ist_fernleihkandidat({"bht_bestand": False}))

    def test_unbekannter_bestand_bleibt_kandidat(self):
        self.assertTrue(tools.ist_fernleihkandidat({"bht_bestand": None}))


class FakeMCP:
    """Nimmt die Tool-Funktionen entgegen, ohne FastMCP zu starten."""

    def __init__(self):
        self.tools = {}

    def tool(self, name=None, annotations=None):
        def deco(fn):
            self.tools[name] = fn
            return fn
        return deco


class TestVerbundsuche(unittest.TestCase):
    """kobv_verbund_suche: Besitznachweis trotz fehlendem Suchfilter."""

    def setUp(self):
        self.mcp = FakeMCP()
        tools.register_opac_tools(self.mcp)
        self.suche = self.mcp.tools["kobv_verbund_suche"]

    def rufe(self, treffer):
        """Ruft das Tool mit vorgegebenen Treffern auf, ohne Netz."""
        daten = {"treffer_gesamt": len(treffer), "treffer": treffer}

        async def stub(**kwargs):
            self.aufruf = kwargs
            return daten

        with patch.object(tools, "suche_bht", stub):
            return asyncio.run(self.suche(suchbegriff="Kosie", suchtyp="any",
                                          max_treffer=10))

    def test_bestand_wird_auch_ohne_suchfilter_ausgewertet(self):
        self.rufe([{"titel": "X", "bht_bestand": True}])
        self.assertIsNone(self.aufruf["isil"])
        self.assertEqual(self.aufruf["bestand_isil"], BHT_ISIL)

    def test_fernleih_nachsatz_nur_bei_kandidaten(self):
        text = self.rufe([{"titel": "X", "bht_bestand": False}])
        self.assertIn("Fernleihe", text)

    def test_kein_nachsatz_wenn_alles_im_bestand(self):
        text = self.rufe([{"titel": "X", "bht_bestand": True},
                          {"titel": "Y", "bht_bestand": True}])
        self.assertIn("Keine Fernleihe nötig", text)
        self.assertNotIn("portal.kobv.de", text)

    def test_bht_treffer_zeigt_bestandszeile(self):
        text = self.rufe([{"titel": "X", "bht_bestand": True}])
        self.assertIn("✅", text)


if __name__ == "__main__":
    unittest.main()
