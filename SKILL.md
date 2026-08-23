---
name: agentische-recherche
description: "Mehrstufige wissenschaftliche Literaturrecherche an der BHT, die den Rechercheprozess sichtbar macht. Durchsucht zuerst den BHT-Bibliothekskatalog (OPAC/KOBV) nach Grundlagenliteratur, dann akademische Paper-Datenbanken nach aktueller Forschung, und fasst die Ergebnisse zusammen. Beide Quellen liegen auf einem Connector (paper-opac-search-mcp). Manuell auszulösen, z. B. mit 'mach eine agentische Recherche zu …', 'systematische Literaturrecherche zu …' oder 'recherchiere Literatur zu …'. Liefert Trefferlisten mit Quell-Links direkt im Chat; beschafft keine Volltexte."
---

# Agentische Recherche (BHT Campusbibliothek)

## Zweck

Dieser Skill bildet den professionellen Rechercheprozess einer wissenschaftlichen
Bibliothek nach und macht ihn für die nutzende Person **transparent**. Statt einer
Trefferliste aus einer einzelnen Quelle geht Claude in nachvollziehbaren Stufen
vor und erklärt bei jeder Stufe knapp, *warum* sie kommt und *was* sie beiträgt –
zuerst die Suchbegriffstabelle (Begriffsfeld), dann Katalog für Grundlagen,
Fachdatenbanken für aktuelle Forschung, Synthese und schließlich konkrete
Suchvorschläge für die nächste Runde.

Der didaktische Anspruch: Die Person soll die **Recherchetechnik** mitnehmen —
Begriffsfeld systematisch entwickeln, Treffer auswerten, Begriffe nachschärfen,
erneut suchen — nicht nur eine fertige Trefferliste erhalten.

Alle Werkzeuge liegen auf **einem** MCP-Connector: `paper-opac-search-mcp`.
Er vereint die OPAC-/KOBV-Tools (BHT-Bibliothekskatalog über Z39.50, gefiltert
auf ISIL DE-B768) und die Paper-Suche über mehrere Datenbanken.

## Grundprinzipien (Datenintegrität)

- **Nur verwenden, was die Werkzeuge zurückgeben.** Jeder Titel, jede Autor*in,
  jedes Jahr, jede Signatur, jeder Link muss aus einem Suchergebnis dieser
  Sitzung stammen – nicht aus dem Trainingswissen, nicht erfunden.
- **Links aus der Tool-Ausgabe immer übernehmen.** Der `[OPAC]`-Link (Katalog) und
  die DOI/URL (Paper) sind der eigentliche praktische Nutzen für die Person und
  dürfen bei der Synthese **nicht** wegfallen. Jeder genannte Treffer trägt seinen
  klickbaren Link. Beim Umschreiben der Trefferliste die Links mitführen, nicht
  durch interne IDs (PPN) ersetzen.
- **Erst abwarten, dann weitergehen.** Eine Suche ist erst abgeschlossen, wenn
  die Ergebnisse da sind und gesichtet wurden.
- **Lücken offenlegen, nicht auffüllen.** Null Treffer wird gesagt, nicht durch
  erfundene Einträge kaschiert.
- **OpenAIRE-DOIs vor dem Zitieren prüfen.** OpenAIRE verschmilzt beim eigenen
  Dedup gelegentlich zwei verschiedene Werke zu einem Datensatz: DOI, URL und
  Autor*innen können dann zu drei verschiedenen Arbeiten gehören. Ein
  OpenAIRE-Treffer wird nur genannt, wenn der DOI zum Titel passt – im Zweifel
  über eine zweite Quelle gegenprüfen. (Upstream-Problem, nicht im Server behebbar.)
- **Keine Volltextbeschaffung.** Dieser Skill *findet* Literatur und liefert Links
  zur Quelle. Er ruft **keine** Download-/Read-Werkzeuge auf (kein
  `download_with_fallback`, kein `download_*`, kein `read_*`). Den Volltext erhält
  die Person über die legitimen Wege der Bibliothek (siehe Schlusshinweis).

## Ablauf

Vorab das Thema mit der Person schärfen, falls zu breit oder vage (Fachgebiet?
Eher Grundlagen oder aktueller Forschungsstand? Deutsch- oder englischsprachige
Literatur?). Bei klarem Auftrag direkt loslegen. Jede Stufe kurz ankündigen und
ihren Beitrag in ein, zwei Sätzen erklären – das ist der sichtbare Prozess, aber
ohne ihn zu zerreden.

### Stufe 0 — Suchbegriffstabelle (Begriffsfeld erarbeiten)

**Vor** der ersten Suche das Begriffsfeld sichtbar machen. Das ist die
Recherchetechnik, die die Campusbibliothek in ihren Schulungen vermittelt
(Blocksuche): Das Thema wird in 2–4 **Suchblöcke** (Facetten/Konzepte) zerlegt,
und je Block werden Synonyme, Ober-/Unterbegriffe, Schreibvarianten und
englische Entsprechungen gesammelt. Innerhalb eines Blocks gilt ODER, zwischen
den Blöcken UND.

Erstelle die Tabelle als Markdown, mit einer Zeile je Block:

| Block | Deutsch | Englisch | Enger / Weiter |
|---|---|---|---|
| 1 (Konzept A) | Begriff, Synonym, Variante | term, synonym | enger: … / weiter: … |
| 2 (Konzept B) | … | … | … |

Hinweise zur Erstellung:
- **2–4 Blöcke** genügen; mehr Blöcke verengen die Treffermenge zu stark.
- Deutsche **und** englische Begriffe: Der Katalog ist überwiegend deutsch, die
  Paper-Quellen überwiegend englisch — die Tabelle bedient beide Stufen.
- Komposita und Wortvarianten mitdenken (z. B. „Gebäudeautomation" /
  „Gebäudeautomatisierung"), da der KOBV-Zugang **keine Trunkierung** unterstützt.
- Kontrolliertes Vokabular gehört in die deutsche Spalte, weil es die
  GND-Schlagwortsuche in Stufe 1 speist.

Sage anschließend in einem Satz, **welche Begriffe** du für die erste Suche
verwendest und warum — so bleibt die Strategie nachvollziehbar. Die Tabelle ist
didaktisches Kernstück: Sie zeigt der Person, wie man Suchbegriffe systematisch
entwickelt, statt nur ein Ergebnis zu konsumieren.

### Stufe 1 — OPAC (Grundlagenliteratur, BHT-Bestand)

Der Katalog liefert die Grundlagen: Lehrbücher, Handbücher, etablierte Werke,
vorrangig den an der BHT verfügbaren Bestand. Suchbegriffe stammen aus der
Tabelle (Stufe 0), vorrangig aus der deutschen Spalte.

- **Beginne mit der Schlagwortsuche:** `opac_suche` mit `suchtyp="subject"`,
  `nur_bht_bestand=true`, `max_treffer` 12–15. Die Schlagwortsuche nutzt das
  kontrollierte Vokabular (GND) und ist **deutlich präziser** als `"any"` –
  empirisch bestätigt: Bei `"any"` mischen sich thematisch lose Treffer in die
  vorderen Ränge, bei `"subject"` sind die vorderen Treffer durchgängig
  einschlägig.
- **Die Trefferliste ist NICHT relevanzsortiert** wie eine Discovery-Suche – die
  angezeigten N sind schlicht die ersten N von vielen. Deshalb bewusst mehr
  scannen (12–15) und die **einschlägigsten selbst auswählen**, statt die ersten
  fünf zu übernehmen. Auswahlkriterien: Passung zum Thema (Titel + Schlagwörter),
  aktuelle Auflagen, Lehrbuch/Handbuch vor enger Monografie.
- **Fallback `"any"`:** Liefert die Schlagwortsuche zu wenig (sehr neues oder
  spezielles Thema ohne etablierte GND-Schlagwörter), mit `suchtyp="any"`
  nachfassen. `suchtyp="title"`, wenn ein bestimmter Titel gesucht wird.
- Deutsche Begriffe für deutschsprachige Themen; einzelne, zentrale Begriffe
  statt langer Mehrwortphrasen.
- `opac_autor_suche` bei bekannter Person, `opac_isbn_suche` bei bekannter ISBN.
- Nichts im BHT-Bestand → `kobv_verbund_suche` (gesamter Verbund, Fernleihe) und
  klar als Fernleihe kennzeichnen.

Nenne zu jedem ausgewählten Treffer: Titel, Autor*in(nen), Jahr, ggf. Auflage,
den **Bestandshinweis** („✅ im BHT-Bestand") und den **`[OPAC]`-Link aus der
Tool-Ausgabe** — diesen Link **unverändert übernehmen**; er führt direkt zum Titel
im lokalen webOPAC mit Signatur & Verfügbarkeit.

Wichtig: Der KOBV-Verbundkatalog enthält **keine** Standortsignatur. Gib deshalb
**nicht** die PPN oder eine DDC/RVK-Klassifikation als „Signatur" aus — der
`[OPAC]`-Link ersetzt die Signatur. Die PPN ist nur eine interne Datensatz-ID und
gehört nicht in die Ausgabe.

### Stufe 2 — Paper-Suche (aktuelle Forschung)

Erkläre den Übergang: Der Katalog zeigt die Grundlagen; für den aktuellen
Forschungsstand braucht es Fachdatenbanken mit Zeitschriftenartikeln.

- **`search_papers` mit gezielten Kernquellen, nicht `sources="all"`.**
  `max_results_per_source` ca. 5 – nicht senken, das kostet relevante Treffer.
  Für Aktualität das Jahr eingrenzen, nicht die Trefferzahl.
- Englische Suchbegriffe bringen hier meist mehr Treffer; 3–8 Wörter.

| Auswahl | Quellen |
|---|---|
| Grundstock, alle Fächer | `openalex,semantic,crossref` |
| + Bau, Umwelt, Maschinenbau | `openaire` – europäische Konferenz- und Repositorienliteratur (z. B. WCTE), sonst nirgends auffindbar |
| + Life Sciences, Verfahrenstechnik | `europepmc` – **nicht** `pubmed`, **nicht** `pmc` |
| + Informatik | `arxiv`, `dblp` |
| + sobald API-Keys gesetzt | `ieee`, `acm` |

Die Achse ist **Grundstock + fachliche Ergänzung**, nicht Fach → Quellenliste:
die Quellen unterscheiden sich vor allem in der Metadatenqualität, nicht in der
Fachabdeckung. Dazu drei Dinge, die man beim Auswerten wissen muss:

- **Crossref liefert oft Titel ohne Inhalt.** Abstract-Abdeckung an identischer
  Stichprobe: OpenAlex 99 %, Semantic Scholar 98 %, **Crossref 75 %** – und das
  verlagsabhängig, Elsevier und ACS liefern 0 %. Deshalb steht Crossref im
  Grundstock nicht allein.
- **Europe PMC ersetzt `pubmed` + `pmc`.** Es bündelt PubMed-Abstracts und
  PMC-Volltexte in einer Suche; die Dreierkombination ist weitgehend redundant.
  `pmc` durchsucht Volltexte, zählt also jede beiläufige Erwähnung und liefert
  entsprechend thematisch danebenliegende Treffer ohne Abstract.
- **dblp findet gut, aber screent schlecht:** keine Abstracts, keine
  Zitationszahlen. Für die Auswahl in dieser Stufe fehlen damit beide Signale.

**Auswahl der besten Titel – das ist Claudes Aufgabe, nicht die des Tools:**
`search_papers` aggregiert pro Quelle und dedupliziert, **rankt aber nicht
quellenübergreifend nach Relevanz**. Deshalb aktiv auswählen anhand der
vorhandenen Signale:

- **Zitationszahl** (OpenAlex liefert sie): hoher Wert = Grundlagen-/Referenzwerk.
- **Erscheinungsjahr**: für die Aktualitäts-Achse.
- **Fehltreffer aktiv aussortieren:** Manche Quellen (v. a. DOAJ) matchen nur den
  Wortlaut. Ein Treffer, der den Suchbegriff im Titel trägt, aber inhaltlich nicht
  zum Thema gehört (Beispielmuster: ein Aufsatz über Berufsschulunterricht, der
  zufällig „Building Information" im Namen führt), wird **nicht** aufgenommen.
- **Ziel ist eine Mischung:** 2–3 Grundlagenarbeiten (hohe Zitationszahl) plus
  2–3 aktuelle Arbeiten (letzte ~3 Jahre, oft Open Access).

Nenne zu jedem ausgewählten Treffer: Titel, Autor*in(nen), Jahr, Quelle/Journal,
die **DOI als klickbaren Link** und – wo vorhanden – die **Zitationszahl** (für die
Person ein starker Relevanz-Hinweis). DOI immer als vollständige URL im Format
`https://doi.org/<doi>` verlinken; liefert das Tool bereits eine volle URL, diese
verwenden. Nackte DOI-Strings ohne Link vermeiden.

### Stufe 3 — Synthese

- Ordne ein, was der Katalog (Grundlagen) und die Paper-Suche (aktuelle Forschung)
  beigetragen haben.
- Benenne Schwerpunkte oder Lücken in den Treffern.

### Stufe 4 — Suchvorschläge (erweitern & vertiefen)

Zum Abschluss **konkrete, direkt ausführbare** Vorschläge für die nächste
Suchrunde — abgeleitet aus dem, was die Treffer gezeigt haben, nicht generisch.
Jeweils 2–3 Vorschläge pro Richtung, mit dem konkreten Suchbegriff bzw. Toolaufruf:

**Erweitern** (mehr/breitere Treffer), wenn die Ausbeute dünn war:
- Nachbarbegriffe aus der Tabelle (Stufe 0), die noch nicht gesucht wurden
- Oberbegriff statt engem Begriff; `suchtyp="any"` statt `"subject"`
- `nur_bht_bestand=false` → KOBV-Verbund (Fernleihe) für Titel außerhalb der BHT
- Englische Begriffe für die Paper-Stufe, weitere Quellen fachabhängig zuschalten

**Vertiefen** (gezielter, spezifischer), wenn die Ausbeute gut war:
- **Schlagwörter aus den besten Treffern** aufgreifen: Die GND-Schlagwörter der
  OPAC-Ergebnisse sind erprobte Sucheinstiege — nenne sie als nächste Suchbegriffe.
- **Autorensuche** (`opac_autor_suche`) zu Personen, die mehrfach auftauchten
- Unterbegriff/Teilaspekt, der in den Treffern sichtbar wurde
- Zeitliche Eingrenzung auf die letzten Jahre für den aktuellen Stand

Formuliere die Vorschläge so, dass die Person sie direkt sagen kann („Suche als
Nächstes nach …"). Erkläre bei ein bis zwei Vorschlägen kurz **warum** gerade
dieser Schritt sinnvoll ist — das ist der didaktische Mehrwert: Die Person lernt
das Muster „Treffer auswerten → Begriffe nachschärfen → erneut suchen".

## Prozess-Transparenz (Audit)

Knapp am Ende sichtbar machen – als kurze Bilanz, keine Tabelle:
OPAC (Anfragen, Treffer, genannt; BHT vorhanden / nur Verbund) und Paper-Suche
(Anfragen über welche Quellen, Treffer, genannt). Stufen ohne Treffer ausdrücklich
benennen.

> Beispiel: **OPAC (subject, BHT):** 1 Anfrage, 93 Treffer, 4 genannt – alle an der BHT.
> **Paper-Suche (openalex, semantic, crossref):** 1 Anfrage, 9 dedupliziert, 5 genannt.
> **Ohne Treffer:** keine.

## Schlusshinweis an die Person (Zugang zum Volltext)

Kurz und sachlich, passend zum Treffertyp:
- **Bücher (OPAC):** über den `[OPAC]`-Link direkt zum Titel im lokalen Katalog
  (dort Signatur & Standort); nicht im BHT-Bestand → Fernleihe über das KOBV-Portal.
- **Artikel:** Open-Access-Artikel direkt über den Link (DOI); lizenzpflichtige
  über die E-Ressourcen der BHT (EZB/DBIS, bei Bedarf Shibboleth oder VPN).

## Abdeckung – ehrliche Grenzen

- Die offenen Paper-Quellen indexieren **englischsprachige** Literatur gut;
  deutschsprachige Zeitschriftenartikel und Repositorien-Inhalte (z. B.
  fachliche OA-Server) sind schwächer abgedeckt. Bei deutschsprachigen Themen ist
  der OPAC (Bücher) das stärkere Bein, die Paper-Stufe eher englisch. Keine
  Vollständigkeit suggerieren.
- Weder OPAC noch `search_papers` liefern ein echtes Relevanz-Ranking über alle
  Treffer. Die Qualität der Auswahl hängt davon ab, dass Claude scannt und nach
  den genannten Signalen auswählt – nicht davon, die ersten N zu übernehmen.

## Werkzeug-Referenz (Connector `paper-opac-search-mcp`)

Katalog:
- `opac_suche(suchbegriff, suchtyp="subject"|"any"|"title"|"author", max_treffer, nur_bht_bestand=true)`
- `opac_autor_suche(autor, max_treffer, nur_bht_bestand=true)`
- `opac_isbn_suche(isbn)`
- `kobv_verbund_suche(suchbegriff, suchtyp="any", max_treffer)`

Paper:
- `search_papers(query, sources="openalex,semantic,crossref", max_results_per_source=5, year=optional)`
- Quellenspezifische `search_*` (z. B. `search_openalex`) für gezielte Einzelabfragen.

Zitationsverfolgung (Schneeballsystem):
- `paper_referenzen(kennung, max_treffer, mit_abstract=false)` – rückwärts: worauf
  baut die Arbeit auf?
- `paper_zitiert_von(kennung, max_treffer, ab_jahr, mit_abstract=false)` – vorwärts:
  wer zitiert sie? **`ab_jahr` immer setzen** (z. B. `ab_jahr=2022`): die Rückgabe ist
  nach Zitationszahl absteigend sortiert. Bei hochzitierten Grundlagenarbeiten stehen
  deshalb ältere Arbeiten oben, und ohne Jahresfilter fällt genau der aktuelle
  Forschungsstand heraus, den der Vorwärtsschritt liefern soll.
- `paper_verwandte` wird nicht verwendet.

Nicht verwenden (Beschaffung): `download_with_fallback`, `download_*`, `read_*`.

## Hinweise

- **Reihenfolge fest:** erst Suchbegriffstabelle (Stufe 0), dann OPAC (subject),
  dann Paper, dann Synthese, dann Suchvorschläge. Die Tabelle steht **vor** der
  ersten Suche — sie ist die Strategie, nicht die Nachbereitung.
- **Kein `opac_erweiterte_suche`** – existiert nicht; Mehrfeld-Logik über mehrere
  `opac_suche`-Aufrufe.
- **Quellen nach der Tabelle in Stufe 2 wählen**, nicht pauschal alle. `base`
  ist unzuverlässig, Google Scholar und SSRN stehen im Connector nicht zur
  Verfügung.
