import sqlite3
import json
import spacy
from spacy.kb import InMemoryLookupKB
from pathlib import Path
import gc


def build_kb():
    BASE_PATH = Path(__file__).parent.parent
    DB_PATH = BASE_PATH / "data" / "dodis_wikidata.db"
    KB_OUTPUT_PATH = BASE_PATH / "data" / "dodis_entities.kb"

    nlp = spacy.load("de_dep_news_trf")
    kb = InMemoryLookupKB(vocab=nlp.vocab, entity_vector_length=768)
    conn = sqlite3.connect(str(DB_PATH))
    cur = conn.cursor()

    print("Phase 1: Registriere IDs und sammle Namen...")
    full_alias_map = {}
    registered_ids = set()

    for qid, raw_json in cur.execute("SELECT id, data FROM entities"):
        # ID registrieren (nur einmal)
        if qid not in registered_ids:
            kb.add_entity(entity=qid, entity_vector=[0.0] * 768, freq=3)
            registered_ids.add(qid)

        # Namen extrahieren
        data = json.loads(raw_json)
        names = set()

        # Labels holen
        for lang in ['de', 'en']:
            label = data.get('labels', {}).get(lang, {}).get('value')
            if label: names.add(label)

            # Aliase holen
            for entry in data.get('aliases', {}).get(lang, []):
                names.add(entry.get('value'))

        # Aliase mappen
        for n in names:
            if n:
                if n not in full_alias_map:
                    full_alias_map[n] = []
                if qid not in full_alias_map[n] and len(full_alias_map[n]) < 30:
                    full_alias_map[n].append(qid)

    print(f"Phase 2: Schreibe {len(full_alias_map)} Aliase in die KB...")
    for name, qid_list in full_alias_map.items():
        probs = [1.0 / len(qid_list)] * len(qid_list)
        kb.add_alias(alias=name, entities=qid_list, probabilities=probs)

    conn.close()
    kb.to_disk(KB_OUTPUT_PATH)
    print(f"✅ FERTIG! {len(registered_ids)} Entitäten in KB.")


if __name__ == "__main__":
    build_kb()