from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from datosenorden.db.base import Base


class RealExpedientRow(Base):
    __tablename__ = "real_expedient"
    __table_args__ = (
        CheckConstraint(
            "provenance_class in ('REAL', 'DEMO', 'TEST', 'UNKNOWN')",
            name="ck_real_expedient_provenance",
        ),
        CheckConstraint("current_version >= 1", name="ck_real_expedient_current_version"),
        Index("ix_real_expedient_provenance_current", "provenance_class", "current_version"),
    )

    expedient_id: Mapped[str] = mapped_column(String(120), primary_key=True)
    provenance_class: Mapped[str] = mapped_column(String(20), nullable=False)
    current_version: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class RealExpedientVersionRow(Base):
    __tablename__ = "real_expedient_version"
    __table_args__ = (
        ForeignKeyConstraint(
            ["expedient_id"], ["real_expedient.expedient_id"], ondelete="RESTRICT"
        ),
        CheckConstraint("version >= 1", name="ck_real_expedient_version_positive"),
        CheckConstraint(
            "lifecycle in ('draft', 'published', 'withdrawn')",
            name="ck_real_expedient_version_lifecycle",
        ),
        Index("ix_real_expedient_version_public", "lifecycle", "expedient_id", "version"),
    )

    expedient_id: Mapped[str] = mapped_column(String(120), primary_key=True)
    version: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    lifecycle: Mapped[str] = mapped_column(String(30), nullable=False)
    fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class RealExpedientReferenceRow(Base):
    __tablename__ = "real_expedient_reference"
    __table_args__ = (
        ForeignKeyConstraint(
            ["expedient_id", "version"],
            ["real_expedient_version.expedient_id", "real_expedient_version.version"],
            ondelete="RESTRICT",
        ),
        CheckConstraint(
            "reference_type in "
            "('claim', 'evidence', 'relationship', 'entity', 'document', 'source')",
            name="ck_real_expedient_reference_type",
        ),
        CheckConstraint("ordinal >= 0", name="ck_real_expedient_reference_ordinal"),
        Index("ix_real_expedient_reference_reverse", "reference_type", "reference_id"),
    )

    expedient_id: Mapped[str] = mapped_column(String(120), primary_key=True)
    version: Mapped[int] = mapped_column(Integer, primary_key=True)
    reference_type: Mapped[str] = mapped_column(String(30), primary_key=True)
    reference_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)


class RealExpedientNarrativeRow(Base):
    __tablename__ = "real_expedient_narrative"
    __table_args__ = (
        ForeignKeyConstraint(
            ["expedient_id", "version"],
            ["real_expedient_version.expedient_id", "real_expedient_version.version"],
            ondelete="RESTRICT",
        ),
        CheckConstraint(
            "epistemic_class in ('FACT', 'SUPPORTED_INFERENCE', 'OPEN_QUESTION', 'UNKNOWN')",
            name="ck_real_expedient_narrative_epistemic",
        ),
        CheckConstraint("ordinal >= 0", name="ck_real_expedient_narrative_ordinal"),
    )

    expedient_id: Mapped[str] = mapped_column(String(120), primary_key=True)
    version: Mapped[int] = mapped_column(Integer, primary_key=True)
    statement_id: Mapped[str] = mapped_column(String(120), primary_key=True)
    section: Mapped[str] = mapped_column(String(120), nullable=False)
    statement: Mapped[str] = mapped_column(Text, nullable=False)
    epistemic_class: Mapped[str] = mapped_column(String(30), nullable=False)
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)


class RealExpedientNarrativeSupportRow(Base):
    __tablename__ = "real_expedient_narrative_support"
    __table_args__ = (
        ForeignKeyConstraint(
            ["expedient_id", "version", "statement_id"],
            [
                "real_expedient_narrative.expedient_id",
                "real_expedient_narrative.version",
                "real_expedient_narrative.statement_id",
            ],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["expedient_id", "version", "support_type", "reference_id"],
            [
                "real_expedient_reference.expedient_id",
                "real_expedient_reference.version",
                "real_expedient_reference.reference_type",
                "real_expedient_reference.reference_id",
            ],
            ondelete="RESTRICT",
        ),
        CheckConstraint(
            "support_type in ('claim', 'evidence')", name="ck_real_expedient_support_type"
        ),
    )

    expedient_id: Mapped[str] = mapped_column(String(120), primary_key=True)
    version: Mapped[int] = mapped_column(Integer, primary_key=True)
    statement_id: Mapped[str] = mapped_column(String(120), primary_key=True)
    support_type: Mapped[str] = mapped_column(String(30), primary_key=True)
    reference_id: Mapped[str] = mapped_column(String(255), primary_key=True)
