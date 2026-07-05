"""Lightweight entity facade over the existing web service layer."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from datosenorden.web import app_services


@dataclass(frozen=True)
class EntityEngine:
    """Facade that centralizes entity lookups without owning engine logic."""

    def get_entity(self, target: str) -> dict[str, Any]:
        return app_services.resolve_investigation_target(target)

    def get_entity_summary(self, target: str) -> dict[str, Any]:
        entity = self.get_entity(target)
        if not entity.get("found", False):
            return {"found": False, "entity": entity, "summary": ""}

        investigation = app_services.get_investigation(str(entity.get("entity_id", target)))
        return {
            "found": bool(investigation.get("found", False)),
            "entity": investigation.get("entity", entity),
            "summary": investigation.get("narrative_summary") or investigation.get("summary", ""),
            "metrics": investigation.get("compact_metrics", []),
            "datasets": investigation.get("dataset_badges", []),
        }

    def get_entity_timeline(self, target: str) -> dict[str, Any]:
        entity = self.get_entity(target)
        entity_id = str(entity.get("entity_id", target)) if entity.get("found", False) else target
        return app_services.get_investigation_timeline(entity_id)

    def get_entity_sources(self, target: str) -> dict[str, Any]:
        entity = self.get_entity(target)
        entity_id = str(entity.get("entity_id", target)) if entity.get("found", False) else target
        return app_services.get_source_trace(entity_id)

    def get_entity_documents(self, target: str) -> list[dict[str, Any]]:
        entity = self.get_entity(target)
        terms = {
            str(target).lower(),
            str(entity.get("entity_id", "")).lower(),
            str(entity.get("entity_name", "")).lower(),
        }
        return [
            document
            for document in app_services.get_knowledge_documents()
            if self._matches_terms(document, terms)
        ]

    def get_entity_events(self, target: str) -> dict[str, Any]:
        return {
            "timeline": self.get_entity_timeline(target),
            "current_topics": app_services.get_current_topics(limit=10),
        }

    def get_entity_relationships(self, target: str) -> dict[str, Any]:
        entity = self.get_entity(target)
        entity_id = str(entity.get("entity_id", target)) if entity.get("found", False) else target
        investigation = app_services.get_investigation(entity_id)
        return investigation.get("connections", {}) if investigation.get("found", False) else {}

    def get_entity_knowledge(self, target: str) -> dict[str, Any]:
        entity = self.get_entity(target)
        entity_id = str(entity.get("entity_id", target)) if entity.get("found", False) else target
        investigation = app_services.get_investigation(entity_id)
        return investigation.get("knowledge", {}) if investigation.get("found", False) else {}

    @staticmethod
    def _matches_terms(payload: dict[str, Any], terms: set[str]) -> bool:
        haystack = " ".join(
            str(payload.get(key, ""))
            for key in ("id", "title", "summary", "source", "source_label", "official_url")
        ).lower()
        return any(term and term in haystack for term in terms)


def get_default_entity_engine() -> EntityEngine:
    return EntityEngine()
