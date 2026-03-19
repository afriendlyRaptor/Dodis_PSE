import os
import warnings

# 1. Warnungen unterdrücken (vor den spaCy imports!)
os.environ["CUDA_PATH"] = ""
warnings.filterwarnings("ignore", category=FutureWarning, module="thinc")

import sqlite3
import json
import spacy
# WICHTIG: Wir importieren jetzt den spezifischen KB-Typ
from spacy.kb import InMemoryLookupKB
from pathlib import Path

# Pfade definieren
BASE_PATH = Path(__file__).parent.parent
DB_PATH = BASE_PATH / "data" / "dodis_wikidata.db"
OUTPUT_KB = BASE_PATH / "data" / "dodis_entities.kb"


def build_kb():
    if not DB_PATH.exists():
        print(f"DB nicht gefunden: {DB_PATH}")
        return

    # 2. Modell laden
    print("Lade Transformer Modell...")
    try:
        nlp = spacy.load("de_dep_news_trf")
    except OSError:
        print("Modell 'de_dep_news_trf' nicht gefunden. Bitte 'python -m spacy download de_dep_news_trf' ausführen.")
        return

    # 3. KB Initialisierung (Fix: InMemoryLookupKB statt KnowledgeBase)
    # 768 Dimensionen passen zum Transformer Modell
    kb = InMemoryLookupKB(vocab=nlp.vocab, entity_vector_length=768)

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    print("Starte Extraktion aus der Datenbank...")
    cur.execute("SELECT id, data FROM entities LIMIT 1000")

    for qid, raw_json in cur.fetchall():
        try:
            item_data = json.loads(raw_json)

            # Name finden (Deutsch -> Englisch -> ID als Backup)
            name = item_data['labels'].get('de', item_data['labels'].get('en', qid))

            # Initialer Vektor (wird später im Training verfeinert)
            vector = [0.0] * 768

            # Entität hinzufügen
            kb.add_entity(entity=qid, entity_vector=vector, freq=3)

            # Den Namen als Alias mappen
            kb.add_alias(alias=name, entities=[qid], probabilities=[1.0])

        except Exception as e:
            print(f"Fehler bei {qid}: {e}")
            continue

    # Speichern
    kb.to_disk(OUTPUT_KB)
    print(f"✅ Fertig! KB mit {kb.get_size_entities()} Entitäten unter {OUTPUT_KB} gespeichert.")
    conn.close()


if __name__ == "__main__":
    build_kb()