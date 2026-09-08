"""Application boundary for public REAL-expedient reads."""

from __future__ import annotations

from datosenorden.db.session import SessionLocal
from datosenorden.infrastructure.real_expedient.repository import PostgresExpedientRepository

from .reader import ComposedPublicExpedientReader


def list_public_expedient_catalog() -> list[dict[str, object]]:
    with SessionLocal() as session:
        return ComposedPublicExpedientReader(
            PostgresExpedientRepository(session)
        ).list_available()


def list_published_real_expedient_catalog() -> list[dict[str, object]]:
    """Return the scalable public catalog boundary for published REAL work."""
    return [
        row
        for row in list_public_expedient_catalog()
        if row.get("provenance_class") == "REAL"
    ]


def get_public_expedient(expedient_id: str) -> dict[str, object] | None:
    with SessionLocal() as session:
        return ComposedPublicExpedientReader(
            PostgresExpedientRepository(session)
        ).get(expedient_id)


def get_citizen_expedient(expedient_id: str) -> dict[str, object] | None:
    """Read a local REAL expedient as approved citizen-facing content."""
    with SessionLocal() as session:
        return ComposedPublicExpedientReader(
            PostgresExpedientRepository(session)
        ).get_citizen(expedient_id)
