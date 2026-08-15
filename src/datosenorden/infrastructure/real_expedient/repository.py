from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from datosenorden.application.provenance.models import ProvenanceClass
from datosenorden.application.real_expedient.models import (
    EpistemicClass,
    ExpedientReferences,
    ExpedientSpecification,
    ExpedientStatus,
    NarrativeStatement,
    ReferenceKind,
    StoredExpedient,
)
from datosenorden.application.real_expedient.service import ExpedientConflictError

from .models import (
    RealExpedientNarrativeRow,
    RealExpedientNarrativeSupportRow,
    RealExpedientReferenceRow,
    RealExpedientRow,
    RealExpedientVersionRow,
)


class PostgresExpedientRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, expedient_id: str) -> StoredExpedient | None:
        root = self._session.get(RealExpedientRow, expedient_id)
        if root is None:
            return None
        return self._load(root, root.current_version)

    def insert(
        self, specification: ExpedientSpecification, content_fingerprint: str
    ) -> StoredExpedient:
        try:
            with self._session.begin_nested():
                now = datetime.now(UTC)
                self._session.add(
                    RealExpedientRow(
                        expedient_id=specification.expedient_id,
                        provenance_class=specification.provenance_class.value,
                        current_version=1,
                        created_at=now,
                        updated_at=now,
                    )
                )
                self._session.flush()
                self._write_version(specification, content_fingerprint, now)
                self._session.flush()
            self._session.commit()
        except IntegrityError as exc:
            self._session.rollback()
            existing = self.get(specification.expedient_id)
            if existing is not None and existing.content_fingerprint == content_fingerprint:
                return existing
            raise ExpedientConflictError(
                "expedient id already exists with incompatible content"
            ) from exc
        except SQLAlchemyError:
            self._session.rollback()
            raise
        stored = self.get(specification.expedient_id)
        if stored is None:
            raise RuntimeError("persisted expedient could not be reopened")
        return stored

    def append_version(
        self,
        specification: ExpedientSpecification,
        content_fingerprint: str,
        *,
        expected_current_version: int,
    ) -> StoredExpedient:
        try:
            with self._session.begin_nested():
                now = datetime.now(UTC)
                result = self._session.execute(
                    update(RealExpedientRow)
                    .where(
                        RealExpedientRow.expedient_id == specification.expedient_id,
                        RealExpedientRow.current_version == expected_current_version,
                        RealExpedientRow.provenance_class == specification.provenance_class.value,
                    )
                    .values(current_version=specification.version, updated_at=now)
                )
                if result.rowcount != 1:
                    raise ExpedientConflictError("expedient version conflict")
                self._write_version(specification, content_fingerprint, now)
                self._session.flush()
            self._session.commit()
        except IntegrityError as exc:
            self._session.rollback()
            raise ExpedientConflictError("expedient version conflict") from exc
        except ExpedientConflictError:
            self._session.rollback()
            raise
        except SQLAlchemyError:
            self._session.rollback()
            raise
        stored = self.get(specification.expedient_id)
        if stored is None:
            raise RuntimeError("revised expedient could not be reopened")
        return stored

    def list_public(self) -> tuple[StoredExpedient, ...]:
        roots = self._session.scalars(
            select(RealExpedientRow)
            .join(
                RealExpedientVersionRow,
                (RealExpedientVersionRow.expedient_id == RealExpedientRow.expedient_id)
                & (RealExpedientVersionRow.version == RealExpedientRow.current_version),
            )
            .where(
                RealExpedientVersionRow.lifecycle == ExpedientStatus.PUBLISHED.value,
                RealExpedientRow.provenance_class.in_(
                    (ProvenanceClass.REAL.value, ProvenanceClass.DEMO.value)
                ),
            )
            .order_by(RealExpedientRow.expedient_id)
        ).all()
        return tuple(self._load(root, root.current_version) for root in roots)

    def _write_version(
        self,
        specification: ExpedientSpecification,
        content_fingerprint: str,
        created_at: datetime,
    ) -> None:
        self._session.add(
            RealExpedientVersionRow(
                expedient_id=specification.expedient_id,
                version=specification.version,
                title=specification.title,
                question=specification.question,
                summary=specification.summary,
                lifecycle=specification.status.value,
                fingerprint=content_fingerprint,
                created_at=created_at,
            )
        )
        self._session.flush()
        for kind, identifiers in specification.references.by_kind().items():
            for ordinal, reference_id in enumerate(identifiers):
                self._session.add(
                    RealExpedientReferenceRow(
                        expedient_id=specification.expedient_id,
                        version=specification.version,
                        reference_type=kind.value,
                        reference_id=reference_id,
                        ordinal=ordinal,
                    )
                )
        self._session.flush()
        for ordinal, statement in enumerate(specification.statements):
            self._session.add(
                RealExpedientNarrativeRow(
                    expedient_id=specification.expedient_id,
                    version=specification.version,
                    statement_id=statement.statement_id,
                    section=statement.section,
                    statement=statement.text,
                    epistemic_class=statement.epistemic_class.value,
                    ordinal=ordinal,
                )
            )
        self._session.flush()
        for statement in specification.statements:
            for kind, identifiers in (
                (ReferenceKind.CLAIM, statement.claim_ids),
                (ReferenceKind.EVIDENCE, statement.evidence_ids),
            ):
                for reference_id in identifiers:
                    self._session.add(
                        RealExpedientNarrativeSupportRow(
                            expedient_id=specification.expedient_id,
                            version=specification.version,
                            statement_id=statement.statement_id,
                            support_type=kind.value,
                            reference_id=reference_id,
                        )
                    )

    def _load(self, root: RealExpedientRow, version: int) -> StoredExpedient:
        version_row = self._session.get(RealExpedientVersionRow, (root.expedient_id, version))
        if version_row is None:
            raise RuntimeError("expedient current version is missing")
        reference_rows = self._session.scalars(
            select(RealExpedientReferenceRow)
            .where(
                RealExpedientReferenceRow.expedient_id == root.expedient_id,
                RealExpedientReferenceRow.version == version,
            )
            .order_by(RealExpedientReferenceRow.reference_type, RealExpedientReferenceRow.ordinal)
        ).all()
        grouped: dict[str, list[str]] = defaultdict(list)
        for row in reference_rows:
            grouped[row.reference_type].append(row.reference_id)
        statement_rows = self._session.scalars(
            select(RealExpedientNarrativeRow)
            .where(
                RealExpedientNarrativeRow.expedient_id == root.expedient_id,
                RealExpedientNarrativeRow.version == version,
            )
            .order_by(RealExpedientNarrativeRow.ordinal)
        ).all()
        support_rows = self._session.scalars(
            select(RealExpedientNarrativeSupportRow).where(
                RealExpedientNarrativeSupportRow.expedient_id == root.expedient_id,
                RealExpedientNarrativeSupportRow.version == version,
            )
        ).all()
        support: dict[tuple[str, str], list[str]] = defaultdict(list)
        for row in support_rows:
            support[(row.statement_id, row.support_type)].append(row.reference_id)
        statements = tuple(
            NarrativeStatement(
                statement_id=row.statement_id,
                section=row.section,
                text=row.statement,
                epistemic_class=EpistemicClass(row.epistemic_class),
                claim_ids=tuple(support[(row.statement_id, ReferenceKind.CLAIM.value)]),
                evidence_ids=tuple(support[(row.statement_id, ReferenceKind.EVIDENCE.value)]),
            )
            for row in statement_rows
        )
        specification = ExpedientSpecification(
            expedient_id=root.expedient_id,
            title=version_row.title,
            question=version_row.question,
            summary=version_row.summary,
            provenance_class=ProvenanceClass(root.provenance_class),
            status=ExpedientStatus(version_row.lifecycle),
            version=version_row.version,
            references=ExpedientReferences(
                claim_ids=tuple(grouped[ReferenceKind.CLAIM.value]),
                evidence_ids=tuple(grouped[ReferenceKind.EVIDENCE.value]),
                relationship_ids=tuple(grouped[ReferenceKind.RELATIONSHIP.value]),
                entity_ids=tuple(grouped[ReferenceKind.ENTITY.value]),
                document_ids=tuple(grouped[ReferenceKind.DOCUMENT.value]),
                source_ids=tuple(grouped[ReferenceKind.SOURCE.value]),
            ),
            statements=statements,
        )
        return StoredExpedient(
            specification=specification,
            content_fingerprint=version_row.fingerprint,
            created_at=root.created_at,
            updated_at=root.updated_at,
        )
