"""Tests für src/dodis/evaluate_dodis.py"""

import sys
from pathlib import Path

import spacy

from dodis.evaluate_dodis import build_gold_index, compute_accuracy, normalize_dodis_id

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Blank-Modell für spaCy-Docs ohne ML-Abhängigkeit
nlp = spacy.blank("de")


# ---------------------------------------------------------------------------
# compute_accuracy
# ---------------------------------------------------------------------------


def test_accuracy_alles_korrekt():
    assert compute_accuracy(correct=10, total=10) == 1.0


def test_accuracy_nichts_korrekt():
    assert compute_accuracy(correct=0, total=10) == 0.0


def test_accuracy_teilweise_korrekt():
    assert abs(compute_accuracy(correct=3, total=4) - 0.75) < 1e-9


def test_accuracy_total_null_gibt_null():
    """Division durch null → 0.0, kein Fehler."""
    assert compute_accuracy(correct=0, total=0) == 0.0


def test_accuracy_ein_von_einem():
    assert compute_accuracy(correct=1, total=1) == 1.0


def test_accuracy_grosse_zahlen():
    assert abs(compute_accuracy(correct=997, total=1000) - 0.997) < 1e-9


# ---------------------------------------------------------------------------
# normalize_dodis_id
# ---------------------------------------------------------------------------


def test_normalize_http_zu_https():
    assert normalize_dodis_id("http://dodis.ch/P123") == "https://dodis.ch/P123"


def test_normalize_https_bleibt_unveraendert():
    assert normalize_dodis_id("https://dodis.ch/P123") == "https://dodis.ch/P123"


def test_normalize_leerer_string():
    assert normalize_dodis_id("") == ""


def test_normalize_nur_http_prefix():
    assert normalize_dodis_id("http://dodis.ch/") == "https://dodis.ch/"


def test_normalize_org_id():
    assert normalize_dodis_id("http://dodis.ch/O42") == "https://dodis.ch/O42"


def test_normalize_loc_id():
    assert normalize_dodis_id("http://dodis.ch/L7") == "https://dodis.ch/L7"


# ---------------------------------------------------------------------------
# build_gold_index
# ---------------------------------------------------------------------------


def make_doc_with_ents(text: str, ents: list[tuple[int, int, str, str]]):
    """
    Erstellt einen spaCy Doc mit Entities.
    ents: Liste von (char_start, char_end, label, kb_id)
    """
    doc = nlp.make_doc(text)
    spans = []
    for char_start, char_end, label, kb_id in ents:
        span = doc.char_span(char_start, char_end, label=label, kb_id=kb_id)
        if span is not None:
            spans.append(span)
    doc.ents = spans
    return doc


def test_gold_index_eine_entity():
    doc = make_doc_with_ents(
        "Max Petitpierre reiste.",
        [(0, 15, "PER", "https://dodis.ch/P1")],
    )
    index = build_gold_index(doc)
    assert len(index) == 1
    # Wert ist die kb_id
    assert "https://dodis.ch/P1" in index.values()


def test_gold_index_schluessel_sind_token_positionen():
    doc = make_doc_with_ents(
        "Max reiste nach Genf.",
        [(0, 3, "PER", "https://dodis.ch/P1")],
    )
    index = build_gold_index(doc)
    # Schlüssel sind (start, end) Token-Indizes
    for key in index:
        start, end = key
        assert isinstance(start, int)
        assert isinstance(end, int)
        assert start < end


def test_gold_index_entity_ohne_kb_id_wird_ignoriert():
    doc = make_doc_with_ents(
        "Max reiste.",
        [(0, 3, "PER", "")],  # Leere kb_id → wird ignoriert
    )
    index = build_gold_index(doc)
    assert index == {}


def test_gold_index_leeres_doc():
    doc = nlp.make_doc("Kein Text mit Entities.")
    # Keine Entities → leeres dict
    index = build_gold_index(doc)
    assert index == {}


def test_gold_index_mehrere_entities():
    # Einfacher Text: genaue Char-Positionen leicht berechenbar
    # "Karl Paris NATO" → Karl=0-4, Paris=5-10, NATO=11-15
    doc = make_doc_with_ents(
        "Karl Paris NATO",
        [
            (0, 4, "PER", "https://dodis.ch/P1"),
            (5, 10, "LOC", "https://dodis.ch/L2"),
            (11, 15, "ORG", "https://dodis.ch/O3"),
        ],
    )
    index = build_gold_index(doc)
    assert len(index) == 3
    assert set(index.values()) == {
        "https://dodis.ch/P1",
        "https://dodis.ch/L2",
        "https://dodis.ch/O3",
    }


def test_gold_index_normalisiert_http_zu_https():
    doc = make_doc_with_ents(
        "Max reiste.",
        [(0, 3, "PER", "http://dodis.ch/P99")],
    )
    index = build_gold_index(doc)
    assert list(index.values())[0] == "https://dodis.ch/P99"


def test_gold_index_mixed_mit_und_ohne_kb_id():
    """Nur Entities mit kb_id landen im Index."""
    doc = make_doc_with_ents(
        "Karl und Anna reisten.",
        [
            (0, 4, "PER", "https://dodis.ch/P1"),
            (9, 13, "PER", ""),  # kein kb_id
        ],
    )
    index = build_gold_index(doc)
    assert len(index) == 1
    assert "https://dodis.ch/P1" in index.values()
