import gzip
import json
import sqlite3
import requests
from pathlib import Path

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
LIMIT = 5000 # Kann beliebeig angepasst werden

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

def is_relevant(item, valid_classes):
    #Prüft, ob 'instance of' (P31) des Items im gültigen Hierarchie-Baum liegt.
    claims = item.get("claims", {})
    if "P31" in claims:
        for claim in claims["P31"]:
            try:
                target_id = claim["mainsnak"]["datavalue"]["value"]["id"]
                if target_id in valid_classes:
                    return True
            except KeyError:
                continue
    return False

def setup_database():
    #Erstellt die SQLite-Datenbank und die Tabelle.
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    # Wir speichern die ID (z.B. Q123) als Primary Key und die rohen JSON-Daten
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS entities (
            id TEXT PRIMARY KEY,
            data JSON
        )
    ''')
    conn.commit()
    return conn

def process_dump_to_sqlite(valid_classes):
    #Liest den Dump und speichert Treffer direkt in SQLite.
    print(f"\n2. Starte Verarbeitung von {INPUT_FILE}")

    conn = setup_database()
    cursor = conn.cursor()

    count_found = 0
    count_processed = 0

    opener = gzip.open if INPUT_FILE.endswith(".gz") else open
    mode = "rt" if INPUT_FILE.endswith(".gz") else "r"

    with opener(INPUT_FILE, mode, encoding="utf-8") as f_in:
        for line in f_in:
            line = line.strip()
            if line in ["[", "]"]: continue
            if line.endswith(","): line = line[:-1]

            try:
                if not line: continue
                item = json.loads(line)
                count_processed += 1

                if is_relevant(item, valid_classes):
                    # Speichere in SQLite (IGNORE falls schon vorhanden)
                    cursor.execute(
                        'INSERT OR IGNORE INTO entities (id, data) VALUES (?, ?)',
                        (item['id'], json.dumps(item))
                    )
                    count_found += 1

                    # Committen alle 500 Einträge, damit die DB nicht blockiert
                    if count_found % 500 == 0:
                        conn.commit()
                        print(f"Gespeichert: {count_found} (Verarbeitet: {count_processed})")

                    if count_found >= LIMIT:
                        print(f"\nLimit von {LIMIT} erreicht. Stoppe.")
                        break

            except json.JSONDecodeError:
                continue

    conn.commit()
    conn.close()
    print(f"\nFertig! {count_found} Einträge in der Datenbank '{DB_NAME}' gespeichert.")

if __name__ == "__main__":
    if not Path(INPUT_FILE).exists():
        print(f"FEHLER: Eingabedatei '{INPUT_FILE}' nicht gefunden.")
    else:
        # 1. Hierarchie-Baum holen
        valid_q_ids = fetch_hierarchy_tree()
        # 2. Dump filtern und in DB speichern
        process_dump_to_sqlite(valid_q_ids)