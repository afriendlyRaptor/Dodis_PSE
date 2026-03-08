from .base_adapter import KnowledgeBaseAdapter
from .models import KBEntity
from .queries import QUERIES
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


class WikidataAdapter(KnowledgeBaseAdapter):
    def __init__(self, client: WikidataClient | None = None) -> None:
        self.client = client or WikidataClient()

    def fetch_entities(self, entity_type: str) -> list[KBEntity]:
        query = QUERIES.get(entity_type)
        if query is None:
            raise ValueError(f"Unbekannter entity_type: {entity_type}")

        rows = self.client.run_query(query)
        entities: list[KBEntity] = []

        for row in rows:
            entity = binding_to_entity(row, entity_type)
            if entity is not None:
                entities.append(entity)

        return entities
