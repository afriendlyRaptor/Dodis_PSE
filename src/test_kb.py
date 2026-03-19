import os
import warnings
import spacy
from spacy.kb import InMemoryLookupKB
from pathlib import Path

# Pfade
BASE_PATH = Path(__file__).parent.parent
KB_FILE = BASE_PATH / "data" / "dodis_entities.kb"


def validate_my_kb():
    print("Lade Modell und Knowledge Base...")
    nlp = spacy.load("de_dep_news_trf")

    # KB laden
    kb = InMemoryLookupKB(vocab=nlp.vocab, entity_vector_length=768)
    kb.from_disk(KB_FILE)

    print(f"KB erfolgreich geladen. Größe: {kb.get_size_entities()} Entitäten.")
    print("-" * 30)

    # Test-Namen prüfen
    test_names = ["Nicolaus Copernicus", "Bern", "Schweiz"]

    for name in test_names:
        candidates = kb.get_alias_candidates(name)
        print(f"Suche nach: '{name}'")
        if not candidates:
            print("  -> Keine Entität gefunden.")
        else:
            print(f"  -> {len(candidates)} Kandidaten gefunden:")
            for c in candidates:
                print(f"     ID: {c.entity_} | Wahrscheinlichkeit: {c.prior_prob:.2f}")
        print("-" * 30)


if __name__ == "__main__":
    validate_my_kb()