"""
Dodis NER Pipeline – Weg 1 (regelbasiert, kein Training)
=========================================================
Erkennt Personen, Orte und Organisationen in Texten
mithilfe der Wikidata-Patterns.

Voraussetzungen:
    pip install spacy
    python -m spacy download de_core_news_lg

Verwendung:
    python dodis_ner.py
"""

import json
import spacy
from pathlib import Path

# ─── Konfiguration ────────────────────────────────────────────────────────────

PATTERNS_FILE   = Path("./spacy_output/patterns.jsonl")
ENTITY_LOOKUP   = Path("./spacy_output/entity_list.json")
SPACY_MODEL     = "de_core_news_lg"   # oder "en_core_web_lg" für Englisch


# ─── Pipeline aufbauen ────────────────────────────────────────────────────────

def build_pipeline(model: str = SPACY_MODEL) -> spacy.Language: # type: ignore
    """Lädt spaCy + EntityRuler mit Wikidata-Patterns."""
    print(f"Lade Sprachmodell: {model} ...")
    nlp = spacy.load(model)

    # EntityRuler VOR dem bestehenden NER einfügen
    # overwrite_ents=True → Wikidata-Patterns haben Vorrang
    ruler = nlp.add_pipe("entity_ruler", before="ner", config={
        "overwrite_ents": True,
        "phrase_matcher_attr": "LOWER",  # case-insensitiv: "einstein" = "Einstein"
    })

    print(f"Lade Patterns: {PATTERNS_FILE} ...")
    ruler.from_disk(str(PATTERNS_FILE))
    print(f"✓ Pipeline bereit\n")
    return nlp


# ─── Entity-Lookup laden ──────────────────────────────────────────────────────

def load_lookup(path: Path = ENTITY_LOOKUP) -> dict:
    """Lädt die QID → Metadaten Tabelle."""
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


# ─── Text analysieren ─────────────────────────────────────────────────────────

def analyze(text: str, nlp: spacy.Language, lookup: dict) -> list[dict]: # type: ignore
    """
    Analysiert einen Text und gibt alle erkannten Entitäten zurück.

    Rückgabe: Liste von Dicts mit:
        text    – erkannter Name im Text
        label   – NER-Label (PER / LOC / ORG)
        qid     – Wikidata QID (falls gefunden)
        label_de – deutscher Name aus Wikidata
        label_en – englischer Name aus Wikidata
        start   – Zeichenposition Anfang
        end     – Zeichenposition Ende
    """
    doc = nlp(text)
    results = []

    for ent in doc.ents:
        qid      = ent.ent_id_ or None   # QID aus EntityRuler-Pattern
        meta     = lookup.get(qid, {}) if qid else {}
        results.append({
            "text":     ent.text,
            "label":    ent.label_,
            "qid":      qid,
            "label_de": meta.get("label_de", ""),
            "label_en": meta.get("label_en", ""),
            "start":    ent.start_char,
            "end":      ent.end_char,
        })

    return results


def print_results(text: str, entities: list[dict]) -> None:
    """Gibt die Ergebnisse übersichtlich aus."""
    print(f"TEXT: {text}")
    print(f"{'─'*60}")
    if not entities:
        print("  Keine Entitäten gefunden.")
    for e in entities:
        qid_str = f"[{e['qid']}]" if e['qid'] else ""
        wiki    = f"→ {e['label_de']}" if e['label_de'] and e['label_de'] != e['text'] else ""
        print(f"  {e['label']:<4}  {e['text']:<30} {qid_str:<12} {wiki}")
    print()


# ─── Hauptprogramm ────────────────────────────────────────────────────────────

if __name__ == "__main__":

    # Pipeline + Lookup laden
    nlp    = build_pipeline()
    lookup = load_lookup()

    # ── Beispieltexte (hier eigene Dodis-Texte einfügen) ──────────────────────
    texte = [
        "Albert Einstein reiste nach Genf, um mit dem Völkerbund zu sprechen.",
        "Der Schweizer Bundesrat diskutierte mit Frankreich über die Neutralitätspolitik.",
        "Die UNO und das Rote Kreuz unterzeichneten ein Abkommen in New York.",
        "Winston Churchill traf sich mit Charles de Gaulle in London.",
        "Die Sowjetunion und die USA verhandelten in Wien über Abrüstung.",
    ]

    for text in texte:
        entities = analyze(text, nlp, lookup)
        print_results(text, entities)

    # ── Interaktiver Modus: eigenen Text eingeben ──────────────────────────────
    print("═" * 60)
    print("INTERAKTIVER MODUS – Text eingeben (Enter zum Beenden):")
    print("═" * 60)
    while True:
        text = input("\nText: ").strip()
        if not text:
            break
        entities = analyze(text, nlp, lookup)
        print_results(text, entities)