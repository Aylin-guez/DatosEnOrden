from __future__ import annotations

from typing import Protocol


class PublicRecordPort(Protocol):
    """Public boundary for investigation payloads consumed by DEO Ciudadano."""

    def resolve_target(self, target: str) -> dict:
        """Resolve a public user-facing target into a loadable investigation id."""

    def load_investigation(self, entity_id: str) -> dict:
        """Return a public investigation payload safe for UI presentation."""


class PublicRecordGraphPort(Protocol):
    """Public boundary for graph, trace, timeline and evidence view data."""

    def load_graph(self, entity_id: str) -> dict:
        """Return graph view-model data without exposing engine internals."""

    def load_timeline(self, entity_id: str) -> dict:
        """Return timeline view-model data without exposing engine internals."""
