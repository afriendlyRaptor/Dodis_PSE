"""
Baut eine spaCy Knowledge Base aus der Dodis SQLite-Datenbank.

Erwartet folgendes Datenbankschema (erstellt von tei_to_db.py):

    entities(id TEXT PRIMARY KEY, type TEXT)
    aliases(alias TEXT, entity_id TEXT, freq INTEGER, PRIMARY KEY (alias, entity_id))

Alias-Wahrscheinlichkeiten werden proportional zur Häufigkeit berechnet:
    P(entity | alias) = freq(entity, alias) / sum(freq für diesen alias über alle entities)

Entity-Frequenz = Summe aller Alias-Häufigkeiten dieser Entity im Corpus.

Unterstützt sowohl statische Modelle (de_core_news_lg, Vektoren 300-dim)
als auch Transformer-Modelle (de_dep_news_trf, Vektoren 768-dim).

Output: data/dodis_entities.kb

Usage:
    python src/dodis/build_dodis_kb.py
    python src/dodis/build_dodis_kb.py --model de_dep_news_trf
    python src/dodis/build_dodis_kb.py --model de_core_news_lg
"""

import argparse
import sqlite3
from pathlib import Path

import numpy as np
import spacy
from spacy.kb import InMemoryLookupKB

# Bekannte Vektordimensionen pro Modell
MODEL_VECTOR_SIZE = {
    "de_dep_news_trf": 768,
    "de_core_news_lg": 300,
    "de_core_news_md": 300,
    "de_core_news_sm": 96,
}


def get_vector(doc, is_transformer: bool) -> np.ndarray | None:
    """
    Extrahiert einen Vektor aus einem spaCy-Doc.

    - Transformer-Modelle: Mittelt den letzten Transformer-Layer über alle Token.
    - Statische Modelle: Mittelt die Token-Vektoren aller bekannten Token.

    Gibt None zurück falls kein Vektor berechnet werden kann.
    """
    if is_transformer:
        trf_data = doc._.trf_data
        if trf_data is None:
            return None
        # Letzter Hidden Layer: Shape (num_tokens, 768)
        last_layer = trf_data.last_hidden_layer_state
        if last_layer is None or last_layer.data.size == 0:
            return None
        # Mitteln über alle Token-Vektoren
        return np.mean(last_layer.data, axis=0)
    else:
        token_vecs = [tok.vector for tok in doc if any(tok.vector)]
        if not token_vecs:
            return None
        return np.mean(np.asarray(token_vecs), axis=0)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--model",
        default="de_core_news_lg",
        help="spaCy-Modell (z.B. de_dep_news_trf oder de_core_news_lg)",
    )
    args = parser.parse_args()

    BASE_PATH = Path(__file__).parent.parent.parent
    DATA_PATH = BASE_PATH / "data"
    DB_PATH = DATA_PATH / "dodis_entities.db"
    KB_OUTPUT = DATA_PATH / "dodis_entities.kb"

    assert DB_PATH.exists(), f"Datenbank nicht gefunden: {DB_PATH} — zuerst tei_to_db.py ausführen"

    print(f"Lade Modell {args.model}...")
    nlp = spacy.load(args.model)

    is_transformer = "trf" in args.model
    vector_size = MODEL_VECTOR_SIZE.get(args.model)
    if vector_size is None:
        # Automatisch ermitteln falls Modell unbekannt
        test_doc = nlp("Test")
        if is_transformer and test_doc._.trf_data:
            vector_size = test_doc._.trf_data.last_hidden_layer_state.data.shape[-1]
        else:
            vector_size = len(test_doc.vector)
    print(f"Vektordimension: {vector_size} ({'Transformer' if is_transformer else 'statisch'})")

    conn = sqlite3.connect(DB_PATH)
    cur_outer = conn.cursor()
    cur_inner = conn.cursor()

    kb = InMemoryLookupKB(vocab=nlp.vocab, entity_vector_length=vector_size)

    # Entities registrieren: Vektor aus dem häufigsten Alias
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
        vector = get_vector(doc, is_transformer)

        if vector is None:
            skipped += 1
            continue

        kb.add_entity(entity=entity_id, entity_vector=vector.tolist(), freq=total_freq)
        registered_entities.add(entity_id)

    assert kb.get_size_entities() > 0, "Keine Entities in KB registriert"
    print(f"{kb.get_size_entities()} Entities registriert, {skipped} übersprungen (kein Vektor/kein Alias)")

    # Aliase mit frequenzbasierten Wahrscheinlichkeiten registrieren
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