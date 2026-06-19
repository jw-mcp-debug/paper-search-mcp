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
Katalog für Grundlagen, Fachdatenbanken für aktuelle Forschung, Synthese am Schluss.

Alle Werkzeuge liegen auf **einem** MCP-Connector: `paper-opac-search-mcp`.
Er vereint die OPAC-/KOBV-Tools (BHT-Bibliothekskatalog über Z39.50, gefiltert
auf ISIL DE-B768) und die Paper-Suche über mehrere Datenbanken.

## Grundprinzipien (Datenintegrität)

- **Nur verwenden, was die Werkzeuge zurückgeben.** Jeder Titel, jede Autor*in,
  jedes Jahr, jede Signatur, jeder Link muss aus einem Suchergebnis dieser
  Sitzung stammen – nicht aus dem Trainingswissen, nicht erfunden.
- **Erst abwarten, dann weitergehen.** Eine Suche ist erst abgeschlossen, wenn
  die Ergebnisse da sind und gesichtet wurden.
- **Lücken offenlegen, nicht auffüllen.** Null Treffer wird gesagt, nicht durch
  erfundene Einträge kaschiert.
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

### Stufe 1 — OPAC (Grundlagenliteratur, BHT-Bestand)

Der Katalog liefert die Grundlagen: Lehrbücher, Handbücher, etablierte Werke,
vorrangig den an der BHT verfügbaren Bestand.

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
**Signatur** (für den direkten Zugriff am Regal) und den Bestandshinweis.

### Stufe 2 — Paper-Suche (aktuelle Forschung)

Erkläre den Übergang: Der Katalog zeigt die Grundlagen; für den aktuellen
Forschungsstand braucht es Fachdatenbanken mit Zeitschriftenartikeln.

- **`search_papers` mit gezielten Kernquellen, nicht `sources="all"`.**
  Standard: `crossref,openalex,doaj` – empirisch sauber und breit.
  `max_results_per_source` ca. 5.
- **Quellen fachabhängig erweitern**, nicht pauschal alle:
  - Informatik / Mathematik / Physik → zusätzlich `arxiv`
  - Medizin / Life Sciences → zusätzlich `pubmed` und/oder `europepmc`
  - Begründung: `arxiv` und `pubmed` lieferten bei einem Bau-/Ingenieurthema
    reinen Fachfremd-Lärm (u. a. ein medizinisches Paper). Sie helfen nur im
    passenden Fach.
- Englische Suchbegriffe bringen hier meist mehr Treffer; 3–8 Wörter.
- Bei Bedarf das Jahr eingrenzen, um aktuelle Arbeiten zu priorisieren.

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
**DOI bzw. Link** und – wo vorhanden – die **Zitationszahl** (für die Person ein
starker Relevanz-Hinweis).

### Stufe 3 — Synthese

- Ordne ein, was der Katalog (Grundlagen) und die Paper-Suche (aktuelle Forschung)
  beigetragen haben.
- Benenne Schwerpunkte oder Lücken in den Treffern.
- Schlage konkrete nächste Schritte vor (Themenverfeinerung, Autorensuche zu einer
  auffällig häufig genannten Person, Fernleihe).

## Prozess-Transparenz (Audit)

Knapp am Ende sichtbar machen – als kurze Bilanz, keine Tabelle:
OPAC (Anfragen, Treffer, genannt; BHT vorhanden / nur Verbund) und Paper-Suche
(Anfragen über welche Quellen, Treffer, genannt). Stufen ohne Treffer ausdrücklich
benennen.

> Beispiel: **OPAC (subject, BHT):** 1 Anfrage, 93 Treffer, 4 genannt – alle an der BHT.
> **Paper-Suche (crossref, openalex, doaj):** 1 Anfrage, 9 dedupliziert, 5 genannt.
> **Ohne Treffer:** keine.

## Schlusshinweis an die Person (Zugang zum Volltext)

Kurz und sachlich, passend zum Treffertyp:
- **Bücher (OPAC):** über die Signatur in der Campusbibliothek; nicht im
  BHT-Bestand → Fernleihe über das KOBV-Portal.
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
- `search_papers(query, sources="crossref,openalex,doaj", max_results_per_source=5, year=optional)`
- Quellenspezifische `search_*` (z. B. `search_openalex`) für gezielte Einzelabfragen.

Nicht verwenden (Beschaffung): `download_with_fallback`, `download_*`, `read_*`.

## Hinweise

- **Reihenfolge fest:** erst OPAC (subject), dann Paper, dann Synthese.
- **Kein `opac_erweiterte_suche`** – existiert nicht; Mehrfeld-Logik über mehrere
  `opac_suche`-Aufrufe.
- **Instabile/fachfremde Paper-Quellen meiden:** Google Scholar, SSRN, BASE sind
  unzuverlässig; `arxiv`/`pubmed` nur im passenden Fach zuschalten.
