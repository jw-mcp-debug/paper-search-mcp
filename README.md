# BHT – KOBV + Paper Search MCP

A Model Context Protocol (MCP) server for academic literature research at the
Berliner Hochschule für Technik (BHT). It combines **two capabilities in a single
server**:

1. **Library catalog search** of the BHT holdings and the KOBV union catalog via a
   Z39.50 query (ISIL filter `DE-B768`).
2. **Multi-source academic paper search** across open and public databases
   (arXiv, Crossref, OpenAlex, PubMed, DOAJ, and more).

The project is a fork of [openags/paper-search-mcp](https://github.com/openags/paper-search-mcp)
with the OPAC/KOBV tools folded in, so that one connector serves both the catalog
and the paper databases. It is intended to be deployed once (as a remote MCP
connector) and used through Claude with the staged `agentische-recherche` workflow.

![Python](https://img.shields.io/badge/python-3.10+-blue.svg) ![License](https://img.shields.io/badge/license-MIT-blue.svg)

---

## Table of Contents

- [Overview](#overview)
- [Scope: find, don't acquire](#scope-find-dont-acquire)
- [Project Principles](#project-principles)
- [Features](#features)
- [Library Catalog (OPAC / KOBV)](#library-catalog-opac--kobv)
- [Paper Source Strategy](#paper-source-strategy)
- [Platform Capability Matrix](#platform-capability-matrix)
- [Credential & API Key Requirements](#credential--api-key-requirements)
- [Known Upstream Limitations](#known-upstream-limitations)
- [Deployment (Render, remote connector)](#deployment-render-remote-connector)
- [Local Development (stdio)](#local-development-stdio)
- [Contributing](#contributing)
- [License & Attribution](#license--attribution)

---

## Overview

This server provides one MCP endpoint that an LLM client (Claude) can use to run a
complete library-style literature search: first the **BHT/KOBV catalog** for
foundational books, then the **paper databases** for current research. Both tool
groups live on the same server process and are exposed over **streamable-HTTP**, so
the whole thing is added to Claude as a single custom connector.

The intended interaction pattern is the `agentische-recherche` skill: OPAC first
(German foundational literature, BHT holdings), then targeted paper search (current
research), then a synthesis with source links.

## Scope: find, don't acquire

This deployment is a **discovery** service. It locates literature and returns links
to the source — it does **not** acquire full text on the user's behalf.

- No Sci-Hub or other shadow-library paths are used. The optional Sci-Hub fallback
  from the upstream project has been removed/disabled in this fork.
- The download/read tools inherited from upstream are **not part of the BHT
  workflow**; the `agentische-recherche` skill calls only the search tools.
- Full text is reached through the library's legitimate channels: open-access links
  (DOI), the BHT e-resources (EZB/DBIS, Shibboleth/VPN), or interlibrary loan
  (Fernleihe via the KOBV portal).

## Project Principles

- **Free-First**: Public and open sources are the default. Paid or restricted
  sources are not the core direction.
- **Find, not acquire**: The server resolves *where* literature is, not *the file
  itself*. Full-text access stays with the library's licensed routes.
- **Optional API Keys**: Keys are supported only where they improve stability, rate
  limits, or metadata quality. The server is usable without them.
- **Source Transparency**: Different sources have different strengths; the server
  makes those tradeoffs explicit instead of pretending every source supports
  full-text retrieval.

---

## Features

- **Unified, two-domain tooling on one connector**:
  - **Library catalog**: `opac_suche`, `opac_isbn_suche`, `opac_autor_suche`,
    `kobv_verbund_suche` — Z39.50 search of BHT holdings and the KOBV union catalog.
  - **Paper search**: high-level `search_papers` for multi-source, deduplicated
    search, plus per-source `search_*` connectors.
- **BHT holdings filter**: catalog searches are filtered to the BHT stock via
  ISIL `DE-B768` (Bib-1 attribute 1044), with an option to widen to the full KOBV
  union catalog for interlibrary loan.
- **Multi-source paper coverage**: arXiv, PubMed, bioRxiv, medRxiv, IACR ePrint,
  Semantic Scholar, Crossref, OpenAlex, PMC, CORE, Europe PMC, dblp, OpenAIRE,
  CiteSeerX, DOAJ, BASE, Zenodo, HAL, SSRN, Unpaywall (DOI lookup).
- **Standardized output**: papers are returned in a consistent dictionary format.
- **Remote-ready transport**: runs over streamable-HTTP, deployable as a single
  always-on endpoint and added to Claude as one custom connector.
- **Extensible**: new paper platforms via the `academic_platforms` module; the OPAC
  tools live in `paper_search_mcp/opac/`.

## Library Catalog (OPAC / KOBV)

The catalog tools query the KOBV Z39.50 server and parse MARC21 records.

- **Z39.50 host**: `z3950.kobv.de:210`, database `k2`
- **BHT holdings filter**: ISIL `DE-B768` via Bib-1 attribute `1044`
- **Record format**: MARC21 → parsed to title, authors, publisher, year, edition,
  ISBN, extent, language, call number (Signatur), subject headings, PPN

| Tool | Purpose |
|---|---|
| `opac_suche` | General catalog search. Default filtered to BHT holdings (`nur_bht_bestand=true`). `suchtyp`: `subject` (controlled vocabulary, most precise), `any`, `title`, `author`. |
| `opac_autor_suche` | All works by a given author held by the BHT. |
| `opac_isbn_suche` | Availability check by ISBN; checks BHT first, then the union catalog with a Fernleihe note. |
| `kobv_verbund_suche` | Full KOBV union catalog (all Berlin-Brandenburg libraries), no BHT filter — for interlibrary loan. |

> Search tip: for topic searches, `suchtyp="subject"` is markedly more precise than
> `"any"` because it uses the GND controlled vocabulary. Results are not relevance-
> ranked, so scan a larger result set and select rather than taking the first few.

## Paper Source Strategy

The goal is not to depend on one engine, but to combine free and public sources with
clear roles:

- **Open metadata backbone**: Crossref, OpenAlex, Semantic Scholar, dblp, CiteSeerX,
  SSRN, Unpaywall (DOI-centric OA metadata).
- **Discipline-specific sources**: arXiv, PubMed, PubMed Central, Europe PMC, IACR.
- **Open-access full-text sources**: arXiv, PMC, CORE, OpenAIRE, DOAJ, BASE, Zenodo,
  HAL, publisher open-access links.
- **Discovery / DOI recovery**: Google Scholar for finding titles, versions, and DOI
  clues when other public metadata is incomplete.

For topic searches a clean, targeted core (`crossref,openalex,doaj`) is recommended,
extended by discipline (`arxiv` for CS/maths/physics; `pubmed`/`europepmc` for
medicine/life sciences) rather than querying all sources at once.

## Platform Capability Matrix

Reflects verified live-integration results. Columns show the highest capability level
observed under normal conditions.

| Platform | Search | Download | Read | Notes |
|---|---|---|---|---|
| arXiv | ✅ | ✅ | ✅ | Open API; reliable |
| PubMed | ✅ | ❌ | ⚠️ info-only | Open API; reliable |
| bioRxiv | ✅ | ✅ | ✅ | Open API; reliable |
| medRxiv | ✅ | ✅ | ✅ | Open API; reliable |
| Google Scholar | ⚠️ | ❌ | ❌ | Bot-detection active; set `PAPER_SEARCH_MCP_GOOGLE_SCHOLAR_PROXY_URL` |
| IACR | ✅ | ✅ | ✅ | Open API; reliable |
| Semantic Scholar | ✅ | ✅ (OA) | ✅ (OA) | Works without key (rate-limited); key improves limits |
| Crossref | ✅ | ❌ | ⚠️ info-only | Open API; reliable |
| OpenAlex | ✅ | ❌ | ⚠️ info-only | Open API; reliable; provides citation counts |
| PMC | ✅ | ✅ (OA only) | ✅ (OA only) | OA PDFs only |
| CORE | ✅ | ✅ (record-dependent) | ✅ (record-dependent) | Free key recommended |
| Europe PMC | ✅ | ✅ (OA) | ✅ (OA) | OA PDFs only |
| dblp | ✅ | ❌ | ⚠️ info-only | Open API; reliable |
| OpenAIRE | ✅ | ❌ | ❌ | Open API; transient 403 retried |
| CiteSeerX | ⚠️ | ✅ (record-dependent) | ⚠️ | Endpoint intermittently unavailable |
| DOAJ | ✅ | ⚠️ (URL-dependent) | ⚠️ (URL-dependent) | PDF availability varies; free key raises limits |
| BASE | ⚠️ | ✅ (record-dependent) | ✅ (record-dependent) | OAI-PMH requires institutional IP registration |
| Zenodo | ✅ | ✅ (record-dependent) | ✅ (record-dependent) | Open API; reliable |
| HAL | ✅ | ✅ (record-dependent) | ✅ (record-dependent) | Open API; reliable |
| SSRN | ⚠️ | ⚠️ best-effort | ⚠️ best-effort | 403 bot-detection; public PDF only |
| Unpaywall | ✅ (DOI lookup) | ❌ | ❌ | **Requires** `PAPER_SEARCH_MCP_UNPAYWALL_EMAIL` |
| **IEEE Xplore** 🔑 | 🚧 skeleton | 🚧 skeleton | 🚧 skeleton | Requires `PAPER_SEARCH_MCP_IEEE_API_KEY` to activate |
| **ACM DL** 🔑 | 🚧 skeleton | 🚧 skeleton | 🚧 skeleton | Requires `PAPER_SEARCH_MCP_ACM_API_KEY` to activate |

> ✅ = reliable in live tests. ⚠️ = works but subject to upstream instability. ❌ = not supported. 🔑 = key required. 🚧 = skeleton only.
>
> Note on the download/read columns: these reflect upstream capability. In the BHT
> deployment the workflow is search/discovery only — download/read tools are not used
> (see [Scope](#scope-find-dont-acquire)).

---

## Credential & API Key Requirements

All keys are **optional** unless noted. Configure them as environment variables on
the host (e.g. in the Render dashboard) or in a `.env` file for local runs. The OPAC
needs **no** key — the KOBV Z39.50 endpoint is public.

| Environment Variable | Provider | Required? | How to obtain |
|---|---|---|---|
| `PAPER_SEARCH_MCP_UNPAYWALL_EMAIL` | Unpaywall | Recommended (Unpaywall skipped without it) | Any valid email; register at [unpaywall.org](https://unpaywall.org/products/api) |
| `PAPER_SEARCH_MCP_CORE_API_KEY` | CORE | Optional | Free at [core.ac.uk/services/api](https://core.ac.uk/services/api) |
| `PAPER_SEARCH_MCP_SEMANTIC_SCHOLAR_API_KEY` | Semantic Scholar | Optional | Free; improves rate limits |
| `PAPER_SEARCH_MCP_GOOGLE_SCHOLAR_PROXY_URL` | Google Scholar | Optional | Your HTTP/HTTPS proxy URL |
| `PAPER_SEARCH_MCP_DOAJ_API_KEY` | DOAJ | Optional | Free at [doaj.org](https://doaj.org/apply-for-api-key/) |
| `PAPER_SEARCH_MCP_ZENODO_ACCESS_TOKEN` | Zenodo | Optional | Free at [zenodo.org](https://zenodo.org/account/settings/applications/) |
| `PAPER_SEARCH_MCP_IEEE_API_KEY` | IEEE Xplore | Required to activate | Free at [developer.ieee.org](https://developer.ieee.org/) |
| `PAPER_SEARCH_MCP_ACM_API_KEY` | ACM DL | Required to activate | See [libraries.acm.org](https://libraries.acm.org/digital-library/acm-open) |

All variables follow the `PAPER_SEARCH_MCP_<NAME>` prefix scheme. Legacy names without
the prefix are still supported for backward compatibility.

---

## Known Upstream Limitations

Some search failures come from external provider instability, not from bugs in this
project:

| Source | Symptom | Cause | Workaround |
|---|---|---|---|
| Google Scholar | 0 results / empty HTML | Bot-detection (CAPTCHA) | Set `PAPER_SEARCH_MCP_GOOGLE_SCHOLAR_PROXY_URL` |
| Semantic Scholar | 429 responses | Anonymous rate limit | Set `PAPER_SEARCH_MCP_SEMANTIC_SCHOLAR_API_KEY` |
| CORE | 500 / timeout | Unauthenticated rate limiting | Set `PAPER_SEARCH_MCP_CORE_API_KEY` |
| OpenAIRE | Transient 403 | IP-based session limiting | Connector retries with escalating profiles |
| CiteSeerX | 404 / archive redirect | Endpoint intermittently redirects | Returns empty gracefully |
| BASE | 0 results | OAI-PMH needs institutional IP | Register at [base-search.net](https://www.base-search.net/about/en/) |
| SSRN | HTTP 403 | Bot-detection (Cloudflare) | Public PDF only; clear failure message |
| PMC / Europe PMC | PDF ProxyError | Local proxy blocking HTTPS PDF | Not relevant to BHT search-only use |
| Unpaywall | Skipped | email var not set | Set `PAPER_SEARCH_MCP_UNPAYWALL_EMAIL` |

---

## Deployment (Render, remote connector)

This server is deployed as a single always-on web service and added to Claude as one
custom connector.

**1. Fork** this repository to your account (browser-only edits are sufficient for
configuration).

**2. Files the deployment relies on:**

- `paper_search_mcp/opac/` — the OPAC module (`z3950_client.py`, `tools.py`,
  `__init__.py`). `register_opac_tools(mcp)` is called from `server.py` after the
  `FastMCP` instance is created.
- `requirements.txt` — paper-search dependencies plus `pymarc` and `ply` (for the OPAC).
- `setup.sh` — build script: installs `requirements.txt`, installs PyZ3950 from its
  GitHub fork (not on PyPI), and applies the `ccl.py` stub patch required for Python
  3.11+ compatibility (the catalog uses PQF queries, so the CCL parser is stubbed).

**3. Render web service settings:**

| Setting | Value |
|---|---|
| Build Command | `bash setup.sh` |
| Start Command | `python -m paper_search_mcp.server` |
| Health Check Path | *(leave empty)* — `/mcp` returns 406 to plain GETs by design |
| Instance Type | Free (pilot) / paid for always-on |
| Region | Frankfurt (EU) |
| Env | `PAPER_SEARCH_MCP_UNPAYWALL_EMAIL` = institutional email (optional keys as needed) |

The entry point runs over streamable-HTTP when `PORT` is set (Render sets it
automatically), binds to `0.0.0.0`, and disables DNS-rebinding protection so the
service is reachable behind Render's proxy.

**4. Add to Claude** as a custom connector with the URL
`https://<your-service>.onrender.com/mcp` (no trailing slash, no port). After any
redeploy that changes the tool set, remove and re-add the connector so the client
re-fetches the tool list.

> Note: the free tier sleeps after ~15 minutes of inactivity; the first request then
> takes ~1 minute to wake. For a production service, host on always-on infrastructure
> (e.g. a university/RZ VM) with a fixed HTTPS endpoint.

## Local Development (stdio)

For development you can run the server locally over stdio (e.g. with Claude Desktop).

```bash
git clone https://github.com/<your-account>/paper-search-mcp.git
cd paper-search-mcp
bash setup.sh                      # installs deps + PyZ3950 + ccl patch
python -m paper_search_mcp.server  # stdio when PORT is not set
```

Claude Desktop config (stdio):

```json
{
  "mcpServers": {
    "paper-opac-search": {
      "command": "python",
      "args": ["-m", "paper_search_mcp.server"],
      "env": {
        "PAPER_SEARCH_MCP_UNPAYWALL_EMAIL": "your@email.com"
      }
    }
  }
}
```

> The OPAC tools require `pymarc`, `ply`, and PyZ3950 with the `ccl.py` stub —
> `setup.sh` handles all three. A plain `pip install -r requirements.txt` alone is not
> sufficient for the catalog tools.

---

## Contributing

1. Fork the repository.
2. Add new paper platforms in `academic_platforms/`; OPAC logic lives in
   `paper_search_mcp/opac/`.
3. Update tests in `tests/`.
4. Open a pull request.

---

## License & Attribution

This project is licensed under the MIT License. See the `LICENSE` file.

It is a fork of [openags/paper-search-mcp](https://github.com/openags/paper-search-mcp)
(MIT), extended with BHT/KOBV catalog search via Z39.50 and adapted for a single
remote-connector deployment. The optional Sci-Hub workflow from the upstream project
has been removed.
