#!/usr/bin/env python3
"""Compare two running paper-search-mcp deployments over MCP.

Points an MCP client at two endpoints — typically one Render service per branch
— and reports what a client actually pays for and receives: the size of the tool
list, and the size and content of an identical search on both sides.

    python scripts/compare_deployments.py \
        https://paper-search-mcp-main.onrender.com/mcp \
        https://paper-search-mcp-v050.onrender.com/mcp

The free Render tier sleeps after ~15 minutes; the first call to a sleeping
service takes about a minute, which is why the timeouts below are generous.
"""
from __future__ import annotations

import argparse
import asyncio
import json
from typing import Any, Dict

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

# Calibrated against a real LibreChat session: 51,207 characters of tool list
# were billed as 14,956 tokens, i.e. ~3.42 characters per token including client
# framing. 3.5 is the conservative rounding of that.
CHARS_PER_TOKEN = 3.5

DEFAULT_QUERY = "cross-laminated timber fire resistance"
DEFAULT_SOURCES = "crossref,arxiv"


def tokens(text: str) -> int:
    return round(len(text) / CHARS_PER_TOKEN)


async def inspect_deployment(url: str, query: str, sources: str, max_results: int) -> Dict[str, Any]:
    async with streamablehttp_client(url, timeout=180, sse_read_timeout=600) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            listed = await session.list_tools()
            serialized = {
                tool.name: json.dumps(tool.model_dump(exclude_none=True), ensure_ascii=False)
                for tool in listed.tools
            }

            result = await session.call_tool(
                "search_papers",
                {"query": query, "sources": sources, "max_results_per_source": max_results},
            )

    text = "".join(getattr(block, "text", "") for block in result.content)
    structured = getattr(result, "structuredContent", None)

    try:
        payload = json.loads(text)
        papers = payload.get("papers", [])
    except (ValueError, AttributeError):
        payload, papers = {}, []

    return {
        "tools": len(serialized),
        "tool_list_token": sum(tokens(p) for p in serialized.values()),
        "tool_names": sorted(serialized),
        "with_output_schema": sum(1 for t in listed.tools if getattr(t, "outputSchema", None)),
        "response_token": tokens(text),
        "structured_copy_token": tokens(json.dumps(structured, ensure_ascii=False)) if structured else 0,
        "source_results": payload.get("source_results", {}),
        "errors": payload.get("errors", {}),
        "total": payload.get("total", len(papers)),
        "mit_abstract": sum(1 for p in papers if p.get("abstract")),
        "mit_zitationen": sum(1 for p in papers if p.get("citations")),
        "epoch_daten": sum(1 for p in papers if str(p.get("published_date", "")).startswith("1970")),
        "jats_reste": sum(1 for p in papers if "<jats:" in (p.get("abstract") or "")),
        "dois": sorted(p.get("doi", "") for p in papers if p.get("doi")),
        "titles": sorted((p.get("title") or "")[:60] for p in papers),
    }


def report(left_url: str, left: Dict[str, Any], right_url: str, right: Dict[str, Any]) -> None:
    print(f"\nA: {left_url}\nB: {right_url}\n")
    rows = [
        ("Tools", "tools"),
        ("Toolliste (Token)", "tool_list_token"),
        ("davon mit outputSchema", "with_output_schema"),
        ("Antwort (Token)", "response_token"),
        ("structuredContent (Token)", "structured_copy_token"),
        ("Treffer", "total"),
        ("mit Abstract", "mit_abstract"),
        ("mit Zitationen", "mit_zitationen"),
        ("Datum 1970", "epoch_daten"),
        ("JATS-Reste", "jats_reste"),
    ]
    print(f"{'':28} {'A':>12} {'B':>12}")
    for label, key in rows:
        print(f"{label:28} {str(left[key]):>12} {str(right[key]):>12}")

    print(f"\n{'Quellen A':28} {left['source_results']}  errors {list(left['errors'])}")
    print(f"{'Quellen B':28} {right['source_results']}  errors {list(right['errors'])}")

    only_a = sorted(set(left["dois"]) - set(right["dois"]))
    only_b = sorted(set(right["dois"]) - set(left["dois"]))
    print(f"\nDOIs nur in A: {only_a or '–'}")
    print(f"DOIs nur in B: {only_b or '–'}")

    only_tools_a = sorted(set(left["tool_names"]) - set(right["tool_names"]))
    only_tools_b = sorted(set(right["tool_names"]) - set(left["tool_names"]))
    if only_tools_a or only_tools_b:
        print(f"\nTools nur in A: {only_tools_a or '–'}")
        print(f"Tools nur in B: {only_tools_b or '–'}")


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("url_a", help="MCP endpoint of the first deployment, including /mcp")
    parser.add_argument("url_b", help="MCP endpoint of the second deployment, including /mcp")
    parser.add_argument("-q", "--query", default=DEFAULT_QUERY)
    parser.add_argument("-s", "--sources", default=DEFAULT_SOURCES)
    parser.add_argument("-n", "--max-results", type=int, default=5)
    parser.add_argument("--json", action="store_true", help="print the raw measurements instead of a table")
    args = parser.parse_args()

    left = await inspect_deployment(args.url_a, args.query, args.sources, args.max_results)
    right = await inspect_deployment(args.url_b, args.query, args.sources, args.max_results)

    if args.json:
        print(json.dumps({args.url_a: left, args.url_b: right}, ensure_ascii=False, indent=2))
    else:
        report(args.url_a, left, args.url_b, right)


if __name__ == "__main__":
    asyncio.run(main())
