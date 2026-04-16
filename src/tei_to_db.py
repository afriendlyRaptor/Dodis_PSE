"""
Lädt alle Dodis TEI-XML Dateien von HuggingFace und erstellt eine SQLite-Datenbank.
Angepasst für Kompatibilität mit dem Wikidata-Pipeline-Format (id TEXT, data JSON).

Output: data/dodis_entities.db

Usage:
    python src/tei_to_db.py
"""

import sqlite3
import xml.etree.ElementTree as ET
import json
from pathlib import Path
from collections import defaultdict
from huggingface_hub import snapshot_download

TEI_NS = "http://www.tei-c.org/ns/1.0"

ENTITY_TAGS = {
    "persName": "PER",
    "placeName": "LOC",
    "orgName": "ORG",
}

if __name__ == "__main__":
    BASE_PATH = Path(__file__).parent.parent
    DATA_PATH = BASE_PATH / "data"
    DATA_PATH.mkdir(exist_ok=True)
    DB_PATH = DATA_PATH / "dodis_entities.db"

    LOCAL_DATASET = DATA_PATH / "dodis_transcription_xml"

    if LOCAL_DATASET.exists() and any(LOCAL_DATASET.glob("**/*.xml")):
        print("Nutze lokalen Cache...")
        dataset_path = LOCAL_DATASET
    else:
        print("Lade Dodis TEI-XML Dataset von HuggingFace...")
        dataset_path = Path(
            snapshot_download(
                repo_id="prg-unibe/dodis_transcription_xml",
                repo_type="dataset",
                local_dir=LOCAL_DATASET,
            )
        )
        assert dataset_path.exists(), f"Download fehlgeschlagen: {dataset_path}"

    # Dictionary zum Sammeln der Daten im Arbeitsspeicher
    # Struktur: { ref_id: {"type": "PER/LOC/ORG", "aliases": {"Name1": freq1, "Name2": freq2}} }
    entities_dict = defaultdict(lambda: {"type": "", "aliases": defaultdict(int)})

    # Alle XML-Dateien aus allen Splits verarbeiten
    xml_files = sorted(dataset_path.glob("**/*.xml"))
    assert len(xml_files) > 0, "Keine XML-Dateien gefunden"
    print(f"{len(xml_files)} XML-Dateien gefunden. Extrahiere Entities...")

    for xml_file in xml_files:
        try:
            tree = ET.parse(xml_file)
        except ET.ParseError:
            print(f"  Überspringe fehlerhafte XML-Datei: {xml_file.name}")
            continue

        root = tree.getroot()

        for tag, label in ENTITY_TAGS.items():
            for elem in root.findall(f".//{{{TEI_NS}}}{tag}"):
                ref = elem.get("ref", "")
                mention = "".join(elem.itertext()).strip()

                if not ref or not mention:
                    continue

                # Typ einmalig speichern
                if not entities_dict[ref]["type"]:
                    entities_dict[ref]["type"] = label

                # Vorkommen (Alias) hochzählen
                entities_dict[ref]["aliases"][mention] += 1

    print("Formatiere Daten und speichere in SQLite...")

    # Datenbankverbindung aufbauen
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Einheitliches Schema: id und data als JSON (wie im Wikidata-Skript)
    cur.execute("DROP TABLE IF EXISTS entities") # Setzt die DB zurück für sauberen Neuaufbau
    cur.execute("CREATE TABLE IF NOT EXISTS entities (id TEXT PRIMARY KEY, data JSON)")

    insert_data = []

    for ref, info in entities_dict.items():
        # Aliase nach Häufigkeit sortieren
        sorted_aliases = sorted(info["aliases"].items(), key=lambda x: x[1], reverse=True)

        # Der häufigste Alias wird zum Haupt-Label, alle anderen (inklusive des Haupt-Labels) in die Alias-Liste
        main_label = sorted_aliases[0][0] if sorted_aliases else ""
        all_aliases_list = [alias for alias, freq in sorted_aliases]

        # JSON-Struktur analog zur Wikidata-Datenbank aufbauen
        json_obj = {
            "id": ref,
            "labels": {
                "de": main_label  # "de" als Standard-Sprachkey für Einheitlichkeit
            },
            "aliases": {
                "de": all_aliases_list
            },
            "type": info["type"], # Behält PER, LOC oder ORG zur leichteren Filterung
            "claims": {
                "P31": [info["type"]] # Fake-Claim, um die Struktur exact von Wikidata zu imitieren
            }
        }

        insert_data.append((ref, json.dumps(json_obj)))

    # Bulk-Insert in die Datenbank
    cur.executemany(
        "INSERT INTO entities (id, data) VALUES (?, ?)",
        insert_data
    )

    conn.commit()

    entity_count = cur.execute("SELECT COUNT(*) FROM entities").fetchone()[0]
    assert entity_count > 0, "Keine Entities in der Datenbank"

    conn.close()
    print(f"{entity_count} Entities erfolgreich im einheitlichen JSON-Format unter {DB_PATH} gespeichert.")