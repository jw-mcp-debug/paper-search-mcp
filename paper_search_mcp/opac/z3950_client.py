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


def _term_clause(use_attr: int, wort: str) -> str:
    """Baut eine einzelne Term-Klausel '@attr 1=<use> <wort>'."""
    return f"@attr 1={use_attr} {wort}"


def _pqf(use_attr: int, term: str, isil: Optional[str] = BHT_ISIL) -> str:
    """
    Baut eine PQF-Suchanfrage (Prefix Query Format).

    Mehrwort-Verhalten (der eigentliche Trefferquoten-Hebel):
    - any / title / author:  Wörter werden UND-verknüpft
        @and @attr 1=<use> Wort1 @attr 1=<use> Wort2
      (findet Titel, in denen beide Begriffe vorkommen – nicht nur als Phrase)
    - subject / isbn:        Mehrwort bleibt PHRASE ("...")
      (GND-Schlagwörter sind echte Mehrwort-Phrasen)

    Hinweis: Der KOBV-Z39.50-Zugang unterstützt KEINE Trunkierung (weder das
    Bib-1-Attribut 5 noch Platzhalter *,? im Suchwort) – Diagnose "unsupported
    search". Deshalb ist keine Trunkierung implementiert.

    Mit ISIL-Filter wird das Ganze per @and auf den BHT-Bestand eingegrenzt:
        @and @attr 1=1044 DE-B768 <suchausdruck>
    """
    term = term.strip()
    woerter = term.split()

    if len(woerter) <= 1:
        main = _term_clause(use_attr, term)
    elif use_attr in _PHRASE_ATTRS:
        # Mehrwort-Phrase (GND-Schlagwort / ISBN)
        main = _term_clause(use_attr, f'"{term}"')
    else:
        # Mehrere Wörter -> UND-Verknüpfung (Rechtsfaltung der @and-Operatoren)
        clauses = [_term_clause(use_attr, w) for w in woerter]
        main = clauses[-1]
        for c in reversed(clauses[:-1]):
            main = f"@and {c} {main}"

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
        schlagw  = gfa("650", "a") + gfa("689", "a")
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
        for f in record.get_fields("924"):
            owner = (f.get("b") or "").strip()
            if isil and owner.upper() == isil.upper():
                bht_bestand = True
                sig = (f.get("g") or "").strip()  # lokale Signatur, FALLS geliefert
                if sig:
                    signatur = sig

        # Klassifikationen – nur zur Orientierung, NICHT die Standortsignatur
        ddc = gf("082", "a")
        rvk = ""
        for f in record.get_fields("084"):
            if (f.get("2") or "").strip().lower() == "rvk":
                rvk = (f.get("a") or "").strip()
                break

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
        }

    except Exception as e:
        log.warning(f"MARC-Parsing-Fehler: {e}")
        return {}


# ---------------------------------------------------------------------------
# Suchfunktion
# ---------------------------------------------------------------------------

def suche_bht_sync(use_attr: int, term: str,
                   isil: Optional[str] = BHT_ISIL,
                   max_records: int = 10) -> dict:
    """
    Synchrone Z39.50-Suche über PyZ3950.
    """
    pqf_query = _pqf(use_attr, term, isil)
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
            marc = _parse_marc(res[i].data, isil)
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


async def suche_bht(use_attr: int, term: str,
                    isil: Optional[str] = BHT_ISIL,
                    max_records: int = 10) -> dict:
    """
    Asynchrone Wrapper-Funktion für suche_bht_sync.
    """
    import asyncio
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        lambda: suche_bht_sync(use_attr, term, isil, max_records)
    )
