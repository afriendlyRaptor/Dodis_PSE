import gzip
import json
import sqlite3
import requests
from pathlib import Path
from multiprocessing import Pool, Queue, Process, cpu_count
import multiprocessing as mp

#KONFIGURATION FÜR DODIS
BASE_CLASSES = [
    "Q5",        # Human (PER)
    "Q6256",     # Country (LOC)
    "Q515",      # City (LOC)
    "Q43229",    # Organization (ORG)
    "Q7278",     # Political Party (ORG)
    "Q4830453",  # Business Enterprise (ORG)
    "Q82794",    # Geographic Region (LOC)
    "Q486972"    # Human Settlement (LOC)
]

DB_NAME = "dodis_wikidata.db"
INPUT_FILE = "wikidata_sample.json.gz" # Dein Download-Sample
LIMIT = None # Kann beliebeig angepasst werden (NEU: Angepasst für höheres Limit)

#NEU: Multiprocessing-Konfiguration für bessere Performance
NUM_WORKERS = max(1, cpu_count() - 2)  # Alle Kerne minus Reader + Writer
CHUNK_SIZE = 5000  # Zeilen pro Paket

def fetch_hierarchy_tree():
    """
    Fragt Wikidata (via SPARQL) nach allen Unterklassen (P279) unserer Basisklassen.
    Dadurch erfassen wir den gesamten Baum (z.B. alle Arten von Städten/Organisationen).
    """
    print("Lade Hierarchie-Baum von Wikidata herunter")

    # Baut den SPARQL Query auf (wdt:P279* bedeutet "Unterklasse von", 0 bis unendlich mal)
    values_str = " ".join([f"wd:{q}" for q in BASE_CLASSES])
    query = f"""
    SELECT DISTINCT ?class WHERE {{
      VALUES ?base {{ {values_str} }}
      ?class wdt:P279* ?base .
    }}
    """

    # Metadaten für die API-Abfrage
    url = "https://query.wikidata.org/sparql"
    headers = {
        'User-Agent': 'Dodis_PSE_Bot/1.0 (UniBern)',
        'Accept': 'application/json'
    }

    response = requests.get(url, params={'query': query}, headers=headers)
    response.raise_for_status()

    data = response.json()
    valid_classes = set()

    for item in data['results']['bindings']:
        # Extrahiert die Q-ID aus der URL (z.B. http://www.wikidata.org/entity/Q123 -> Q123)
        q_id = item['class']['value'].split('/')[-1]
        valid_classes.add(q_id)

    print(f"-> Erfolgreich {len(valid_classes)} relevante Unterklassen gefunden.")
    return valid_classes

#NEU: Funktion zum Extrahieren nur der relevanten Felder für NER
def extract_relevant_fields(item):
    """Nur das Nötigste für NER"""
    return {
        "id": item.get("id"),
        "labels": {
            lang: item["labels"][lang]["value"]
            for lang in ["de", "en"]
            if lang in item.get("labels", {})
        },
        "aliases": {
            lang: [a["value"] for a in item["aliases"][lang]]
            for lang in ["de", "en"]
            if lang in item.get("aliases", {})
        },
        "claims": {
            "P31": [
                claim["mainsnak"]["datavalue"]["value"]["id"]
                for claim in item.get("claims", {}).get("P31", [])
                if "datavalue" in claim.get("mainsnak", {})
            ]
        }
    }

def process_chunk(args):
    """Wird von jedem Worker-Prozess aufgerufen. Verarbeitet ein Paket Zeilen."""
    chunk, valid_classes = args
    results = []
    for line in chunk:
        line = line.strip()
        if line in ["[", "]"] or not line:
            continue
        if line.endswith(","):
            line = line[:-1]
        try:
            item = json.loads(line)
            claims = item.get("claims", {})
            if "P31" in claims:
                for claim in claims["P31"]:
                    try:
                        target_id = claim["mainsnak"]["datavalue"]["value"]["id"]
                        if target_id in valid_classes:
                            small_item = extract_relevant_fields(item) #NEU: Nur relevante Felder extrahieren
                            results.append((item['id'], json.dumps(small_item)))
                            break
                    except KeyError:
                        continue
        except json.JSONDecodeError:
            continue
    return results

def setup_database():
    #Erstellt die SQLite-Datenbank und die Tabelle.
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # NEU: Performance-Optimierungen für grosse Datenmengen
    cursor.execute("PRAGMA journal_mode = WAL")       # Schnelleres Schreiben
    cursor.execute("PRAGMA synchronous = NORMAL")     # Weniger Disk-Flushes
    cursor.execute("PRAGMA cache_size = -64000")      # 64 MB Cache
    cursor.execute("PRAGMA temp_store = MEMORY")      # Temp-Daten im RAM
    
    # Wir speichern die ID (z.B. Q123) als Primary Key und die rohen JSON-Daten
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS entities (
            id TEXT PRIMARY KEY,
            data JSON
        )
    ''')
    conn.commit()
    return conn

def process_dump_parallel(valid_classes):
    print(f"\nStarte parallele Verarbeitung mit {NUM_WORKERS} Worker-Prozessen...")
    conn = setup_database()
    cursor = conn.cursor()

    count_found = 0
    count_processed = 0

    # Wieviele Einträge bereits in der DB?
    cursor.execute("SELECT COUNT(*) FROM entities")
    already_saved = cursor.fetchone()[0]
    print(f"Bereits in DB: {already_saved:,} Einträge")

    opener = gzip.open if INPUT_FILE.endswith(".gz") else open

    with opener(INPUT_FILE, "rt", encoding="utf-8") as f_in:
        with Pool(processes=NUM_WORKERS) as pool:
            
            # Zeilen in Pakete aufteilen
            def generate_chunks():
                chunk = []
                for line in f_in:
                    chunk.append(line)
                    if len(chunk) >= CHUNK_SIZE:
                        yield (chunk, valid_classes)
                        chunk = []
                if chunk:
                    yield (chunk, valid_classes)

            # Pakete parallel verarbeiten
            for batch_results in pool.imap_unordered(process_chunk, generate_chunks(), chunksize=4):
                count_processed += CHUNK_SIZE

                if batch_results:
                    cursor.executemany(
                        'INSERT OR IGNORE INTO entities (id, data) VALUES (?, ?)',
                        batch_results
                    )
                    count_found += len(batch_results)

                # Fortschritt
                if count_processed % 1_000_000 == 0:
                    conn.commit()
                    print(f"Verarbeitet: {count_processed:,} | Gefunden: {count_found:,}")

                if LIMIT is not None and count_found >= LIMIT:
                    print(f"Limit erreicht. Stoppe.")
                    break

    conn.commit()
    conn.close()
    print(f"\nFertig! {count_found} Einträge in '{DB_NAME}' gespeichert.")

if __name__ == "__main__":
    if not Path(INPUT_FILE).exists():
        print(f"FEHLER: Eingabedatei '{INPUT_FILE}' nicht gefunden.")
    else:
        # 1. Hierarchie-Baum holen
        valid_q_ids = fetch_hierarchy_tree()
        # 2. Dump filtern und in DB speichern
        process_dump_parallel(valid_q_ids)