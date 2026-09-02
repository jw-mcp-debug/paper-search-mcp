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
## [0.7.1] – 2026-09-02

Jeder Katalogtreffer sagt jetzt, wie er zu bekommen ist: im BHT-Bestand, frei im
Netz, lizenzpflichtige E-Ressource oder Fernleihfall. Fernleihe wird nur noch
dort angeboten, wo sie überhaupt möglich ist. Und die Sammelsuche mischt keine
zufälligen Preprints mehr unter die Treffer.

**Upgrading:** nichts zu tun. Die Tool-Liste, die Parameter und ihre
Beschreibungen sind unverändert — der Connector muss nicht neu geladen werden.

### Fixed

- **Ein Treffer konnte ganz ohne Bestandszeile erscheinen.** `bht_bestand` wurde
  auf `None` gesetzt und ausschließlich auf `True` — der Zweig für `False` in der
  Ausgabe war toter Code und hat nie ausgelöst. Darunter stand trotzdem ein
  pauschaler Nachsatz, der Fernleihe bewarb. Eine fehlende Angabe plus stehende
  Werbung liest sich wie eine Auskunft: bestellen. In einer echten Sitzung ist
  genau das passiert.
- **In der Verbundsuche wurde Bestand grundsätzlich nicht erkannt.**
  `kobv_verbund_suche` ruft ohne ISIL auf, und dasselbe `isil` steuerte bis in
  den MARC-Parser hinein die 924-Auswertung. Auch ein Titel, den die BHT im
  Regal hat, erschien dort ohne Nachweis — mit demselben Fernleih-Nachsatz
  darunter. Das ist die teure Richtung des Fehlers, weil sie Bestellungen für
  vorhandene Bücher auslöst. Suchfilter (`isil`) und Bestandsauswertung
  (`bestand_isil`, Vorgabe BHT) sind jetzt getrennt.
- **bioRxiv und medRxiv lieferten in der Sammelsuche Zufallstreffer.** Beide
  APIs kennen keine Stichwortsuche; sie filtern über exakte Kategorienamen und
  ignorieren alles andere stillschweigend. `search_papers` reicht aber den
  Suchbegriff des Aufrufenden durch, nicht einen Kategorienamen — gemessen:
  `machine learning` und `voelliger unsinn xyz` ergaben dieselben fünf Sätze,
  schlicht die zuletzt eingestellten Preprints, ausgewiesen als Treffer zur
  Anfrage. Beide sind deshalb aus `ALL_SOURCES` genommen und laufen nur noch auf
  ausdrückliche Nennung (`sources="biorxiv"`), wo die Kategorieabfrage
  funktioniert. Zusätzlich filtert der Client die Kategorie selbst nach, statt
  dem Serverfilter zu glauben, und ein Begriff, der keine Kategorie ist, wird
  gemeldet — mit der Liste der tatsächlich vorhandenen Kategorien und dem
  Verweis auf `europepmc`. **Es geht keine Abdeckung verloren:** Europe PMC
  indexiert die Preprints beider Server und sucht sie per Stichwort; der
  bioRxiv-Preprint aus dem Zufallsbefund oben ist dort auf Platz 1 auffindbar.
- **Der Fernleih-Nachsatz hängt an einer Prüfung** statt unbedingt angehängt zu
  werden: E-Ressourcen sind nicht fernleihfähig, frei zugängliche Volltexte
  braucht niemand zu bestellen, der eigene Bestand schon gar nicht. Enthält die
  Liste keinen Fernleihfall, sagt der Nachsatz das, statt zu werben. Betrifft
  `kobv_verbund_suche` und den Verbund-Zweig von `opac_isbn_suche`.

### Added

- **Ein Bestandslabel für jeden Treffer**, auch für den unklaren Fall: ✅ im
  BHT-Bestand bzw. für die BHT lizenziert, 🌐 frei zugänglicher Volltext, 🔒
  lizenzpflichtige E-Ressource ohne BHT-Nachweis (nicht fernleihfähig), ℹ️ nur
  im Verbund (→ Fernleihe), ❔ kein Besitznachweis im Datensatz. `False` wird
  nur noch vergeben, wenn 924-Felder vorhanden sind und keines passt — fehlt 924
  ganz, bleibt es bei „ungeklärt". „Unbekannt" und „nicht vorhanden" dürfen
  nicht dasselbe Label bekommen, sonst wird aus einer Lücke im Datensatz eine
  Bestellung.
- **Volltextlink, Lizenz und Trägerform aus dem MARC-Satz.** Der Datensatz kam
  die ganze Zeit vollständig an — 856, 540, Leader und 008 hat der Parser nur
  nie angefasst; die Information lag im Speicher und wurde im Mapping verworfen.
  Kein zusätzlicher Request nötig. 856 mit Negativliste auf `$3`, damit ein
  Inhaltsverzeichnis nicht als Volltext ausgegeben wird, und mit `$z`/`$3` als
  Nachweis freier Zugänglichkeit; 540 `$a`/`$u` als Lizenz; E-Ressourcen über
  008/23, 007/00 und 338 `$b`.
- **653 (freie Schlagwörter)** ergänzt 650/689. Bei Repositoriumssätzen ohne
  GND-Erschließung ist das die einzige inhaltliche Angabe im Satz.
- `tests/test_opac_bestand.py`: 23 netzfreie Fälle über synthetische MARC-Sätze,
  darunter der vorher tote `False`-Zweig und „Inhaltsverzeichnis ist kein
  Volltext".
- `tests/test_biorxiv.py` neu geschrieben: netzfrei über eine gestellte
  API-Antwort statt eines echten Downloads. Der alte Test prüfte
  `download_pdf`/`read_paper` — die Oberfläche, die 0.7.0 als Tools entfernt hat
  — und scheiterte zuverlässig an `os.rmdir("./downloads")`, weil dort PDFs
  anderer Testläufe liegen.

### Beispiel

Der Forschungsbericht *Kohlenstoff in versiegelten und entsiegelten Böden in
Berlin* (edoc HU Berlin, 2023) hatte weder Bestandszeile noch Link noch Lizenz —
nur den Fernleih-Nachsatz darunter. Jetzt:

```
**Lizenz:** (CC BY-SA 4.0) Attribution-ShareAlike 4.0 International · …
**Bestand:** 🌐 Frei zugänglicher Volltext – keine Ausleihe nötig
**Volltext:** [frei zugänglich](http://edoc.hu-berlin.de/18452/27457)
```

---
## [0.7.0] – 2026-08-29

Die Katalogsuche versteht Konzepte und ihre Synonyme in einer Anfrage, die
Beschaffungswerkzeuge sind entfernt, und ein fehlgeleiteter Aufruf bekommt eine
Antwort, mit der sich etwas anfangen lässt. Die Tool-Liste kostet damit rund
7.900 statt 13.499 Tokens in **jeder** Anfrage.

**Breaking:** Die 29 Werkzeuge `download_*` und `read_*` gibt es nicht mehr. Ein
Client, der Volltexte über diesen Server bezieht, bleibt auf 0.6.0 — die Suche
ist nicht betroffen.

**Upgrading:** remove the connector in the client and add it again — the tool set
and the parameter descriptions changed, and clients cache the tool list.

### Added

- **Die Katalog-Tools verstehen eine Blocksuche.** `;` trennt Konzepte (die
  UND-verknüpft werden), ` OR ` deren Synonyme, Anführungszeichen erzwingen
  eine Phrase: `KI OR "Künstliche Intelligenz"; Bildung OR Unterricht`. Der
  KOBV-Katalog sortiert nicht nach Relevanz und liest jedes Wort als harten
  UND-Filter — wer drei Konzepte in eine Anfrage schreibt, bekommt regelmäßig
  null Treffer, obwohl der Bestand zum Thema etwas hergibt. In einer echten
  Recherchesitzung liefen 9 von 24 Kataloganfragen leer, sechs davon
  vermeidbar: `Deskilling Künstliche Intelligenz` (0 Treffer) ergibt als
  `Deskilling OR Dequalifizierung; Bildung OR Hochschule` 12 Treffer,
  `KI Künstliche Intelligenz Bildung` (0) im BHT-Bestand 28. Eingaben ohne
  `;` und ` OR ` verhalten sich unverändert.

### Changed

- **Eine Schlagwortsuche ohne Treffer sucht zusätzlich im Freitextfeld** und
  weist das im Ergebnis aus. Ein Begriff, der nicht als GND-Schlagwort
  angesetzt ist, ergab bisher null Treffer, ohne dass erkennbar war warum:
  `Deskilling` findet als Schlagwort nichts, im Freitext 115 Titel. Der
  Rückfall greift nur bei null Treffern — die Präzision einer erfolgreichen
  Schlagwortsuche bleibt unangetastet, und der Wechsel steht im Ergebnistext,
  statt still zu geschehen.
- **`*` und `?` werden als wirkungslos gemeldet.** Der KOBV-Server beherrscht
  keine Trunkierung (Bib-1-Attribut 5 antwortet „unsupported search"), lehnt
  Platzhalter aber nicht ab, sondern liest sie als Wortbestandteil: `Bildung*`
  liefert exakt dieselbe Treffermenge wie `Bildung`. Das sah bisher wie eine
  funktionierende Trunkierung aus.
- **Das Nullresultat erklärt die UND-Verknüpfung**, statt vier allgemeine
  Tipps zu geben, und `kobv_verbund_suche` beschreibt sein Mehrwort-Verhalten
  jetzt so wie `opac_suche` — dort fehlte der Hinweis ganz, was einen Teil der
  leeren Verbundsuchen erklärt.
- **Argumente, die zu keinem Parameter passen, werden erklärt statt vermisst.**
  Ein Client mit zwischengespeicherter Tool-Liste sendet nach einer
  Parameteränderung weiter die alte Form. Pydantic meldete daraufhin das
  *fehlende* Feld („suchbegriff Field required"), während der Aufrufende auf
  ein `suchbegriff` blickte, das er sehr wohl übergeben hatte — nur eine Ebene
  tiefer in einem Wrapper. Diese Antwort kostete eine echte Sitzung sechs
  identische Wiederholungen, bevor sie das Tool aufgab und aus dem
  Ersatzwerkzeug eine falsche Aussage über den BHT-Bestand ableitete. Die
  Meldung nennt jetzt die tatsächlichen Parameter und beide Auswege: flach
  übergeben, und den Connector im Client neu laden. Sie greift nur, wenn
  *kein* übergebenes Argument passt — sobald eines passt, ist die Meldung von
  pydantic die genauere.
- **`CHARS_PER_TOKEN` in `scripts/compare_deployments.py`: 3,5 → 2,6.** Die alte
  Zahl stammt aus einer Messung von vor den Diätrunden und hat die Tool-Liste
  seither um 34 % zu billig gerechnet — der Changelog zu 0.5.0 nennt 9.582 Tokens,
  wo in Wirklichkeit 13.499 anfielen. Der Kommentar an der Konstante sagt jetzt,
  woher der Wert stammt und wann er neu zu messen ist, statt ihn auf Treu und
  Glauben weiterzureichen.
- Tool-Liste 10.065 → 10.179 Tokens (+114) für die erweiterten Beschreibungen.

### Fixed

- **Die Semantic-Scholar-Netztests überspringen sich, wenn der Lauf gedrosselt
  wird.** Sie fragen die Live-API ohne Schlüssel ab, und ein CI-Runner teilt
  seine IP mit jedem anderen Job auf dem Host: Die Erreichbarkeitsprüfung beim
  Import kann durchgehen, während die Anfrage Sekunden später 429 bekommt. Genau
  daran ist der erste 0.7.0-Build gescheitert. Dieselbe Behandlung, die dblp in
  `9ac2084` bekommen hat — eine Drosselung ist eine Netzbedingung, kein Defekt
  im Prüfgegenstand.

### Removed

- **Die 29 Beschaffungswerkzeuge (`download_*`, `read_*`) sind entfernt.** Sie
  waren der größte Block der Tool-Liste — 15.031 Zeichen, 42 %, mehr als die acht
  Werkzeuge, die eine Recherche tatsächlich benutzt — und wurden in jeder
  einzelnen Anfrage mitgeschickt, obwohl sie an drei Stellen ausgeschlossen
  waren: im System-Prompt des Rechercheagenten, in SKILL.md und in der dafür
  vorgesehenen Allowlist. Ein Ausschluss, den man an drei Stellen wiederholen
  muss, ist keine Funktion mehr. Die Searcher-Klassen in `academic_platforms/`
  bleiben unberührt, `search_papers` erreicht weiterhin jede Quelle. Mit
  entfallen sind die nur von ihnen benutzten Helfer `_download_from_url`,
  `_try_repository_fallback`, `_safe_filename` und `tests/test_fallback.py`;
  `server.py` schrumpft von 1.526 auf 943 Zeilen.
- Die Tool-Liste fällt damit von **13.499 auf rund 7.900 Tokens** je Anfrage.
  Diese Zahlen sind an der Kontextanzeige einer laufenden LibreChat-Sitzung
  abgelesen, nicht geschätzt: die im Repo verwendete Näherung von 3,5 Zeichen je
  Token unterschätzt die reale Dichte von 2,61 um 34 %. Die früheren Diätrunden
  haben vor allem gut komprimierbare Zeichen entfernt (Einrückung, wiederholte
  Schlüssel, `{"result": …}`-Wrapper) — 31 % der Zeichen, aber nur 10 % der
  Tokens. Übrig blieb deutscher Fließtext, der je Zeichen am teuersten ist.

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
