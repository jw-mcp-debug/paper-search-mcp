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

Release history and breaking changes are documented in [`CHANGELOG.md`](CHANGELOG.md).

---

## Table of Contents

- [Overview](#overview)
- [Scope: legal sources only](#scope-legal-sources-only)
- [Project Principles](#project-principles)
- [Features](#features)
- [Library Catalog (OPAC / KOBV)](#library-catalog-opac--kobv)
- [Paper Source Strategy](#paper-source-strategy)
- [Citation Chaining (Snowballing)](#citation-chaining-snowballing)
- [Journal Metrics](#journal-metrics)
- [Platform Capability Matrix](#platform-capability-matrix)
- [Credential & API Key Requirements](#credential--api-key-requirements)
- [Known Upstream Limitations](#known-upstream-limitations)
- [Deployment (Render, remote connector)](#deployment-render-remote-connector)
- [Container Image (GHCR / Kubernetes)](#container-image-ghcr--kubernetes)
- [Local Development (stdio)](#local-development-stdio)
- [Version Bump & Release](#version-bump--release)
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

## Scope: legal sources only

This is primarily a **discovery** service: it locates literature and returns links
to the source. Where a full text is legally and freely available, the download tools
can retrieve it.

- **No shadow libraries.** Sci-Hub support has been removed entirely — the tool, the
  fallback path, and the hard-coded mirror URL (see `CHANGELOG.md`, 0.2.0).
- **No circumvention of licences or paywalls.** Downloads are limited to open-access
  material and publisher open-access links.
- **Licensed full text stays with the library.** It is reached through the BHT
  e-resources (EZB/DBIS, Shibboleth/VPN) or interlibrary loan (Fernleihe via the
  KOBV portal), not through this service.

## Project Principles

- **Free-First**: Public and open sources are the default. Paid or restricted
  sources are not the core direction.
- **Legal sources only**: The server resolves *where* literature is and can fetch
  it where it is legally free. Access to licensed material stays with the
  library's own routes.
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
    - **Citation chaining**: `paper_referenzen` (backward), `paper_zitiert_von`
    (forward), `paper_verwandte` (sideways) — snowballing over OpenAlex metadata.
    - **Journal metrics**: `zeitschrift_profil` — publisher, access route and
    OpenAlex citation statistics for a journal. Deliberately not the Clarivate
    Journal Impact Factor; see [Journal Metrics](#journal-metrics).
- **BHT holdings filter**: catalog searches are filtered to the BHT stock via
  ISIL `DE-B768` (Bib-1 attribute 1044), with an option to widen to the full KOBV
  union catalog for interlibrary loan.
- **Multi-source paper coverage**: arXiv, PubMed, bioRxiv, medRxiv, IACR ePrint,
  Semantic Scholar, Crossref, OpenAlex, PMC, CORE, Europe PMC, dblp, OpenAIRE,
  DOAJ, BASE, Zenodo, HAL, Unpaywall (DOI lookup).
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

- **Open metadata backbone**: Crossref, OpenAlex, Semantic Scholar, dblp,
  Unpaywall (DOI-centric OA metadata).
- **Discipline-specific sources**: arXiv, PubMed, PubMed Central, Europe PMC, IACR.
- **Open-access full-text sources**: arXiv, PMC, CORE, OpenAIRE, DOAJ, BASE, Zenodo,
  HAL, publisher open-access links.

For topic searches a clean, targeted core (`crossref,openalex,doaj`) is recommended,
extended by discipline (`arxiv` for CS/maths/physics; `pubmed`/`europepmc` for
medicine/life sciences) rather than querying all sources at once.

## Citation Chaining (Snowballing)

Beyond keyword search, the connector can follow the citation graph from a known
paper. This is the snowballing method: from one relevant paper, move backward to
the works it builds on and forward to the works that build on it. All three tools
read structured OpenAlex metadata — no full text is fetched and no reference lists
are parsed from PDFs.

| Tool | Direction | Purpose |
|---|---|---|
| `paper_referenzen` | backward | Works the paper cites (`referenced_works`), hydrated with metadata and sorted by citation count. Leads to the foundational literature. |
| `paper_zitiert_von` | forward | Works that cite the paper (`cites:` filter), sorted by citation count. `ab_jahr` restricts to recent work. Leads to the current state of research. |
| `paper_verwandte` | sideways | OpenAlex `related_works`. **Unreliable — not recommended** (see note). |

All three accept a DOI or an OpenAlex work ID (`W…`), including full URLs of either
form. Abstracts are opt-in via `mit_abstract` (default off), since they enlarge the
response; set it on for term harvesting (pearl growing).

> **Reliability note.** `paper_verwandte` relies on OpenAlex `related_works`, which is
> algorithmically derived and can return topically unrelated results when a record's
> leading concept is an ambiguous token. Prefer `paper_referenzen` and
> `paper_zitiert_von` for snowballing. Rule of thumb: the backward step from a
> *review* surfaces methodology references, while the forward step surfaces the
> substantive follow-on work — for subject literature, forward is usually richer.

> **Credits.** Citation tools use the OpenAlex key (see
> [Credential & API Key Requirements](#credential--api-key-requirements)).
> `paper_referenzen` costs two requests per call, the others one to two. Without a
> key, OpenAlex allows ~100 credits/day and then returns HTTP 409.

## Journal Metrics

`zeitschrift_profil(kennung)` returns the profile of a publishing journal: publisher,
open-access status, DOAJ listing, number of indexed works, h-index, and the mean
citations of the works of the last two years. It accepts an ISSN (`0005-1098`), an
OpenAlex source ID (`S51360982`), a journal name, or the DOI of an article — the
first three resolve unambiguously, a name search is reported as
`zuordnung: "unscharf"` and should be confirmed against the ISSN.

Search results from OpenAlex now also carry the journal in `extra`: `journal`,
`quelle_id`, `issn_l`, `quelle_typ` (journal / repository / conference) and, where
they apply, `zeitschrift_oa` and `in_doaj`. `quelle_typ` is useful on its own — it
separates a journal article from a repository copy without involving any metric at
all. `search_openalex(mit_kennzahlen=True)` adds `zit_schnitt_2j` and
`zeitschrift_h_index` to each result; it is off by default and costs one extra
request per 50 distinct journals.

> **This is not the Journal Impact Factor.** The JIF is Clarivate's, is delivered
> only through the Journal Citation Reports, has no free API, and the BHT licenses
> neither Web of Science nor JCR. "Impact Factor" is also a Clarivate trademark and
> must not be used as a label for a value computed elsewhere. What this server
> returns is OpenAlex's `2yr_mean_citedness` — the same concept on a different data
> basis, in the same order of magnitude, but not the same number. It is named
> `zit_schnitt_2j` throughout, and the term "Impact Factor" appears nowhere in the
> code, the docstrings or the skill output.

> **What the number can and cannot carry.** It describes the journal, not the
> article. Citation distributions within a journal are strongly skewed and most
> articles fall well below the mean, so the value does not support a judgement about
> an individual paper. Sorting result lists by it is deliberately not implemented —
> that is precisely the use [DORA](https://sfdora.org/) and CoARA address.

> **Credits.** `/sources` costs the same as `/works`: one credit per request
> regardless of how many IDs a batch carries, so 50 journals cost one credit.
> Journals are cached for the lifetime of the process.

## Platform Capability Matrix

Reflects verified live-integration results. Columns show the highest capability level
observed under normal conditions.

| Platform | Search | Download | Read | Notes |
|---|---|---|---|---|
| arXiv | ✅ | ✅ | ✅ | Open API; reliable |
| PubMed | ✅ | ❌ | ⚠️ info-only | Open API; reliable |
| bioRxiv | ✅ | ✅ | ✅ | Open API; reliable |
| medRxiv | ✅ | ✅ | ✅ | Open API; reliable |
| IACR | ✅ | ✅ | ✅ | Open API; reliable |
| Semantic Scholar | ✅ | ✅ (OA) | ✅ (OA) | Works without key (rate-limited); key improves limits |
| Crossref | ✅ | ❌ | ⚠️ info-only | Open API; reliable |
| OpenAlex | ✅ | ❌ | ⚠️ info-only | Open API; reliable; provides citation counts and backs the citation-chaining tools |
| PMC | ✅ | ✅ (OA only) | ✅ (OA only) | OA PDFs only |
| CORE | ✅ | ✅ (record-dependent) | ✅ (record-dependent) | Free key recommended |
| Europe PMC | ✅ | ✅ (OA) | ✅ (OA) | OA PDFs only |
| dblp | ✅ | ❌ | ⚠️ info-only | Open API; reliable |
| OpenAIRE | ✅ | ❌ | ❌ | Open API; transient 403 retried |
| DOAJ | ✅ | ⚠️ (URL-dependent) | ⚠️ (URL-dependent) | PDF availability varies; free key raises limits |
| BASE | ⚠️ | ✅ (record-dependent) | ✅ (record-dependent) | OAI-PMH requires institutional IP registration |
| Zenodo | ✅ | ✅ (record-dependent) | ✅ (record-dependent) | Open API; reliable |
| HAL | ✅ | ✅ (record-dependent) | ✅ (record-dependent) | Open API; reliable |
| Unpaywall | ✅ (DOI lookup) | ❌ | ❌ | **Requires** `PAPER_SEARCH_MCP_UNPAYWALL_EMAIL` |
| **IEEE Xplore** 🔑 | 🚧 skeleton | 🚧 skeleton | 🚧 skeleton | Requires `PAPER_SEARCH_MCP_IEEE_API_KEY` to activate |
| **ACM DL** 🔑 | 🚧 skeleton | 🚧 skeleton | 🚧 skeleton | Requires `PAPER_SEARCH_MCP_ACM_API_KEY` to activate |

> ✅ = reliable in live tests. ⚠️ = works but subject to upstream instability. ❌ = not supported. 🔑 = key required. 🚧 = skeleton only.
>
> Note on the download/read columns: these reflect upstream capability. Downloads are
> restricted to legally free material (see [Scope](#scope-legal-sources-only)); the
> `agentische-recherche` workflow itself only calls the search tools.

---

## Credential & API Key Requirements

All keys are **optional** unless noted. Configure them as environment variables on
the host (e.g. in the Render dashboard) or in a `.env` file for local runs. The OPAC
needs **no** key — the KOBV Z39.50 endpoint is public.

| Environment Variable | Provider | Required? | How to obtain |
|---|---|---|---|
| `PAPER_SEARCH_MCP_UNPAYWALL_EMAIL` | Unpaywall | Recommended (Unpaywall skipped without it) | Any valid email; register at [unpaywall.org](https://unpaywall.org/products/api) |
| `PAPER_SEARCH_MCP_OPENALEX_API_KEY` | OpenAlex | **Effectively required** (see note) | Free at [openalex.org](https://openalex.org/) |
| `PAPER_SEARCH_MCP_CORE_API_KEY` | CORE | Optional | Free at [core.ac.uk/services/api](https://core.ac.uk/services/api) |
| `PAPER_SEARCH_MCP_SEMANTIC_SCHOLAR_API_KEY` | Semantic Scholar | **Recommended** — part of the default source set in `SKILL.md` | Free; the anonymous pool is shared and rate limited within a few requests |
| `PAPER_SEARCH_MCP_DOAJ_API_KEY` | DOAJ | Optional | Free at [doaj.org](https://doaj.org/apply-for-api-key/) |
| `PAPER_SEARCH_MCP_ZENODO_ACCESS_TOKEN` | Zenodo | Optional | Free at [zenodo.org](https://zenodo.org/account/settings/applications/) |
| `PAPER_SEARCH_MCP_IEEE_API_KEY` | IEEE Xplore | Required to activate | Free at [developer.ieee.org](https://developer.ieee.org/) |
| `PAPER_SEARCH_MCP_ACM_API_KEY` | ACM DL | Required to activate | See [libraries.acm.org](https://libraries.acm.org/digital-library/acm-open) |

All variables follow the `PAPER_SEARCH_MCP_<NAME>` prefix scheme. Legacy names without
the prefix are still supported for backward compatibility.

### Limiting the exposed tools

`PAPER_SEARCH_MCP_ENABLED_TOOLS` takes a comma-separated list of tool names and
registers only those. Empty or unset registers all of them, so a deployment
without the variable is unaffected.

This is a token measure, not a feature switch. The tool list is part of **every**
request a client sends, whether it does research in that turn or not. The full set
of 56 tools costs about 14,600 tokens per request; the seven the BHT research skill
actually calls cost about 2,900:

```
PAPER_SEARCH_MCP_ENABLED_TOOLS=opac_suche,opac_autor_suche,opac_isbn_suche,kobv_verbund_suche,search_papers,paper_referenzen,paper_zitiert_von,zeitschrift_profil
```

Search coverage is untouched: `search_papers` keeps querying every source in
`ALL_SOURCES`, because the per-source functions stay callable inside the server
even when they are not exposed as tools. A name that matches no tool is reported
as a warning at startup, with a suggestion, so a typo cannot drop a tool silently.

> **After changing the list, remove the connector in the client and add it again.**
> A reconnect is not enough — clients cache the tool list.

> **OpenAlex:** since 2026-02-13 the OpenAlex API requires a key. Without one, a
> deployment gets roughly ten searches per day and then receives HTTP 409, which
> surfaces as empty result lists. The former "polite pool" (mailto parameter) no
> longer applies.

---

## Known Upstream Limitations

Some search failures come from external provider instability, not from bugs in this
project:

| Source | Symptom | Cause | Workaround |
|---|---|---|---|
| OpenAlex | Empty results after ~10 searches | Credit limit without API key (HTTP 409) | Set `PAPER_SEARCH_MCP_OPENALEX_API_KEY` |
| Semantic Scholar | 429 responses | Anonymous rate limit | Set `PAPER_SEARCH_MCP_SEMANTIC_SCHOLAR_API_KEY` |
| CORE | 500 / timeout | Unauthenticated rate limiting | Set `PAPER_SEARCH_MCP_CORE_API_KEY` |
| OpenAIRE | Transient 403 | IP-based session limiting | Connector retries with escalating profiles |
| BASE | 0 results | OAI-PMH needs institutional IP | Register at [base-search.net](https://www.base-search.net/about/en/) |
| PMC / Europe PMC | PDF ProxyError | Local proxy blocking HTTPS PDF | Not relevant to BHT search-only use |
| Unpaywall | Skipped | email var not set | Set `PAPER_SEARCH_MCP_UNPAYWALL_EMAIL` |


> **OpenAIRE deduplication artefacts:** OpenAIRE merges records during its own
> deduplication and occasionally fuses two distinct works into one. The result is
> a record whose DOI, URL and author list belong to different papers — for example
> `doi_dedup___::c2f9…` carrying an ETH dissertation DOI, an MDPI article URL and
> authors matching neither. **OpenAIRE DOIs should be verified against a second
> source before they are cited.** This happens in OpenAIRE's data, not in this
> server, so there is nothing to fix on our side.

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

### Comparing two branches on Render

`render.yaml` is a Blueprint that defines two web services, one tracking `main`
and one tracking a release candidate branch, so a change can be measured against
the current deployment under identical conditions. Create it from the Render
dashboard (**Blueprints → New Blueprint Instance**) and point it at this
repository; the API keys are declared with `sync: false`, so Render asks for them
in the dashboard and they never live in the repository.

With both services up, `scripts/compare_deployments.py` talks to them over MCP
and reports what a client actually pays for and gets back — tool-list size,
response size, and whether the results differ:

```bash
python scripts/compare_deployments.py \
    https://paper-search-mcp-main.onrender.com/mcp \
    https://paper-search-mcp-candidate.onrender.com/mcp
```

It prints tool count and tool-list tokens, the response size (including the
`structuredContent` copy, if the deployment still sends one), per-source hit
counts and errors, and which DOIs only one side returned. `-q`, `-s` and `-n`
change the query, the sources and the results per source. The first call against
a sleeping free-tier service takes about a minute.

Delete the candidate service when the comparison is done.

## Container Image (GHCR / Kubernetes)

GitHub Actions publishes the Docker image to GitHub Container Registry:

```text
ghcr.io/jw-mcp-debug/paper-search-mcp
```

The `main` branch produces `main` and `sha-<commit>` tags. Release tags such as
`v0.2.0` additionally produce immutable version tags such as `0.2.0` and `0.2`.
The workflow also supports manual dispatch, which can be run against an existing
release tag after workflow changes. Use the full version tag in cluster manifests:

```yaml
image: ghcr.io/jw-mcp-debug/paper-search-mcp:0.2.0
```

The container defaults to streamable HTTP on port `8000` and includes the OPAC
runtime dependencies installed by `setup.sh`, including the PyZ3950 compatibility
patch. Configure the same `PAPER_SEARCH_MCP_*` environment variables documented
above in the Kubernetes `Deployment`.

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

## Version Bump & Release

The product version is defined in `pyproject.toml` under `[project].version`.
Release publishing is triggered by pushing a Git tag that matches `v*.*.*`; the
GitHub workflow builds the package and uploads the distributions to a GitHub
Release for that tag.

Minimal release procedure:

```bash
# 1. Choose the new version, for example 0.1.5

# 2. Edit pyproject.toml:
# version = "0.1.5"

# 3. Refresh uv.lock so its paper-search-mcp package entry matches
uv lock

# 4. Commit the version bump
git add pyproject.toml uv.lock README.md
git commit -m "Bump version to 0.1.5"

# 5. Create and push the release tag
git tag v0.1.5
git push origin main
git push origin v0.1.5
```

If the release branch is not `main`, replace `main` with the active release
branch. Do not push the tag until the version commit has been pushed, because the
tag is what starts the publish workflow.

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

Journal and work metadata comes from [OpenAlex](https://openalex.org/), whose data is
released into the public domain under CC0. `zit_schnitt_2j` is OpenAlex's
`2yr_mean_citedness`. "Impact Factor" and "Journal Citation Reports" are trademarks
of Clarivate; neither product is used, reproduced or approximated here under those
names.
