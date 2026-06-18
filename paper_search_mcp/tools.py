"""
opac/tools.py
=============
OPAC-/KOBV-Werkzeuge (Z39.50) für die kombinierte BHT-Recherche.

Die vier Tools werden NICHT auf Modulebene registriert, sondern über
`register_opac_tools(mcp)` auf eine bereits bestehende FastMCP-Instanz
gehängt. Dadurch teilen sie sich denselben Server-Prozess mit der
Paper-Suche – ein Connector, ein Endpunkt, alle Tools.

Einbindung im Haupt-Server (paper_search_mcp/server.py), direkt nach
`mcp = FastMCP(...)`:

    from paper_search_mcp.opac.tools import register_opac_tools
    register_opac_tools(mcp)

Die Hilfsfunktionen und Eingabemodelle bleiben auf Modulebene (sie hängen
nicht von der mcp-Instanz ab); nur die mit @mcp.tool dekorierten Funktionen
liegen in register_opac_tools.
"""

from pydantic import BaseModel, Field, ConfigDict

from .z3950_client import suche_bht, BIB1_ATTR, BHT_ISIL


# ---------------------------------------------------------------------------
# Ergebnis-Formatierung
# ---------------------------------------------------------------------------

def _formatiere_treffer(treffer: dict, nummer: int) -> str:
    """Formatiert einen einzelnen Treffer als Markdown-Block."""
    autoren_str = " / ".join(treffer.get("autoren", ["(kein Autor)"]))
    zeilen = [f"### {nummer}. {treffer.get('titel', '(kein Titel)')}"]
    zeilen.append(f"**Autor(en):** {autoren_str}")

    if treffer.get("verlag"):
        zeilen.append(f"**Verlag:** {treffer['verlag']}")
    if treffer.get("jahr"):
        zeilen.append(f"**Jahr:** {treffer['jahr']}")
    if treffer.get("auflage"):
        zeilen.append(f"**Auflage:** {treffer['auflage']}")
    if treffer.get("isbn"):
        zeilen.append(f"**ISBN:** {treffer['isbn']}")
    if treffer.get("umfang"):
        zeilen.append(f"**Umfang:** {treffer['umfang']}")
    if treffer.get("sprache"):
        zeilen.append(f"**Sprache:** {treffer['sprache']}")
    if treffer.get("signatur"):
        zeilen.append(f"**Signatur:** `{treffer['signatur']}`")
    if treffer.get("schlagwoerter"):
        zeilen.append(f"**Schlagwörter:** {' · '.join(treffer['schlagwoerter'])}")
    if treffer.get("ppn"):
        ppn = treffer["ppn"].replace("(DE-599)", "").strip()
        zeilen.append(f"**PPN:** `{ppn}`")

    # Bestandshinweis
    if treffer.get("bht_bestand") is True:
        zeilen.append("**Bestand:** ✅ In der BHT-Bibliothek vorhanden")
    elif treffer.get("bht_bestand") is False:
        zeilen.append("**Bestand:** ℹ️ Nur im Verbund (→ Fernleihe möglich)")

    return "\n".join(zeilen)


def _formatiere_ergebnisse(daten: dict, suchbegriff: str,
                           modus: str = "BHT-OPAC") -> str:
    """Formatiert die komplette Trefferliste als Markdown."""
    if "fehler" in daten and daten["fehler"]:
        return (
            f"## ⚠️ Fehler bei der {modus}-Suche\n\n"
            f"**Suchbegriff:** `{suchbegriff}`\n\n"
            f"**Fehlermeldung:** {daten['fehler']}\n\n"
            f"**Hinweis:** Bitte prüfen Sie die Netzwerkverbindung oder "
            f"wenden Sie sich an die BHT-Bibliothek "
            f"(bibliothek@bht-berlin.de)."
        )

    gesamt = daten.get("treffer_gesamt", 0)
    treffer_liste = daten.get("treffer", [])

    if gesamt == 0:
        return (
            f"## Keine Treffer – {modus}\n\n"
            f"Die Suche nach `{suchbegriff}` ergab keine Ergebnisse.\n\n"
            f"**Tipps zur Verbesserung der Suche:**\n"
            f"- Suchbegriffe vereinfachen oder englische Synonyme verwenden\n"
            f"- Trunkierung nutzen: `Bauphysik` statt `Bauphysikalisch`\n"
            f"- Anderen Suchtyp probieren: Autor statt Titel, oder Schlagwort\n"
            f"- Verbundsuche: Titel aus anderen Berliner Bibliotheken per Fernleihe"
        )

    ausgabe = [
        f"## {modus}: `{suchbegriff}`",
        f"**{gesamt} Treffer gefunden** | Angezeigt: {len(treffer_liste)}\n",
    ]

    for i, t in enumerate(treffer_liste, 1):
        ausgabe.append(_formatiere_treffer(t, i))

    if gesamt > len(treffer_liste):
        ausgabe.append(
            f"\n---\n*{gesamt - len(treffer_liste)} weitere Treffer vorhanden. "
            f"Parameter `max_treffer` erhöhen oder Suche verfeinern.*"
        )

    return "\n\n".join(ausgabe)


# ---------------------------------------------------------------------------
# Input-Modelle
# ---------------------------------------------------------------------------

class OpacSucheInput(BaseModel):
    """Parameter für die allgemeine OPAC-Suche im BHT-Bestand."""
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    suchbegriff: str = Field(
        ...,
        description=(
            "Suchbegriff: Titel, Autor, Schlagwort oder freier Text. "
            "Mehrere Wörter werden als Phrase gesucht, "
            "z.B. 'nachhaltiges Bauen' oder 'Klimaschutz Gebäude'."
        ),
        min_length=2,
        max_length=200,
    )
    suchtyp: str = Field(
        default="any",
        description=(
            "Art der Suche: "
            "'any' = Alle Felder (Standard), "
            "'title' = Nur Titel, "
            "'author' = Nur Autor/Herausgeber, "
            "'subject' = Nur Schlagwort"
        ),
    )
    max_treffer: int = Field(
        default=10,
        description="Maximale Anzahl Treffer (1–25)",
        ge=1, le=25,
    )
    nur_bht_bestand: bool = Field(
        default=True,
        description=(
            "True (Standard): Nur Titel im BHT-Bestand (ISIL DE-B768). "
            "False: Gesamter KOBV-Verbund (für Fernleihe-Recherche)."
        ),
    )


class IsbnSucheInput(BaseModel):
    """Parameter für die ISBN-Suche."""
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    isbn: str = Field(
        ...,
        description="ISBN-10 oder ISBN-13, mit oder ohne Bindestriche",
        min_length=10,
        max_length=20,
    )


class AutorSucheInput(BaseModel):
    """Parameter für die Autorensuche."""
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    autor: str = Field(
        ...,
        description=(
            "Name des Autors oder der Autorin, vorzugsweise als "
            "'Nachname, Vorname' oder nur Nachname"
        ),
        min_length=2,
        max_length=100,
    )
    max_treffer: int = Field(default=10, ge=1, le=25)
    nur_bht_bestand: bool = Field(default=True)


# ---------------------------------------------------------------------------
# Registrierung der Tools auf der geteilten FastMCP-Instanz
# ---------------------------------------------------------------------------

def register_opac_tools(mcp):
    """Hängt die vier OPAC-/KOBV-Tools an die übergebene FastMCP-Instanz."""

    @mcp.tool(
        name="opac_suche",
        annotations={
            "title": "BHT OPAC Suche (Z39.50)",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": True,
        },
    )
    async def opac_suche(params: OpacSucheInput) -> str:
        """
        Durchsucht den OPAC der Berliner Hochschule für Technik (BHT)
        über den Z39.50-Server des KOBV.

        Standardmäßig gefiltert auf den BHT-Bestand (ISIL DE-B768).
        Kann auf den gesamten KOBV-Verbund erweitert werden.
        """
        use_attr = BIB1_ATTR.get(params.suchtyp, BIB1_ATTR["any"])
        isil = BHT_ISIL if params.nur_bht_bestand else None
        modus = "BHT-OPAC" if params.nur_bht_bestand else "KOBV-Verbund"

        daten = await suche_bht(
            use_attr=use_attr,
            term=params.suchbegriff,
            isil=isil,
            max_records=params.max_treffer,
        )
        return _formatiere_ergebnisse(daten, params.suchbegriff, modus)

    @mcp.tool(
        name="opac_isbn_suche",
        annotations={
            "title": "BHT OPAC ISBN-Suche (Z39.50)",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": True,
        },
    )
    async def opac_isbn_suche(params: IsbnSucheInput) -> str:
        """
        Prüft, ob ein Titel anhand der ISBN im BHT-OPAC vorhanden ist.

        Sucht zunächst im BHT-Bestand (ISIL DE-B768). Falls nicht gefunden,
        wird automatisch der gesamte KOBV-Verbund durchsucht und auf
        Fernleihe-Möglichkeiten hingewiesen.
        """
        isbn_clean = params.isbn.replace("-", "").replace(" ", "")

        # Erst BHT-Bestand prüfen
        daten = await suche_bht(
            use_attr=BIB1_ATTR["isbn"],
            term=isbn_clean,
            isil=BHT_ISIL,
            max_records=3,
        )

        if daten.get("treffer_gesamt", 0) > 0:
            return _formatiere_ergebnisse(daten, f"ISBN: {params.isbn}", "BHT-OPAC")

        # Nicht in BHT – Verbund prüfen
        daten_verbund = await suche_bht(
            use_attr=BIB1_ATTR["isbn"],
            term=isbn_clean,
            isil=None,
            max_records=3,
        )

        if daten_verbund.get("treffer_gesamt", 0) > 0:
            ergebnis = _formatiere_ergebnisse(
                daten_verbund, f"ISBN: {params.isbn}", "KOBV-Verbund"
            )
            return (
                f"## ISBN {params.isbn} – Nicht im BHT-Bestand\n\n"
                f"Dieses Werk ist **nicht** in der BHT-Bibliothek vorhanden, "
                f"aber im KOBV-Verbund nachgewiesen:\n\n"
                + ergebnis
                + "\n\n---\n**Fernleihe:** Über das "
                "[KOBV-Portal](https://portal.kobv.de) bestellbar."
            )

        return (
            f"## ISBN {params.isbn} – Nicht gefunden\n\n"
            f"Dieses Werk ist weder im BHT-Bestand noch im KOBV-Verbund nachgewiesen.\n\n"
            f"**Alternativen:**\n"
            f"- Andere ISBN-Ausgabe prüfen (andere Auflage?)\n"
            f"- Suche im [WorldCat](https://search.worldcat.org) (internationale Fernleihe)\n"
            f"- Preprint oder Open-Access-Version bei [BASE](https://base-search.net) suchen"
        )

    @mcp.tool(
        name="opac_autor_suche",
        annotations={
            "title": "BHT OPAC Autorensuche (Z39.50)",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": True,
        },
    )
    async def opac_autor_suche(params: AutorSucheInput) -> str:
        """
        Sucht alle Werke eines Autors/einer Autorin im BHT-OPAC.

        Nützlich um zu prüfen, welche Werke eines Autors die BHT-Bibliothek
        besitzt, z.B. für Semesterapparate oder Lehrbuchlisten.
        """
        isil = BHT_ISIL if params.nur_bht_bestand else None
        modus = f"BHT-OPAC (Autor: {params.autor})"

        daten = await suche_bht(
            use_attr=BIB1_ATTR["author"],
            term=params.autor,
            isil=isil,
            max_records=params.max_treffer,
        )
        return _formatiere_ergebnisse(daten, params.autor, modus)

    @mcp.tool(
        name="kobv_verbund_suche",
        annotations={
            "title": "KOBV Verbundsuche für Fernleihe (Z39.50)",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": True,
        },
    )
    async def kobv_verbund_suche(
        suchbegriff: str = Field(..., description="Suchbegriff (Titel, Schlagwort, freier Text)"),
        suchtyp: str = Field(default="any", description="'any', 'title', 'author', 'subject'"),
        max_treffer: int = Field(default=10, ge=1, le=25),
    ) -> str:
        """
        Durchsucht den gesamten KOBV-Verbundkatalog (alle Bibliotheken
        Berlin-Brandenburg) ohne Einschränkung auf den BHT-Bestand.

        Sinnvoll wenn ein Titel nicht in der BHT vorhanden ist und geprüft
        werden soll, ob er über Fernleihe aus einer anderen KOBV-Bibliothek
        bezogen werden kann.
        """
        use_attr = BIB1_ATTR.get(suchtyp, BIB1_ATTR["any"])

        daten = await suche_bht(
            use_attr=use_attr,
            term=suchbegriff,
            isil=None,   # kein ISIL-Filter = gesamter Verbund
            max_records=max_treffer,
        )

        ergebnis = _formatiere_ergebnisse(daten, suchbegriff, "KOBV-Verbund")
        return (
            ergebnis
            + "\n\n---\n*Titel, die nicht in der BHT sind, können per "
            "**Fernleihe** bestellt werden: "
            "[KOBV-Portal Fernleihe](https://portal.kobv.de)*"
        )
