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


def get_public_expedient(expedient_id: str) -> dict[str, object] | None:
    with SessionLocal() as session:
        return ComposedPublicExpedientReader(
            PostgresExpedientRepository(session)
        ).get(expedient_id)
