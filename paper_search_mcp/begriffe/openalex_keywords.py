"""
begriffe/openalex_keywords.py
=============================
Englisches Suchvokabular aus den OpenAlex-Keywords (Stand Oktober 2026).

Seit 2026-10 vergibt OpenAlex Keywords aus Titel und Abstract — 1,88 Mio.
Begriffe, englisch, auch für deutsch- und anderssprachige Arbeiten. Drei
Endpunkte machen daraus eine Vokabularquelle für die Suchbegriffstabelle:

- ``/text/keywords?title=…`` taggt beliebigen Text, auch deutschen
  („Wärmepumpen im Altbau" -> heat pumps, old buildings, building retrofit).
  Kostet 0,01 $ je Aufruf — zehnmal so viel wie eine Suche. Mit Key reicht das
  Tagesbudget (1 $) für 100 Aufrufe, ohne Key (0,10 $) für zehn.
- ``/keywords?filter=id:a|b|c`` liefert Werkzahl und Schreibvarianten aller
  Begriffe in einem Request (0,0001 $).
- ``/autocomplete/keywords?q=…`` liefert verwandte, meist engere Begriffe mit
  Werkzahl (kostenlos).

HTTP-Schicht, API-Key und Fehlerübersetzung kommen aus
``citations/openalex_graph.py``.
"""

from __future__ import annotations

import logging
from typing import Dict, List

from ..citations.openalex_graph import OpenAlexFehler, hole_json, kurz_id

logger = logging.getLogger(__name__)

TEXT_KEYWORDS = "https://api.openalex.org/text/keywords"
KEYWORDS = "https://api.openalex.org/keywords"
AUTOCOMPLETE = "https://api.openalex.org/autocomplete/keywords"

# /text verlangt Titel + Abstract zusammen mindestens 20 Zeichen und antwortet
# sonst mit HTTP 400. Vorher prüfen, statt einen Request zu verschwenden.
MIN_ZEICHEN = 20
# Ein Thema in einem Absatz; längere Texte werden abgeschnitten, damit die URL
# unter der OpenAlex-Grenze von rund 4.000 Zeichen bleibt.
MAX_ZEICHEN = 1500

MAX_SYNONYME = 4
# Varianten nur zu den zwei stärksten spezifischen Begriffen. Zu einem
# Allerweltsbegriff liefert die Autovervollständigung fachfremdes Rauschen
# ('artificial intelligence' -> '… in healthcare', 'accessibility' ->
# 'chromatin accessibility'), und jede Liste kostet Kontext.
VARIANTEN_ZU = 2
MAX_VARIANTEN = 4
SPEZIFISCH_MAX_WERKE = 50_000

# Prozessweiter Cache: /text ist der teure Aufruf, und ein Thema wird in einer
# Sitzung gern zweimal angefragt (Stufe 0, dann „p").
_CACHE: Dict[str, Dict] = {}


def cache_leeren() -> None:
    """Nur für Tests und für einen erzwungenen Neuabruf."""
    _CACHE.clear()


def _kern(begriff: str) -> str:
    """Vergleichsform: Kleinschreibung, ohne Plural-s, ohne Bindestriche.

    'skilled labour shortages' und 'skilled labour shortage' sind für die
    Suche dasselbe; als Synonym ausgegeben kosten sie nur Kontext.
    """
    wort = " ".join((begriff or "").lower().replace("-", " ").split())
    return wort[:-1] if wort.endswith("s") else wort


def synonyme(name: str, alternativen: List[str]) -> List[str]:
    """Schreibvarianten ohne bloße Plural-, Groß- oder Bindestrich-Formen."""
    gesehen = {_kern(name)}
    ergebnis = []
    for alt in alternativen or []:
        kern = _kern(alt)
        if kern in gesehen:
            continue
        gesehen.add(kern)
        ergebnis.append(alt)
        if len(ergebnis) == MAX_SYNONYME:
            break
    return ergebnis


def _tagge(text: str) -> List[Dict]:
    antwort = hole_json(TEXT_KEYWORDS, {"title": text})
    return [
        {"id": kurz_id(k.get("id", "")), "begriff": k.get("display_name") or "",
         "relevanz": round(float(k.get("score") or 0), 2)}
        for k in antwort.get("keywords") or []
        if k.get("id") and k.get("display_name")
    ]


def _kennzahlen(ids: List[str]) -> Dict[str, Dict]:
    antwort = hole_json(KEYWORDS, {
        "filter": "id:" + "|".join(ids),
        "select": "id,display_name,works_count,display_name_alternatives",
        "per_page": len(ids),
    })
    return {kurz_id(k.get("id", "")): k for k in antwort.get("results") or []}


def _varianten(begriff: Dict, bekannt: set) -> List[Dict]:
    antwort = hole_json(AUTOCOMPLETE, {"q": begriff["begriff"]})
    ergebnis = []
    for treffer in antwort.get("results") or []:
        kennung = kurz_id(treffer.get("id", ""))
        if not kennung or kennung in bekannt or not treffer.get("works_count"):
            continue
        bekannt.add(kennung)
        ergebnis.append({
            "begriff": treffer.get("display_name") or "",
            "werke": treffer["works_count"],
            "zu": begriff["begriff"],
        })
        if len(ergebnis) == MAX_VARIANTEN:
            break
    return ergebnis


def vorschlagen(text: str) -> Dict:
    """Taggt den Text und reichert die Begriffe mit Werkzahl und Varianten an.

    Raises:
        OpenAlexFehler: Text zu kurz oder OpenAlex nicht verfügbar. Fällt nur
            der Anreicherungsschritt aus, kommen die Begriffe trotzdem zurück.
    """
    text = " ".join((text or "").split())
    if len(text) < MIN_ZEICHEN:
        raise OpenAlexFehler(
            f"Text zu kurz ({len(text)} Zeichen, mindestens {MIN_ZEICHEN}). "
            "Das Thema in einem Satz beschreiben, nicht als Stichwort — "
            "„Wärmepumpen im Altbau“ statt „Wärmepumpe“."
        )
    text = text[:MAX_ZEICHEN]
    if text in _CACHE:
        return _CACHE[text]

    begriffe = sorted(_tagge(text), key=lambda b: -b["relevanz"])
    ergebnis: Dict = {"begriffe": begriffe, "varianten": []}
    if not begriffe:
        return ergebnis

    try:
        daten = _kennzahlen([b["id"] for b in begriffe])
        for b in begriffe:
            eintrag = daten.get(b["id"]) or {}
            if eintrag.get("works_count") is not None:
                b["werke"] = eintrag["works_count"]
            gleich = synonyme(b["begriff"], eintrag.get("display_name_alternatives") or [])
            if gleich:
                b["synonyme"] = gleich

        bekannt = {b["id"] for b in begriffe}
        spezifisch = [b for b in begriffe if 0 < b.get("werke", 0) <= SPEZIFISCH_MAX_WERKE]
        for b in spezifisch[:VARIANTEN_ZU]:
            ergebnis["varianten"] += _varianten(b, bekannt)
    except OpenAlexFehler as exc:
        # Die Begriffe selbst sind das Ergebnis; Werkzahlen und Varianten sind
        # Zugabe. Den teuren /text-Aufruf nicht wegen der Zugabe verwerfen.
        logger.warning("begriffe_vorschlagen: Anreicherung fehlgeschlagen: %s", exc)
        ergebnis["errors"] = {"openalex": f"Werkzahlen/Varianten fehlen: {exc}"}

    for b in begriffe:
        del b["id"]
    if "errors" not in ergebnis:
        _CACHE[text] = ergebnis
    return ergebnis
