import sqlite3
from pathlib import Path

from .models import KBEntity


class SQLiteStore:
    def __init__(self, db_path: str) -> None:
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(db_path)
        self.conn.execute("PRAGMA foreign_keys = ON;")

    def create_schema(self) -> None:
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS entities (
                qid TEXT PRIMARY KEY,
                label TEXT NOT NULL,
                entity_type TEXT NOT NULL,
                description TEXT
            );

            CREATE TABLE IF NOT EXISTS aliases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                qid TEXT NOT NULL,
                alias TEXT NOT NULL,
                FOREIGN KEY (qid) REFERENCES entities(qid) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_aliases_alias ON aliases(alias);
            CREATE INDEX IF NOT EXISTS idx_entities_type ON entities(entity_type);
            """
        )
        self.conn.commit()

    def upsert_entity(self, entity: KBEntity) -> None:
        self.conn.execute(
            """
            INSERT INTO entities (qid, label, entity_type, description)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(qid) DO UPDATE SET
                label = excluded.label,
                entity_type = excluded.entity_type,
                description = excluded.description
            """,
            (entity.qid, entity.label, entity.entity_type, entity.description),
        )

        self.conn.execute("DELETE FROM aliases WHERE qid = ?", (entity.qid,))
        self.conn.executemany(
            "INSERT INTO aliases (qid, alias) VALUES (?, ?)",
            [(entity.qid, alias) for alias in entity.aliases],
        )
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()
