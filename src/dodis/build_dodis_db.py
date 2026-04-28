"""
Lädt alle Dodis TEI-XML Dateien von HuggingFace und erstellt eine SQLite-Datenbank
mit allen Entities (Personen, Orte, Organisationen) und ihren Alias-Häufigkeiten.

Output: data/dodis_entities.db

Usage:
    python src/dodis/build_dodis_db.py
"""

import sqlite3
import xml.etree.ElementTree as ET
from pathlib import Path

from huggingface_hub import snapshot_download

TEI_NS = "http://www.tei-c.org/ns/1.0"

ENTITY_TAGS = {
    "persName": "PER",
    "placeName": "LOC",
    "orgName": "ORG",
}

if __name__ == "__main__":
    BASE_PATH = Path(__file__).parent.parent.parent
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

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("DROP TABLE IF EXISTS aliases")
    cur.execute("DROP TABLE IF EXISTS entities")
    cur.execute("CREATE TABLE entities (id TEXT PRIMARY KEY, type TEXT)")
    cur.execute(
        """
        CREATE TABLE aliases (
            alias     TEXT,
            entity_id TEXT,
            freq      INTEGER DEFAULT 0,
            PRIMARY KEY (alias, entity_id)
        )
        """
    )
    conn.commit()

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
                ref = elem.get("ref", "").strip()
                mention = "".join(elem.itertext()).strip()

                if not ref or not mention:
                    continue

                cur.execute(
                    "INSERT OR IGNORE INTO entities (id, type) VALUES (?, ?)",
                    (ref, label),
                )
                cur.execute(
                    """
                    INSERT INTO aliases (alias, entity_id, freq) VALUES (?, ?, 1)
                        ON CONFLICT (alias, entity_id) DO UPDATE SET freq = freq + 1
                    """,
                    (mention, ref),
                )

    conn.commit()

    entity_count = cur.execute("SELECT COUNT(*) FROM entities").fetchone()[0]
    alias_count = cur.execute("SELECT COUNT(*) FROM aliases").fetchone()[0]
    assert entity_count > 0, "Keine Entities in der Datenbank"
    assert alias_count > 0, "Keine Aliases in der Datenbank"

    conn.close()
    print(f"{entity_count} Entities und {alias_count} Aliases gespeichert unter {DB_PATH}")
