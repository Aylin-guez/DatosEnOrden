from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship as orm_relationship

from datosenorden.db.base import Base
from datosenorden.models.catalog import Dataset, Source
from datosenorden.models.types import TimestampMixin


class SourceRecord(Base, TimestampMixin):
    __tablename__ = "source_record"
    __table_args__ = (
        CheckConstraint(
            "status in ('ingested', 'normalized', 'validated', 'published', 'rejected', 'disputed', 'withdrawn')",
            name="ck_source_record_status",
        ),
        UniqueConstraint(
            "dataset_id",
            "record_type",
            "external_id",
            name="uq_source_record_dataset_type_external_id",
        ),
        Index("ix_source_record_source_id", "source_id"),
        Index("ix_source_record_dataset_id", "dataset_id"),
        Index("ix_source_record_status", "status"),
        Index("ix_source_record_payload_hash", "payload_hash"),
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
    dataset_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("dataset.id", ondelete="RESTRICT"),
        nullable=False,
    )
    external_id: Mapped[str] = mapped_column(String(255), nullable=False)
    record_type: Mapped[str] = mapped_column(String(120), nullable=False)
    payload_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    raw_payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    error_log: Mapped[str | None] = mapped_column(Text)

    source: Mapped[Source] = orm_relationship()
    dataset: Mapped[Dataset] = orm_relationship()
