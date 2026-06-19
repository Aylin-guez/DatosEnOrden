from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship as orm_relationship

from datosenorden.db.base import Base
from datosenorden.models.catalog import Dataset
from datosenorden.models.types import TimestampMixin


class ImportJob(Base, TimestampMixin):
    __tablename__ = "import_job"
    __table_args__ = (
        CheckConstraint(
            "status in ('pending', 'running', 'succeeded', 'failed', 'cancelled')",
            name="ck_import_job_status",
        ),
        CheckConstraint("records_processed >= 0", name="ck_import_job_records_processed"),
        Index("ix_import_job_dataset_id", "dataset_id"),
        Index("ix_import_job_status", "status"),
    )

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    dataset_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("dataset.id", ondelete="RESTRICT"),
        nullable=False,
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="pending")
    records_processed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_log: Mapped[str | None] = mapped_column(Text)
    job_metadata: Mapped[dict | None] = mapped_column(JSONB)

    dataset: Mapped[Dataset] = orm_relationship()
