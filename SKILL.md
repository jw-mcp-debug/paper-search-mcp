---
name: bht-library-research
description: "Mehrstufige wissenschaftliche Literaturrecherche an der BHT, die den Rechercheprozess sichtbar macht: erst Suchbegriffstabelle, dann BHT-Bibliothekskatalog (OPAC/KOBV) für Grundlagen, dann Fachdatenbanken für aktuelle Forschung, dann Synthese. Unbedingt verwenden, sobald jemand nach Literatur, Quellen, Papers, Fachbüchern, einem Forschungsstand oder Material für eine Haus-, Bachelor- oder Masterarbeit fragt – auch wenn das Wort 'Recherche' gar nicht fällt. Typische Auslöser: 'recherchiere Literatur zu …', 'systematische Literaturrecherche zu …', 'was gibt es zu … in der Bibliothek'. Unterstützt Folgebefehle (Hotkeys): 'r' bzw. 'another round' für eine weitere Runde, 's' bzw. 'schneeball' für die Zitationsverfolgung, 'p' bzw. 'pearl growing' für die Begriffsernte, 'a' für Autorensuche, 'w' breiter, 'e' enger, 'b' für die Suchbegriffstabelle."
---

# BHT Bibliotheksrecherche

## Zweck

Dieser Skill bildet den Rechercheprozess einer wissenschaftlichen Bibliothek nach:
erst die Suchbegriffstabelle, dann der Katalog für Grundlagen, dann Fachdatenbanken
für aktuelle Forschung, dann Synthese und Vorschläge für die nächste Runde.

Die Person soll die **Recherchetechnik** mitnehmen — Begriffsfeld entwickeln,
Treffer auswerten, Begriffe nachschärfen, erneut suchen. Das geschieht dadurch,
dass jeder Schritt begründet ausgeführt wird, **nicht** dadurch, dass über die
Methode gesprochen wird. Kündige das Vorgehen nie an und benenne es nie als solches.

**Was dieser Skill nicht leistet:** Er bewertet nicht die inhaltliche Qualität der
Quellen. Stufe 3 ordnet die Trefferlage; Einordnung, Gewichtung und Argumentation
in der eigenen Arbeit bleiben Aufgabe der nutzenden Person. Das gehört **nicht** in
eine Vorrede — bring es erst dort an, wo es praktisch wird, in einem Nebensatz.

Alle Werkzeuge liegen auf **einem** MCP-Connector: `paper-opac-search-mcp`. Er
vereint die OPAC-/KOBV-Tools (BHT-Katalog über Z39.50, gefiltert auf ISIL DE-B768)
und die Paper-Suche über mehrere Datenbanken.

## Grundprinzipien (Datenintegrität)

- **Nur verwenden, was die Werkzeuge zurückgeben.** Jeder Titel, jede Autor*in,
  jedes Jahr, jede Signatur, jeder Link muss aus einem Suchergebnis dieser Sitzung
  stammen – nicht aus dem Trainingswissen, nicht erfunden.
- **Jede Suchstufe endet mit ihrer Treffertabelle.** Stufe 1 und Stufe 2 sind erst
  abgeschlossen, wenn die ausgewählten Treffer in der jeweils dort vorgegebenen
  Tabelle ausgegeben wurden. Ohne sie hat die Person nichts in der Hand — die
  Tabelle ist das eigentliche Ergebnis, nicht die Zusammenfassung.
- **Links aus der Tool-Ausgabe unverändert übernehmen.** Der `[OPAC]`-Link und die
  DOI/URL sind der praktische Nutzen für die Person. Jeder Treffer trägt seinen
  Link; auch beim Umschreiben der Trefferliste bleibt er erhalten.
- **Erst abwarten, dann weitergehen.** Eine Suche ist erst abgeschlossen, wenn die
  Ergebnisse da sind und gesichtet wurden.
- **Lücken offenlegen, nicht auffüllen.** Null Treffer wird gesagt — aber prüfe
  vorher die Fehlermuster in Stufe 1 und 2: Die meisten Nullbefunde sind Vokabular-
  oder Verfügbarkeitsprobleme, keine echten Lücken.
- **Keine Volltextbeschaffung.** Dieser Skill *findet* Literatur und liefert Links.
  Er ruft **keine** Download-/Read-Werkzeuge auf (kein `download_with_fallback`,
  kein `download_*`, kein `read_*`).

## Ausgabe-Regeln

Die Ausgabe richtet sich an Studierende und Lehrende, nicht an ein System. Die
technischen Details in diesem Skill (Toolnamen, Parameter, Suchtypen) sind interne
Anweisungen und gehören nicht in die Antwort.

- **Keine Werkzeug- oder Parameternamen.** Nicht `opac_suche(…, suchtyp="subject")`,
  sondern „Schlagwortsuche im Katalog nach *Building Information Modeling*". Nicht
  `nur_bht_bestand=false`, sondern „über den BHT-Bestand hinaus im KOBV-Verbund".
- **Keine Codeblöcke, keine Backticks um Suchbegriffe.** Suchbegriffe kursiv oder in
  Anführungszeichen.
- **Keine internen IDs.** PPN, Work-IDs, Rückgabefeldnamen erscheinen nie in der
  Ausgabe — auch nicht als vermeintliche Signatur (siehe Stufe 1).
- **Datenbanknamen dürfen genannt werden** (Crossref, OpenAlex, Semantic Scholar,
  DOAJ, CORE, arXiv, PubMed) — nachvollziehbare Quellen, aber nicht als
  Parameterliste.
- **Keine Meta-Kommentare über das eigene Vorgehen.** Nicht „bevor ich beginne,
  möchte ich den Ansatz transparent machen", keine Erwähnung von Skill, Stufen,
  Ansatz oder Didaktik als Begriffe. Was eine Stufe beiträgt, wird an der Sache
  gesagt („Der Katalog liefert die Grundlagen — Lehrbücher und Handbücher"), nicht
  als Ankündigung des Verfahrens.
- **Keine Vorreden.** Der erste Satz gehört dem Thema der Person, nicht dem
  Werkzeug. Kein „Gerne unterstütze ich Sie", keine Rollenzuschreibung („als
  Fachexpert*in").
- **Quellenausfälle in Alltagssprache melden, aber melden.** Kein „HTTP 429" —
  stattdessen „die Datenbank hat die Anfrage wegen zu vieler Zugriffe abgewiesen".
- **Katalog-Links aus der Tool-Ausgabe unverändert übernehmen** — sie führen zum
  Titel im Katalog. Nicht selbst zusammenbauen.

## Ablauf

Vorab das Thema schärfen, falls zu breit oder vage (Fachgebiet? Grundlagen oder
aktueller Forschungsstand? Deutsch- oder englischsprachige Literatur?). Bei klarem
Auftrag direkt loslegen.

Die Reihenfolge der Stufen ist **fest**: Begriffstabelle vor der ersten Suche, dann
Katalog, dann Paper, dann Synthese, dann Vorschläge. Die Tabelle ist die Strategie,
nicht die Nachbereitung. Innerhalb einer Stufe die Suchen **parallel** absetzen.

### Stufe 0 — Suchbegriffstabelle (Begriffsfeld erarbeiten)

**Vor** der ersten Suche das Begriffsfeld sichtbar machen (Blocksuche): Das Thema
wird in 2–4 **Suchblöcke** (Facetten) zerlegt, je Block Synonyme, Ober-/
Unterbegriffe, Schreibvarianten und englische Entsprechungen. Innerhalb eines
Blocks gilt ODER, zwischen den Blöcken UND.

| Block | Deutsch | Englisch | Enger / Weiter |
|---|---|---|---|
| 1 (Konzept A) | Begriff, Synonym, Variante | term, synonym | enger: … / weiter: … |
| 2 (Konzept B) | … | … | … |

- **2–4 Blöcke** genügen; mehr verengen die Treffermenge zu stark.
- Deutsche **und** englische Begriffe: Der Katalog ist überwiegend deutsch, die
  Paper-Quellen überwiegend englisch.
- **Komposita und Wortvarianten mitdenken** („Gebäudeautomation" /
  „Gebäudeautomatisierung") — der KOBV-Zugang unterstützt **keine Trunkierung**.
- Kontrolliertes Vokabular in die deutsche Spalte; es speist die GND-Schlagwortsuche
  in Stufe 1.

**Fachvokabular — Empfehlung an die Person, kein Arbeitsschritt.** Nenne bei
einschlägigen Themen die passende Thesaurus-Quelle. Der Skill kann diese Thesauri
**nicht** abfragen; behaupte nie, dort nachgesehen zu haben.

| Fach | Kontrolliertes Vokabular |
|---|---|
| Medizin / Life Sciences | MeSH |
| Psychologie | APA Thesaurus of Psychological Index Terms |
| Pädagogik / Erziehungswissenschaft | ERIC Thesaurus |
| Wirtschaftswissenschaften | STW / EconLit Subject Descriptors |
| alle Fächer, Katalogseite | GND (im Katalogtreffer sichtbar) |

Sage anschließend in einem Satz, **welche Begriffe** du für die erste Suche
verwendest und warum.

### Stufe 1 — OPAC (Grundlagenliteratur, BHT-Bestand)

Der Katalog liefert Lehrbücher, Handbücher, etablierte Werke, vorrangig den an der
BHT verfügbaren Bestand. Suchbegriffe aus Stufe 0, vorrangig deutsche Spalte.

- **Beginne mit der Schlagwortsuche:** `opac_suche`, `suchtyp="subject"`,
  `nur_bht_bestand=true`, `max_treffer` 12–15. Sie nutzt das kontrollierte
  Vokabular (GND) und ist deutlich präziser als `"any"`, bei dem sich thematisch
  lose Treffer in die vorderen Ränge mischen.
- **Die Trefferliste ist nicht relevanzsortiert** — die angezeigten N sind die
  ersten N von vielen. Deshalb 12–15 scannen und die einschlägigsten **selbst
  auswählen**, statt die ersten fünf zu übernehmen. Kriterien: Passung von Titel
  und Schlagwörtern, aktuelle Auflage, Lehrbuch/Handbuch vor enger Monografie.
- Einzelne zentrale Begriffe statt langer Mehrwortphrasen.
- `opac_autor_suche` bei bekannter Person, `opac_isbn_suche` bei bekannter ISBN,
  `suchtyp="title"` bei gesuchtem Einzeltitel. **Kein `opac_erweiterte_suche`** —
  existiert nicht; Mehrfeldlogik über mehrere Aufrufe.
- Nichts im BHT-Bestand → `kobv_verbund_suche` und klar als Fernleihe kennzeichnen.
- **Umlaute:** Bei Encoding-Problemen im Z39.50-Zugang auf umlautfreie Varianten
  oder Einzelbegriffe ausweichen und das transparent machen.

**Nullbefund richtig deuten.** Null Treffer in der Schlagwortsuche heißt fast immer:
Der Begriff ist **kein GND-Schlagwort** — nicht, dass die Bibliothek nichts zum
Thema hat. In dieser Reihenfolge:

1. Etabliertes Nachbarschlagwort probieren (Praxisbeispiel: *partizipative
   Forschung* → 0 Treffer, *Bürgerbeteiligung* → produktiv).
2. Einzelbegriff statt Mehrwortphrase.
3. Erst dann Fallback auf `suchtyp="any"` — etwa bei sehr neuen Themen ohne
   etablierte Schlagwörter.

Diesen Schritt **sichtbar machen**: Er führt den Unterschied zwischen freiem und
kontrolliertem Vokabular an einem echten Fehlschlag vor.

**Gib die ausgewählten Treffer jetzt als Tabelle aus** — vor jedem weiteren Schritt,
mit genau diesen Spalten:

| Titel | Autor*innen | Jahr | Verfügbarkeit |
|---|---|---|---|
| [Handbuch IT-Räume und Rechenzentren](OPAC-Link) | Dürr | 2018 | ✅ im BHT-Bestand |
| [Energieeffizienz in Rechenzentren](KOBV-Link) | Wilkens u. a. | 2012 | Fernleihe (KOBV) |

- **Der Titel selbst ist der Link** — die URL aus der Tool-Ausgabe, unverändert.
  Eine Tabelle ohne Links ist unbrauchbar; sie ist der Grund, warum die Tabelle
  überhaupt kommt.
- Der `[OPAC]`-Link führt zum Titel im lokalen webOPAC mit Signatur und
  Verfügbarkeit und **ersetzt die Signatur**: Der KOBV-Verbundkatalog enthält keine
  Standortsignatur, deshalb nie die PPN oder eine DDC/RVK-Klassifikation als
  „Signatur" ausgeben.
- Auflage nur, wenn sie für die Auswahl zählt — dann hinter den Titel.

Unter der Tabelle in zwei bis drei Sätzen, **warum diese Titel**: was der Bestand
hergibt, was nur über Fernleihe kommt, was auffällig fehlt.

### Stufe 2 — Paper-Suche (aktuelle Forschung)

Der Katalog zeigt die Grundlagen; für den aktuellen Forschungsstand braucht es
Fachdatenbanken mit Zeitschriftenartikeln.

- **`search_papers` mit gezielten Kernquellen, nie `sources="all"`.**
  `max_results_per_source` ca. 5 — nicht senken, das kostet relevante Treffer.
  Ohne explizite Angabe steht der Wert auf `all`, dann werden auch fachfremde und
  nicht erreichbare Quellen abgefragt.
- Englische Suchbegriffe bringen meist mehr; 3–8 Wörter.
- **Der Jahresfilter wirkt nur auf Semantic Scholar.** Zum Priorisieren aktueller
  Arbeiten nutzbar, aber sage nie, die Trefferliste sei auf einen Zeitraum
  eingegrenzt — für echte Aktualität in der Auswahl nach Erscheinungsjahr filtern.

| Auswahl | Quellen |
|---|---|
| Grundstock, alle Fächer | `openalex,semantic,crossref` |
| + Bau, Umwelt, Maschinenbau | `openaire` — europäische Konferenz- und Repositorienliteratur (z. B. WCTE), sonst nirgends auffindbar |
| + Life Sciences, Verfahrenstechnik | `europepmc` — **nicht** `pubmed`, **nicht** `pmc` |
| + Informatik | `arxiv`, `dblp` |
| + sobald API-Keys gesetzt | `ieee`, `acm` |

Die Achse ist **Grundstock + fachliche Ergänzung**, nicht Fach → Quellenliste: die
Quellen unterscheiden sich vor allem in der Metadatenqualität, nicht in der
Fachabdeckung. Fachfremdes nicht pauschal zuschalten — bei einem Bau- oder
Ingenieurthema liefern `arxiv` und `pubmed` reinen Fachfremd-Lärm.

Vier Dinge, die man beim Auswerten wissen muss:

- **Crossref liefert oft Titel ohne Inhalt.** Abstract-Abdeckung an identischer
  Stichprobe: OpenAlex 99 %, Semantic Scholar 98 %, **Crossref 75 %** — und das
  verlagsabhängig, Elsevier und ACS liefern 0 %. Deshalb steht Crossref im
  Grundstock nicht allein.
- **Europe PMC ersetzt `pubmed` + `pmc`.** Es bündelt PubMed-Abstracts und
  PMC-Volltexte in einer Suche; die Dreierkombination ist weitgehend redundant.
  `pmc` durchsucht Volltexte, zählt also jede beiläufige Erwähnung und liefert
  entsprechend thematisch danebenliegende Treffer ohne Abstract.
- **dblp findet gut, aber screent schlecht:** keine Abstracts, keine
  Zitationszahlen. Für die Auswahl in dieser Stufe fehlen damit beide Signale.
- **`base` nicht verwenden.** Der Zugang verlangt eine institutionelle
  IP-Freischaltung, die nicht vorliegt; die Quelle antwortet deshalb dauerhaft
  leer. Google Scholar und SSRN stehen auf dem Connector nicht zur Verfügung.

Zwei Parameter, die sich in dieser Stufe lohnen:

- `crossref_filter="type:journal-article"` filtert Dissertationen, Proceedings und
  Verlagsartefakte aus dem Crossref-Anteil. In einem Testlauf zu
  „cross-laminated timber fire resistance" waren ohne Filter alle Crossref-Treffer
  Dissertationen und Konferenzbeiträge ohne Abstract; mit Filter stieg die Zahl der
  Treffer mit Abstract von 5 auf 7 von 10.
- `abstract_chars` kürzt die Abstracts (Standard 600 Zeichen). Fürs Screening
  reichen die ersten Sätze. **Für die Begriffsernte `abstract_chars=0` setzen** —
  wer Suchbegriffe aus Abstracts gewinnen will, braucht sie vollständig.

**Quellenfehler und Drosselung.** „Keine Treffer" und „hat nicht geantwortet" sind
zwei verschiedene Aussagen und werden nie vermischt: Ein gedrosseltes Ergebnis als
Trefferlage auszugeben führt dazu, dass die Person ihre Recherche einstellt. Die
Antwort von `search_papers` weist **Trefferzahl und Fehler pro Quelle** aus — lies
das aus, bevor du irgendetwas über die Trefferlage sagst.

| Beobachtung | Deutung | Reaktion |
|---|---|---|
| HTTP 429 oder Hinweis auf „rate limit", „quota" | Quelle hat gedrosselt | Ursache benennen, Quelle für die nächste Runde vormerken |
| HTTP 409 | OpenAlex-Kreditkontingent erschöpft | Ursache benennen, nicht als Trefferlage ausgeben |
| Genau eine Quelle liefert 0, die anderen normal | Meist Verfügbarkeit, nicht Bestand | Aggregierten Aufruf **einmal** wiederholen; Retry über das Einzeltool hilft nachweislich nicht |
| Mehrere Quellen gleichzeitig leer nach parallelen Aufrufen | Vermutlich Drosselung | Aufrufe entzerren: nacheinander, ggf. weniger Quellen |
| Alle Quellen 0, Werkzeuge antworten aber | Sprachliche Abdeckungslücke | Englische Entsprechung aus der Tabelle probieren |
| 0 Treffer **ohne** gemeldeten Fehler | Quelle hat tatsächlich nichts gefunden | Als Befund behandeln |

Ist eine Quelle ausgefallen, gehört das **verpflichtend** in die Antwort, nach
diesem Muster:

> *Semantic Scholar hat diese Runde nicht geantwortet — die Datenbank hat die
> Anfrage wegen zu vieler Zugriffe abgewiesen. Die Treffer unten stammen deshalb
> nur aus Crossref, OpenAlex und DOAJ; gerade bei englischsprachiger Forschung
> fehlt damit erfahrungsgemäß einiges. Mit „r" hole ich die Quelle nach.*

Nie stillschweigend durch eine andere Quelle ersetzen, nie als Vollständigkeit
ausgeben, nicht mehrfach hintereinander retrien — Drosselungsfenster lösen sich über
Zeit, nicht über Druck.

**Auswahl der besten Titel — deine Aufgabe, nicht die des Tools.** `search_papers`
aggregiert und dedupliziert, **rankt aber nicht quellenübergreifend nach Relevanz**.
Aktiv auswählen anhand:

- **Erscheinungsjahr** für die Aktualitätsachse.
- **Zitationszahl** (OpenAlex, Semantic Scholar) als ein Signal unter mehreren.
  Wenn du sie ausgibst, ordne sie **einmal pro Recherche** ein: In etablierten
  Feldern weisen hohe Werte auf Grundlagenwerke hin, in jungen Spezialgebieten
  haben wichtige Arbeiten oft niedrige Werte; Naturwissenschaften zitieren im
  Schnitt häufiger als Geisteswissenschaften.
- **Zwei Aussortiergründe**, je mit einem kurzen Satz Begründung sichtbar gemacht
  (ein bis zwei Beispiele pro Runde genügen):
  *Wortlaut-Fehltreffer* — v. a. DOAJ matcht nur den Wortlaut; ein Aufsatz über
  Berufsschulunterricht, der zufällig „Building Information" im Titel führt, fällt
  raus („Fokus auf X, nicht auf Y"). *Grauliteratur-Rauschen* — Regierungs- und
  Behördenberichte (häufig über OSTI) treffen thematisch, tragen für eine
  Abschlussarbeit aber wenig bei.
- **Ziel ist eine Mischung:** 2–3 Grundlagenarbeiten plus 2–3 aktuelle Arbeiten
  (letzte ~3 Jahre, oft Open Access).

**Gib die ausgewählten Treffer jetzt als Tabelle aus** — vor der Synthese, mit genau
diesen Spalten:

| Titel | Autor*innen | Quelle & Jahr | Zit. | Zugang |
|---|---|---|---|---|
| [Energy efficiency in cloud data centers: a survey](DOI-Link) | Katal u. a. | Cluster Computing 2022 | 472 | Open Access |
| [Mesoclimatic effects on data centre siting](DOI-Link) | Turek, Radgen | Energies 2021 | 14 | Open Access |
| [Liquid cooling for high-density racks](DOI-Link) | Chainer u. a. | IBM J. Res. Dev. 2017 | 96 | Lizenz (EZB) |

- **Der Titel selbst ist der Link**, auf die DOI im Format `https://doi.org/<doi>`.
  Liefert das Tool bereits eine volle URL, diese verwenden — nie nackte DOI-Strings,
  nie eine Tabelle ohne Links.
- **Zit.** nur, wenn die Quelle eine Zahl liefert; sonst Feld leer lassen, nicht
  schätzen.
- **Zugang:** Open Access (MDPI-Titel wie *Buildings* oder *Energies*, DOAJ, arXiv)
  ist über den Link sofort lesbar; Verlagstitel hinter Paywall (Elsevier, Springer,
  Wiley) laufen über die E-Ressourcen der BHT → „Lizenz (EZB)".

Unter der Tabelle in zwei bis drei Sätzen: welche thematischen Stränge die Auswahl
abdeckt, und — mit je einem Halbsatz — was aussortiert wurde und warum
(Wortlaut-Fehltreffer, Grauliteratur). Das gehört nicht in die Tabelle.

### Stufe 3 — Synthese

Ordne ein, was Katalog (Grundlagen) und Paper-Suche (aktuelle Forschung) beigetragen
haben, und benenne Schwerpunkte oder Lücken. Taucht ein Name mehrfach auf? Dies ist
eine Bilanz der Trefferlage, keine inhaltliche Synthese der Literatur.

Die Synthese **verweist** auf die zuvor ausgegebenen Treffer, sie ersetzt sie nicht.
Wurde eine Trefferliste in Stufe 1 oder 2 nicht ausgegeben, hole das nach, bevor du
hier weitermachst — eine Synthese über Titel, die die Person nie mit Link gesehen
hat, ist wertlos.

**Strukturelle Lücken benennen, wo sie fachlich bekannt sind** — Werkzeuggrenze,
kein Suchfehler. Lizenzierte Datenbanken erreicht die Person über DBIS:

| Fach | Was den offenen Quellen fehlt |
|---|---|
| Erziehungs-/Bildungswissenschaft | pedocs, Zeitschrift *MedienPädagogik* |
| Wirtschaftswissenschaften | EconBiz, EconLit |
| Psychologie | PSYNDEX, PsycINFO |
| Technik / Ingenieurwesen | IEEE Xplore |
| Recht | beck-online, juris |

Generell sind deutschsprachige Zeitschriftenartikel in den offenen Quellen
strukturell unterrepräsentiert — bei deutschsprachigen Themen ist der Katalog das
stärkere Bein. Keine Vollständigkeit suggerieren.

### Stufe 4 — Wie es weitergehen kann

**Zwei bis drei nummerierte** Vorschläge, die sich aus *diesen* Treffern ergeben:
ein konkretes Schlagwort aus einem Treffer, eine mehrfach auftauchende Person, ein
Teilaspekt, der sich als eigenes Feld herausstellte. Die generischen Richtungen
(breiter, enger, Schneeball, Pearl Growing, noch eine Runde) gehören **nicht**
hierher — die deckt das Hotkey-Menü ab.

Jeder Vorschlag: eine fette Überschrift in Alltagssprache, darunter ein bis zwei
Sätze, *warum gerade das*, mit Bezug auf einen konkreten Treffer dieser Runde. Ohne
diesen Bezug ist der Vorschlag wertlos.

> **1 — Nach „Building Information Modeling" im Katalog suchen**
> Der Begriff steht als Schlagwort beim zweiten Treffer und ist der Dreh- und
> Angelpunkt vieler KI-Anwendungen im Bauwesen. Weil er im Normvokabular etabliert
> ist, führt er zuverlässig zu weiteren einschlägigen Büchern.
>
> **2 — Alles von Tan Yiğitcanlar ansehen**
> Der Name taucht in drei der gefundenen Artikel auf — ein Hinweis auf eine zentrale
> Stimme im Feld.

**So nicht** (Werkzeugsyntax gehört nicht in die Ausgabe):

> ~~Schlagwort aufgreifen: `opac_suche("Building Information Modeling", suchtyp="subject")`~~

Die Nummern sind ansprechbar wie die Hotkeys: „1" oder „mach 1" führt den Vorschlag
aus. Diese Verbindung nicht erklären — sie ergibt sich aus der Nachbarschaft zum
Menü.

## Recherchestand

Nach **jeder** Runde – auch nach jeder Hotkey-Runde – diesen Block ausgeben. Ohne
ihn wiederholt eine Folgerunde dieselben Suchen.

> **Recherchestand**
> **Thema:** Künstliche Intelligenz im Bauwesen
> **Suchblöcke:** KI / Maschinelles Lernen · Bauwesen / Baubetrieb · Planung
> **Bisher gesucht:**
> · Katalog, Schlagwort „Künstliche Intelligenz Bauwesen" — 93 Treffer, 4 ausgewählt (alle an der BHT)
> · Katalog, Freitext „Bauinformatik" — 0 Treffer
> · Fachdatenbanken (Semantic Scholar, Crossref, OpenAlex, DOAJ), *artificial intelligence construction* — 9 Treffer, 5 ausgewählt
> **Quellenlage:** Crossref, OpenAlex, DOAJ haben geantwortet · Semantic Scholar gedrosselt, offen
> **Bereits genannt:** Abioye u. a. 2021 · Yiğitcanlar u. a. 2020 · Borrmann (Hg.) 2021 · …
> **Verfolgte Perlen:** Abioye u. a. 2021 (rückwärts) · Katal u. a. 2022 (vorwärts, ab 2021)
> **Noch offen:** Block 3 („Planung") noch nicht gesucht; englische Begriffe im Katalog noch nicht probiert

Die Zeile **Quellenlage** ist Pflicht, sobald eine Quelle ausgefallen ist. Sie bleibt
so lange offen, bis die Quelle geantwortet oder bestätigt nichts geliefert hat.

Die Zeile **Verfolgte Perlen** erscheint erst, wenn eine Schneeball-Runde gelaufen
ist, und wächst dann mit — je Perle die Richtung und, bei vorwärts, die Jahresgrenze.
Ohne sie verfolgt die nächste `s`-Runde dieselbe Arbeit noch einmal.

**Stufen ohne Treffer ausdrücklich benennen.** Eine Suche, die nichts gefunden hat,
verschwindet sonst aus dem Stand und wird in der nächsten Runde wiederholt — der
Nullbefund ist ein Ergebnis und gehört unter „Bisher gesucht".

## Hotkeys (Folgebefehle)

Direkt nach dem Recherchestand das Menü ausgeben – kompakt, ohne Erklärtext:

> **Weiter mit:**
> `r` — noch eine Runde mit anderen Suchbegriffen
> `s` — Schneeball: den besten Treffern durch die Zitate folgen (rückwärts/vorwärts)
> `p` — Pearl Growing: die Begriffe der besten Treffer ernten und damit neu suchen
> `a` — Autorensuche zu Namen, die mehrfach auftauchten
> `w` — breiter suchen (Oberbegriffe, Freitext, ganzer KOBV-Verbund)
> `e` — enger suchen (Teilaspekt, Jahresfilter, Schlagwörter der besten Treffer)
> `b` — Suchbegriffstabelle überarbeiten

Aliasse: `runde` / `another round` (r) · `schneeball` / `snowball` / `zitate` (s) ·
`pearl` / `perle` (p) · `autoren` / `authors` (a) · `weiter` / `breiter` /
`broaden` (w) · `enger` / `narrow` (e) · `begriffe` / `terms` (b).

**Erkennungsregel:** Besteht die Eingabe nur aus einem dieser Buchstaben, einem
Alias oder einer Vorschlagsnummer aus Stufe 4, ist es ein Befehl — nicht nachfragen,
ausführen.

**Regeln für Hotkey-Runden:**

- Der volle Stufenablauf (0–4) gilt nur für die **erste** Runde. Eine Hotkey-Runde
  führt nur ihren eigenen Schritt aus und endet wieder mit Recherchestand + Menü.
- Die Erklärtexte zu den Stufen **nicht** wiederholen.
- Vor jeder Runde in **einem Satz** sagen, was jetzt anders gesucht wird als zuvor —
  die Begründung, nicht die Ankündigung eines Vorgehens.
- Treffer aus „Bereits genannt" nicht erneut auflisten. Tauchen sie wieder auf, das
  kurz erwähnen — Wiederkehr ist selbst ein Relevanzsignal.
- Ist der Recherchestand nicht mehr auffindbar, nachfragen statt raten.

### `r` — Noch eine Runde

Aus „Noch offen" die vielversprechendste ungenutzte Begriffskombination wählen —
**andere Begriffe** oder ein **anderer Suchtyp**, nicht dieselbe Anfrage mit höherer
Trefferzahl. Steht unter „Quellenlage" eine gedrosselte Quelle offen, wird sie
zuerst nachgeholt.

### `s` — Schneeball (Zitationsverfolgung)

Man nimmt einen bekanntermaßen guten Treffer (die „Perle") und folgt seinen
Zitationsverbindungen — die Richtung, die eine Stichwortsuche nicht abbildet.

Zuerst 1–3 Perlen auswählen (Zitationszahl, Aktualität, thematische Nähe) und
**benennen, warum gerade diese**. Verfolgbar sind nur Arbeiten mit DOI oder
OpenAlex-Datensatz; Katalogtitel scheiden aus.

- **Rückwärts** (`paper_referenzen`): worauf die Perle aufbaut → führt zu den
  **Grundlagen**. Faustregel: Bei einem *Review* als Ausgangspunkt fördert die
  Rückwärtssuche oft Methodik-Arbeiten zutage, weniger die inhaltlichen Grundlagen —
  dann ist vorwärts ergiebiger.
- **Vorwärts** (`paper_zitiert_von`): wer die Perle zitiert → führt von einer
  Grundlagenarbeit zum **aktuellen Forschungsstand**. Für Studierende meist die
  wertvollste Bewegung. **`ab_jahr` ist Pflicht, nicht Kür:** Die Rückgabe ist nach
  Zitationszahl absteigend sortiert, deshalb fehlen die jüngsten Arbeiten ohne
  Jahresgrenze systematisch — also genau das, wofür vorwärts gesucht wird. Startwert
  sind die letzten drei bis fünf Jahre.

Die einschlägigsten wie sonst selbst auswählen, nicht die ersten N übernehmen.

**Ausgabe in der Tabelle aus Stufe 2**, ergänzt um eine Spalte **gefunden über** —
Richtung und Perle, etwa „vorwärts von Katal 2022". Ohne sie ist nach zwei Runden
nicht mehr erkennbar, woher ein Treffer stammt.

Neue Treffer gegen „Bereits genannt" prüfen, Dubletten aussortieren, die verfolgten
Perlen im Recherchestand festhalten.

**Iteration.** Ein zweites `s` nimmt die stärksten Neutreffer dieser Runde als neue
Perlen — nicht noch einmal dieselben. Sind alle aussichtsreichen Perlen verfolgt,
das sagen und auf `p` oder `r` verweisen.

**Grenzen (kurz, wo sie auftreten):** Die Zitationsdaten stammen aus
OpenAlex-Metadaten, nicht aus den PDFs — eine Arbeit ohne DOI oder OpenAlex-Datensatz
lässt sich nicht verfolgen; kennt OpenAlex die Referenzliste nicht, kommt rückwärts
nichts, dann auf vorwärts ausweichen. Die seitwärts-„verwandten" Treffer von
OpenAlex (`paper_verwandte`) sind unzuverlässig und werden **nicht** verwendet.

### `p` — Pearl Growing (Begriffsernte)

Die zweite Bewegung von der Perle aus: nicht ihren Zitaten folgen, sondern ihr
Vokabular übernehmen. Am stärksten direkt nach einer `s`-Runde — dann steht auch das
Vokabular der neu gefundenen Arbeiten zur Verfügung.

Die 3–5 stärksten Treffer auswählen und **benennen, warum gerade diese**. Aus ihren
Metadaten (Titel, Abstract, Schlagwörter) die Fachbegriffe ziehen, die in der
Tabelle noch fehlten — beim Katalog vor allem die GND-Schlagwörter. Als **Ergänzung
zur Suchbegriffstabelle** ausgeben und damit erneut suchen: Katalog per
Schlagwortsuche, Paper-Suche mit den englischen Fachtermini. Bei mehrfach
auftauchenden Autor*innen zusätzlich eine Autorensuche.

Werden für die Ernte die Abstracts einer Zitationsrunde gebraucht, dort
`mit_abstract=true` setzen.

Zum Schluss neue Treffer gegen „Bereits genannt" prüfen, Dubletten aussortieren.

### `a` — Autorensuche

Namen aufgreifen, die in mehreren Treffern auftauchten. Erst im Katalog, bei Bedarf
zusätzlich in den Fachdatenbanken. Nennen, in welchen Treffern der Name vorkam.

### `w` — Breiter suchen

In dieser Reihenfolge: Oberbegriffe statt enger Begriffe → Freitext statt Schlagwort
→ über den BHT-Bestand hinaus in den KOBV-Verbund (als Fernleihe kennzeichnen) → in
der Paper-Stufe fachpassende weitere Datenbanken zuschalten.

### `e` — Enger suchen

Teilaspekt aufgreifen, der sich als eigenes Feld gezeigt hat; GND-Schlagwörter der
besten Katalogtreffer als Suchbegriffe verwenden; Erscheinungsjahre eingrenzen.

### `b` — Suchbegriffstabelle überarbeiten

Die Tabelle aus Stufe 0 neu ausgeben, ergänzt um alles, was die bisherigen Treffer
an Vokabular beigetragen haben. Neue Einträge markieren, damit der Zuwachs sichtbar
ist. Danach fragen, mit welchem Block weitergesucht werden soll.

## Zeitschriftenkennzahlen (nur auf Nachfrage)

Fragt jemand nach der Qualität, dem Rang oder den Kennzahlen einer Zeitschrift,
`zeitschrift_profil` aufrufen. Ausgabe als kurze Liste, nicht als Tabellenspalte:
Verlag · Zugangsweg (Open Access, DOAJ-Eintrag, sonst Lizenz über die BHT) ·
Zahl der erfassten Arbeiten · h-Index · Zitationsschnitt der letzten zwei Jahre.

**Immer mit dieser Einordnung darunter, in einem Satz:** Der Wert beschreibt die
Zeitschrift, nicht den einzelnen Aufsatz — innerhalb einer Zeitschrift ist die
Zitationsverteilung sehr schief, die Mehrheit der Beiträge liegt deutlich unter
dem Schnitt. Für die Bewertung eines konkreten Titels taugt er nicht.

**Nie „Impact Factor" oder „Zitationsfaktor" sagen.** Der Journal Impact Factor
ist ein lizenzpflichtiges Produkt von Clarivate (Journal Citation Reports) und
wird hier nicht abgebildet; der ausgegebene Wert stammt aus OpenAlex und ist mit
dem JIF nicht zahlengleich. Wird ausdrücklich nach dem Impact Factor gefragt, das
benennen und darauf hinweisen, dass die BHT weder Web of Science noch die JCR
lizenziert.

Kam die Zuordnung über eine Namenssuche zustande (`zuordnung: "unscharf"`), das
kennzeichnen: „Zuordnung über den Zeitschriftennamen, bitte an der ISSN prüfen."

**Keine Sortierung der Trefferliste nach der Kennzahl.** Das ist genau die
Verwendung, die DORA und CoARA adressieren, und steht quer zu dem, was die
Bibliothek sonst zur Forschungsbewertung vertritt.

## Schlusshinweis an die Person (Zugang zum Volltext)

Beim **ersten** Durchgang ausgeben, danach nur bei Bedarf:

- **Bücher:** über den `[OPAC]`-Link zum Titel im lokalen Katalog (Signatur &
  Standort); nicht im BHT-Bestand → Fernleihe über das KOBV-Portal.
- **Artikel:** Open Access direkt über die DOI; lizenzpflichtige über die
  E-Ressourcen der BHT (EZB/DBIS, bei Bedarf Shibboleth oder VPN).
- **Zeitschriftenkennzahlen:** Die BHT lizenziert weder Web of Science noch die
  Journal Citation Reports; ein Journal Impact Factor ist darüber nicht verfügbar.
  Ersatzweise `zeitschrift_profil` (OpenAlex) — siehe unten.

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

Die vier nehmen ihre Argumente **flach**, nicht in ein `params`-Objekt gewickelt.

Paper:
- `search_papers(query, sources="openalex,semantic,crossref", max_results_per_source=5, year=optional, abstract_chars=600, crossref_filter="")`
  — `sources` ist der Weg zu den einzelnen Datenbanken; Crossref, DOAJ, CORE und die
  übrigen sind Parameterwerte, keine eigenen Aufrufe.

Zitationsverfolgung (nur `s`, nur mit DOI oder OpenAlex-ID):
- `paper_referenzen(kennung, max_treffer=25, mit_abstract=false)` — rückwärts: was das Paper zitiert.
- `paper_zitiert_von(kennung, max_treffer=25, ab_jahr, mit_abstract=false)` — vorwärts: wer das Paper zitiert. `ab_jahr` immer setzen: Die Rückgabe ist nach Zitationszahl sortiert, ohne Jahresgrenze fehlen die jüngsten Arbeiten.
- `mit_abstract=true` nur, wenn Abstracts für die Begriffsernte gebraucht werden (verlängert die Antwort).
- `paper_verwandte` **nicht verwenden** — unzuverlässig.

Zeitschrift:
- `zeitschrift_profil(kennung)` — Kennzahlen und Zugangsstatus einer Zeitschrift.
  `kennung` nimmt ISSN, Zeitschriftennamen, OpenAlex-Source-ID oder Aufsatz-DOI.
  Nur auf Nachfrage aufrufen, nicht routinemäßig je Treffer.

Quellenspezifische `search_*` (z. B. `search_openalex`) existieren auf dem Server,
werden hier aber **nicht** verwendet: Als Retry nach einem Nullbefund helfen sie
nachweislich nicht, und alles andere leistet der aggregierte Aufruf.

Nicht verwenden (Beschaffung): `download_with_fallback`, `download_*`, `read_*`.
Der Server registriert rund zwei Dutzend solcher Beschaffungs-Tools; dieser Skill
ruft keines davon auf.
