from __future__ import annotations

from typing import Protocol


class DocumentReadingPort(Protocol):
    """Public boundary for document-reading payloads consumed by DEO Ciudadano."""

    def list_documents(self) -> list[dict]:
        """Return public document metadata already safe for the frontend."""

    def load_document_reading(self, document_id: str) -> dict:
        """Return a product-level reading payload without exposing engine internals."""


class EvidenceCandidatePort(Protocol):
    """Public boundary for evidence candidates related to a document reading."""

    def list_evidence_candidates(self, document_id: str) -> list[dict]:
        """Return candidate evidence rows prepared for product orchestration."""
