from .config import DEFAULT_DB_PATH, ENTITY_TYPES
from .sqlite_store import SQLiteStore
from .wikidata_adapter import WikidataAdapter


def main() -> None:
    adapter = WikidataAdapter()
    store = SQLiteStore(DEFAULT_DB_PATH)
    store.create_schema()

    total = 0

    for entity_type in ENTITY_TYPES:
        try:
            store.delete_entities_by_type(entity_type)
            entities = adapter.fetch_entities(entity_type)
            count = 0

            for entity in entities:
                store.upsert_entity(entity)
                count += 1

            total += count
            print(f"{entity_type}: {count} Einträge gespeichert")

        except Exception as exc:
            print(f"{entity_type}: Fehler beim Laden - {exc}")

    print(f"Fertig. Insgesamt gespeichert: {total}")
    store.close()


if __name__ == "__main__":
    main()
