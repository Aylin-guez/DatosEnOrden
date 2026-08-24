from __future__ import annotations

from sqlalchemy.exc import SQLAlchemyError

from datosenorden.application.laboratory.models import LABORATORY_EXPEDIENT_ID
from datosenorden.application.laboratory.service import get_expedient, load_expedient_catalog

from .ports import ExpedientRepository
from .projection import public_expedient_projection
from .citizen_projection import CitizenProjectionContext, citizen_expedient_projection


class PublicExpedientUnavailableError(RuntimeError):
    pass


class ComposedPublicExpedientReader:
    def __init__(self, repository: ExpedientRepository) -> None:
        self._repository = repository

    def get(self, expedient_id: str) -> dict[str, object] | None:
        normalized = str(expedient_id or "").strip().upper()
        try:
            persisted = self._repository.get(normalized)
        except SQLAlchemyError as exc:
            raise PublicExpedientUnavailableError(
                "public expedient repository unavailable"
            ) from exc
        if persisted is not None:
            return public_expedient_projection(persisted)
        if normalized == LABORATORY_EXPEDIENT_ID:
            return get_expedient(LABORATORY_EXPEDIENT_ID)
        return None

    def list_available(self) -> list[dict[str, object]]:
        try:
            persisted = [
                public_expedient_projection(item) for item in self._repository.list_public()
            ]
        except SQLAlchemyError as exc:
            raise PublicExpedientUnavailableError(
                "public expedient repository unavailable"
            ) from exc
        legacy = load_expedient_catalog()
        return persisted + [item for item in legacy if item.get("id") == LABORATORY_EXPEDIENT_ID]

    def get_citizen(self, expedient_id: str) -> dict[str, object] | None:
        """Return the reusable citizen projection when the local record exists.

        The context resolver is deliberately outside Reflex: the UI receives only
        human-readable, approved public content.
        """
        normalized = str(expedient_id or "").strip().upper()
        try:
            persisted = self._repository.get(normalized)
        except SQLAlchemyError as exc:
            raise PublicExpedientUnavailableError(
                "public expedient repository unavailable"
            ) from exc
        if persisted is None:
            return None
        return citizen_expedient_projection(persisted, _citizen_context(persisted))


def _citizen_context(expedient) -> CitizenProjectionContext:
    """Select certified local context without letting a renderer know an ID."""
    from datosenorden.application.legislative_ingestion.expedient import EXPEDIENT_ID
    from datosenorden.application.legislative_ingestion.golden_expedient import (
        golden_citizen_context,
    )

    if expedient.specification.expedient_id == EXPEDIENT_ID:
        return golden_citizen_context()
    from datosenorden.application.legislative_ingestion.escuelas_protegidas import (
        EXPEDIENT_ID as ESCUELAS_EXPEDIENT_ID,
        escuelas_citizen_context,
    )
    if expedient.specification.expedient_id == ESCUELAS_EXPEDIENT_ID:
        return escuelas_citizen_context()
    from datosenorden.application.legislative_ingestion.reconstruccion_nacional import (
        EXPEDIENT_ID as RECONSTRUCCION_EXPEDIENT_ID,
        reconstruccion_citizen_context,
    )
    if expedient.specification.expedient_id == RECONSTRUCCION_EXPEDIENT_ID:
        return reconstruccion_citizen_context()
    from datosenorden.application.legislative_ingestion.cybersecurity_21663 import (
        EXPEDIENT_ID as CYBERSECURITY_EXPEDIENT_ID,
        cybersecurity_citizen_context,
    )
    if expedient.specification.expedient_id == CYBERSECURITY_EXPEDIENT_ID:
        return cybersecurity_citizen_context()
    return CitizenProjectionContext()
