# Changelog

All notable changes to this fork are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

> **Note on versioning:** This repository is an independent fork of
> [openags/paper-search-mcp](https://github.com/openags/paper-search-mcp) (MIT),
> extended for the Campusbibliothek der Berliner Hochschule für Technik (BHT).
> Version numbers are maintained independently of upstream and do not correspond
> to upstream releases. The last common upstream base is 0.1.4.
>
> The `0.x` series signals that the tool interface is **not yet stable**: tool
> names, parameters, and result formats may still change between minor versions.

---
## [Unreleased]

### Changed

- **Tool schemas are trimmed of everything that carries no information.** The
  tool list is part of every request, so its cost is paid in every turn of every
  chat. Three sources of ballast are gone: the generated `outputSchema` (an
  informationless `{"result": ...}` wrapper for most tools, 2,598 tokens across
  all 56), the `title` keyword pydantic derives from every field name
  (`max_treffer` → `"title": "Max Treffer"`, 191 occurrences), and the docstring
  indentation FastMCP copied verbatim into every description. Full tool list:
  14,629 → 9,564 tokens; the seven tools of the BHT research skill: 2,926 →
  2,032.
- **The three OPAC tools take flat arguments** (`opac_suche(suchbegriff=…,
  suchtyp=…)`) instead of a wrapped `params` object, matching
  `kobv_verbund_suche`. Argument names, defaults and validation limits are
  unchanged; the wrapper only added a `$defs`/`$ref` indirection and a nesting
  level to the schema. **Callers must pass the arguments flat.**
- Dropping the output schema also stops the server from sending every result
  twice, once as text and once as `structuredContent`. Clients read the text;
  LibreChat discards the structured copy entirely.
- The `ab_jahr` guidance for `paper_zitiert_von` moved from the tool docstring
  into `SKILL.md`, where it costs tokens only in research sessions. `SKILL.md`
  now documents the citation-chaining tools.
- **`SKILL.md` prescribes source sets instead of one fixed default.** The axis is
  a base set plus a subject-specific addition, because the sources differ mainly
  in metadata quality, not in subject coverage: `openalex,semantic,crossref` as
  the base, `openaire` for civil/environmental/mechanical engineering,
  `europepmc` instead of `pubmed`+`pmc` for life sciences, `arxiv`+`dblp` for
  computer science. The previous default `crossref,openalex,doaj` put Crossref —
  75 % abstract coverage, 0 % for Elsevier and ACS — in a set without a reliable
  abstract source. `SKILL.md` and the README now also warn that OpenAIRE DOIs
  need verification before they are cited (see below).
- The Semantic Scholar API key is documented as recommended rather than optional:
  it is part of the default source set, and the anonymous pool is rate limited
  within a few requests.

### Fixed

- **dblp: outages are no longer reported as zero results.** dblp throttles per
  client IP with HTTP 429 and a `Retry-After` header, then with 503, and finally
  by dropping connections. The retry loop only handled 5xx, so a 429 fell
  straight through to the HTML fallback — which queried the same throttled host
  with the same session, swallowed its own failure and returned an empty list.
  From the outside an outage was indistinguishable from "no hits". `search()`
  now retries 429 honouring `Retry-After`, paces requests at one per 1.5s, and
  raises `DBLPUnavailable` for transport errors, error statuses, non-XML content
  types and unparseable bodies. The HTML fallback is only used when the API
  itself answered with a parseable but empty result.
- **HAL, Zenodo and SSRN: results no longer fail to serialize.** All three
  passed `published_date` as a string where `Paper` expects a `datetime`, so
  `to_dict()` raised `AttributeError` for every result and both sources
  reported zero hits. SSRN additionally passed a comma-joined author string
  where a list is expected. (Adapted from upstream PR #62, extended to SSRN.)
- **arXiv: soft rate limiting is detected.** arXiv answers a rate limit with
  HTTP 200 and a body of `Rate exceeded.`, which the status-code-only retry
  loop treated as an empty feed. It is now retried, raises when it persists,
  and requests are paced to the one-per-three-seconds the arXiv terms of use
  ask for. (Rate-limit handling from upstream PR #81.)
- **CrossRef: sub-component types are skipped.** Peer-review material and
  figures are registered under their own DOI and arrived as results without
  citable content. (Search-side part of upstream PR #93.)
- Replaced a bare `except:` in the IACR connector. (Upstream commit 48005b3.)

### Added

- **`PAPER_SEARCH_MCP_ENABLED_TOOLS` restricts which tools are registered.**
  The tool list is serialized into every request a client sends, so all 56 tools
  cost roughly 14,600 tokens per turn even in a chat that does no research at
  all. The seven tools the BHT research skill calls cost about 2,900. Empty or
  unset registers everything, so existing deployments are unaffected. Search
  coverage is untouched — `search_papers` keeps querying every source, since the
  per-source functions stay callable inside the server when they are not
  exposed. Entries that match no tool are logged at startup with a suggestion.
- **Per-source timeout in `search_papers`.** A single stalled provider kept the
  whole aggregated search pending until the client gave up, discarding the
  results of every other source. Each source now runs under a 45s cap and a
  timeout is reported like any other per-source error. (Adapted from upstream
  PR #55.)
- Packaging entrypoint release checks: a `dev` extra, a metadata test for both
  console scripts and a wheel `entry_points.txt` check in CI. (Upstream commit
  c8b6421, re-applied to this fork's workflow.)

---
## [0.3.4] – 2026-08-20

### Fixed

- **Semantic Scholar: retry budget no longer carries over into the anonymous
  fallback after a 403.** When a configured API key was rejected, the
  authenticated retry budget (3 attempts) stayed in effect for the anonymous
  fallback, letting it retry 429s against the already-throttled shared pool.
  `max_retries` is now capped right after the fallback so only one anonymous
  attempt is made before giving up.

## [0.3.3] – 2026-08-20

### Fixed

- **Semantic Scholar: API failures are no longer reported as zero results.**
  `search()` now raises `SemanticScholarUnavailable` when the API is rate
  limited or returns a non-200 status, so `search_papers` records the failure
  in its `errors` mapping. Previously an unreachable source and a query with
  no matches were indistinguishable from the outside.

## [0.3.2] – 2026-08-19

Reliability fixes for the Semantic Scholar connector. No tool names, parameters,
or result formats changed; clients do not need to reconnect.

### Added

- **Semantic Scholar: client-side request serialisation.** Consecutive requests
  are spaced by at least `MIN_REQUEST_INTERVAL` (1.05 s) using a class-wide
  lock, so concurrent users cannot collectively exceed the 1 request/second
  limit that applies to an authenticated key. Note that the lock is
  process-local: deployments running multiple worker processes must adjust the
  interval accordingly.
  
### Fixed

- **Semantic Scholar: `limit` is now clamped to the API maximum of 100.**
  The relevance search endpoint rejects larger values with HTTP 400. Requests
  with `max_results > 100` therefore returned no results at all, which surfaced
  as an apparently empty source rather than an error.
- **Semantic Scholar: missing `data` key no longer raises.** The response is
  now read via `.get()`. Previously a KeyError was swallowed by the generic
  exception handler, masking the underlying cause.
- **Semantic Scholar: a single HTTP 429 backoff is capped at 10 seconds.**
  Exponential backoff is retained, but an uncapped wait could stall a
  multi-source search past the MCP client timeout on a cold-started instance.

### Changed

- Semantic Scholar: log the reported `total` and a truncated raw payload when a
  query returns no results, so genuine zero-hit queries can be distinguished
  from capped or malformed requests.
- Translated the remaining upstream Chinese comments in `semantic.py` to English.

### Removed

- Semantic Scholar: unused `SEMANTIC_SEARCH_URL` constant. The request URL is
  built from `SEMANTIC_BASE_URL` and the endpoint path.


## [0.3.0] – 2026-08-12

Adds citation chaining (snowballing) over OpenAlex as a third tool group. This is a
purely additive release: no existing tool changed its name, parameters, or result
format. Metadata-only — no full text is fetched and no reference lists are parsed
from PDFs.

### Added

- **Citation chaining tools** (`paper_search_mcp/citations/`), registered through
  `register_citation_tools(mcp)` from `server.py`, following the same pattern as the
  OPAC tool group:
  - `paper_referenzen` — **backward** search: the works a given paper cites, read
    from the OpenAlex `referenced_works` field and hydrated with metadata. Leads to
    the foundational literature of a topic.
  - `paper_zitiert_von` — **forward** search: the works that cite a given paper,
    via the OpenAlex `cites:` filter, sorted by citation count. Optional `ab_jahr`
    restricts to recent work. Leads from a known key paper to the current state of
    research — the direction a keyword search cannot provide.
  - `paper_verwandte` — **sideways** search: OpenAlex `related_works`. See the
    reliability caveat under *Known Limitations* below.
- All three accept either a DOI or an OpenAlex work ID (`W…`), including full URLs of
  either form; identifiers are normalized internally.
- Results are returned in the same `Paper` dictionary format as the `search_*` tools,
  so downstream formatting is unchanged.
- Requests use the `select=` parameter to fetch only the needed fields, keeping
  responses compact; abstracts are opt-in via `mit_abstract` (default off) because
  they enlarge the payload substantially.
- HTTP 409 (OpenAlex credit exhaustion) and 429 (rate limit) are translated into
  explicit, actionable error messages rather than empty result lists.

### Known Limitations

- **`paper_verwandte` is unreliable** and is not recommended as a load-bearing step.
  OpenAlex `related_works` is algorithmically derived and, for records whose leading
  concept is an ambiguous token, can return topically unrelated results. Live testing
  on a construction digital-twin review (whose first OpenAlex concept was the
  ambiguous "Pace") returned works on authorship analysis and unrelated topics. The
  backward and forward tools are unaffected and verified reliable. The tool is kept
  because it is nearly free (one field from the already-fetched work object), but the
  `agentische-recherche` skill should lean on `paper_referenzen` and
  `paper_zitiert_von`.

### Requirements

- Citation tools use the existing OpenAlex key (`PAPER_SEARCH_MCP_OPENALEX_API_KEY`
  or `OPENALEX_API_KEY`). Without a key, OpenAlex allows roughly 100 credits/day and
  then returns HTTP 409; `paper_referenzen` costs two requests per call, the others
  one to two.

--- 

## [0.2.0] – 2026-07-24

Cleanup release in preparation for institutional deployment. **Breaking**: several
tools were removed; any client configuration or skill referring to them must be updated.

### Added

- **Release pipeline** (GitHub Actions). Pushing a tag matching `v*.*.*` builds the
  package, runs the unit tests, creates a GitHub Release for that tag, and attaches
  the built distributions as release assets. Publishing targets GitHub Releases only
  (not PyPI) and requires no external secrets.
- Release procedure documented in the README (`Version Bump & Release`).

### Removed

- **Sci-Hub support removed entirely.** The `download_scihub` tool block, the
  `use_scihub` / `scihub_base_url` parameters of `download_with_fallback`, the
  hard-coded mirror URL, and the `SciHubFetcher` call path are gone. Accessing
  shadow libraries is out of scope for a library service; full text is reached
  through open access or the library's licensed routes.
- **Google Scholar** (`search_google_scholar`). Google provides no public API for
  Scholar; the implementation scraped result pages, which conflicts with Google's
  terms of use and is regularly blocked by bot detection. Crossref, OpenAlex, and
  Semantic Scholar cover the same need through official APIs.
- **CiteSeerX** (`search_citeseerx`, `download_citeseerx`, `read_citeseerx_paper`).
  The endpoint is unreliable and returns 404 / redirects to an archive.
- **SSRN** (`search_ssrn`, `download_ssrn`, `read_ssrn_paper`). Blocked by
  bot detection (HTTP 403); the connector could not return results.

### Changed

- `download_with_fallback` now ends after the open-access / Unpaywall stage and
  documents the deliberate scope limit in its docstring.
- `ALL_SOURCES` reduced accordingly; the multi-source dispatch in `search_papers`
  and the primary downloader map were updated to match.

---

## [0.1.4-1] – BHT integration (documented retroactively)

The state demonstrated internally in July 2026. Changes relative to upstream 0.1.4:

### Added

- **BHT/KOBV library catalog search** via Z39.50 as a second tool group in the same
  server process (`paper_search_mcp/opac/`), registered through
  `register_opac_tools(mcp)`:
  `opac_suche`, `opac_autor_suche`, `opac_isbn_suche`, `kobv_verbund_suche`.
  Searches are filtered to BHT holdings via ISIL `DE-B768` (Bib-1 attribute 1044)
  and can be widened to the full KOBV union catalog for interlibrary loan.
- **Deep links into the local webOPAC** for catalog hits with an ISBN, replacing the
  call number that the union catalogue does not provide.
- **OpenAlex API key support** (`PAPER_SEARCH_MCP_OPENALEX_API_KEY`). Since
  2026-02-13 the OpenAlex API requires a key; without one, requests are limited to
  roughly ten searches per day and then fail with HTTP 409, which previously
  surfaced as silently empty result lists. HTTP 409 and 429 are now logged explicitly.
- Deployment as a single remote MCP connector over streamable HTTP, plus `setup.sh`
  (dependency install, PyZ3950 from source, `ccl.py` stub for Python 3.11+).

### Fixed

- **Umlauts in catalog search terms.** PyZ3950 encoded query terms as ASCII, so any
  term containing ä/ö/ü/ß aborted with `UnicodeEncodeError`. Search terms in the RPN
  query are now converted to UTF-8 bytes before transmission.
- **Wrong call number.** The parser read MARC field 082 (Dewey classification) and
  presented it as the shelf mark. The union catalogue does not contain local call
  numbers; holdings are now confirmed via field 924 (`$b` = ISIL) and the webOPAC
  link is offered instead. DDC and RVK are kept separately as classifications.
- **Multi-word catalog searches.** Multiple words were sent as a rigid phrase, which
  missed titles containing all terms in different positions. For `any` / `title` /
  `author` the words are now AND-combined; for `subject` the phrase is preserved,
  since GND subject headings are genuine multi-word expressions.

### Removed

- Sci-Hub download tool disabled (fully removed in 0.2.0).

---

## Upstream

Earlier history belongs to the upstream project; see
[openags/paper-search-mcp](https://github.com/openags/paper-search-mcp).
