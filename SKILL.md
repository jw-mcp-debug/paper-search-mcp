---
name: agentische-recherche
description: "Mehrstufige wissenschaftliche Literaturrecherche an der BHT, die den Rechercheprozess sichtbar macht: erst Suchbegriffstabelle, dann BHT-Bibliothekskatalog (OPAC/KOBV) für Grundlagen, dann Fachdatenbanken für aktuelle Forschung, dann Synthese. Unbedingt verwenden, sobald jemand nach Literatur, Quellen, Papers, Fachbüchern, einem Forschungsstand oder Material für eine Haus-, Bachelor- oder Masterarbeit fragt – auch wenn das Wort 'Recherche' gar nicht fällt. Typische Auslöser: 'recherchiere Literatur zu …', 'systematische Literaturrecherche zu …', 'was gibt es zu … in der Bibliothek'. Unterstützt Folgebefehle (Hotkeys): 'r' bzw. 'another round' für die nächste Suchrunde in Katalog und Fachdatenbanken, 'p' bzw. 'pearl' für die Begriffsernte aus den besten Treffern, 's' bzw. 'schneeball' für die Zitationsverfolgung rückwärts und vorwärts, 'a' für Autorensuche, 'w' breiter."
user-invocable: true
# Bewusst nur die Tools, die dieser Skill aufruft. Crossref, Semantic Scholar,
# CORE und die übrigen Quellen brauchen KEINEN eigenen Eintrag: Sie sind Werte
# des sources-Parameters von search_papers, keine eigenen Aufrufe.
# Die quellenspezifischen search_*-Tools bitte nicht wieder aufnehmen — der Skill
# rät in Stufe 2 ausdrücklich davon ab, sie als Retry nach einem Nullbefund zu
# verwenden, und die Allowlist ist die einzige harte Durchsetzung dieser Regel.
# search_unpaywall ist die eine Ausnahme und trotz des Namens kein Suchwerkzeug:
# Es schlägt zu einer bekannten DOI den Open-Access-Status nach und ersetzt damit
# das Raten am Verlagsnamen (Stufe 2, Spalte „Zugang"). Als Trefferquelle bleibt
# es verboten.
# get_crossref_paper_by_doi: Gegenprobe für OpenAIRE-DOIs (Grundprinzipien).
# paper_referenzen/paper_zitiert_von: Zitationsverfolgung im s-Hotkey.
# paper_verwandte bewusst NICHT gelistet — unzuverlässig (siehe p).
# zeitschrift_profil: Kennzahlen einer Zeitschrift, nur auf Nachfrage.
allowed-tools:
  - opac_suche
  - opac_autor_suche
  - opac_isbn_suche
  - kobv_verbund_suche
  - search_papers
  - search_unpaywall
  - get_crossref_paper_by_doi
  - paper_referenzen
  - paper_zitiert_von
  - zeitschrift_profil
---

# Agentische Recherche (BHT Campusbibliothek)

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
  abgeschlossen, wenn die ausgewählten Treffer in der dort vorgegebenen Tabelle
  ausgegeben wurden. Ohne sie hat die Person nichts in der Hand — die Tabelle ist
  das Ergebnis, nicht die Zusammenfassung.
- **Links aus der Tool-Ausgabe unverändert übernehmen.** Jeder genannte Treffer
  trägt seinen Link; auch beim Umschreiben bleibt er erhalten, und interne IDs
  (PPN) ersetzen ihn nie.
- **Lücken offenlegen, nicht auffüllen.** Null Treffer wird gesagt — aber prüfe
  vorher die Fehlermuster in Stufe 1 und 2: Die meisten Nullbefunde sind Vokabular-
  oder Verfügbarkeitsprobleme, keine echten Lücken.
- **OpenAIRE-DOIs gegenprüfen.** OpenAIRE verschmilzt beim eigenen Dedup
  gelegentlich zwei Werke zu einem Datensatz: DOI, URL und Autor*innen können dann
  zu drei verschiedenen Arbeiten gehören. Deshalb: Stammt ein Treffer, den du in
  eine Tabelle aufnimmst, aus `openaire` und trägt er eine DOI, rufe
  `get_crossref_paper_by_doi` mit dieser DOI auf und vergleiche den Titel mit dem
  der Trefferzeile. Weichen sie voneinander ab, nimm den Treffer nicht auf. Nur für
  Zeilen, die tatsächlich in die Tabelle kommen — nicht für die ganze Trefferliste.
  (Upstream-Problem, im Server nicht behebbar.)
- **Keine Volltextbeschaffung.** Dieser Skill *findet* Literatur und liefert Links.
  Er ruft **keine** Download-/Read-Werkzeuge auf (kein `download_*`, kein `read_*`).

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
- **Datenbanknamen als Quellenzeile nennen** (Crossref, OpenAlex, Semantic Scholar,
  DOAJ, CORE, arXiv, PubMed, BHT-webOPAC, KOBV) — verpflichtend direkt unter jeder
  Trefferliste, nicht als Parameterliste. Grund: Lizenzpflicht aus dem Semantic
  Scholar API License Agreement (§4 Attribution), auf die übrigen Quellen
  ausgeweitet, damit die Regel einheitlich gilt.
- **Keine Meta-Kommentare über das eigene Vorgehen.** Kein „bevor ich beginne,
  möchte ich den Ansatz transparent machen", keine Erwähnung von Skill, Stufen,
  Ansatz oder Didaktik als Begriffe. Was eine Stufe beiträgt, wird an der Sache
  gesagt („Der Katalog liefert die Grundlagen — Lehrbücher und Handbücher"), nicht
  als Ankündigung des Verfahrens.
- **Keine Vorreden.** Der erste Satz gehört dem Thema der Person, nicht dem
  Werkzeug. Kein „Gerne unterstütze ich Sie", keine Rollenzuschreibung.
- **Quellenausfälle in Alltagssprache melden, aber melden.** Kein „HTTP 429" —
  stattdessen „die Datenbank hat die Anfrage wegen zu vieler Zugriffe abgewiesen".
- **Katalog-Links nach Herkunft bilden**, in dieser Reihenfolge:
  1. Trägt der Treffer einen **Volltextlink**, ist das der Link.
  2. Sonst, bei einem Treffer aus `opac_suche` mit `nur_bht_bestand=true`, den
     `[OPAC]`-Link aus der Ausgabe übernehmen.
  3. Sonst — Verbundtreffer ohne Volltext — den BHT-webOPAC-Link **verwerfen** (für
     einen Titel, den die BHT nicht hat, führt er ins Leere) und den Titel
     URL-kodiert in den KOBV-Portal-Endpunkt einsetzen:
     `https://portal.kobv.de/KobvIndex/Results?lookfor={titel}&type=AllFields&limit=10`.

## Ablauf

**Nachfragen nur in zwei Fällen:** Aus dem Auftrag ist kein Fachgebiet erkennbar,
oder es lassen sich keine zwei Suchblöcke bilden. Dann genau eine Rückfrage stellen
(Fachgebiet? Grundlagen oder aktueller Forschungsstand? Deutsch- oder
englischsprachige Literatur?) und die Antwort abwarten. In jedem anderen Fall ohne
Rückfrage beginnen: Eine Rückfrage hält die gesamte Recherche an, und ein zu breites
Thema lässt sich an der ersten Trefferlage besser einengen als an einer Vermutung
vorab.

Die Reihenfolge der Stufen ist **fest**: Begriffstabelle vor der ersten Suche, dann
Katalog, dann Paper, dann Synthese, dann Vorschläge. Die Tabelle ist die Strategie,
nicht die Nachbereitung. Innerhalb einer Stufe die Suchen **parallel** absetzen.

### Stufe 0 — Suchbegriffstabelle (Begriffsfeld erarbeiten)

**Vor** der ersten Suche das Begriffsfeld sichtbar machen: Das Thema wird in 2–4
**Suchblöcke** (Facetten) zerlegt, je Block Synonyme, Ober-/Unterbegriffe,
Schreibvarianten und englische Entsprechungen. Innerhalb eines Blocks gilt ODER,
zwischen den Blöcken UND — genau so nimmt der Katalog die Anfrage in Stufe 1
entgegen.

| Block | Deutsch | Englisch | Enger / Weiter |
|---|---|---|---|
| 1 (Konzept A) | Begriff, Synonym, Variante | term, synonym | enger: … / weiter: … |
| 2 (Konzept B) | … | … | … |

- **2–4 Blöcke** genügen; mehr verengen die Treffermenge zu stark.
- Deutsche **und** englische Begriffe: Der Katalog ist überwiegend deutsch, die
  Paper-Quellen überwiegend englisch.
- **Komposita und Wortvarianten mitdenken** („Gebäudeautomation" /
  „Gebäudeautomatisierung") — der Katalog kann keine Trunkierung (siehe Stufe 1).
- Kontrolliertes Vokabular in die deutsche Spalte. Fachtermini, die im Deutschen
  unübersetzt bleiben („Gamification", „Building Information Modeling"), gehören in
  **beide** Spalten. Welchen Katalogzugriff die Tabelle bekommt, entscheidet Stufe 1
  an der Trefferlage — hier nur sammeln, nicht vorsortieren.
- **Block 1 ist das spezifischste Konzept, Block 2 der Kontext.** Mit diesen beiden
  sucht Stufe 1; mehr als zwei Konzepte nimmt der Katalog nicht an. Weitere Blöcke
  sind Reserve: Sie gehören in den Recherchestand unter „Noch offen" und kommen in
  einer `r`-Runde dran. Ohne diese Festlegung greift jede Runde zu anderen zwei
  Blöcken, und die Trefferlagen sind nicht mehr vergleichbar.

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

**Ziel:** die Grundlagen zum Thema aus dem BHT-Bestand — Lehrbücher, Handbücher,
etablierte Werke — als Tabelle mit Bestandsangabe und Link.

**Fertig, wenn** ein Aufruf keinen Titel mehr bringt, den du in die Tabelle aufnehmen
würdest. Wie viele Aufrufe das braucht, entscheidet die Trefferlage: Ein Thema mit
einem etablierten Schlagwort ist nach zwei Aufrufen erledigt, ein interdisziplinäres
nach acht. Nicht früher aufhören, weil die ersten Treffer brauchbar aussahen, und
nicht weitersuchen, weil sich noch eine Variante bilden ließe.

#### Verfahren

**1 — Sondieren.** Zwei Aufrufe parallel, mit Block 1 aus Stufe 0, jeweils
`max_treffer=15`, `nur_bht_bestand=true`:

    opac_suche(begriff,                    suchtyp="subject")
    opac_suche(begriff OR Schreibvarianten, suchtyp="title")

Nicht vorab entscheiden, welcher Zugriff der richtige ist. Das hängt daran, ob der
Begriff in der GND angesetzt ist — und das steht erst nach dem Aufruf fest.

**2 — Zugriff festlegen.** Die erste zutreffende Zeile gilt für den Rest der Stufe:

| Beobachtung | Zugriff |
|---|---|
| `subject` = 0 Treffer | Nachbarschlagwort probieren (siehe „Wenn nichts kommt"), sonst `"any"` |
| `title` liefert mindestens die Hälfte mehr als `subject` | `"title"` |
| die Titeltreffer teilen keine Schlagwörter mit dem Konzept | Begriff ist generisch: verwerfen, engeren Begriff aus Stufe 0 nehmen |
| sonst | `"subject"` |

**3 — Zweites Konzept anhängen** (Block 2 aus Stufe 0), als Blocksuche in **einer**
Anfrage: `;` trennt die Konzepte (UND), ` OR ` deren Synonyme (ODER),
Anführungszeichen erzwingen eine Phrase.

    KI OR "Künstliche Intelligenz"; Bildung OR Unterricht OR Hochschule

- **Nie mehr als zwei Konzepte.** Der Katalog kennt kein Relevanzranking und
  verknüpft alle Wörter mit UND — jedes weitere Wort ist ein harter Filter. Synonyme
  dagegen kosten nichts: Sie vergrößern die Treffermenge und gehören per ` OR ` in
  denselben Block, deutsche und englische Fassung zusammen.
- **Nie zwei Konzepte in `"any"`.** Dort trifft der UND-Filter einen
  metadatenarmen Datensatz, in dem zwei Konzepte fast nie zusammenkommen. Die
  Blocksuche gehört in `"subject"` und `"title"`; bei `"any"` ein Konzept pro
  Anfrage.
- **Unter drei Treffern die Kombination verwerfen** und beide Konzepte einzeln
  suchen, die Schnittmenge beim Lesen bilden. Eine Kombination mit einem einzigen
  Treffer ist kein Befund über den Bestand, sondern einer über die Anfrage.
- **Keine Trunkierung.** `*` und `?` liest der Katalog als Wortbestandteil;
  Wortformen per ` OR ` ausschreiben (`Bildung OR Bildungsforschung`).

**4 — Verbund.** Bleiben weniger als vier Titel aus dem BHT-Bestand:
`kobv_verbund_suche` mit dem Zugriff aus Schritt 2. Auch dort weist jeder Treffer
seine Bestandszeile aus — Titel mit ✅ besitzt die BHT und sind **keine**
Fernleihfälle.

**5 — Auswählen.** Die Trefferliste ist **nicht relevanzsortiert**; die angezeigten N
sind die ersten N von vielen. Deshalb alle 12–15 scannen und selbst auswählen, statt
die ersten fünf zu übernehmen. Kriterien: Passung von Titel und Schlagwörtern,
aktuelle Auflage, Lehrbuch oder Handbuch vor enger Monografie.

**Nach jedem Aufruf mitschreiben:** Suchbegriff, Suchtyp, Trefferzahl, Zahl der
ausgewählten Titel. Diese vier Werte füllen später „Bisher gesucht" im
Recherchestand; nachträglich lassen sie sich nur noch schätzen.

#### Wenn nichts kommt

Null Treffer in der Schlagwortsuche heißt fast immer: Der Begriff ist **kein
GND-Schlagwort** — nicht, dass die Bibliothek nichts zum Thema hat. In dieser
Reihenfolge:

1. Etabliertes Nachbarschlagwort probieren (Praxisbeispiel: *partizipative
   Forschung* → 0 Treffer, *Bürgerbeteiligung* → produktiv).
2. Synonyme per ` OR ` in dieselbe Anfrage nehmen, statt sie nacheinander zu
   probieren; ein Konzept ganz weglassen.
3. Erst dann `"any"`. Bei null Treffern sucht das Werkzeug von sich aus zusätzlich im
   Freitext und weist das im Ergebnis aus — diesen Hinweis übernehmen: Die Treffer
   sind dann weniger trennscharf als eine Schlagwortsuche.

Der Freitext-Fallback greift **nur bei null** Treffern, nicht bei einer kleinen
Trefferliste — deshalb erledigt Schritt 1 die Gegenprobe von vornherein. Bevor du
sagst, die Bibliothek habe zu einem Thema nichts, muss die Titelsuche gelaufen sein.

Den Fehlschlag **sichtbar machen**: Er führt den Unterschied zwischen freiem und
kontrolliertem Vokabular an einem echten Beispiel vor.

#### Werkzeugfälle

- `opac_autor_suche` bei bekannter Person, `opac_isbn_suche` bei bekannter ISBN.
  **Kein `opac_erweiterte_suche`** — existiert nicht; Mehrfeldlogik über mehrere
  Aufrufe.
- **Argumente flach übergeben** — `suchbegriff`, `suchtyp`, `max_treffer`,
  `nur_bht_bestand` stehen nebeneinander, nicht in einem `params`-Objekt.
- **Umlaute:** Bei Encoding-Problemen im Z39.50-Zugang auf umlautfreie Varianten oder
  Einzelbegriffe ausweichen und das transparent machen.
- **Schema- oder Validierungsfehler:** denselben Aufruf höchstens **einmal**
  wiederholen. Scheitert er erneut, ist es ein Werkzeugfehler, kein Suchproblem: in
  Alltagssprache melden („der Katalog hat die Anfrage abgewiesen"), mit der
  Paper-Stufe weitermachen und den Katalog im Recherchestand unter „Quellenlage" als
  offen führen.

#### Ausgabe

**Gib die ausgewählten Treffer jetzt als Tabelle aus** — vor jedem weiteren Schritt,
mit genau diesen Spalten:

| Titel | Autor*innen | Jahr | Verfügbarkeit |
|---|---|---|---|
| [Stadtböden: Entwicklungen, Belastungen, Bewertung und Planung](OPAC-Link) | Pietsch, Kamieth | 1991 | ✅ BHT-Bestand |
| [Unsere Böden entdecken](Volltext-Link) | Don, Prietz | 2025 | ✅ BHT-Lizenz (E-Book) |
| [Kohlenstoff in versiegelten und entsiegelten Böden in Berlin](Volltext-Link) | Thrum u. a. | 2023 | 🌐 Frei zugänglich |
| [Urbane Böden](Verlagsseite) | Hiller, Meuser | 1998 | 🔒 Keine BHT-Lizenz, keine Fernleihe |
| [Bodenfunktionen nach Entsiegelung](KOBV-Link) | Gaßner | 2001 | ℹ️ Fernleihe (KOBV) |
| [Verkehrsflächenüberbauung](KOBV-Link) | — | o. J. | ❔ Bestand ungeklärt |

*Quelle: BHT-webOPAC* (und *KOBV-Verbundkatalog*, sobald Verbundtreffer in der
Tabelle stehen) — Pflichtzeile direkt unter der Tabelle.

- **Die Spalte „Verfügbarkeit" ist die Kurzform der Bestandszeile des Treffers**,
  nicht deine Einschätzung. Sechs Zustände: ✅ BHT-Bestand · ✅ BHT-Lizenz (E-Book) ·
  🌐 Frei zugänglich · 🔒 Keine BHT-Lizenz, keine Fernleihe · ℹ️ Fernleihe (KOBV) ·
  ❔ Bestand ungeklärt. Nie ℹ️ setzen, wo das Werkzeug ✅, 🌐 oder 🔒 meldet:
  E-Ressourcen sind nicht fernleihfähig, freie Volltexte braucht niemand zu
  bestellen, und ungeklärt heißt nicht „nicht vorhanden". Fehlt die Bestandszeile,
  gilt ❔.
- **Der Titel selbst ist der Link** (Herkunft siehe Ausgabe-Regeln). Eine Tabelle
  ohne Links ist unbrauchbar; sie ist der Grund, warum die Tabelle kommt.
- Der `[OPAC]`-Link führt zum Titel im lokalen webOPAC mit Signatur und
  Verfügbarkeit und **ersetzt die Signatur**: Der KOBV-Verbundkatalog enthält keine
  Standortsignatur, deshalb nie die PPN oder eine DDC/RVK-Klassifikation als
  „Signatur" ausgeben.
- Auflage nur, wenn sie für die Auswahl zählt — dann hinter den Titel.

Unter der Tabelle in zwei bis drei Sätzen, **warum diese Titel**: was der Bestand
hergibt, was nur über Fernleihe kommt, was auffällig fehlt.

#### Bevor Stufe 2 beginnt

- Tabelle ausgegeben, mit der Quellenzeile darunter?
- Jeder Titel verlinkt, der Link unverändert aus der Werkzeugausgabe?
- Verfügbarkeit aus der Bestandszeile übernommen, nicht selbst eingeschätzt?
- Trefferzahl und Auswahl je Aufruf notiert?
- Zwei bis drei Sätze darunter, warum diese Titel?

#### Warum das Verfahren so aussieht

Nicht Teil der Ausführung — Hintergrund für Fälle, die keine Regel abdeckt.

**Die Schlagwortsuche verliert gerade die neueren Titel.** Der Katalog mischt
Datenherkünfte: Verbundaufnahmen (Kennung `b3kat_…`) tragen deutsche
GND-Schlagwörter, die Aufnahmen aus den lizenzierten E-Book-Paketen (`almahu_…`,
`almatuudk_…`, `edocfu_…`) stattdessen die englischen Fachkategorien des Verlags.
Eine GND-Schlagwortsuche filtert damit unbeabsichtigt fast die gesamte E-Book-Ebene
weg — den Teil des Bestands, in dem die Literatur der letzten Jahre liegt.

**Gemessen an einer Recherche zu Gamification.** „Gamification" ergab als Schlagwort
17 Treffer, als Titelsuche mit Varianten 32, über alle Felder 43. Die beiden
einschlägigsten Titel des Bestands waren für die Schlagwortsuche unsichtbar: „The
gamification of learning and instruction" (Kapp 2012) ist als „Lernspiel ·
Trainingsmethode" verschlagwortet, „Gamification in der Hochschullehre" (Körner
u. a. 2024) trägt nur Springer-Kategorien. Dass derselben Autorengruppe der Band von
2025 ein *Gamification*-Schlagwort bekam und der von 2024 nicht, zeigt, wie wenig
verlässlich die Verschlagwortung ist. Umgekehrt war „Lernmotivation" als Schlagwort
mit 14 Treffern präzise, während `Spiel OR spielerisch; Lernen OR Unterricht` als
Titelsuche 28 Treffer brachte, überwiegend Programmierlehrbücher — an einer
technischen Hochschule ist „spielerisch lernen" ein Verlagsslogan. Und
`Gamification OR Gamifizierung OR "Serious Game"; Motivation OR Lernmotivation`
ergab über alle Felder genau 1 Treffer, schlechter als jede Einzelsuche.

Daraus folgt die Tabelle in Schritt 2: messen statt vorab einordnen, weil die
Eigenschaft, auf die es ankommt, erst im Ergebnis sichtbar wird.

### Stufe 2 — Paper-Suche (aktuelle Forschung)

Der Katalog zeigt die Grundlagen; für den aktuellen Forschungsstand braucht es
Fachdatenbanken mit Zeitschriftenartikeln.

- **`search_papers` mit gezielten Kernquellen, nie `sources="all"`.**
  `max_results_per_source` ca. 5. Ohne explizite Angabe steht der Wert auf `all`,
  dann werden auch fachfremde und nicht erreichbare Quellen abgefragt.
- Englische Suchbegriffe bringen meist mehr; 3–8 Wörter.

| Auswahl | Quellen |
|---|---|
| Grundstock, alle Fächer | `openalex,semantic,crossref` |
| + Bau, Umwelt, Maschinenbau | `openaire` — europäische Konferenz- und Repositorienliteratur (z. B. WCTE), sonst nirgends auffindbar |
| + Life Sciences, Verfahrenstechnik | `europepmc` — **nicht** `pubmed`, **nicht** `pmc`; die bioRxiv- und medRxiv-Preprints stecken hier mit drin |
| + Informatik | `arxiv`, `dblp` |
| + sobald API-Keys gesetzt | `ieee`, `acm` |

Die Achse ist **Grundstock + fachliche Ergänzung**, nicht Fach → Quellenliste: die
Quellen unterscheiden sich vor allem in der Metadatenqualität, nicht in der
Fachabdeckung. Fachfremdes nicht pauschal zuschalten — bei einem Bau- oder
Ingenieurthema liefern `arxiv` und `pubmed` reinen Fachfremd-Lärm.

Fünf Dinge, die man beim Auswerten wissen muss:

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
- **`biorxiv` und `medrxiv` nicht in die Quellenliste nehmen.** Beide haben keine
  Stichwortsuche, sondern listen nur eine Kategorie der letzten 30 Tage; sie sind
  deshalb auch nicht Teil von `sources="all"`. Ihre Preprints erreicht `europepmc`,
  das sie indexiert und tatsächlich durchsucht.
- **`base` nicht verwenden.** Der Zugang verlangt eine institutionelle
  IP-Freischaltung, die nicht vorliegt; die Quelle antwortet dauerhaft leer. Google
  Scholar und SSRN stehen auf dem Connector nicht zur Verfügung.

Drei Parameter, die sich in dieser Stufe lohnen:

- `crossref_filter="type:journal-article"` filtert Dissertationen, Proceedings und
  Verlagsartefakte aus dem Crossref-Anteil. In einem Testlauf zu „cross-laminated
  timber fire resistance" waren ohne Filter alle Crossref-Treffer Dissertationen
  und Konferenzbeiträge ohne Abstract; mit Filter stieg die Zahl der Treffer mit
  Abstract von 5 auf 7 von 10.
- `abstract_chars` kürzt die Abstracts (Standard 600 Zeichen). Fürs Screening
  reichen die ersten Sätze; für die Begriffsernte im `p`-Hotkey `abstract_chars=0`
  setzen, sonst fehlt gerade das Vokabular aus dem hinteren Teil.
- **Der Jahresfilter wirkt nur auf Semantic Scholar.** Zum Priorisieren aktueller
  Arbeiten nutzbar, aber sage nie, die Trefferliste sei auf einen Zeitraum
  eingegrenzt — für echte Aktualität in der Auswahl nach Erscheinungsjahr filtern.

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

**Auch hier jeden Aufruf sofort mitschreiben:** Suchbegriff, abgefragte Quellen,
Trefferzahl, Zahl der ausgewählten Titel — dazu jede Quelle, die nicht geantwortet
hat, mit dem Grund. Das füllt „Bisher gesucht" und „Quellenlage" im Recherchestand.
Die Fehlerangaben stehen nur in der Antwort des jeweiligen Aufrufs; nach der
nächsten Suche sind sie nicht mehr rekonstruierbar.

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
  (ein bis zwei Beispiele pro Runde genügen): *Wortlaut-Fehltreffer* — v. a. DOAJ
  matcht nur den Wortlaut; ein Aufsatz über Berufsschulunterricht, der zufällig
  „Building Information" im Titel führt, fällt raus („Fokus auf X, nicht auf Y").
  *Grauliteratur-Rauschen* — Regierungs- und Behördenberichte (häufig über OSTI)
  treffen thematisch, tragen für eine Abschlussarbeit aber wenig bei.
- **Ziel ist eine Mischung:** 2–3 Grundlagenarbeiten plus 2–3 aktuelle Arbeiten
  (letzte ~3 Jahre, oft Open Access).

**Gib die ausgewählten Treffer jetzt als Tabelle aus** — vor der Synthese, mit genau
diesen Spalten:

| Titel | Autor*innen | Quelle & Jahr | Zit. | Zugang |
|---|---|---|---|---|
| [Energy efficiency in cloud data centers: a survey](DOI-Link) | Katal u. a. | Cluster Computing 2022 | 472 | Open Access |
| [Mesoclimatic effects on data centre siting](DOI-Link) | Turek, Radgen | Energies 2021 | 14 | Open Access |
| [Liquid cooling for high-density racks](DOI-Link) | Chainer u. a. | IBM J. Res. Dev. 2017 | 96 | Lizenz (EZB) |

*Quelle: Crossref, OpenAlex, Semantic Scholar* — Pflichtzeile direkt unter der
Tabelle, vor der Begründung.

- **Der Titel selbst ist der Link**, auf die DOI im Format `https://doi.org/<doi>`.
  Liefert das Tool bereits eine volle URL, diese verwenden — nie nackte DOI-Strings,
  nie eine Tabelle ohne Links.
- **Zit.** nur, wenn die Quelle eine Zahl liefert; sonst Feld leer lassen, nicht
  schätzen.
- **Zugang: aus der Werkzeugausgabe, nicht aus dem Verlagsnamen.** „Open Access",
  wenn der Treffer es selbst ausweist (`open_access`, `in_doaj`, `zeitschrift_oa`)
  oder aus `doaj`, `arxiv` oder `europepmc` stammt. Sagt die Ausgabe nichts, für die
  Zeilen der Tabelle `search_unpaywall` mit der DOI fragen. Bleibt es danach offen,
  „Zugang über die DOI prüfen" schreiben und nichts behaupten; „Lizenz (EZB)" nur,
  wenn eine Quelle den Titel als nicht frei ausweist.
  **Nie vom Verlag auf den Zugang schließen.** Das wäre Trainingswissen und
  verstößt gegen das erste Grundprinzip: Springer und Elsevier publizieren ebenso
  Open Access, wie MDPI- oder DOAJ-Titel einzeln hinter einer Schranke stehen
  können.

Unter der Tabelle in zwei bis drei Sätzen: welche thematischen Stränge die Auswahl
abdeckt, und — mit je einem Halbsatz — was aussortiert wurde und warum. Das gehört
nicht in die Tabelle.

### Stufe 3 — Synthese

Ordne ein, was Katalog (Grundlagen) und Paper-Suche (aktuelle Forschung) beigetragen
haben, und benenne Schwerpunkte oder Lücken. Dies ist eine Bilanz der Trefferlage,
keine inhaltliche Synthese der Literatur.

**Autorennamen auszählen.** Geh die Autorenlisten aller in dieser Runde genannten
Treffer durch und nenne jeden Namen, der in zwei oder mehr Treffern vorkommt,
zusammen mit den Treffern, in denen er steht — das ist der Anschluss an `a`, und
Wiederkehr über mehrere Quellen hinweg ist ein Relevanzsignal, das keine einzelne
Trefferliste zeigt. Kommt kein Name zweimal vor, entfällt die Zeile wortlos.

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
(breiter, enger, Pearl Growing, noch eine Runde) gehören **nicht** hierher — die
deckt das Hotkey-Menü ab.

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
> · Katalog, Schlagwort „KI OR Künstliche Intelligenz; Bauwesen" — 93 Treffer, 4 ausgewählt (3 im Bestand, 1 Fernleihe)
> · Katalog, Freitext „Bauinformatik" — 0 Treffer
> · Fachdatenbanken (Semantic Scholar, Crossref, OpenAlex, DOAJ), *artificial intelligence construction* — 9 Treffer, 5 ausgewählt
> **Quellenlage:** Crossref, OpenAlex, DOAJ haben geantwortet · Semantic Scholar gedrosselt, offen
> **Bereits genannt:** Abioye u. a. 2021 · Yiğitcanlar u. a. 2020 · Borrmann (Hg.) 2021 · …
> **Offene Begriffe:** Digitaler Zwilling (Katalog) · Bauwerksdatenmodellierung (Katalog) · predictive maintenance · construction automation
> **Noch offen:** Block 3 („Planung") noch nicht gesucht; englische Begriffe im Katalog noch nicht probiert

Die Zeile **Quellenlage** ist Pflicht, sobald eine Quelle ausgefallen ist. Sie bleibt
so lange offen, bis die Quelle geantwortet oder bestätigt nichts geliefert hat.

Die Zeile **Offene Begriffe** führt die Begriffe, die eine `p`-Runde geerntet hat,
mit denen aber noch nicht gesucht wurde — katalogtaugliche deutsche Begriffe mit dem
Zusatz „(Katalog)", englische Fachtermini für die Paper-Suche. Sie erscheint erst,
wenn eine Ernte gelaufen ist, und ist die **erste Quelle, aus der `r` schöpft**.
Begriffe, mit denen gesucht wurde, verschwinden aus der Zeile und erscheinen unter
„Bisher gesucht"; ist die Zeile leer, entfällt sie wieder. Ohne diese Zeile bleibt
eine Ernte folgenlos, weil die nächste Runde nicht weiß, dass es sie gab.

## Hotkeys (Folgebefehle)

Direkt nach dem Recherchestand das Menü ausgeben – kompakt, ohne Erklärtext:

> **Weiter mit:**
> `r` — noch eine Suchrunde in Katalog und Fachdatenbanken, mit den offenen Begriffen
> `p` — Pearl Growing: Begriffe aus den besten Treffern ernten und die Suchbegriffstabelle nachschärfen (gesucht wird dann mit `r`)
> `s` — Schneeball: den Zitaten der besten Treffer folgen, rückwärts und vorwärts
> `a` — Autorensuche zu Namen, die mehrfach auftauchten
> `w` — breiter suchen (Synonyme, Oberbegriffe, Freitext, ganzer KOBV-Verbund)

Enger wird nicht per Hotkey gesucht: Dazu den Aspekt einfach nennen („nur Holzbau
im Bestand").

Aliasse: `runde` / `another round` (r) · `begriffe` / `terms` / `pearl` / `perle` (p) ·
`schneeball` / `zitate` / `snowball` (s) · `autoren` / `authors` (a) · `weiter` /
`breiter` / `broaden` (w).

**Erkennungsregel:** Besteht die Eingabe nur aus einem dieser Buchstaben, einem
Alias oder einer Vorschlagsnummer aus Stufe 4, ist es ein Befehl — nicht nachfragen,
ausführen.

**Regeln für Hotkey-Runden:**

- Der volle Stufenablauf (0–4) gilt nur für die **erste** Runde. Eine Hotkey-Runde
  führt nur ihren eigenen Schritt aus und endet wieder mit Recherchestand + Menü.
- **Jede Hotkey-Runde führt ihren eigenen Schritt tatsächlich aus.** Sie darf ihn
  nicht durch nummerierte Vorschläge im Stil von Stufe 4 ersetzen — ein „Nächster
  Schritt: …" statt der Arbeit ist der häufigste Fehler. Auf einen anderen Hotkey
  zu **verweisen** ist etwas anderes und bleibt erlaubt.
- Die Erklärtexte zu den Stufen **nicht** wiederholen.
- Vor jeder Runde in **einem Satz** sagen, was jetzt anders gesucht wird als zuvor —
  die Begründung, nicht die Ankündigung eines Vorgehens.
- Treffer aus „Bereits genannt" nicht erneut auflisten. Tauchen sie wieder auf, das
  kurz erwähnen — Wiederkehr ist selbst ein Relevanzsignal.
- Ist der Recherchestand nicht mehr auffindbar, nachfragen statt raten.
- Eine Eingabe in Freitext, die kein Hotkey und keine Vorschlagsnummer ist, ist
  keine neue Recherche, sondern eine **Einschränkung der laufenden**: Thema und
  Suchbegriffstabelle aus dem Recherchestand bleiben, der genannte Aspekt kommt
  hinzu. In einem Satz sagen, was dadurch wegfällt. Nur wenn ein erkennbar anderes
  Thema genannt wird, beginnt der Stufenablauf neu.

### `r` — Noch eine Suchrunde

`r` ist die Runde, in der gesucht wird — und zwar **in beiden Stufen**: erst der
Katalog (Verfahren wie in Stufe 1), dann die Fachdatenbanken (wie in Stufe 2). Beide
Trefferlisten kommen als Tabelle, jede mit ihrer Quellenzeile.

Den Katalog auch dann abfragen, wenn die vorangegangenen Runden nur Paper geliefert
haben. Sonst bleibt die Grundlagenliteratur zu den neuen Begriffen unentdeckt — und
genau dafür ist der Katalog da. Übersprungen wird er nur, wenn ein Begriff erkennbar
nicht katalogfähig ist (ein englischer Fachterminus ohne deutsche GND-Entsprechung
etwa), und dann mit einem Halbsatz Begründung.

Welche Begriffe, in dieser Reihenfolge:

1. Steht unter „Quellenlage" eine gedrosselte Quelle offen, wird sie zuerst
   nachgeholt.
2. Stehen unter „Offene Begriffe" Einträge, wird **mit diesen** gesucht — sie sind
   in einer `p`-Runde bereits als aussichtsreich ausgewählt worden. Die verwendeten
   aus der Zeile streichen, die übrigen stehen lassen.
3. Ist die Zeile leer, aus „Noch offen" die vielversprechendste ungenutzte
   Begriffskombination wählen — **andere Begriffe** oder ein **anderer Suchtyp**,
   nicht dieselbe Anfrage mit höherer Trefferzahl.

Für den Katalog die deutsche Spalte der Suchbegriffstabelle, für die Paper-Suche die
englische; bei geernteten Begriffen ist das oft dieselbe Zeile in zwei Sprachen.
Geerntete Synonyme gehören per ` OR ` in **denselben** Block, nicht in eine eigene
Anfrage — das ist der Unterschied zwischen einer größeren und einer kleineren
Treffermenge.

### `p` — Pearl Growing (Begriffe ernten)

Pearl Growing im engeren Sinn: aus den inhaltlich besten Treffern das Vokabular
ziehen, mit dem das Feld selbst arbeitet, und die Suchbegriffstabelle damit
nachschärfen. Das repariert die **Suchanfrage** — der richtige Schritt, wenn Treffer
da sind, aber thematisch streuen, und besonders dann, wenn der Katalog leer blieb,
während die Datenbanken geliefert haben: Dann passt das eigene Vokabular nicht zum
Normvokabular.

**Diese Runde erntet, sie sucht nicht.** Gesucht wird anschließend mit `r`. Die
Trennung ist gewollt: Wer die Begriffe erst sieht, kann sie verwerfen oder ergänzen,
bevor sie eine Suche bestimmen.

Zuerst die 3–5 inhaltlich stärksten Treffer wählen und **benennen, warum gerade
diese**. Daraus die Begriffe ziehen, die in der Tabelle fehlten — aus Titel, Abstract
und Schlagwörtern. Für den Katalog vor allem die GND-Schlagwörter der Katalogtreffer,
für die Paper-Suche die englischen Fachtermini. Stammen die Abstracts aus einer Runde
mit gekürzten Abstracts, die Suche mit `abstract_chars=0` wiederholen.

Dann die **Suchbegriffstabelle aus Stufe 0 vollständig neu ausgeben**, die neuen
Einträge markiert, damit der Zuwachs sichtbar ist.

Zuletzt die 2–4 aussichtsreichsten der geernteten Begriffe in die Zeile **Offene
Begriffe** des Recherchestands eintragen — nicht die ganze Ernte, sondern die
Auswahl, mit der `r` als Nächstes arbeitet. Katalogtaugliche deutsche Begriffe mit
dem Zusatz „(Katalog)". In einem Satz sagen, warum gerade diese und was mit `r` als
Nächstes gesucht wird. Tauchen Autor*innen mehrfach auf, zusätzlich auf `a`
hinweisen.

Liegen noch keine Treffer vor, gibt `p` die Tabelle aus Stufe 0 neu aus und fragt,
mit welchem Block gesucht werden soll.

### `s` — Schneeball (Zitationsverfolgung)

Zitationsverfolgung: von einer bekannten Arbeit (der „Perle") dem Zitationsnetz
folgen. Das repariert nicht die Anfrage, sondern umgeht sie — unabhängig davon, wie
das Feld benennt. Der richtige Schritt, wenn wenige, aber inhaltlich sehr treffende
Arbeiten mit DOI vorliegen.

Eine oder zwei Perlen wählen und benennen, warum. Beide Richtungen sind verschieden
ergiebig:

- **Rückwärts** (`paper_referenzen`): worauf die Perle aufbaut → führt zu den
  **Grundlagen**. Das Literaturverzeichnis ist endlich und nach Zitationszahl
  sortiert, die Grundlagenarbeiten stehen also oben; `max_treffer=15` genügt. Bei
  einem *Review* als Ausgangspunkt kommen oft Methodik-Arbeiten statt inhaltlicher
  Grundlagen — dann vorwärts weiterarbeiten.
- **Vorwärts** (`paper_zitiert_von`): wer die Perle zitiert → führt zum **aktuellen
  Forschungsstand**, die Richtung, die eine Stichwortsuche nicht abbildet.

**Zur Vorwärtssuche zwei Regeln, die zusammengehören.** Die Treffer sind nach
Zitationszahl sortiert, und neue Arbeiten haben naturgemäß wenige Zitationen: Bei
einer stark zitierten Perle endet die Liste deshalb mehrere Jahre in der
Vergangenheit, obwohl gerade das Aktuelle gesucht war. Also `ab_jahr` auf die letzten
drei bis vier Jahre setzen — **aber nur bei Perlen mit dreistelliger Zitationszahl.**
`ab_jahr` filtert hart, es sortiert nicht: Bei einer schwach zitierten Perle fielen
dadurch ältere zitierende Arbeiten weg, die problemlos in die Antwort gepasst hätten.

Die Gesamtzahl gehört in die Ausgabe — „von 271 zitierenden Arbeiten die 25
meistzitierten seit 2022". Ohne sie ist der Ausschnitt unsichtbar.

Zum Schluss neue Treffer gegen „Bereits genannt" prüfen und Dubletten aussortieren.
Sind dabei neue Fachbegriffe aufgefallen, `p` als nächsten Schritt vorschlagen.

**Grenzen (kurz, wo sie auftreten):** Die Zitationsdaten stammen aus
OpenAlex-Metadaten, nicht aus den PDFs — eine Arbeit ohne DOI oder OpenAlex-Datensatz
lässt sich nicht verfolgen; kennt OpenAlex die Referenzliste nicht, kommt rückwärts
nichts, dann auf vorwärts ausweichen. Der Schneeball findet nur Aufsätze, nie ein
Lehrbuch und nie eine Signatur — zurück in den Katalog führen allein `p` und `r`. Die
seitwärts-„verwandten" Treffer von OpenAlex (`paper_verwandte`) sind unzuverlässig
und werden **nicht** verwendet.

### `a` — Autorensuche

Namen aufgreifen, die in mehreren Treffern auftauchten. Erst im Katalog, bei Bedarf
zusätzlich in den Fachdatenbanken. Nennen, in welchen Treffern der Name vorkam.

### `w` — Breiter suchen

In dieser Reihenfolge: weitere Synonyme per ` OR ` in die vorhandenen Blöcke → ein
Konzept ganz weglassen → Oberbegriffe statt enger Begriffe → den Katalogzugriff
wechseln, den Stufe 1 nicht gewählt hat (Schlagwort ↔ Titel ↔ alle Felder) → über
den BHT-Bestand hinaus in den KOBV-Verbund → in der Paper-Stufe fachpassende weitere
Datenbanken zuschalten. Die ersten beiden Schritte wirken am
stärksten und kosten nichts: Im Katalog verengt jedes zusätzliche Konzept, jedes
Synonym erweitert.

Brachte eine Runde weniger als etwa fünf brauchbare Treffer, `w` im Menü an erster
Stelle nennen: Bei dünner Trefferlage können die Vorschläge aus Stufe 4 nichts
tragen, weil ihnen die Treffer fehlen, auf die sie sich beziehen müssten.

### `d` — PDF exportieren

Den `bht-pdf-generation`-Skill aufrufen und dabei die gesamte bisherige Recherche
als kanonisches Markdown zusammenstellen. Das PDF enthält:

1. **Einleitung** — ein bis zwei Sätze zum Thema und dessen Relevanz (aus den
   bisherigen Suchblöcken ableiten).
2. **Suchbegriffstabelle** — der aktuelle Stand der Blöcke und Begriffe.
3. **Katalog-Treffer** — die Tabellen aus Stufe 1 mit ihren Links.
4. **Paper-Treffer** — die Tabelle aus Stufe 2 mit DOI-Links, Zitationszahlen und
   Zugangshinweisen.
5. **Synthese** — Stufe 3, ohne die Trefferlisten zu wiederholen.
6. **Vorschläge** — Stufe 4.
7. **Recherchestand** — der aktuelle Block, inklusive Hotkey-Menü.

Dabei gilt:

- Alle Katalog-Links und DOIs als intakte klickbare URLs übernehmen und kenntlich
  machen (blaue Schrift, unterstrichen).
- **Kein** Volltext, keine Abstracts — nur die in dieser Sitzung gefundenen
  bibliographischen Daten.
- Den Schlusshinweis zu Zugang und Fernleihe ans Ende stellen (EZB/DBIS, KOBV).
- Die PDF-Skill-Anweisung strikt befolgen: `document.md` in ein temporäres
  Verzeichnis schreiben, dann Pandoc → Typst oder den ReportLab-Fallback,
  `document.pdf` und `document-preview.png` nach `/mnt/data`.
- **Fehlt `bht-pdf-generation` in dieser Sitzung** oder gibt es `/mnt/data` nicht:
  kein Ersatzverfahren erfinden und keine andere Bibliothek suchen. Sag in einem
  Satz, dass der PDF-Export hier nicht zur Verfügung steht, und gib denselben
  Inhalt in derselben Gliederung als Markdown im Chat aus, mit allen Links intakt.

## Zeitschriftenkennzahlen (nur auf Nachfrage)

Fragt jemand nach der Qualität, dem Rang oder den Kennzahlen einer Zeitschrift,
`zeitschrift_profil` aufrufen. Ausgabe als kurze Liste, **nicht** als Spalte in der
Trefferliste: Verlag · Zugangsweg (Open Access, DOAJ-Eintrag, sonst Lizenz über die
BHT) · Zahl der erfassten Arbeiten · h-Index · Zitationsschnitt der letzten zwei
Jahre.

**Immer mit dieser Einordnung darunter, in einem Satz:** Der Wert beschreibt die
Zeitschrift, nicht den einzelnen Aufsatz — innerhalb einer Zeitschrift ist die
Zitationsverteilung sehr schief, die Mehrheit der Beiträge liegt deutlich unter dem
Schnitt. Für die Bewertung eines konkreten Titels taugt er nicht.

**Nie „Impact Factor" oder „Zitationsfaktor" sagen.** Der Journal Impact Factor ist
ein lizenzpflichtiges Produkt von Clarivate (Journal Citation Reports) und wird hier
nicht abgebildet; der ausgegebene Wert stammt aus OpenAlex und ist mit dem JIF nicht
zahlengleich. Wird ausdrücklich nach dem Impact Factor gefragt, das benennen und
darauf hinweisen, dass die BHT weder Web of Science noch die JCR lizenziert.

Kam die Zuordnung über eine Namenssuche zustande (`zuordnung: "unscharf"`), das
kennzeichnen: „Zuordnung über den Zeitschriftennamen, bitte an der ISSN prüfen."

**Keine Sortierung der Trefferliste nach der Kennzahl.** Das ist genau die
Verwendung, die DORA und CoARA adressieren, und steht quer zu dem, was die
Bibliothek sonst zur Forschungsbewertung vertritt.

## Schlusshinweis an die Person (Zugang zum Volltext)

Beim **ersten** Durchgang ausgeben, danach nur bei Bedarf. Der Weg richtet sich nach
der Verfügbarkeitsspalte aus Stufe 1:

- **Bücher:** ✅ über den `[OPAC]`-Link zum Titel im lokalen Katalog (Signatur und
  Standort) · 🌐 direkt über den Volltextlink · ℹ️ Fernleihe über das KOBV-Portal ·
  🔒 nicht fernleihfähig, E-Ressourcen werden nicht verliehen (dann einen
  Erwerbungsvorschlag oder eine Alternative aus der Trefferliste nennen).
- **Artikel:** Open Access direkt über die DOI; lizenzpflichtige über die
  E-Ressourcen der BHT (EZB/DBIS, bei Bedarf Shibboleth oder VPN).
- **Zeitschriftenkennzahlen:** Die BHT lizenziert weder Web of Science noch die
  Journal Citation Reports; ein Journal Impact Factor ist darüber nicht verfügbar.

## Werkzeug-Referenz (Connector `paper-opac-search-mcp`)

- `opac_suche(suchbegriff, suchtyp="subject"|"any"|"title"|"author", max_treffer, nur_bht_bestand=true)`
  — `suchbegriff` nimmt die Blocksuche: `Konzept1 OR Synonym; Konzept2 OR Synonym`.
- `opac_autor_suche(autor, max_treffer, nur_bht_bestand=true)`
- `opac_isbn_suche(isbn)`
- `kobv_verbund_suche(suchbegriff, suchtyp="any", max_treffer)` — ohne BHT-Filter,
  weist den BHT-Bestand aber trotzdem aus.

Die vier Katalog-Tools nehmen ihre Argumente **flach**, nicht in ein `params`-Objekt
gewickelt. Jeder Treffer trägt eine Bestandszeile; sie füllt die Spalte
„Verfügbarkeit" und bestimmt den Beschaffungsweg (siehe Stufe 1).

- `search_papers(query, sources="openalex,semantic,crossref", max_results_per_source=5, year=optional, abstract_chars=600, crossref_filter="")`
  — `sources` ist der Weg zu den einzelnen Datenbanken; Crossref, CORE, OpenAIRE und
  die übrigen sind Parameterwerte, keine eigenen Aufrufe. Welches Set wann, steht in
  Stufe 2.

Nachschlagen zu einer bekannten DOI (nie als Trefferquelle):

- `get_crossref_paper_by_doi(doi)` — Gegenprobe für OpenAIRE-Treffer, siehe
  Grundprinzipien.
- `search_unpaywall(doi)` — Open-Access-Status für die Spalte „Zugang" in Stufe 2.

Zitationsverfolgung (nur `s`, nur mit DOI oder OpenAlex-ID):

- `paper_referenzen(kennung, max_treffer=25, mit_abstract=false)` — rückwärts: was
  das Paper zitiert.
- `paper_zitiert_von(kennung, max_treffer=25, ab_jahr=optional, mit_abstract=false)`
  — vorwärts: wer das Paper zitiert.
- `mit_abstract=false` beibehalten. Die Abstracts der Stufe-2-Treffer liegen bereits
  im Kontext; für die Begriffsernte braucht es keinen neuen Aufruf.
- `paper_verwandte` **nicht verwenden** — unzuverlässig.

Zeitschrift:

- `zeitschrift_profil(kennung)` — Kennzahlen und Zugangsstatus einer Zeitschrift.
  `kennung` nimmt ISSN, Zeitschriftennamen, OpenAlex-Source-ID oder Aufsatz-DOI.
  Nur auf Nachfrage aufrufen, nicht routinemäßig je Treffer.

Quellenspezifische `search_*` (z. B. `search_openalex`) existieren auf dem Server,
werden hier aber **nicht** verwendet: Als Retry nach einem Nullbefund helfen sie
nachweislich nicht, und alles andere leistet der aggregierte Aufruf.

Nicht verwenden (Beschaffung): `download_*`, `read_*`. Der Server registriert diese
Werkzeuge seit 0.7.0 nicht mehr; die Regel bleibt als Absicherung für ältere
Installationen stehen.

In LibreChat können MCP-Tools namespaced registriert sein (Muster
`<toolname>_mcp_<servername>`). Maßgeblich sind die Namen, die im Agenten
tatsächlich verfügbar sind.
