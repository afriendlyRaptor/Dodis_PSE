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

    # PHASE 1: IDs registrieren
    print("Phase 1: Registriere IDs...")
    for (qid,) in cur.execute("SELECT id FROM entities"):
        kb.add_entity(entity=qid, entity_vector=[0.0] * 768, freq=3)

    # PHASE 2: Aliase im RAM sammeln
    print("Phase 2: Sammle alle Aliase im RAM...")
    full_alias_map = {}

    count = 0
    for qid, raw_json in cur.execute("SELECT id, data FROM entities"):
        data = json.loads(raw_json)
        names = {data['labels'].get('de'), data['labels'].get('en')}
        for lang in ['de', 'en']:
            for a in data.get('aliases', {}).get(lang, []):
                names.add(a)

        for n in names:
            if n:
                if n not in full_alias_map:
                    full_alias_map[n] = []
                # Wir nehmen die ersten 30 Kandidaten pro Name
                if len(full_alias_map[n]) < 30:
                    full_alias_map[n].append(qid)

        count += 1
        if count % 250000 == 0:
            print(f"{count} Entitäten gescannt...")

    # PHASE 3: Alles in einem Rutsch in die KB schreiben
    print(f"Phase 3: Schreibe {len(full_alias_map)} Aliase in die KB...")
    for name, qids in full_alias_map.items():
        probs = [1.0 / len(qids)] * len(qids)
        kb.add_alias(alias=name, entities=qids, probabilities=probs)

    del full_alias_map  # Platz schaffen
    gc.collect()

    print("Speichere KB auf Disk...")
    kb.to_disk(KB_OUTPUT_PATH)
    print("✅ FERTIG!")


if __name__ == "__main__":
    build_kb()