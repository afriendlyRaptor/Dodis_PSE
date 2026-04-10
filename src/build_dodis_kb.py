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

import spacy
from spacy.kb import InMemoryLookupKB

if __name__ == "__main__":
    BASE_PATH = Path(__file__).parent.parent
    DATA_PATH = BASE_PATH / "data"
    DB_PATH = DATA_PATH / "dodis_entities.db"
    KB_OUTPUT = DATA_PATH / "dodis_entities.kb"

    assert DB_PATH.exists(), f"Datenbank nicht gefunden: {DB_PATH} — zuerst tei_to_db.py ausführen"

    print("Lade Modell de_dep_news_trf...")
    nlp = spacy.load("de_dep_news_trf")

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    kb = InMemoryLookupKB(vocab=nlp.vocab, entity_vector_length=768)

    # Entities registrieren: Vektor aus dem häufigsten Alias
    print("Registriere Entities...")
    for (entity_id,) in cur.execute("SELECT id FROM entities"):
        row = cur.execute(
            "SELECT alias FROM aliases WHERE entity_id = ? ORDER BY freq DESC LIMIT 1",
            (entity_id,),
        ).fetchone()

        if row is None:
            continue

        total_freq = cur.execute(
            "SELECT SUM(freq) FROM aliases WHERE entity_id = ?", (entity_id,)
        ).fetchone()[0]

        vector = nlp(row[0]).vector
        assert len(vector) == 768, f"Unerwartete Vektorlänge für {entity_id}: {len(vector)}"
        kb.add_entity(entity=entity_id, entity_vector=vector.tolist(), freq=total_freq)

    assert kb.get_size_entities() > 0, "Keine Entities in KB registriert"
    print(f"{kb.get_size_entities()} Entities registriert")

    # Aliase mit frequenzbasierten Wahrscheinlichkeiten registrieren
    print("Registriere Aliases...")
    for (alias,) in cur.execute("SELECT DISTINCT alias FROM aliases"):
        rows = cur.execute(
            "SELECT entity_id, freq FROM aliases WHERE alias = ?", (alias,)
        ).fetchall()

        entity_ids = [r[0] for r in rows]
        freqs = [r[1] for r in rows]
        total = sum(freqs)
        probs = [f / total for f in freqs]

        kb.add_alias(alias=alias, entities=entity_ids, probabilities=probs)

    assert kb.get_size_aliases() > 0, "Keine Aliases in KB registriert"
    print(f"{kb.get_size_aliases()} Aliases registriert")

    conn.close()

    kb.to_disk(KB_OUTPUT)
    assert KB_OUTPUT.exists(), f"KB-Datei wurde nicht geschrieben: {KB_OUTPUT}"
    print(f"KB gespeichert unter {KB_OUTPUT}")
