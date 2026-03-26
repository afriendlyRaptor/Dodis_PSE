import spacy
from spacy.kb import InMemoryLookupKB
from spacy.tokens import DocBin
from pathlib import Path


def create_mini_kb():
    BASE_PATH = Path(__file__).parent.parent.absolute()
    train_data = BASE_PATH / "data" / "train.spacy"
    output_kb = BASE_PATH / "data" / "mini_entities.kb"

    nlp = spacy.blank("de")
    doc_bin = DocBin(store_user_data=True).from_disk(train_data)
    docs = list(doc_bin.get_docs(nlp.vocab))

    # vektorlänge 768 passend für BERT/Transformer
    kb = InMemoryLookupKB(vocab=nlp.vocab, entity_vector_length=768)

    entities = {}  # qid -> text

    for doc in docs:
        for ent in doc.ents:
            entities[ent.kb_id_] = ent.text

    print(f"registriere {len(entities)} entitäten in der kb")

    for qid, text in entities.items():
        # entity hinzufügen
        kb.add_entity(entity=qid, freq=100, entity_vector=[0.0] * 768)
        # alias hinzufügen
        kb.add_alias(alias=text, entities=[qid], probabilities=[1.0])

    kb.to_disk(output_kb)
    print(f"kb erfolgreich unter {output_kb} gespeichert.")


if __name__ == "__main__":
    create_mini_kb()