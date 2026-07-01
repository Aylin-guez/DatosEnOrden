from __future__ import annotations

from dataclasses import asdict, dataclass, field
import json
from pathlib import Path
import re
from typing import Any
import unicodedata


DEFAULT_ENTITY_REGISTRY_PATH = Path("config/entity_resolution/datosenorden_demo.json")


@dataclass(frozen=True)
class Identifier:
    type: str
    value: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class EntityAlias:
    value: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class CanonicalEntity:
    id: str
    canonical_name: str
    aliases: tuple[EntityAlias, ...] = ()
    identifiers: tuple[Identifier, ...] = ()
    tags: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ResolutionResult:
    found: bool
    query: str
    confidence: float
    method: str
    entity: CanonicalEntity | None = None
    matched_value: str = ""
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        if self.entity is None:
            payload["entity"] = None
        return payload


@dataclass(frozen=True)
class EntityRegistry:
    entities: tuple[CanonicalEntity, ...]
    metadata: dict[str, Any] = field(default_factory=dict)

    def resolve(self, query: str) -> ResolutionResult:
        cleaned = str(query or "").strip()
        if not cleaned:
            return ResolutionResult(False, cleaned, 0.0, "", reason="empty_query")

        exact = self._resolve_exact(cleaned)
        if exact is not None:
            return exact

        normalized_query = normalize_entity_key(cleaned)
        if not normalized_query:
            return ResolutionResult(False, cleaned, 0.0, "", reason="empty_normalized_query")

        for entity in self.entities:
            if normalize_entity_key(entity.canonical_name) == normalized_query:
                return ResolutionResult(True, cleaned, 0.95, "canonical", entity, entity.canonical_name)

        for entity in self.entities:
            for alias in entity.aliases:
                if normalize_entity_key(alias.value) == normalized_query:
                    return ResolutionResult(True, cleaned, 0.9, "alias", entity, alias.value)

        for entity in self.entities:
            for identifier in entity.identifiers:
                if normalize_identifier_value(identifier.value) == normalize_identifier_value(cleaned):
                    return ResolutionResult(True, cleaned, 1.0, "identifier", entity, identifier.value)

        return ResolutionResult(False, cleaned, 0.0, "", reason="no_match")

    def _resolve_exact(self, query: str) -> ResolutionResult | None:
        for entity in self.entities:
            if entity.canonical_name == query:
                return ResolutionResult(True, query, 1.0, "exact", entity, entity.canonical_name)
            for alias in entity.aliases:
                if alias.value == query:
                    return ResolutionResult(True, query, 0.98, "alias", entity, alias.value)
            for identifier in entity.identifiers:
                if identifier.value == query:
                    return ResolutionResult(True, query, 1.0, "identifier", entity, identifier.value)
        return None


def normalize_entity_key(value: str) -> str:
    text = unicodedata.normalize("NFKD", str(value or "").strip().lower())
    text = "".join(character for character in text if not unicodedata.combining(character))
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return " ".join(text.split())


def normalize_identifier_value(value: str) -> str:
    text = unicodedata.normalize("NFKD", str(value or "").strip().lower())
    text = "".join(character for character in text if not unicodedata.combining(character))
    return re.sub(r"[^a-z0-9]+", "", text)


def load_entity_registry(path: str | Path = DEFAULT_ENTITY_REGISTRY_PATH) -> EntityRegistry:
    source = Path(path)
    with source.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    return entity_registry_from_dict(payload)


def get_default_entity_registry() -> EntityRegistry:
    return load_entity_registry(DEFAULT_ENTITY_REGISTRY_PATH)


def entity_registry_from_dict(payload: dict[str, Any]) -> EntityRegistry:
    entities = tuple(_canonical_entity_from_dict(row) for row in payload.get("entities", []))
    registry = EntityRegistry(entities=entities, metadata=dict(payload.get("metadata", {})))
    validate_entity_registry(registry)
    return registry


def resolve_entity(query: str, registry: EntityRegistry | None = None) -> ResolutionResult:
    active_registry = registry if registry is not None else get_default_entity_registry()
    return active_registry.resolve(query)


def validate_entity_registry(registry: EntityRegistry) -> None:
    seen_ids: set[str] = set()
    seen_names: set[str] = set()
    seen_identifiers: set[tuple[str, str]] = set()

    for entity in registry.entities:
        if not entity.id.strip():
            raise ValueError("canonical entity id is required")
        if not entity.canonical_name.strip():
            raise ValueError(f"canonical name is required for entity {entity.id}")
        if entity.id in seen_ids:
            raise ValueError(f"duplicate canonical entity id: {entity.id}")
        seen_ids.add(entity.id)

        normalized_name = normalize_entity_key(entity.canonical_name)
        if normalized_name in seen_names:
            raise ValueError(f"duplicate normalized canonical name: {entity.canonical_name}")
        seen_names.add(normalized_name)

        for identifier in entity.identifiers:
            key = (identifier.type.strip().lower(), normalize_identifier_value(identifier.value))
            if not key[0] or not key[1]:
                raise ValueError(f"identifier type and value are required for entity {entity.id}")
            if key in seen_identifiers:
                raise ValueError(f"duplicate identifier: {identifier.type}:{identifier.value}")
            seen_identifiers.add(key)


def summarize_entity_registry(registry: EntityRegistry) -> dict[str, Any]:
    return {
        "entities": len(registry.entities),
        "aliases": sum(len(entity.aliases) for entity in registry.entities),
        "identifiers": sum(len(entity.identifiers) for entity in registry.entities),
        "tags": sorted({tag for entity in registry.entities for tag in entity.tags}),
        "metadata": dict(registry.metadata),
    }


def _canonical_entity_from_dict(row: dict[str, Any]) -> CanonicalEntity:
    aliases = tuple(_alias_from_value(value) for value in row.get("aliases", []))
    identifiers = tuple(_identifier_from_value(value) for value in row.get("identifiers", []))
    return CanonicalEntity(
        id=str(row.get("id", "")).strip(),
        canonical_name=str(row.get("canonical_name", "")).strip(),
        aliases=aliases,
        identifiers=identifiers,
        tags=tuple(str(tag) for tag in row.get("tags", [])),
        metadata=dict(row.get("metadata", {})),
    )


def _alias_from_value(value: str | dict[str, Any]) -> EntityAlias:
    if isinstance(value, dict):
        return EntityAlias(value=str(value.get("value", "")).strip(), metadata=dict(value.get("metadata", {})))
    return EntityAlias(value=str(value).strip())


def _identifier_from_value(value: dict[str, Any]) -> Identifier:
    return Identifier(
        type=str(value.get("type", "")).strip(),
        value=str(value.get("value", "")).strip(),
        metadata=dict(value.get("metadata", {})),
    )
