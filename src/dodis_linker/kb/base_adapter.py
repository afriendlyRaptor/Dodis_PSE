from abc import ABC, abstractmethod

from .models import KBEntity


class KnowledgeBaseAdapter(ABC):
    @abstractmethod
    def fetch_entities(self, entity_type: str) -> list[KBEntity]:
        """Lädt Entitäten eines bestimmten Typs aus dem Backend."""
        raise NotImplementedError
