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
## [0.6.0] – 2026-08-27

Zeitschriftenkennzahlen: ein neues Tool `zeitschrift_profil`, die Zeitschrift als
strukturiertes Feld an jedem OpenAlex-Treffer, und die Anreicherung als Opt-in.

**Upgrading:** remove the connector in the client and add it again — the tool list
grew by one entry and clients cache it. Nothing existing changed shape.

**Deliberately not the Journal Impact Factor.** The JIF is Clarivate's, ships only
through the Journal Citation Reports, has no free API, and the BHT licenses neither
Web of Science nor JCR; "Impact Factor" is a Clarivate trademark and is not used as
a label for a value computed elsewhere. What ships is OpenAlex's
`2yr_mean_citedness` under the name `zit_schnitt_2j` — same concept, different data
basis, different number.

### Added

- **`zeitschrift_profil(kennung)` returns a journal's profile:** publisher, open
  access status, DOAJ listing, indexed works, h-index and the mean citations of the
  works of the last two years. `kennung` takes an ISSN, an OpenAlex source ID, a
  journal name or an article DOI; the first three resolve unambiguously, a name
  search is flagged `zuordnung: "unscharf"` so the caller can confirm it against
  the ISSN. New package `paper_search_mcp/journals/`, wired into `server.py` the
  way `citations/` and `opac/` already are.
- **OpenAlex results carry the publishing journal in `extra`:** `journal`,
  `quelle_id`, `issn_l`, `quelle_typ` and, where they apply, `zeitschrift_oa` and
  `in_doaj`. All of these were already in the API response — `primary_location`
  is selected either way — so this costs no additional request. `quelle_typ`
  earns its place without any metric attached: it separates a journal article
  from a repository copy and a conference paper.
- **`search_openalex(mit_kennzahlen=True)`** adds `zit_schnitt_2j` and
  `zeitschrift_h_index` to each result. Off by default. The distinct journals of
  a result set are fetched in one batch, not one request per hit, and cached for
  the life of the process; `/sources` costs the same as `/works`, one credit per
  request regardless of batch size. A failed enrichment is logged and swallowed —
  it is supplementary information and must never topple a working result list.
- A missing metric is **omitted rather than reported as 0**. A zero in a metrics
  column reads as a statement about the journal but is almost always a gap in the
  data.

### Changed

- `EXTRA_KEYS` in `paper.py` admits the journal fields. Without that entry the
  0.5.0 payload diet would have dropped every one of them silently.
- `citations/openalex_graph.py`: `_get` and `_kurz_id` are now the public
  `hole_json` and `kurz_id`, so the journals module reuses one HTTP layer — same
  session, same API key, same error translation — instead of duplicating it.
- The BHT research skill gains a section on journal metrics: output as a short
  list rather than a table column, always with the note that the value describes
  the journal and not the article, and never under the name "Impact Factor".
  Sorting result lists by the metric is deliberately not implemented — that is
  the use [DORA](https://sfdora.org/) and CoARA address.
- `PAPER_SEARCH_MCP_ENABLED_TOOLS` gains `zeitschrift_profil` in the documented
  BHT set, which grows from seven tools to eight: 2,151 → 2,433 tokens.

### Fixed

- **The OpenAlex adapter no longer discards the journal name.** It read
  `primary_location` for the landing page and the PDF link and then built `Paper`
  without any `extra` at all, so `search_openalex` and every `search_papers` run
  lost the journal of every OpenAlex hit.
- **`tests/test_semantic.py::test_search_max_results` no longer fails on a rate
  limit.** It calls the live API but was missing the `skipUnless` guard its
  neighbours in the same file carry. With that fixed, the file joins the CI list,
  as does `tests/test_openalex_sources.py`.
- **`tests/test_server.py` no longer asserts a source list that does not exist.**
  `test_all_sources_include_new_platforms` and `test_parse_sources_with_new_platforms`
  still expected `citeseerx` and `ssrn` in `ALL_SOURCES`; both were removed in
  0.2.0 and the two tests have failed ever since. **SSRN is not part of the
  aggregated search** and `search_papers` cannot reach it — a re-check on
  2026-08-27 confirms why: the documented result page
  (`www.ssrn.com/index.cfm/en/rps-stage1-results/`) answers 404, and the
  alternate (`papers.ssrn.com/sol3/results.cfm`) answers 403 with a Cloudflare
  challenge, so `SSRNSearcher.search()` returns zero hits for every query.
  `academic_platforms/ssrn.py` stays in the tree and keeps its unit tests — those
  parse recorded HTML and do not touch the network — and the 0.5.0 serialization
  fix remains correct; neither makes the live endpoint reachable. The
  assertions now match the actual list, and a new
  `test_retired_platforms_stay_out_of_all_sources` pins the exclusion so a
  future re-add has to come with a connector that works.

---
## [0.5.0] – 2026-08-23

This release bundles the packages planned as 0.4.0 through 0.5.0: the tool
allowlist and the dblp fix (0.4.0), the schema diet and the source table in
`SKILL.md` (0.4.1), the payload diet and the CrossRef metadata fixes (0.4.2),
and abstract truncation plus the CrossRef filter passthrough (0.5.0). They ship
together because they were developed on one branch.

**Upgrading:** remove the connector in the client and add it again — a reconnect
is not enough, clients cache the tool list. Callers of the OPAC tools must pass
arguments flat instead of wrapped in `params`, and `search_papers` no longer
returns `sources_used`, `sources_requested` and `raw_total`.

Measured against 0.3.4: tool list 14,629 → 9,679 tokens, or 2,147 with the
allowlist set to the seven tools the BHT research skill uses; search responses
−40 % at identical results.

### Added

- **`search_papers(abstract_chars=600)` shortens abstracts.** Abstracts are by
  far the largest field of a result — 1,599 of 2,781 tokens in a reference query
  — and screening works on the first few sentences. Truncation cuts on a word
  boundary and marks the cut with ` […]`. **`abstract_chars=0` keeps them whole**,
  which is what harvesting search terms from abstracts needs; `SKILL.md` says so
  at the step where that happens. Measured on identical results: 2,781 → 2,061
  tokens.
- **`search_papers(crossref_filter=…)` passes a CrossRef filter into the
  aggregation**, so it applies with deduplication and error handling rather than
  requiring a separate `search_crossref` call. `type:journal-article` filters out
  the dissertations and proceedings that dominated the CrossRef share of a
  reference query; results carrying an abstract rose from 5 to 7 of 10.

### Changed

- **Search results carry only what helps judge a paper.** `Paper.to_dict()`
  serialized all 15 fields including the empty ones; `updated_date`, `keywords`
  and `references` were empty in every result of a reference query. Empty fields
  are now omitted, `published_date` is the year, a `url` that only restates the
  DOI and a `paper_id` identical to the DOI are dropped, `extra` is a real dict
  limited to the fields that help judgement instead of a stringified one,
  `categories` is capped at three, and author lists are capped at three names
  plus `u. a. (n=47)` — hyperauthorship papers could otherwise cost more than a
  thousand tokens for a single result. Measured on an identical query with
  identical results: 3,459 → 2,781 tokens, 346 → 278 per paper.
- **`search_papers` no longer returns `sources_used`, `sources_requested` and
  `raw_total`.** The first restates the keys of `source_results`, the other two
  were debugging aids, and all three are paid for on every call.

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

- **CrossRef: a missing date is no longer filled with 1970-01-01.** The
  placeholder corrupted every year filter and sort — and it did more damage than
  that: `_extract_date` substituted 1970 whenever the year part was missing, and
  since that value is truthy, the fallback chain `published` → `issued` →
  `created` stopped at the first field and never reached the one that had the
  real date. Three of five results for a reference query carried 1970-01-01;
  after the fix all three carry their actual publication year.
- **CrossRef: abstracts are stripped of JATS markup.** They arrived with
  `<jats:p>`, `<jats:title>`, `<jats:italic>` and friends, which cost tokens and
  get in the way while screening. A leading "Abstract" heading goes with it.
- **Deduplication merges instead of discarding, and matches across sources.**
  The unique key ignored casing and singular/plural, so "… to a Microservices
  Architecture" (CrossRef) and "… to a microservice architecture" (dblp) both
  reached the client; it also mixed the author string into the key, where
  sources disagree on formatting. Titles are now normalized and paired with the
  year. When a duplicate is found, empty fields are filled from it, the higher
  citation count and the longer abstract win, and `extra` is merged key by key —
  previously whichever source answered first won outright, so a record without
  an abstract could displace one that had it.

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
