"""Jedes Tool trägt Annotationen; nur Schreibendes ist nicht read-only.

Nach upstream #86/#120 (Peter Lemenkov): Claude führt read-only-Tools getrennt
und kann sie ohne Rückfrage freigeben. Die Katalog-Tools setzen eigene
Annotationen samt Titel; die bleiben erhalten.
"""
import asyncio
import unittest

from paper_search_mcp.server import mcp


class TestToolAnnotations(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tools = asyncio.run(mcp.list_tools())

    def test_jedes_lesende_tool_ist_read_only_und_offen(self):
        for tool in self.tools:
            with self.subTest(tool=tool.name):
                self.assertIsNotNone(tool.annotations)
                schreibt = tool.name.startswith(("download_", "read_"))
                self.assertEqual(tool.annotations.readOnlyHint, not schreibt)
                self.assertFalse(tool.annotations.destructiveHint)
                self.assertTrue(tool.annotations.openWorldHint)

    def test_katalog_behaelt_eigene_annotationen(self):
        opac = next(t for t in self.tools if t.name == "opac_suche")
        self.assertEqual(opac.annotations.title, "BHT OPAC Suche (Z39.50)")
        self.assertTrue(opac.annotations.idempotentHint)


if __name__ == "__main__":
    unittest.main()
