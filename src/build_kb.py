import sqlite3
import json
import spacy
from spacy.kb import InMemoryLookupKB
from pathlib import Path
import gc
import os
import argparse


def build_kb(database, outputPath):

    DB_PATH = database
    KB_OUTPUT_PATH = outputPath

    assert DB_PATH is not None, "DB_PATH ist None!"
    assert KB_OUTPUT_PATH is not None, "KB_OUTPUT_PATH ist None!"
    assert isinstance(DB_PATH, str), f"DB_PATH muss ein String sein, ist aber: {type(DB_PATH)}"
    assert isinstance(KB_OUTPUT_PATH, str), f"KB_OUTPUT_PATH muss ein String sein, ist aber: {type(KB_OUTPUT_PATH)}"
    assert os.path.isfile(DB_PATH), f"Datenbankdatei nicht gefunden: {DB_PATH}"

    print(DB_PATH)
    print(KB_OUTPUT_PATH)

    nlp = spacy.load("de_dep_news_trf")
    assert nlp is not None, "spaCy-Modell konnte nicht geladen werden!"
    assert nlp.vocab is not None, "nlp.vocab ist None!"

    kb = InMemoryLookupKB(vocab=nlp.vocab, entity_vector_length=768)
    assert kb is not None, "KnowledgeBase konnte nicht erstellt werden!"

    conn = sqlite3.connect(DB_PATH)
    assert conn is not None, "Datenbankverbindung ist None!"

    cur = conn.cursor()
    assert cur is not None, "Datenbank-Cursor ist None!"

    # Sicherstellen dass die Tabelle existiert und Daten enthält
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='entities'")
    table_check = cur.fetchone()
    assert table_check is not None, "Tabelle 'entities' existiert nicht in der Datenbank!"

    cur.execute("SELECT COUNT(*) FROM entities")
    row_count = cur.fetchone()
    assert row_count is not None, "COUNT-Abfrage hat None zurückgegeben!"
    assert row_count[0] > 0, "Tabelle 'entities' ist leer!"
    print(f"Datenbank enthält {row_count[0]:,} Einträge")

    print("Schritt 1: Registriere IDs und sammle Namen")
    full_alias_map = {}
    registered_ids = set()

    for qid, raw_json in cur.execute("SELECT id, data FROM entities"):

        assert qid is not None, "qid ist None!"
        assert isinstance(qid, str), f"qid muss ein String sein, ist aber: {type(qid)}"
        assert raw_json is not None, f"raw_json ist None für qid={qid}!"
        assert isinstance(raw_json, str), f"raw_json muss ein String sein für qid={qid}, ist aber: {type(raw_json)}"
        assert len(raw_json) > 0, f"raw_json ist leer für qid={qid}!"

        # JSON parsen
        try:
            data = json.loads(raw_json)
        except json.JSONDecodeError as e:
            assert False, f"JSON konnte nicht geparst werden für qid={qid}: {e}"

        assert isinstance(data, dict), f"Geparste JSON-Daten sind kein Dict für qid={qid}, ist: {type(data)}"
        assert "id" in data, f"Kein 'id'-Feld in den Daten für qid={qid}!"
        assert data["id"] == qid, f"ID-Mismatch: DB-ID={qid}, JSON-ID={data['id']}"

        # Entity registrieren
        if qid not in registered_ids:
            kb.add_entity(entity=qid, entity_vector=[0.0] * 768, freq=3)
            registered_ids.add(qid)

        assert qid in registered_ids, f"qid={qid} wurde nicht korrekt in registered_ids eingetragen!"

        # Namen extrahieren
        names = set()

        labels_data = data.get('labels', {})
        assert isinstance(labels_data, dict), f"'labels' ist kein Dict für qid={qid}, ist: {type(labels_data)}"

        aliases_data = data.get('aliases', {})
        assert isinstance(aliases_data, dict), f"'aliases' ist kein Dict für qid={qid}, ist: {type(aliases_data)}"

        for lang in ['de', 'en']:
            assert isinstance(lang, str), f"lang muss ein String sein, ist aber: {type(lang)}"

            label_data = labels_data.get(lang)

            if isinstance(label_data, dict):
                label = label_data.get('value')
            elif isinstance(label_data, str):
                label = label_data
            else:
                label = None

            if label is not None:
                assert isinstance(label, str), f"Label muss ein String sein für qid={qid}, lang={lang}, ist: {type(label)}"
                assert len(label.strip()) > 0, f"Label ist ein leerer String für qid={qid}, lang={lang}!"
                names.add(label)

            # Aliases – jetzt korrekt innerhalb der for-lang-Schleife
            alias_list = aliases_data.get(lang, [])
            assert isinstance(alias_list, list), f"Alias-Liste ist kein List für qid={qid}, lang={lang}, ist: {type(alias_list)}"

            for entry in alias_list:
                assert entry is not None, f"Alias-Eintrag ist None für qid={qid}, lang={lang}!"

                if isinstance(entry, dict):
                    val = entry.get('value')
                elif isinstance(entry, str):
                    val = entry
                else:
                    val = None

                if val is not None:
                    assert isinstance(val, str), f"Alias-Wert muss ein String sein für qid={qid}, ist: {type(val)}"
                    assert len(val.strip()) > 0, f"Alias-Wert ist ein leerer String für qid={qid}, lang={lang}!"
                    names.add(val)

        # Alias-Map befüllen
        for n in names:
            assert n is not None, f"Name in names-Set ist None für qid={qid}!"
            assert isinstance(n, str), f"Name muss ein String sein für qid={qid}, ist: {type(n)}"
            assert len(n.strip()) > 0, f"Name ist ein leerer String für qid={qid}!"

            if n not in full_alias_map:
                full_alias_map[n] = []

            assert isinstance(full_alias_map[n], list), f"Alias-Map-Eintrag ist keine Liste für name='{n}'!"

            if qid not in full_alias_map[n] and len(full_alias_map[n]) < 30:
                full_alias_map[n].append(qid)

    assert len(registered_ids) > 0, "Keine Entitäten wurden registriert!"
    assert len(full_alias_map) > 0, "Alias-Map ist leer – keine Namen gefunden!"
    print(f"Registrierte Entitäten: {len(registered_ids):,}")

    print(f"Schritt 2: Schreibe {len(full_alias_map):,} Aliase in die KB")

    for name, qid_list in full_alias_map.items():
        assert name is not None, "Name in full_alias_map ist None!"
        assert isinstance(name, str), f"Name muss ein String sein, ist aber: {type(name)}"
        assert len(name.strip()) > 0, f"Name in full_alias_map ist ein leerer String!"
        assert qid_list is not None, f"qid_list ist None für name='{name}'!"
        assert isinstance(qid_list, list), f"qid_list ist keine Liste für name='{name}'!"
        assert len(qid_list) > 0, f"qid_list ist leer für name='{name}'!"
        assert len(qid_list) <= 30, f"qid_list überschreitet Limit von 30 für name='{name}': {len(qid_list)}"

        for qid in qid_list:
            assert qid is not None, f"qid in qid_list ist None für name='{name}'!"
            assert isinstance(qid, str), f"qid muss ein String sein für name='{name}', ist: {type(qid)}"
            assert qid in registered_ids, f"qid='{qid}' in Alias-Map ist nicht in registered_ids! (name='{name}')"

        probs = [1.0 / len(qid_list)] * len(qid_list)

        assert len(probs) == len(qid_list), f"Länge von probs ({len(probs)}) stimmt nicht mit qid_list ({len(qid_list)}) überein!"
        assert abs(sum(probs) - 1.0) < 1e-6, f"Wahrscheinlichkeiten summieren sich nicht zu 1.0 für name='{name}': {sum(probs)}"
        for p in probs:
            assert 0.0 < p <= 1.0, f"Wahrscheinlichkeit ausserhalb [0,1] für name='{name}': {p}"

        kb.add_alias(alias=name, entities=qid_list, probabilities=probs)

    # Ausgabepfad vorbereiten und KB speichern
    output_dir = os.path.dirname(KB_OUTPUT_PATH)
    if output_dir:
        assert os.path.isdir(output_dir), f"Ausgabeverzeichnis existiert nicht: {output_dir}"

    kb.to_disk(KB_OUTPUT_PATH)

    assert os.path.exists(KB_OUTPUT_PATH), f"KB-Datei wurde nicht erstellt unter: {KB_OUTPUT_PATH}!"

    conn.close()
    print(f"Fertig! {len(registered_ids):,} Entitäten in KB gespeichert unter: {KB_OUTPUT_PATH}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-d", "--database")
    parser.add_argument("-o", "--outputPath")
    args = parser.parse_args()

    assert args.database is not None, "Kein Datenbankpfad angegeben! Bitte -d verwenden."
    assert args.outputPath is not None, "Kein Ausgabepfad angegeben! Bitte -o verwenden."

    if os.path.isfile(args.database):
        build_kb(args.database, args.outputPath)
    else:
        print(f"Datenbankpfad nicht gefunden: {args.database}")
