"""
Erstellt eine SQLite-Datenbank mit allen Entities (Personen, Orte, Organisationen)
und ihren Alias-Häufigkeiten aus den lokal vorhandenen Dodis TEI-XML Dateien.

Erwartet die XML-Dateien unter data/dodis_transcription_xml/.
Falls diese nicht vorhanden sind: src/helpers/download_dodis_xml.py ausführen.

Output: data/dodis_entities.db

Usage:
    python src/dodis/build_dodis_db.py
"""

import sqlite3
import xml.etree.ElementTree as ET
from pathlib import Path

TEI_NS = "http://www.tei-c.org/ns/1.0"

ENTITY_TAGS = {
    "persName": "PER",
    "placeName": "LOC",
    "orgName": "ORG",
}


def normalize_ref(ref: str) -> str:
    """Normalisiert eine Dodis-URL auf https."""
    return ref.strip().replace("http://dodis.ch/", "https://dodis.ch/")


def extract_entity_mentions(root: ET.Element) -> list[tuple[str, str, str]]:
    """
    Extrahiert alle Entity-Erwähnungen aus einem XML-Root-Element.
    Gibt eine Liste von (ref, label, mention) zurück.
    """
    results = []
    for tag, label in ENTITY_TAGS.items():
        for elem in root.findall(f".//{{{TEI_NS}}}{tag}"):
            ref = normalize_ref(elem.get("ref", ""))
            mention = "".join(elem.itertext()).strip()
            if ref and mention:
                results.append((ref, label, mention))
    return results


if __name__ == "__main__":
    BASE_PATH = Path(__file__).parent.parent.parent
    DATA_PATH = BASE_PATH / "data"
    DATA_PATH.mkdir(exist_ok=True)
    DB_PATH = DATA_PATH / "dodis_entities.db"

    LOCAL_DATASET = DATA_PATH / "dodis_transcription_xml"

    assert LOCAL_DATASET.exists() and any(LOCAL_DATASET.glob("**/*.xml")), (
        f"Keine XML-Dateien gefunden unter {LOCAL_DATASET}. "
        "Zuerst src/testsAndHelpers/download_dodis_xml.py ausführen."
    )
    dataset_path = LOCAL_DATASET

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("DROP TABLE IF EXISTS aliases")
    cur.execute("DROP TABLE IF EXISTS entities")
    cur.execute("CREATE TABLE entities (id TEXT PRIMARY KEY, type TEXT)")
    cur.execute("""
        CREATE TABLE aliases (
            alias     TEXT,
            entity_id TEXT,
            freq      INTEGER DEFAULT 0,
            PRIMARY KEY (alias, entity_id)
        )
        """)
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

        for ref, label, mention in extract_entity_mentions(root):
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
    print(
        f"{entity_count} Entities und {alias_count} Aliases gespeichert unter {DB_PATH}"
    )
