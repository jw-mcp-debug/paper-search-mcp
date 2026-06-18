"""
z3950_client.py
===============
Z39.50-Client für den KOBV-Server auf Basis von PyZ3950.

KOBV-Server: z3950.kobv.de:210, Datenbank k2
BHT ISIL:    DE-B768 (Bib-1 Attribut 1044)

Voraussetzungen:
    pip install PyZ3950 pymarc ply
    # ccl.py muss durch Stub ersetzt werden (siehe setup.py)
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

def _pqf(use_attr: int, term: str, isil: Optional[str] = BHT_ISIL) -> str:
    """
    Baut eine PQF-Suchanfrage (Prefix Query Format).

    Mit ISIL-Filter (AND-Verknüpfung):
        @and @attr 1=1044 DE-B768 @attr 1=<use> <term>

    Ohne ISIL-Filter (Verbundsuche):
        @attr 1=<use> <term>

    Mehrwörtige Terme werden in Anführungszeichen gesetzt.
    """
    # Terme mit Leerzeichen in Anführungszeichen
    if " " in term:
        term_pqf = f'"{term}"'
    else:
        term_pqf = term

    main = f"@attr 1={use_attr} {term_pqf}"

    if isil:
        return f"@and @attr 1={BIB1_ATTR['isil']} {isil} {main}"
    return main


# ---------------------------------------------------------------------------
# MARC-Parsing
# ---------------------------------------------------------------------------

def _parse_marc(raw_data) -> dict:
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
            """Erstes Vorkommen eines Feldes oder Unterfeldes."""
            f = record.get(tag)
            if f is None:
                return ""
            if code is None:
                return str(f.value()).strip()
            val = f.get(code)
            return val.strip() if val else ""

        def gfa(tag: str, code: str) -> list:
            """Alle Vorkommen eines Unterfeldes."""
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
        signatur = gf("082", "a") or gf("092", "a")
        ppn      = gf("001")

        # Bereinigungen
        jahr = jahr.strip(".,©[] ")

        return {
            "titel":        voller_titel or "(kein Titel)",
            "autoren":      autoren or ["(kein Autor)"],
            "verlag":       f"{ort}: {verlag}".strip(": ") if verlag else ort,
            "jahr":         jahr,
            "auflage":      auflage,
            "isbn":         isbn,
            "sprache":      sprache,
            "umfang":       umfang,
            "schlagwoerter": schlagw[:8],
            "signatur":     signatur,
            "ppn":          ppn,
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

    Args:
        use_attr:    Bib-1 Use-Attribut (z.B. 4=Titel, 1=Autor, 1016=Any)
        term:        Suchbegriff
        isil:        ISIL für Bestandsfilter (None = Verbundsuche)
        max_records: Maximale Trefferanzahl

    Returns:
        dict mit 'treffer_gesamt', 'treffer' (Liste), optional 'fehler'
    """
    pqf_query = _pqf(use_attr, term, isil)
    log.debug(f"PQF: {pqf_query}")

    try:
        conn = zoom.Connection(Z3950_HOST, Z3950_PORT)
        conn.databaseName = Z3950_DB
        conn.preferredRecordSyntax = "USMARC"

        query = zoom.Query("PQF", pqf_query)
        res   = conn.search(query)
        total = len(res)

        treffer = []
        for i in range(min(max_records, total)):
            marc = _parse_marc(res[i].data)
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
    Führt die synchrone Z39.50-Suche in einem Thread-Pool aus,
    damit der MCP-Server nicht blockiert.
    """
    import asyncio
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        lambda: suche_bht_sync(use_attr, term, isil, max_records)
    )
