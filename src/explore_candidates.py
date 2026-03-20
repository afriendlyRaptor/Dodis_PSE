import spacy
from spacy.kb import InMemoryLookupKB
from pathlib import Path

# Pfade
BASE_PATH = Path(__file__).parent.parent
KB_FILE = BASE_PATH / "data" / "dodis_entities.kb"


def explore():
    print("Lade Modell und KB (dauert etwas bei 23.9M Einträgen)...")
    nlp = spacy.load("de_dep_news_trf")
    kb = InMemoryLookupKB(vocab=nlp.vocab, entity_vector_length=768)
    kb.from_disk(KB_FILE)

    while True:
        name = input("\nGib einen Namen zum Testen ein (oder 'exit'): ")
        if name.lower() == 'exit':
            break

        candidates = kb.get_alias_candidates(name)

        if not candidates:
            print(f"  -> Keinen Eintrag für '{name}' gefunden.")
            continue

        print(f"  -> {len(candidates)} Kandidaten für '{name}' gefunden:")

        # Wir sortieren sie nicht, wir schauen uns einfach an, was drin ist
        for i, c in enumerate(candidates):
            # Wir zeigen nur die ersten 10, falls es zu viele sind
            if i > 10:
                print("     ...")
                break
            print(f"     [{i + 1}] ID: {c.entity_} | Prior-Wahrscheinlichkeit: {c.prior_prob:.2f}")


if __name__ == "__main__":
    explore()