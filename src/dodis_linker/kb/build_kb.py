from .config import DEFAULT_DB_PATH
from .models import KBEntity
from .queries import QUERIES
from .sqlite_store import SQLiteStore
from .wikidata_client import WikidataClient


def extract_qid(uri: str) -> str:
    return uri.rsplit("/", maxsplit=1)[-1]


def split_aliases(raw_aliases: str | None) -> list[str]:
    if not raw_aliases:
        return []
    values = [alias.strip() for alias in raw_aliases.split("||")]
    return sorted({alias for alias in values if alias})


def binding_to_entity(binding: dict, entity_type: str) -> KBEntity | None:
    label = binding.get("itemLabel", {}).get("value")
    item_uri = binding.get("item", {}).get("value")

    if not label or not item_uri:
        return None

    description = binding.get("itemDescription", {}).get("value")
    aliases = split_aliases(binding.get("aliases", {}).get("value"))

    return KBEntity(
        qid=extract_qid(item_uri),
        label=label,
        entity_type=entity_type,
        description=description,
        aliases=aliases,
    )


def main() -> None:
    client = WikidataClient()
    store = SQLiteStore(DEFAULT_DB_PATH)
    store.create_schema()

    total = 0

    for entity_type, query in QUERIES.items():
        try:
            rows = client.run_query(query)
            count = 0

            for row in rows:
                entity = binding_to_entity(row, entity_type)
                if entity is None:
                    continue
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
