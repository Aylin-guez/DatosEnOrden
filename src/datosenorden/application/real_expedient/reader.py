from __future__ import annotations

from sqlalchemy.exc import SQLAlchemyError

from datosenorden.application.laboratory.models import LABORATORY_EXPEDIENT_ID
from datosenorden.application.laboratory.service import get_expedient, load_expedient_catalog

from .ports import ExpedientRepository
from .projection import public_expedient_projection


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
