import json
import sqlite3
from pathlib import Path

import spacy
from spacy.tokens import DocBin


def get_value(entry):
    if isinstance(entry, dict):
        return entry.get("value")
    return entry


def _build_docbin(cur, nlp):
    db = DocBin(store_user_data=True)
    count = 0
    for qid, raw_json in cur:
        data = json.loads(raw_json)
        labels_de = data.get("labels", {}).get("de", {})
        label = get_value(labels_de)
        aliases_list = data.get("aliases", {}).get("de", [])
        if not (label and aliases_list):
            continue
        alias_text = get_value(aliases_list[0])
        if not alias_text:
            continue
        text = f"{alias_text} ist eine Bezeichnung für {label}."
        doc = nlp.make_doc(text)
        span = doc.char_span(0, len(alias_text), label="MISC", kb_id=qid)
        if span:
            doc.ents = [span]
            db.add(doc)
            count += 1
    return db, count


def generate():
    BASE_PATH = Path(__file__).parent.parent.absolute()
    DATA_PATH = BASE_PATH / "data"
    DB_PATH = DATA_PATH / "dodis_wikidata.db"

    if not DB_PATH.exists():
        print(f"Datenbank nicht gefunden unter: {DB_PATH}")
        return

    conn = sqlite3.connect(str(DB_PATH))
    cur = conn.cursor()
    nlp = spacy.blank("de")

    cur.execute("SELECT id, data FROM entities LIMIT 2000")
    db, count = _build_docbin(cur, nlp)

    DATA_PATH.mkdir(parents=True, exist_ok=True)
    db.to_disk(DATA_PATH / "train.spacy")
    db.to_disk(DATA_PATH / "dev.spacy")

    conn.close()
    print(f"{count} Sätze in 'train.spacy' und 'dev.spacy' gespeichert.")


if __name__ == "__main__":
    generate()
