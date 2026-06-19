from datetime import date
from uuid import UUID

from sqlalchemy import Date, ForeignKey, Index, String, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship as orm_relationship

from datosenorden.db.base import Base
from datosenorden.models.catalog import Dataset, Source
from datosenorden.models.source_records import SourceRecord
from datosenorden.models.types import TimestampMixin


class Evidence(Base, TimestampMixin):
    __tablename__ = "evidence"
    __table_args__ = (
        UniqueConstraint("source_record_id", "url", name="uq_evidence_source_record_url"),
        Index("ix_evidence_source_id", "source_id"),
        Index("ix_evidence_dataset_id", "dataset_id"),
        Index("ix_evidence_source_record_id", "source_record_id"),
        Index("ix_evidence_claim_id", "claim_id"),
        Index("ix_evidence_published_at", "published_at"),
    )

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    source_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("source.id", ondelete="RESTRICT"),
        nullable=False,
    )
    dataset_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("dataset.id", ondelete="RESTRICT"),
    )
    source_record_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("source_record.id", ondelete="RESTRICT"),
    )
    claim_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("claim.id", ondelete="SET NULL", use_alter=True, name="fk_evidence_claim"),
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    published_at: Mapped[date | None] = mapped_column(Date)
    excerpt: Mapped[str | None] = mapped_column(Text)
    evidence_metadata: Mapped[dict | None] = mapped_column(JSONB)

    source: Mapped[Source] = orm_relationship()
    dataset: Mapped[Dataset | None] = orm_relationship()
    source_record: Mapped[SourceRecord | None] = orm_relationship()
