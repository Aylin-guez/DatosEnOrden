from uuid import UUID

from sqlalchemy import CheckConstraint, Index, String, text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from datosenorden.db.base import Base
from datosenorden.models.types import TimestampMixin


class ChangeLog(Base, TimestampMixin):
    __tablename__ = "change_log"
    __table_args__ = (
        CheckConstraint(
            "action in ('insert', 'update', 'delete')",
            name="ck_change_log_action",
        ),
        Index("ix_change_log_entity", "entity_table", "entity_id"),
    )

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    entity_table: Mapped[str] = mapped_column(String(120), nullable=False)
    entity_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    action: Mapped[str] = mapped_column(String(30), nullable=False)
    previous_value: Mapped[dict | None] = mapped_column(JSONB)
    new_value: Mapped[dict | None] = mapped_column(JSONB)
