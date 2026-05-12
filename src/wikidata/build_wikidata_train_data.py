"""
Konvertiert die heruntergeladenen Wikipedia-JSON-Dateien (aus scrape_wikipedia.py)
in spaCy .spacy Dateien für das Entity Linking Training.

Jede JSON-Datei enthält:
  { "title": "...", "text": "...", "annotations": [{"start": int, "end": int, "qid": "Q123", ...}] }

Die Entitätstypen (PER/LOC/ORG) werden aus der Wikidata-Datenbank abgerufen.
Die Daten werden 80/10/10 in Train/Dev/Test aufgeteilt.

Erwartet:
  - data/qid_pages/*.json     (Wikipedia-Seiten, von scrape_wikipedia.py)
  - data/dodis_wikidata.db    (Wikidata-Entitäten-DB, von build_wikidata_db.py)

Output: data/wikidata/wiki_train.spacy, data/wikidata/wiki_dev.spacy, data/wikidata/wiki_test.spacy

Usage:
    python src/wikidata/build_wikidata_train_data.py
    python src/wikidata/build_wikidata_train_data.py --pages data/qid_pages --db data/dodis_wikidata.db
"""

import argparse
import json
import random
import sqlite3
from pathlib import Path

import spacy
from spacy.tokens import DocBin
from spacy.util import filter_spans

PERSON_CLASSES = {"Q5"}
LOC_CLASSES = {
    "Q6256",
    "Q515",
    "Q82794",
    "Q486972",
    "Q3624078",
    "Q35657",
    "Q1549591",
    "Q532",
    "Q5119",
}
ORG_CLASSES = {"Q43229", "Q7278", "Q4830453"}


def _get_type_from_p31(p31_values: list) -> str | None:
    p31 = set(p31_values)
    if p31 & PERSON_CLASSES:
        return "PER"
    if p31 & LOC_CLASSES:
        return "LOC"
    if p31 & ORG_CLASSES:
        return "ORG"
    return None


def load_entity_types(db_path: Path) -> dict:
    """Lädt {qid: type} Mapping aus der Wikidata-Datenbank (via P31-Claims im JSON)."""
    conn = sqlite3.connect(str(db_path))
    result = {}
    for qid, raw_json in conn.execute("SELECT id, data FROM entities"):
        try:
            p31 = json.loads(raw_json).get("claims", {}).get("P31", [])
            entity_type = _get_type_from_p31(p31)
            if entity_type:
                result[qid] = entity_type
        except (json.JSONDecodeError, AttributeError):
            pass
    conn.close()
    return result


def build_docs(json_files: list, nlp, entity_types: dict) -> list:
    """Konvertiert JSON-Annotationsdateien zu spaCy Docs mit Entity-Spans."""
    docs = []
    skipped = 0

    for json_file in json_files:
        try:
            with open(json_file, encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            print(f"  Überspringe fehlerhafte Datei {json_file.name}: {e}")
            skipped += 1
            continue

        text = data.get("text", "")
        annotations = data.get("annotations", [])

        if not text.strip() or not annotations:
            skipped += 1
            continue

        doc = nlp.make_doc(text)
        ents = []

        for ann in annotations:
            qid = ann.get("qid")
            if not qid or qid not in entity_types:
                continue

            label = entity_types[qid]
            span = doc.char_span(
                ann["start"],
                ann["end"],
                label=label,
                kb_id=qid,
                alignment_mode="strict",
            )
            if span is not None:
                ents.append(span)

        doc.ents = filter_spans(ents)

        if doc.ents:
            docs.append(doc)
        else:
            skipped += 1

    if skipped:
        print(f"  {skipped} Dateien ohne verwendbare Annotationen übersprungen.")

    return docs


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--pages",
        default="data/qid_pages",
        help="Verzeichnis mit Wikipedia-JSON-Dateien (default: data/qid_pages)",
    )
    parser.add_argument(
        "--db",
        default="data/dodis_wikidata.db",
        help="Pfad zur Wikidata-SQLite-Datenbank (default: data/dodis_wikidata.db)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Zufalls-Seed für die Datenteilung (default: 42)",
    )
    args = parser.parse_args()

    BASE_PATH = Path(__file__).parent.parent.parent
    DATA_PATH = BASE_PATH / "data" / "wikidata"
    DATA_PATH.mkdir(parents=True, exist_ok=True)

    pages_dir = BASE_PATH / args.pages
    db_path = BASE_PATH / args.db

    assert pages_dir.exists(), (
        f"Seiten-Verzeichnis nicht gefunden: {pages_dir}\n"
        "Zuerst src/wikidata/scrape_wikipedia.py ausführen."
    )
    assert db_path.exists(), (
        f"Datenbank nicht gefunden: {db_path}\n"
        "Zuerst src/wikidata/build_wikidata_db.py ausführen."
    )

    entity_types = load_entity_types(db_path)
    print(f"{len(entity_types)} Entitätstypen aus DB geladen.")

    json_files = sorted(pages_dir.glob("*.json"))
    assert len(json_files) > 0, f"Keine JSON-Dateien in {pages_dir}"
    print(f"{len(json_files)} JSON-Dateien gefunden.")

    random.seed(args.seed)
    json_files_shuffled = list(json_files)
    random.shuffle(json_files_shuffled)

    n = len(json_files_shuffled)
    n_train = int(n * 0.8)
    n_dev = int(n * 0.1)

    splits = {
        "wiki_train.spacy": json_files_shuffled[:n_train],
        "wiki_dev.spacy": json_files_shuffled[n_train : n_train + n_dev],
        "wiki_test.spacy": json_files_shuffled[n_train + n_dev :],
    }

    nlp = spacy.blank("de")

    for output_name, files in splits.items():
        print(f"\nVerarbeite {len(files)} Dateien für '{output_name}'...")
        docs = build_docs(files, nlp, entity_types)

        assert len(docs) > 0, (
            f"Keine Trainingsdokumente für {output_name} generiert. "
            "Prüfe ob die JSON-Annotationen QIDs enthalten, die in der DB vorhanden sind."
        )

        doc_bin = DocBin(store_user_data=True)
        for doc in docs:
            doc_bin.add(doc)

        output_path = DATA_PATH / output_name
        doc_bin.to_disk(output_path)
        assert output_path.exists(), f"Datei wurde nicht geschrieben: {output_path}"
        print(f"Gespeichert: {len(docs)} Docs → {output_path}")
