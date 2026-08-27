"""PAPER_SEARCH_MCP_ENABLED_TOOLS restricts which tools are registered.

Every registered tool is serialized into the tool list of *every* request, so
a client that needs seven of them should not pay for fifty-six. Functions that
are not registered must stay awaitable, because search_papers() calls them
internally no matter what is exposed to the client.
"""
import asyncio
import importlib
import inspect
import os
import unittest
from unittest.mock import AsyncMock, patch

from paper_search_mcp import server as server_module

BHT_TOOLS = [
    "opac_suche",
    "opac_autor_suche",
    "opac_isbn_suche",
    "kobv_verbund_suche",
    "search_papers",
    "paper_referenzen",
    "paper_zitiert_von",
]


def _reload_with_allowlist(value):
    with patch.dict(os.environ, {"PAPER_SEARCH_MCP_ENABLED_TOOLS": value}, clear=False):
        return importlib.reload(server_module)


class TestToolAllowlist(unittest.TestCase):
    def tearDown(self):
        # Leave the unfiltered server behind for the rest of the suite.
        _reload_with_allowlist("")

    def test_allowlist_registers_only_the_named_tools(self):
        module = _reload_with_allowlist(",".join(BHT_TOOLS))
        names = sorted(t.name for t in asyncio.run(module.mcp.list_tools()))
        self.assertEqual(names, sorted(BHT_TOOLS))

    def test_unset_variable_registers_everything(self):
        module = _reload_with_allowlist("")
        names = {t.name for t in asyncio.run(module.mcp.list_tools())}
        self.assertGreater(len(names), len(BHT_TOOLS))
        self.assertIn("search_arxiv", names)
        self.assertIn("download_with_fallback", names)

    def test_whitespace_and_empty_entries_are_tolerated(self):
        module = _reload_with_allowlist(" search_papers , ,opac_suche ")
        names = sorted(t.name for t in asyncio.run(module.mcp.list_tools()))
        self.assertEqual(names, ["opac_suche", "search_papers"])

    def test_unregistered_tools_stay_awaitable(self):
        module = _reload_with_allowlist(",".join(BHT_TOOLS))
        self.assertTrue(inspect.iscoroutinefunction(module.search_arxiv))
        self.assertTrue(inspect.iscoroutinefunction(module.search_crossref))

    def test_aggregation_is_unaffected(self):
        module = _reload_with_allowlist(",".join(BHT_TOOLS))
        self.assertEqual(len(module._parse_sources("all")), len(module.ALL_SOURCES))

        with patch.object(module, "search_crossref",
                          AsyncMock(return_value=[{"title": "c", "paper_id": "c-1"}])), \
             patch.object(module, "search_openalex",
                          AsyncMock(return_value=[{"title": "o", "paper_id": "o-1"}])):
            result = asyncio.run(module.search_papers(
                "anything", max_results_per_source=1, sources="crossref,openalex"))

        self.assertEqual(result["source_results"], {"crossref": 1, "openalex": 1})
        self.assertEqual(result["errors"], {})
        self.assertEqual(result["total"], 2)

    def test_unknown_entry_is_reported(self):
        with self.assertLogs("paper_search_mcp.server", level="WARNING") as logs:
            _reload_with_allowlist("search_papers,opac_such")

        message = "\n".join(logs.output)
        self.assertIn("opac_such", message)
        self.assertIn("opac_suche", message)  # close-match suggestion

    def test_known_entries_are_not_reported(self):
        with patch.object(server_module.logger, "warning") as warn:
            _reload_with_allowlist(",".join(BHT_TOOLS))
        allowlist_warnings = [c for c in warn.call_args_list if "ENABLED_TOOLS" in str(c)]
        self.assertEqual(allowlist_warnings, [])


if __name__ == "__main__":
    unittest.main()
