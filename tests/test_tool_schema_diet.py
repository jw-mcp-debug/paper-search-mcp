"""The tool list is serialized into every request, so it must carry no ballast.

Three sources of ballast are removed centrally in server.py: the generated
`outputSchema`, the `title` keyword pydantic derives from every field name, and
the docstring indentation FastMCP copies verbatim into the description.
"""
import asyncio
import json
import unittest

from paper_search_mcp import server
from paper_search_mcp.server import mcp


def _tools():
    return asyncio.run(mcp.list_tools())


class TestToolSchemaDiet(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tools = _tools()

    def test_no_tool_carries_an_output_schema(self):
        with_schema = [t.name for t in self.tools if getattr(t, "outputSchema", None)]
        self.assertEqual(with_schema, [])

    def test_descriptions_are_dedented(self):
        for tool in self.tools:
            for line in (tool.description or "").splitlines():
                if line.strip().startswith(("Args:", "Returns:")):
                    self.assertFalse(
                        line.startswith(" "),
                        f"{tool.name}: docstring indentation kept in description",
                    )

    def test_generated_title_keywords_are_gone(self):
        def title_keywords(schema, inside_properties=False):
            found = []
            if isinstance(schema, dict):
                for key, value in schema.items():
                    if key == "title" and not inside_properties:
                        found.append(value)
                    found += title_keywords(value, inside_properties=(key == "properties"))
            elif isinstance(schema, list):
                for item in schema:
                    found += title_keywords(item)
            return found

        for tool in self.tools:
            self.assertEqual(
                title_keywords(tool.inputSchema), [],
                f"{tool.name}: {json.dumps(tool.inputSchema, ensure_ascii=False)}",
            )

    def test_no_retrieval_tools_are_registered(self):
        """Retrieval is not this server's job, and it is the largest block.

        The agent's system prompt forbids download/read tools, SKILL.md lists
        them under "do not use", and they were 42% of the tool list — paid for
        in every request. They are gone; this keeps them gone.
        """
        retrieval = [t.name for t in self.tools
                     if t.name.startswith(("download_", "read_"))]
        self.assertEqual(retrieval, [])

    def test_opac_tools_take_flat_arguments(self):
        for name in ("opac_suche", "opac_isbn_suche", "opac_autor_suche"):
            tool = next(t for t in self.tools if t.name == name)
            schema = json.dumps(tool.inputSchema)
            self.assertNotIn("$defs", schema, f"{name} still wraps its arguments")
            self.assertNotIn("$ref", schema, f"{name} still wraps its arguments")
            self.assertNotIn("params", tool.inputSchema["properties"])

    def test_opac_argument_names_are_unchanged(self):
        expected = {
            "opac_suche": {"suchbegriff", "suchtyp", "max_treffer", "nur_bht_bestand"},
            "opac_isbn_suche": {"isbn"},
            "opac_autor_suche": {"autor", "max_treffer", "nur_bht_bestand"},
        }
        for name, arguments in expected.items():
            tool = next(t for t in self.tools if t.name == name)
            self.assertEqual(set(tool.inputSchema["properties"]), arguments)
            self.assertIn("suchbegriff" if name == "opac_suche" else
                          "isbn" if name == "opac_isbn_suche" else "autor",
                          tool.inputSchema["required"])

    def test_tool_results_are_still_delivered(self):
        result = asyncio.run(mcp._tool_manager.call_tool(
            "search_papers", {"query": "x", "sources": "none"}, context=None, convert_result=True))
        self.assertIsInstance(result, list)  # content blocks only, no structured copy
        self.assertTrue(result[0].text)

    def test_strip_titles_keeps_other_keywords(self):
        schema = {
            "title": "Args",
            "properties": {
                "title": {"title": "Title", "type": "string", "description": "keep me"},
                "n": {"title": "N", "default": 3, "type": "integer"},
            },
            "required": ["title"],
        }
        server._strip_titles(schema)
        self.assertEqual(schema, {
            "properties": {
                "title": {"type": "string", "description": "keep me"},
                "n": {"default": 3, "type": "integer"},
            },
            "required": ["title"],
        })


if __name__ == "__main__":
    unittest.main()
