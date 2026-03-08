from dataclasses import dataclass, field


@dataclass(slots=True)
class KBEntity:
    qid: str
    label: str
    entity_type: str
    description: str | None = None
    aliases: list[str] = field(default_factory=list)
    languages: list[str] = field(default_factory=list)
