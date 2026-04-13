"""
Baut eine spaCy Knowledge Base aus der Dodis SQLite-Datenbank.

Alias-Wahrscheinlichkeiten werden proportional zur Häufigkeit berechnet:
P(entity | alias) = freq(entity, alias) / sum(freq für diesen alias)

Output: data/dodis_entities.kb

Usage:
    python src/build_dodis_kb.py
"""

import sqlite3
from pathlib import Path

import numpy as np
import spacy
from spacy.kb import InMemoryLookupKB

if __name__ == "__main__":
    BASE_PATH = Path(__file__).parent.parent
    DATA_PATH = BASE_PATH / "data"
    DB_PATH = DATA_PATH / "dodis_entities.db"
    KB_OUTPUT = DATA_PATH / "dodis_entities.kb"

    assert DB_PATH.exists(), f"Datenbank nicht gefunden: {DB_PATH} — zuerst tei_to_db.py ausführen"

    print("Lade Modell de_core_news_lg...")
    nlp = spacy.load("de_core_news_lg")

    conn = sqlite3.connect(DB_PATH)
    cur_outer = conn.cursor()  # Cursor für äussere Loops
    cur_inner = conn.cursor()  # Cursor für innere Abfragen (getrennt um Überschreiben zu vermeiden)

    kb = InMemoryLookupKB(vocab=nlp.vocab, entity_vector_length=300)

    # Entities registrieren: Vektor aus dem häufigsten Alias
    # Nullvektoren werden übersprungen (unbekannte Wörter ohne Vektorrepräsentation)
    print("Registriere Entities...")
    skipped = 0
    registered_entities = set()

    for (entity_id,) in cur_outer.execute("SELECT id FROM entities"):
        row = cur_inner.execute(
            "SELECT alias FROM aliases WHERE entity_id = ? ORDER BY freq DESC LIMIT 1",
            (entity_id,),
        ).fetchone()

        if row is None:
            skipped += 1
            continue

        total_freq = cur_inner.execute(
            "SELECT SUM(freq) FROM aliases WHERE entity_id = ?", (entity_id,)
        ).fetchone()[0]

        doc = nlp(row[0])
        token_vecs = [tok.vector for tok in doc if any(tok.vector)]
        if not token_vecs:
            skipped += 1
            continue
        vector = np.mean(np.asarray(token_vecs), axis=0)

        kb.add_entity(entity=entity_id, entity_vector=vector.tolist(), freq=total_freq)
        registered_entities.add(entity_id)

    assert kb.get_size_entities() > 0, "Keine Entities in KB registriert"
    print(f"{kb.get_size_entities()} Entities registriert, {skipped} übersprungen (Nullvektor/kein Alias)")

    # Aliase mit frequenzbasierten Wahrscheinlichkeiten registrieren
    # Nur Aliases für tatsächlich registrierte Entities hinzufügen
    print("Registriere Aliases...")
    skipped_aliases = 0

    for (alias,) in cur_outer.execute("SELECT DISTINCT alias FROM aliases"):
        rows = cur_inner.execute(
            "SELECT entity_id, freq FROM aliases WHERE alias = ?", (alias,)
        ).fetchall()

        # Nur Entities die auch wirklich in der KB registriert sind
        filtered = [(r[0], r[1]) for r in rows if r[0] in registered_entities]

        if not filtered:
            skipped_aliases += 1
            continue

        entity_ids = [r[0] for r in filtered]
        freqs = [r[1] for r in filtered]
        total = sum(freqs)
        probs = [f / total for f in freqs]

        kb.add_alias(alias=alias, entities=entity_ids, probabilities=probs)

    assert kb.get_size_aliases() > 0, "Keine Aliases in KB registriert"
    print(f"{kb.get_size_aliases()} Aliases registriert, {skipped_aliases} übersprungen (keine registrierte Entity)")

    conn.close()

    kb.to_disk(KB_OUTPUT)
    assert KB_OUTPUT.exists(), f"KB-Datei wurde nicht geschrieben: {KB_OUTPUT}"
    print(f"KB gespeichert unter {KB_OUTPUT}")