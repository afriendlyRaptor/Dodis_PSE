import spacy
from spacy.kb import InMemoryLookupKB
from pathlib import Path

# Pfade
BASE_PATH = Path(__file__).parent.parent
KB_FILE = BASE_PATH / "data" / "dodis_entities.kb"


def explore():
    print("lade modell und kb (dauert etwas bei 23.9 millionen einträgen)")
    nlp = spacy.load("de_dep_news_trf")
    kb = InMemoryLookupKB(vocab=nlp.vocab, entity_vector_length=768)
    kb.from_disk(KB_FILE)

    while True:
        name = input("\ngib einen namen zum testen ein (oder 'exit'): ")
        if name.lower() == 'exit':
            break

        candidates = kb.get_alias_candidates(name)

        if not candidates:
            print(f"  -> keinen eintrag für '{name}' gefunden.")
            continue

        print(f"  -> {len(candidates)} kandidaten für '{name}' gefunden:")

        for i, c in enumerate(candidates):
            if i > 10:
                print("     ...")
                break
            print(f"     [{i + 1}] ID: {c.entity_} | wahrscheinlichkeit: {c.prior_prob:.2f}")


if __name__ == "__main__":
    explore()