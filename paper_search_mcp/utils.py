import re

def extract_doi(text: str) -> str:
    """Extract DOI from arbitrary text or URL if present."""
    if not text:
        return ""
    match = re.search(r"10\.\d{4,9}/[-._;()/:A-Z0-9]+", text, re.IGNORECASE)
    return match.group(0).rstrip(".,;)") if match else ""


def quelle_felder(quelle_obj: dict) -> dict:
    """Die Zeitschriftenfelder aus einem OpenAlex-``primary_location.source``.

    Leere und falsche Werte werden weggelassen. Die Felder hängen an jedem
    OpenAlex-Treffer, und ein ``"in_doaj": false`` an jeder Zeile kostet Tokens,
    ohne etwas auszusagen — es steht dort schlicht, wenn es zutrifft.
    """
    quelle_obj = quelle_obj or {}
    felder = {
        "journal": quelle_obj.get("display_name") or "",
        "quelle_id": (quelle_obj.get("id") or "").rstrip("/").rsplit("/", 1)[-1],
        "issn_l": quelle_obj.get("issn_l") or "",
        "quelle_typ": quelle_obj.get("type") or "",
        "zeitschrift_oa": bool(quelle_obj.get("is_oa")),
        "in_doaj": bool(quelle_obj.get("is_in_doaj")),
    }
    return {schluessel: wert for schluessel, wert in felder.items() if wert}
