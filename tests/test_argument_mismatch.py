"""A schema mismatch must answer with something the caller can act on.

Clients cache the tool list. After a release that renames or restructures a
parameter, they keep sending the old shape, and pydantic then reports the
field it is *missing* while the caller is looking at an argument it did pass,
one level down in a wrapper. That answer cost one real session six identical
retries before it abandoned the tool — and the fallback tool it reached for
produced a wrong statement about the library's holdings.
"""
import asyncio
import unittest

from mcp.server.fastmcp.exceptions import ToolError

from paper_search_mcp import server
from paper_search_mcp.server import mcp

VERALTET = {"params": {"suchbegriff": "Gamification", "suchtyp": "subject"}}


class TestArgumentMismatch(unittest.TestCase):
    def test_wrapped_arguments_are_named_as_the_problem(self):
        hinweis = server._argument_mismatch("opac_suche", VERALTET)
        self.assertIn("no parameter named params", hinweis)

    def test_hint_lists_the_parameters_the_tool_does_take(self):
        hinweis = server._argument_mismatch("opac_suche", VERALTET)
        for erwartet in ("suchbegriff", "suchtyp", "max_treffer", "nur_bht_bestand"):
            self.assertIn(erwartet, hinweis)

    def test_hint_names_both_remedies(self):
        """Flat arguments for the model, connector reload for the human."""
        hinweis = server._argument_mismatch("opac_suche", VERALTET)
        self.assertIn("flat", hinweis)
        self.assertIn("connector", hinweis)

    def test_valid_arguments_pass_through(self):
        self.assertIsNone(server._argument_mismatch(
            "opac_suche", {"suchbegriff": "Gamification"}))

    def test_one_matching_argument_leaves_pydantic_in_charge(self):
        """Pydantic's message is the more precise one as soon as anything fits."""
        self.assertIsNone(server._argument_mismatch(
            "opac_suche", {"suchbegriff": "x", "quatsch": 1}))

    def test_empty_arguments_are_not_reported(self):
        self.assertIsNone(server._argument_mismatch("opac_suche", {}))

    def test_non_dict_arguments_are_not_reported(self):
        self.assertIsNone(server._argument_mismatch("opac_suche", "suchbegriff=x"))

    def test_unknown_tool_does_not_raise(self):
        self.assertIsNone(server._argument_mismatch("gibtsnicht", {"a": 1}))


class TestCallToolWiring(unittest.TestCase):
    def test_mismatch_is_raised_before_the_tool_runs(self):
        with self.assertRaises(ToolError) as fehler:
            asyncio.run(mcp._tool_manager.call_tool(
                "opac_suche", VERALTET, context=None))
        self.assertIn("no parameter named params", str(fehler.exception))

    def test_a_valid_call_still_reaches_the_tool(self):
        result = asyncio.run(mcp._tool_manager.call_tool(
            "search_papers", {"query": "x", "sources": "none"},
            context=None, convert_result=True))
        self.assertTrue(result[0].text)

    def test_unknown_tool_keeps_its_own_error(self):
        with self.assertRaises(ToolError) as fehler:
            asyncio.run(mcp._tool_manager.call_tool("gibtsnicht", {"a": 1}, context=None))
        self.assertIn("Unknown tool", str(fehler.exception))


if __name__ == "__main__":
    unittest.main()
