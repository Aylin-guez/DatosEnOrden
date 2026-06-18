from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import CheckConstraint, Date, ForeignKey, Index, Numeric, String, text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship as orm_relationship

from datosenorden.db.base import Base
from datosenorden.models.graph import Entity
from datosenorden.models.source_records import SourceRecord
from datosenorden.models.types import TimestampMixin


class Claim(Base, TimestampMixin):
    __tablename__ = "claim"
    __table_args__ = (
        CheckConstraint("confidence >= 0 and confidence <= 1", name="ck_claim_confidence_range"),
        CheckConstraint(
            "status in ('ingested', 'normalized', 'validated', 'published', 'rejected', 'disputed', 'withdrawn')",
            name="ck_claim_status",
        ),
        CheckConstraint(
            "object_entity_id is not null or object_value is not null",
            name="ck_claim_has_object",
        ),
        CheckConstraint(
            "valid_to is null or valid_from is null or valid_to >= valid_from",
            name="ck_claim_valid_date_range",
        ),
        Index("ix_claim_subject_entity_id", "subject_entity_id"),
        Index("ix_claim_object_entity_id", "object_entity_id"),
        Index("ix_claim_source_record_id", "source_record_id"),
        Index("ix_claim_evidence_id", "evidence_id"),
        Index("ix_claim_predicate", "predicate"),
        Index("ix_claim_status", "status"),
    )

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    subject_entity_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("entity.id", ondelete="RESTRICT"),
        nullable=False,
    )
    predicate: Mapped[str] = mapped_column(String(120), nullable=False)
    object_entity_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("entity.id", ondelete="RESTRICT"),
    )
    object_value: Mapped[dict | None] = mapped_column(JSONB)
    source_record_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("source_record.id", ondelete="RESTRICT"),
        nullable=False,
    )
    evidence_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("evidence.id", ondelete="RESTRICT"),
        nullable=False,
    )
    valid_from: Mapped[date | None] = mapped_column(Date)
    valid_to: Mapped[date | None] = mapped_column(Date)
    confidence: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False)

    subject_entity: Mapped[Entity] = orm_relationship(foreign_keys=[subject_entity_id])
    object_entity: Mapped[Entity | None] = orm_relationship(foreign_keys=[object_entity_id])
    source_record: Mapped[SourceRecord] = orm_relationship()
