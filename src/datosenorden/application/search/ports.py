from __future__ import annotations

from typing import Protocol


class WorkspaceSearchPort(Protocol):
    """Public product boundary for workspace search results.

    Implementations may live behind app services, a gateway, or a private engine.
    The public application layer only consumes the already-built product payload.
    """

    def search_workspace(self, query: str) -> dict:
        """Return a DEO Ciudadano workspace payload for a public query."""
