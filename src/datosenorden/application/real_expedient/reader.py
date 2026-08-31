from __future__ import annotations

from sqlalchemy.exc import SQLAlchemyError

from datosenorden.application.laboratory.models import LABORATORY_EXPEDIENT_ID
from datosenorden.application.laboratory.service import get_expedient, load_expedient_catalog

from .ports import ExpedientRepository
from .projection import public_expedient_projection
from .citizen_projection import (
    CitizenDocument,
    CitizenEvidence,
    CitizenProjectionContext,
    citizen_expedient_projection,
)


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
        return citizen_expedient_projection(persisted, _citizen_context(persisted, self._repository))


def _citizen_context(expedient, repository=None) -> CitizenProjectionContext:  # noqa: ANN001
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
    from datosenorden.application.legislative_ingestion.data_protection_21719 import (
        EXPEDIENT_ID as DATA_PROTECTION_EXPEDIENT_ID,
        data_protection_citizen_context,
    )
    if expedient.specification.expedient_id == DATA_PROTECTION_EXPEDIENT_ID:
        return data_protection_citizen_context()
    from datosenorden.application.real_expedient.democracia_viva_antofagasta import (
        EXPEDIENT_ID as DEMOCRACIA_VIVA_EXPEDIENT_ID,
        democracia_viva_citizen_context,
    )
    if expedient.specification.expedient_id == DEMOCRACIA_VIVA_EXPEDIENT_ID:
        return democracia_viva_citizen_context()
    from datosenorden.application.real_expedient.control_preventivo_identidad import (
        EXPEDIENT_ID as CONTROL_IDENTIDAD_EXPEDIENT_ID,
        control_preventivo_identidad_citizen_context,
    )
    if expedient.specification.expedient_id == CONTROL_IDENTIDAD_EXPEDIENT_ID:
        return control_preventivo_identidad_citizen_context()
    return _reference_context(expedient, repository)


def _reference_context(expedient, repository) -> CitizenProjectionContext:  # noqa: ANN001
    """Expose already-persisted public evidence for generic REAL readings.

    This fallback deliberately reads only references embedded in the immutable
    expedient version. It gives compact records such as ChileCompra orders the
    same document and source visibility as richer hand-composed contexts without
    inventing a narrative document or altering the stored expedient.
    """
    session = getattr(repository, "_session", None)
    if session is None:
        return CitizenProjectionContext()

    from uuid import UUID

    from sqlalchemy import select

    from datosenorden.models import Evidence, Source

    references = expedient.specification.references
    try:
        evidence_ids = tuple(UUID(str(value)) for value in references.evidence_ids)
        source_ids = tuple(UUID(str(value)) for value in references.source_ids)
    except ValueError:
        return CitizenProjectionContext()
    evidence_rows = session.scalars(select(Evidence).where(Evidence.id.in_(evidence_ids))).all()
    source_rows = session.scalars(select(Source).where(Source.id.in_(source_ids))).all()
    evidence_by_id = {str(item.id): item for item in evidence_rows}
    source_by_id = {str(item.id): item for item in source_rows}
    ordered_evidence = [evidence_by_id[item] for item in references.evidence_ids if item in evidence_by_id]
    ordered_sources = [source_by_id[item] for item in references.source_ids if item in source_by_id]
    evidence = tuple(
        CitizenEvidence(
            str(item.id), item.title, item.source.name, item.url, item.excerpt,
            item.published_at.isoformat() if item.published_at else None,
        )
        for item in ordered_evidence
    )
    documents = tuple(
        CitizenDocument(
            item.title, item.source.name, "Documento oficial referenciado",
            "Fuente incorporada", item.url,
            item.published_at.isoformat() if item.published_at else None,
        )
        for item in ordered_evidence
    )
    return CitizenProjectionContext(
        evidence=evidence,
        documents=documents,
        sources=tuple(item.name for item in ordered_sources),
    )
