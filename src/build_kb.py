import os
import warnings
import sqlite3
import json
import spacy
from spacy.kb import InMemoryLookupKB
from pathlib import Path

# 1. Warnungen unterdrücken, damit die Konsole sauber bleibt
os.environ["CUDA_PATH"] = ""
warnings.filterwarnings("ignore", category=FutureWarning, module="thinc")

# Pfade relativ zum Projekt-Root definieren
BASE_PATH = Path(__file__).parent.parent
DB_PATH = BASE_PATH / "data" / "dodis_wikidata.db"
OUTPUT_KB = BASE_PATH / "data" / "dodis_entities.kb"


def build_kb():
    # Prüfen ob die Datenbank am richtigen Ort liegt
    if not DB_PATH.exists():
        print(f"Fehler: Datenbank nicht gefunden unter {DB_PATH}")
        return

    # 2. Transformer Modell laden (für das Vokabular)
    print("Lade das Transformer Modell (de_dep_news_trf)...")
    try:
        nlp = spacy.load("de_dep_news_trf")
    except OSError:
        print("Modell nicht gefunden. Bitte 'python -m spacy download de_dep_news_trf' ausführen.")
        return

    # 3. Knowledge Base initialisieren
    # Wir nutzen InMemoryLookupKB für spaCy v3
    # 768 ist die Vektor-Dimension für dieses Transformer Modell
    kb = InMemoryLookupKB(vocab=nlp.vocab, entity_vector_length=768)

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    print("Starte Daten-Extraktion und Alias-Mapping...")

    # HINWEIS: Für den finalen Durchlauf das 'LIMIT 1000' entfernen!
    cur.execute("SELECT id, data FROM entities LIMIT 1000")

    processed_count = 0

    for qid, raw_json in cur.fetchall():
        try:
            item_data = json.loads(raw_json)

            # Hauptnamen extrahieren (Deutsch vor Englisch)
            main_name = item_data['labels'].get('de', item_data['labels'].get('en', qid))

            # Alle Aliase sammeln (Synonyme für die ID)
            # Wir nutzen ein Set, um doppelte Namen zu vermeiden
            all_aliases = {main_name}
            for lang in ['de', 'en']:
                lang_aliases = item_data.get('aliases', {}).get(lang, [])
                for a in lang_aliases:
                    all_aliases.add(a)

            # Entität in der KB registrieren (initialer Null-Vektor)
            # Dieser Vektor wird später beim Training des Linkers wichtig
            vector = [0.0] * 768
            kb.add_entity(entity=qid, entity_vector=vector, freq=3)

            # JEDEN Alias mit dieser QID verknüpfen
            for alias_name in all_aliases:
                # Wir setzen die Wahrscheinlichkeit (Prior) erstmal auf 1.0
                # Wenn ein Name für mehrere QIDs existiert, regelt spaCy das intern
                try:
                    kb.add_alias(alias=alias_name, entities=[qid], probabilities=[1.0])
                except Exception:
                    # Falls spaCy eine Warnung wirft (Alias existiert schon), ignorieren wir das
                    pass

            processed_count += 1
            if processed_count % 100 == 0:
                print(f"Fortschritt: {processed_count} Entitäten verarbeitet...")

        except Exception as e:
            print(f"Fehler bei {qid}: {e}")
            continue

    # 4. Speichern der fertigen KB auf die Festplatte
    # Erstellt einen Ordner mit binären Dateien
    kb.to_disk(OUTPUT_KB)

    print("-" * 30)
    print(f"✅ Fertig! KB gespeichert unter: {OUTPUT_KB}")
    print(f"Gesamtanzahl Entitäten: {kb.get_size_entities()}")

    conn.close()


if __name__ == "__main__":
    build_kb()