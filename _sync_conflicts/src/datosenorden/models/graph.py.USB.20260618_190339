from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship as orm_relationship

from datosenorden.db.base import Base
from datosenorden.models.types import TimestampMixin, UpdatedAtMixin


class Entity(Base, UpdatedAtMixin):
    __tablename__ = "entity"
    __table_args__ = (
        CheckConstraint("status in ('active', 'inactive', 'deprecated')", name="ck_entity_status"),
        UniqueConstraint("entity_type", "external_id", name="uq_entity_type_external_id"),
        Index("ix_entity_type", "entity_type"),
        Index("ix_entity_name", "name"),
    )

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    entity_type: Mapped[str] = mapped_column(String(80), nullable=False)
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    external_id: Mapped[str | None] = mapped_column(String(255))
    normalized_key: Mapped[str | None] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="active")
    entity_metadata: Mapped[dict | None] = mapped_column(JSONB)

    outgoing_relationships: Mapped[list["RelationshipPublic"]] = orm_relationship(
        foreign_keys="RelationshipPublic.source_entity_id",
        back_populates="source_entity",
    )
    incoming_relationships: Mapped[list["RelationshipPublic"]] = orm_relationship(
        foreign_keys="RelationshipPublic.target_entity_id",
        back_populates="target_entity",
    )


class RelationshipPublic(Base, TimestampMixin):
    __tablename__ = "relationship_public"
    __table_args__ = (
        CheckConstraint(
            "status in ('ingested', 'normalized', 'validated', 'published', 'rejected', 'disputed', 'withdrawn')",
            name="ck_relationship_public_status",
        ),
        UniqueConstraint(
            "claim_id",
            name="uq_relationship_public_claim_id",
        ),
        Index("ix_relationship_public_source_entity_id", "source_entity_id"),
        Index("ix_relationship_public_target_entity_id", "target_entity_id"),
        Index("ix_relationship_public_type", "relationship_type"),
        Index("ix_relationship_public_claim_id", "claim_id"),
        Index("ix_relationship_public_status", "status"),
    )

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    source_entity_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("entity.id", ondelete="RESTRICT"),
        nullable=False,
    )
    target_entity_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("entity.id", ondelete="RESTRICT"),
        nullable=False,
    )
    relationship_type: Mapped[str] = mapped_column(String(80), nullable=False)
    claim_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("claim.id", ondelete="RESTRICT"),
        nullable=False,
    )
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    relationship_metadata: Mapped[dict | None] = mapped_column(JSONB)

    source_entity: Mapped[Entity] = orm_relationship(
        foreign_keys=[source_entity_id],
        back_populates="outgoing_relationships",
    )
    target_entity: Mapped[Entity] = orm_relationship(
        foreign_keys=[target_entity_id],
        back_populates="incoming_relationships",
    )
    claim: Mapped["Claim"] = orm_relationship()
