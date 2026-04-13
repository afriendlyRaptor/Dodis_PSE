import spacy
from spacy.kb import InMemoryLookupKB
from spacy.tokens import DocBin
from pathlib import Path
import numpy as np

def create_mini_kb():
    BASE_PATH = Path(__file__).parent.parent.parent.absolute()
    train_data = BASE_PATH / "data" / "wiki_train_s.spacy"
    output_kb = BASE_PATH / "data" / "mini_entities.kb"

    nlp = spacy.load("de_core_news_sm")
    doc_bin = DocBin(store_user_data=True).from_disk(train_data)
    docs = list(doc_bin.get_docs(nlp.vocab))

    kb = InMemoryLookupKB(vocab=nlp.vocab, entity_vector_length=96)

    entities = {}
    for doc in docs:
        for ent in doc.ents:
            entities[ent.kb_id_] = ent.text

    print(f"registriere {len(entities)} entitäten in der kb")

    for qid, text in entities.items():
        vec_doc = nlp(text)
        vector = vec_doc.vector
        kb.add_entity(entity=qid, freq=100, entity_vector=vector.tolist())
        kb.add_alias(alias=text, entities=[qid], probabilities=[1.0])

    kb.to_disk(output_kb)
    print(f"kb erfolgreich unter {output_kb} gespeichert.")

if __name__ == "__main__":
    create_mini_kb()