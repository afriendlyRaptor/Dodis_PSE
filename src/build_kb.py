import os
import warnings
import sqlite3
import json
import spacy
from spacy.kb import InMemoryLookupKB
from pathlib import Path
import gc  # Garbage Collector

# 1. Warnungen und CUDA-Pfad unterdrücken
os.environ["CUDA_PATH"] = ""
warnings.filterwarnings("ignore", category=FutureWarning, module="thinc")
warnings.filterwarnings("ignore", message=r".*\[W017\].*", category=UserWarning)

BASE_PATH = Path(__file__).parent.parent
DB_PATH = BASE_PATH / "data" / "dodis_wikidata.db"
OUTPUT_KB = BASE_PATH / "data" / "dodis_entities.kb"


def build_kb():
    if not DB_PATH.exists(): return

    print("Lade Transformer Modell...")
    nlp = spacy.load("de_dep_news_trf")

    # 768 Dimensionen für Transformer
    kb = InMemoryLookupKB(vocab=nlp.vocab, entity_vector_length=768)

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Wir laden die Daten in Batches, um den RAM nicht zu sprengen
    print("Starte massiven KB-Aufbau (Vollständiger Dump)...")
    cur.execute("SELECT id, data FROM entities")

    processed_count = 0

    while True:
        # in 50'000 batches verarbeiten
        rows = cur.fetchmany(50000)
        if not rows:
            break

        for qid, raw_json in rows:
            try:
                item_data = json.loads(raw_json)

                # Fokus auf Deutsch und Englisch (falls beides nicht vorhanden qid)
                name = item_data['labels'].get('de', item_data['labels'].get('en', qid))

                # Wir sammeln Aliase (Set verhindert Duplikate)
                all_aliases = {name}
                for lang in ['de', 'en']:
                    for a in item_data.get('aliases', {}).get(lang, []):
                        all_aliases.add(a)

                # Zur Knowledge Base hinzufügen
                kb.add_entity(entity=qid, entity_vector=[0.0] * 768, freq=3)

                for alias_name in all_aliases:
                    try:
                        kb.add_alias(alias=alias_name, entities=[qid], probabilities=[1.0])
                    except:
                        pass

                processed_count += 1

            except Exception:
                continue

        # Kleines Status-Update und RAM-Cleanup
        print(f"Fortschritt: {processed_count} Entitäten verarbeitet...")
        gc.collect()

    print("Schreibe KB auf Festplatte (das kann bei Millionen Einträgen dauern)...")
    kb.to_disk(OUTPUT_KB)
    print(f"✅ Fertig! Insgesamt {kb.get_size_entities()} Entitäten gespeichert.")
    conn.close()


if __name__ == "__main__":
    build_kb()