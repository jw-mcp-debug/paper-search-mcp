"""
z3950_client.py
===============
Z39.50-Client für den KOBV-Server auf Basis von PyZ3950.

KOBV-Server: z3950.kobv.de:210, Datenbank k2
BHT ISIL:    DE-B768 (Bib-1 Attribut 1044)

Voraussetzungen:
    pip install PyZ3950 pymarc ply
    # ccl.py muss durch Stub ersetzt werden (siehe setup.sh)
"""

import io
import logging
import re
from typing import Optional

import pymarc
from PyZ3950 import zoom

log = logging.getLogger("z3950_client")

# ---------------------------------------------------------------------------
# Konfiguration
# ---------------------------------------------------------------------------

Z3950_HOST = "z3950.kobv.de"
Z3950_PORT = 210
Z3950_DB   = "k2"
BHT_ISIL   = "DE-B768"

# Bib-1 Use-Attribute
BIB1_ATTR = {
    "any":     1016,
    "author":  1,
    "title":   4,
    "isbn":    7,
    "issn":    8,
    "subject": 21,
    "year":    31,
    "isil":    1044,
}

# ---------------------------------------------------------------------------
# PQF-Query-Bau
# ---------------------------------------------------------------------------

# Felder, bei denen Mehrwort-Eingaben als PHRASE (nicht als UND) gesucht werden:
# subject = GND-Schlagwort (echte Mehrwort-Phrasen), isbn = einzelner Token.
_PHRASE_ATTRS = {BIB1_ATTR["subject"], BIB1_ATTR["isbn"]}

# Blocksuche: ';' trennt Blöcke (UND-verknüpft), ' OR ' die Alternativen
# innerhalb eines Blocks. Das bildet die Suchbegriffstabelle einer Recherche
# direkt ab: ein Block je Konzept, die Synonyme des Konzepts per OR.
_BLOCK_TRENNER = ";"
_ODER_TRENNER = re.compile(r"\s+OR\s+", re.IGNORECASE)

# Der KOBV-Server unterstützt keine Trunkierung (Bib-1-Attribut 5 antwortet
# "unsupported search"). Ein * oder ? im Suchwort wird nicht etwa abgelehnt,
# sondern stillschweigend als Wortbestandteil gelesen: "Bildung*" liefert
# exakt dieselbe Treffermenge wie "Bildung". Das ist gefährlicher als ein
# Fehler, weil es wie eine funktionierende Trunkierung aussieht.
_PLATZHALTER = re.compile(r"[*?]")


def _term_clause(use_attr: int, wort: str) -> str:
    """Baut eine einzelne Term-Klausel '@attr 1=<use> <wort>'."""
    return f"@attr 1={use_attr} {wort}"


def _falte(operator: str, klauseln) -> str:
    """Faltet Klauseln rechts zu einem PQF-Operatorbaum ('and' oder 'or')."""
    klauseln = list(klauseln)
    ausdruck = klauseln[-1]
    for klausel in reversed(klauseln[:-1]):
        ausdruck = f"@{operator} {klausel} {ausdruck}"
    return ausdruck


def zerlege_bloecke(term: str) -> list:
    """Zerlegt eine Eingabe in Blöcke von Alternativen.

        'Deskilling OR Dequalifizierung; Bildung'
        -> [['Deskilling', 'Dequalifizierung'], ['Bildung']]

    Ohne ';' und ' OR ' entsteht genau ein Block mit einer Alternative — solche
    Eingaben verhalten sich exakt wie vor Einführung der Blocksuche.
    """
    bloecke = []
    for roh in term.split(_BLOCK_TRENNER):
        alternativen = [a.strip() for a in _ODER_TRENNER.split(roh) if a.strip()]
        if alternativen:
            bloecke.append(alternativen)
    return bloecke


def _alternative_klausel(use_attr: int, alternative: str) -> str:
    """Baut die Klausel für eine einzelne Alternative.

    Explizit gesetzte Anführungszeichen erzwingen eine Phrase. Sonst gilt das
    bisherige Verhalten: subject/isbn als Phrase, alles andere UND-verknüpft.
    """
    if len(alternative) > 2 and alternative.startswith('"') and alternative.endswith('"'):
        return _term_clause(use_attr, alternative)

    woerter = alternative.split()
    if len(woerter) <= 1:
        return _term_clause(use_attr, alternative)
    if use_attr in _PHRASE_ATTRS:
        return _term_clause(use_attr, f'"{alternative}"')
    return _falte("and", (_term_clause(use_attr, w) for w in woerter))


def _pqf(use_attr: int, term: str, isil=BHT_ISIL,
         auch_freitext: bool = False) -> str:
    """
    Baut eine PQF-Suchanfrage (Prefix Query Format).

    Mehrwort-Verhalten (der eigentliche Trefferquoten-Hebel):
    - any / title / author:  Wörter werden UND-verknüpft
        @and @attr 1=<use> Wort1 @attr 1=<use> Wort2
      (findet Titel, in denen beide Begriffe vorkommen – nicht nur als Phrase)
    - subject / isbn:        Mehrwort bleibt PHRASE ("...")
      (GND-Schlagwörter sind echte Mehrwort-Phrasen)

    Blocksuche: 'A OR B; C' wird zu @and @or(A,B) C. Jeder Block ist ein
    Konzept, die Alternativen darin sind seine Synonyme. Der Katalog kennt
    kein Relevanzranking — jedes zusätzliche Konzept ist ein harter Filter,
    weshalb zwei Blöcke in der Regel ergiebiger sind als drei.

    auch_freitext=True sucht jede Alternative zusätzlich im Freitextfeld
    (@or über use_attr und 'any'). Das fängt Begriffe ab, die als GND-
    Schlagwort nicht angesetzt sind und in einer reinen Schlagwortsuche
    deshalb null Treffer ergäben.

    Mit ISIL-Filter wird das Ganze per @and auf den BHT-Bestand eingegrenzt:
        @and @attr 1=1044 DE-B768 <suchausdruck>
    """
    term = term.strip()
    bloecke = zerlege_bloecke(term) or [[term]]

    block_klauseln = []
    for alternativen in bloecke:
        klauseln = []
        for alternative in alternativen:
            klausel = _alternative_klausel(use_attr, alternative)
            if auch_freitext and use_attr != BIB1_ATTR["any"]:
                klausel = _falte("or", [
                    klausel,
                    _alternative_klausel(BIB1_ATTR["any"], alternative),
                ])
            klauseln.append(klausel)
        block_klauseln.append(_falte("or", klauseln))

    main = _falte("and", block_klauseln)

    if isil:
        return f"@and @attr 1={BIB1_ATTR['isil']} {isil} {main}"
    return main


# ---------------------------------------------------------------------------
# Umlaut-Fix für Suchterme
# ---------------------------------------------------------------------------

def _terme_auf_utf8(node, _seen=None):
    """
    Wandelt jeden Suchterm ('general', str) in der RPN-Query rekursiv in
    UTF-8-Bytes um.

    Hintergrund: PyZ3950 kodiert GeneralString-Terme mangels registriertem
    Codec als ASCII und bricht bei Umlauten (ä/ö/ü/ß) mit UnicodeEncodeError
    ab. Der ASN.1-Encoder reicht bytes-Werte jedoch unverändert durch – ein
    als UTF-8-Bytes vorliegender Term landet also korrekt UTF-8-kodiert auf
    der Leitung, unabhängig von einer (hier nicht funktionierenden)
    Zeichensatz-Aushandlung. Offline gegen den echten PyZ3950-Encoder verifiziert.
    """
    if _seen is None:
        _seen = set()
    if id(node) in _seen:
        return
    _seen.add(id(node))

    t = getattr(node, "term", None)
    if (isinstance(t, tuple) and len(t) == 2
            and t[0] == "general" and isinstance(t[1], str)):
        node.term = ("general", t[1].encode("utf-8"))

    if hasattr(node, "__dict__"):
        for v in vars(node).values():
            _terme_auf_utf8(v, _seen)
    elif isinstance(node, (tuple, list)):
        for x in node:
            _terme_auf_utf8(x, _seen)


# ---------------------------------------------------------------------------
# MARC-Parsing
# ---------------------------------------------------------------------------

# 856 $3 sagt, worauf ein Link zeigt. Diese Angaben sind Beiwerk zum
# gedruckten Buch, kein Volltext — ein Inhaltsverzeichnis als "Volltext"
# auszugeben, wäre irreführender als gar kein Link.
_KEIN_VOLLTEXT = (
    "inhaltsverzeichnis", "inhaltstext", "inhaltsangabe", "inhaltsbeschreibung",
    "cover", "umschlagbild", "klappentext", "rezension", "besprechung",
    "verlagsinformation", "beschreibung für den leser", "autorenbiografie",
    "leseprobe", "register", "literaturverzeichnis",
)

# Marker für freie Zugänglichkeit, wie sie der B3Kat in $z/$3 notiert.
_FREI_MARKER = ("kostenfrei", "kostenlos", "frei zugänglich", "frei zugaenglich",
                "open access", "free")


def _feldtext(record, tag: str) -> str:
    """Rohdaten eines Kontrollfelds (007/008) — leer, wenn nicht vorhanden."""
    f = record.get(tag)
    if f is None:
        return ""
    return str(getattr(f, "data", "") or f.value() or "")


def _volltext_aus_856(record) -> tuple:
    """Sucht in 856 den Link auf das Werk selbst.

    Rückgabe: (url, frei). Indikator 2 == '2' meint eine verwandte Ressource
    (nicht das Werk), $3 mit Inhaltsverzeichnis o.ä. ist Beiwerk. Ein als
    kostenfrei ausgezeichneter Link hat Vorrang vor einem lizenzpflichtigen.
    """
    kandidaten = []
    for f in record.get_fields("856"):
        url = (f.get("u") or "").strip()
        if not url:
            continue
        if (f.indicator2 or "").strip() == "2":
            continue
        art = (f.get("3") or "").lower()
        if any(marker in art for marker in _KEIN_VOLLTEXT):
            continue
        notiz = f"{art} {(f.get('z') or '').lower()}"
        kandidaten.append((url, any(m in notiz for m in _FREI_MARKER)))

    if not kandidaten:
        return "", False
    for url, frei in kandidaten:
        if frei:
            return url, True
    return kandidaten[0][0], False


def _ist_online(record) -> bool:
    """Erkennt elektronische Ausgaben (fernleihe scheidet dann aus).

    Drei unabhängige Nachweise, weil der Verbund sie uneinheitlich pflegt:
    008/23 (Form of item) 'o'/'q', 007/00 'c' (electronic resource) und
    338 $b 'cr' (online resource).
    """
    f008 = _feldtext(record, "008")
    if len(f008) > 23 and f008[23] in ("o", "q"):
        return True
    if _feldtext(record, "007")[:1] == "c":
        return True
    for f in record.get_fields("338"):
        if (f.get("b") or "").strip().lower() == "cr":
            return True
    return False


def _parse_marc(raw_data, isil: Optional[str] = BHT_ISIL) -> dict:
    """
    Parst einen MARC21-Datensatz aus PyZ3950-Rohdaten.
    Gibt ein dict mit bibliografischen Kernfeldern zurück.
    """
    try:
        if isinstance(raw_data, str):
            raw = raw_data.encode("latin-1")
        else:
            raw = bytes(raw_data)

        reader = pymarc.MARCReader(
            io.BytesIO(raw),
            to_unicode=True,
            force_utf8=True,
            utf8_handling="ignore",
        )
        record = next(reader, None)
        if record is None:
            return {}

        def gf(tag: str, code: str = None) -> str:
            f = record.get(tag)
            if f is None:
                return ""
            if code is None:
                return str(f.value()).strip()
            val = f.get(code)
            return val.strip() if val else ""

        def gfa(tag: str, code: str) -> list:
            return [
                f.get(code).strip()
                for f in record.get_fields(tag)
                if f.get(code)
            ]

        titel      = gf("245", "a").rstrip(" /:")
        untertitel = gf("245", "b").rstrip(" /:")
        voller_titel = f"{titel}: {untertitel}" if untertitel else titel

        autoren  = gfa("100", "a") + gfa("700", "a")
        verlag   = gf("264", "b") or gf("260", "b")
        ort      = gf("264", "a") or gf("260", "a")
        jahr     = gf("264", "c") or gf("260", "c")
        isbn_raw = gf("020", "a")
        isbn     = isbn_raw.split()[0] if isbn_raw else ""
        auflage  = gf("250", "a")
        sprache  = gf("041", "a")
        umfang   = gf("300", "a")
        # 653 = freie Schlagwörter; bei Repositoriumssätzen ohne GND-
        # Erschließung ist das die einzige inhaltliche Angabe.
        schlagw  = gfa("650", "a") + gfa("689", "a") + gfa("653", "a")
        ppn      = gf("001")

        # --- Bestand & Signatur aus dem lokalen Bestandsfeld 924 ---
        # WICHTIG: Der KOBV-Verbundkatalog (k2/B3Kat) enthält im 924-Feld der
        # BHT NUR den Besitznachweis ($b=DE-B768), i.d.R. OHNE lokale Signatur
        # ($g fehlt). Die genaue Standortsignatur (z.B. "33.12.242-2") liegt
        # ausschließlich im lokalen BHT-System und ist über diesen Verbund-
        # Z39.50-Zugang NICHT abrufbar.
        # Feld 082 ist die Dewey-Klassifikation (z.B. "025.524") und darf NICHT
        # als Standortsignatur ausgegeben werden.
        signatur = ""
        bht_bestand = None
        felder_924 = record.get_fields("924")
        if isil:
            for f in felder_924:
                owner = (f.get("b") or "").strip()
                if owner.upper() == isil.upper():
                    bht_bestand = True
                    sig = (f.get("g") or "").strip()  # lokale Signatur, FALLS geliefert
                    if sig:
                        signatur = sig
            # Besitznachweise anderer Häuser, aber keiner der BHT: dann ist der
            # Titel nachweislich NICHT im Bestand. Fehlt 924 ganz, bleibt es bei
            # None — "unbekannt" und "nicht vorhanden" dürfen nicht dasselbe
            # Label bekommen, sonst wird aus einer Lücke im Datensatz eine
            # Fernleihbestellung.
            if bht_bestand is None and felder_924:
                bht_bestand = False

        # Klassifikationen – nur zur Orientierung, NICHT die Standortsignatur
        ddc = gf("082", "a")
        rvk = ""
        for f in record.get_fields("084"):
            if (f.get("2") or "").strip().lower() == "rvk":
                rvk = (f.get("a") or "").strip()
                break

        volltext_url, volltext_frei = _volltext_aus_856(record)
        lizenz = " · ".join(t for t in (gf("540", "a"), gf("540", "u")) if t)
        ist_online = _ist_online(record)

        # Bereinigungen
        jahr = jahr.strip(".,©[] ")

        return {
            "titel":         voller_titel or "(kein Titel)",
            "autoren":       autoren or ["(kein Autor)"],
            "verlag":        f"{ort}: {verlag}".strip(": ") if verlag else ort,
            "jahr":          jahr,
            "auflage":       auflage,
            "isbn":          isbn,
            "sprache":       sprache,
            "umfang":        umfang,
            "schlagwoerter": schlagw[:8],
            "signatur":      signatur,      # aus dem Verbund meist leer (siehe oben)
            "bht_bestand":   bht_bestand,   # True, wenn 924 $b == BHT-ISIL
            "ddc":           ddc,           # Dewey-Klassifikation (NICHT Signatur)
            "rvk":           rvk,           # RVK-Notation (NICHT Signatur)
            "ppn":           ppn,
            "volltext_url":  volltext_url,   # 856 $u, nur Links auf das Werk
            "volltext_frei": volltext_frei,  # $z/$3 weisen den Link als frei aus
            "lizenz":        lizenz,         # 540 $a/$u
            "ist_online":    ist_online,     # E-Ressource -> nicht fernleihfähig
        }

    except Exception as e:
        log.warning(f"MARC-Parsing-Fehler: {e}")
        return {}


# ---------------------------------------------------------------------------
# Suchfunktion
# ---------------------------------------------------------------------------

def _suche_einmal(use_attr: int, term: str, isil: Optional[str],
                  max_records: int, auch_freitext: bool = False,
                  bestand_isil: Optional[str] = BHT_ISIL) -> dict:
    """Setzt genau eine Z39.50-Anfrage ab.

    `isil` filtert die Suche, `bestand_isil` wertet den Besitznachweis im
    Datensatz aus. Beide sind absichtlich getrennt: eine Verbundsuche ohne
    Suchfilter soll trotzdem sagen können, welche Treffer die BHT besitzt.
    """
    pqf_query = _pqf(use_attr, term, isil, auch_freitext=auch_freitext)
    log.debug(f"PQF: {pqf_query}")

    try:
        conn = zoom.Connection(Z3950_HOST, Z3950_PORT)
        conn.databaseName = Z3950_DB
        conn.preferredRecordSyntax = "USMARC"

        query = zoom.Query("PQF", pqf_query)
        # Umlaut-Fix: Suchterme in der RPN-Query auf UTF-8-Bytes umstellen,
        # damit PyZ3950 sie nicht als ASCII zu kodieren versucht.
        _terme_auf_utf8(query.query)

        res   = conn.search(query)
        total = len(res)

        treffer = []
        for i in range(min(max_records, total)):
            marc = _parse_marc(res[i].data, bestand_isil)
            if marc:
                treffer.append(marc)

        conn.close()
        return {"treffer_gesamt": total, "treffer": treffer}

    except zoom.ConnectionError as e:
        return {
            "fehler": f"Verbindungsfehler zu {Z3950_HOST}:{Z3950_PORT} – {e}",
            "treffer_gesamt": 0, "treffer": [],
        }
    except zoom.QuerySyntaxError as e:
        return {
            "fehler": f"Ungültige Suchanfrage: {e} (PQF: {pqf_query})",
            "treffer_gesamt": 0, "treffer": [],
        }
    except Exception as e:
        return {
            "fehler": f"Unerwarteter Fehler: {type(e).__name__}: {e}",
            "treffer_gesamt": 0, "treffer": [],
        }


def suche_bht_sync(use_attr: int, term: str,
                   isil: Optional[str] = BHT_ISIL,
                   max_records: int = 10,
                   bestand_isil: Optional[str] = BHT_ISIL) -> dict:
    """
    Synchrone Z39.50-Suche über PyZ3950.

    Der Besitznachweis wird immer gegen `bestand_isil` (Vorgabe: BHT)
    ausgewertet, auch wenn ohne ISIL-Suchfilter im ganzen Verbund gesucht
    wird. Sonst erschiene ein Titel, den die BHT im Regal hat, in der
    Verbundsuche ohne Bestandszeile — und damit als Fernleihfall.

    Eine Schlagwortsuche ohne Treffer bedeutet selten, dass der Bestand nichts
    hergibt — meist ist der Begriff schlicht nicht als GND-Schlagwort
    angesetzt ("Deskilling": 0 als Schlagwort, 115 im Freitext). Dann wird
    dieselbe Anfrage zusätzlich über das Freitextfeld gestellt und das
    Ergebnis als `freitext_fallback` gekennzeichnet, damit der Wechsel im
    Rechercheweg sichtbar wird statt still zu geschehen.
    """
    ergebnis = _suche_einmal(use_attr, term, isil, max_records,
                             bestand_isil=bestand_isil)

    if (use_attr == BIB1_ATTR["subject"]
            and not ergebnis.get("fehler")
            and ergebnis.get("treffer_gesamt", 0) == 0):
        erweitert = _suche_einmal(use_attr, term, isil, max_records,
                                  auch_freitext=True,
                                  bestand_isil=bestand_isil)
        if erweitert.get("treffer_gesamt", 0) > 0:
            erweitert["freitext_fallback"] = True
            ergebnis = erweitert

    if _PLATZHALTER.search(term):
        ergebnis["platzhalter"] = True

    return ergebnis


async def suche_bht(use_attr: int, term: str,
                    isil: Optional[str] = BHT_ISIL,
                    max_records: int = 10,
                    bestand_isil: Optional[str] = BHT_ISIL) -> dict:
    """
    Asynchrone Wrapper-Funktion für suche_bht_sync.
    """
    import asyncio
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        lambda: suche_bht_sync(use_attr, term, isil, max_records,
                               bestand_isil=bestand_isil)
    )
