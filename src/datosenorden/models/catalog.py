from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship as orm_relationship

from datosenorden.db.base import Base
from datosenorden.models.types import TimestampMixin


class Source(Base, TimestampMixin):
    __tablename__ = "source"
    __table_args__ = (
        UniqueConstraint("url", name="uq_source_url"),
        Index("ix_source_publisher", "publisher"),
    )

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    publisher: Mapped[str | None] = mapped_column(String(255))
    url: Mapped[str] = mapped_column(Text, nullable=False)
    license: Mapped[str | None] = mapped_column(String(255))
    retrieved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    source_metadata: Mapped[dict | None] = mapped_column(JSONB)

    datasets: Mapped[list["Dataset"]] = orm_relationship(back_populates="source")


class Dataset(Base, TimestampMixin):
    __tablename__ = "dataset"
    __table_args__ = (
        UniqueConstraint("source_id", "name", "version", name="uq_dataset_source_name_version"),
        Index("ix_dataset_source_id", "source_id"),
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
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    version: Mapped[str] = mapped_column(String(100), nullable=False)
    dataset_url: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str | None] = mapped_column(String(128))
    loaded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    dataset_metadata: Mapped[dict | None] = mapped_column(JSONB)

    source: Mapped[Source] = orm_relationship(back_populates="datasets")
