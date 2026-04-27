import gzip
import json
import sqlite3
import requests
from pathlib import Path
from multiprocessing import Pool, cpu_count
import argparse

# KONFIGURATION FÜR DODIS
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

DODIS_TYPES = {
    "Q5": "PER",
    "Q6256": "LOC",
    "Q515": "LOC",
    "Q43229": "ORG",
    "Q7278": "ORG",
    "Q4830453": "ORG",
    "Q82794": "LOC",
    "Q486972": "LOC"
}

DB_NAME = "dodis_wikidata.db"
INPUT_FILE = "wikidata_sample.json.gz"
LIMIT = None

YEAR_MIN = 1848
YEAR_MAX = 2000
PERSON_CLASSES = {"Q5"}

NUM_WORKERS = max(1, cpu_count() - 2)
CHUNK_SIZE = 5000

def fetch_hierarchy_tree():
    """Fragt Wikidata nach allen Unterklassen ab und ordnet sie PER, LOC oder ORG zu."""
    print("Lade Hierarchie-Baum von Wikidata herunter...")

    values_str = " ".join([f"wd:{q}" for q in BASE_CLASSES])
    # NEU: ?base ebenfalls selektieren, um das Mapping zu erhalten
    query = f"""
    SELECT DISTINCT ?class ?base WHERE {{
      VALUES ?base {{ {values_str} }}
      ?class wdt:P279* ?base .
    }}
    """

    url = "https://query.wikidata.org/sparql"
    headers = {
        'User-Agent': 'Dodis_PSE_Bot/1.0 (UniBern)',
        'Accept': 'application/json'
    }

    response = requests.get(url, params={'query': query}, headers=headers)
    response.raise_for_status()
    data = response.json()

    valid_classes = {}

    for item in data['results']['bindings']:
        q_id = item['class']['value'].split('/')[-1]
        base_id = item['base']['value'].split('/')[-1]
        valid_classes[q_id] = DODIS_TYPES[base_id]

    print(f"-> Erfolgreich {len(valid_classes)} relevante Unterklassen gefunden.")
    return valid_classes

def extract_year(claims, prop):
    for claim in claims.get(prop, []):
        try:
            datavalue = claim["mainsnak"]["datavalue"]["value"]
            time_str = datavalue.get("time", "")
            return int(time_str[1:5])
        except (KeyError, ValueError, TypeError):
            continue
    return None

def is_in_time_range(item, matched_class_ids):
    claims = item.get("claims", {})
    is_person = bool(PERSON_CLASSES & matched_class_ids)

    if is_person:
        year = extract_year(claims, "P569")
        if year is None:
            return False
        return YEAR_MIN <= year <= YEAR_MAX
    else:
        year = extract_year(claims, "P571")
        if year is None:
            return True
        return YEAR_MIN <= year <= YEAR_MAX

def process_chunk(args):
    chunk, valid_classes = args
    entities_list = []
    aliases_list = []

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
                matched_class_ids = set()
                for claim in claims["P31"]:
                    try:
                        target_id = claim["mainsnak"]["datavalue"]["value"]["id"]
                        if target_id in valid_classes:
                            matched_class_ids.add(target_id)
                    except KeyError:
                        continue

                if matched_class_ids and is_in_time_range(item, matched_class_ids):
                    entity_id = item['id']
                    # Bestimme den Typ (PER, LOC, ORG)
                    base_q_id = list(matched_class_ids)[0]
                    dodis_type = valid_classes[base_q_id]

                    entities_list.append((entity_id, dodis_type))

                    # Aliase und Labels sammeln
                    names = set()
                    for lang in ["de", "en"]:
                        if lang in item.get("labels", {}):
                            names.add(item["labels"][lang]["value"])
                        if lang in item.get("aliases", {}):
                            for a in item["aliases"][lang]:
                                names.add(a["value"])

                    # Alle gefundenen Namen mit Frequenz 1 einfügen
                    for name in names:
                        aliases_list.append((name, entity_id, 1))

        except json.JSONDecodeError:
            continue

    return entities_list, aliases_list

def setup_database():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("PRAGMA journal_mode = WAL")
    cursor.execute("PRAGMA synchronous = NORMAL")
    cursor.execute("PRAGMA cache_size = -64000")
    cursor.execute("PRAGMA temp_store = MEMORY")

    cursor.execute("CREATE TABLE IF NOT EXISTS entities (id TEXT PRIMARY KEY, type TEXT)")
    cursor.execute('''
                   CREATE TABLE IF NOT EXISTS aliases (
                                                          alias TEXT,
                                                          entity_id TEXT,
                                                          freq INTEGER DEFAULT 0,
                                                          PRIMARY KEY (alias, entity_id)
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

    cursor.execute("SELECT COUNT(*) FROM entities")
    already_saved = cursor.fetchone()[0]
    print(f"Bereits in DB: {already_saved:,} Einträge")

    opener = gzip.open if INPUT_FILE.endswith(".gz") else open

    with opener(INPUT_FILE, "rt", encoding="utf-8") as f_in:
        with Pool(processes=NUM_WORKERS) as pool:

            def generate_chunks():
                chunk = []
                for line in f_in:
                    chunk.append(line)
                    if len(chunk) >= CHUNK_SIZE:
                        yield (chunk, valid_classes)
                        chunk = []
                if chunk:
                    yield (chunk, valid_classes)

            try:
                for entities_batch, aliases_batch in pool.imap_unordered(process_chunk, generate_chunks(), chunksize=4):
                    count_processed += CHUNK_SIZE

                    if entities_batch:
                        cursor.executemany(
                            'INSERT OR IGNORE INTO entities (id, type) VALUES (?, ?)',
                            entities_batch
                        )
                        count_found += len(entities_batch)

                    if aliases_batch:
                        cursor.executemany(
                            'INSERT OR IGNORE INTO aliases (alias, entity_id, freq) VALUES (?, ?, ?)',
                            aliases_batch
                        )

                    if count_processed % 1_000_000 == 0:
                        conn.commit()
                        print(f"Verarbeitet: {count_processed:,} | Gefunden: {count_found:,}")

                    if LIMIT is not None and count_found >= LIMIT:
                        print(f"Limit erreicht. Stoppe.")
                        break
            except EOFError:
                print("Ende der (unvollständigen) Testdatei erreicht – das ist beim Testen normal.")

    conn.commit()
    conn.close()
    print(f"\nFertig! {count_found} Einträge in '{DB_NAME}' gespeichert.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--inputfile")
    parser.add_argument("-o", "--outputPath")
    parser.add_argument("-l", "--limitEntries", nargs='?', const=1, type=int, default=None)
    args, leftovers = parser.parse_known_args()

    # Syntax Error (global) behoben
    if args.outputPath is not None:
        DB_NAME = args.outputPath
    if args.inputfile is not None:
        INPUT_FILE = args.inputfile
    if args.limitEntries is not None:
        LIMIT = args.limitEntries

    if not Path(INPUT_FILE).exists():
        print(f"FEHLER: Eingabedatei '{INPUT_FILE}' nicht gefunden.")
    else:
        valid_q_ids = fetch_hierarchy_tree()
        process_dump_parallel(valid_q_ids)