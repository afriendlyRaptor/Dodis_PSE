import sqlite3

from .config import DEFAULT_DB_PATH


def print_entities(entity_type: str, limit: int = 10) -> None:
    conn = sqlite3.connect(DEFAULT_DB_PATH)
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT qid, label, description
        FROM entities
        WHERE entity_type = ?
        ORDER BY label
        LIMIT ?
        """,
        (entity_type, limit),
    )

    rows = cursor.fetchall()

    print(f"\n=== {entity_type.upper()} ===")
    if not rows:
        print("Keine Einträge gefunden.")
    else:
        for qid, label, description in rows:
            print(f"{qid} | {label} | {description}")

    conn.close()


def main() -> None:
    for entity_type in ("person", "place", "organization"):
        print_entities(entity_type, limit=10)


if __name__ == "__main__":
    main()
