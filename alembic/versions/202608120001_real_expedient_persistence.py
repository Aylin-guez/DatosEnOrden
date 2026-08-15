"""REAL expedient versioned persistence

Revision ID: 202608120001
Revises: 202606180001
Create Date: 2026-08-12 00:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "202608120001"
down_revision: str | None = "202606180001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "real_expedient",
        sa.Column("expedient_id", sa.String(length=120), nullable=False),
        sa.Column("provenance_class", sa.String(length=20), nullable=False),
        sa.Column("current_version", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "provenance_class in ('REAL', 'DEMO', 'TEST', 'UNKNOWN')",
            name="ck_real_expedient_provenance",
        ),
        sa.CheckConstraint("current_version >= 1", name="ck_real_expedient_current_version"),
        sa.PrimaryKeyConstraint("expedient_id"),
    )
    op.create_index(
        "ix_real_expedient_provenance_current",
        "real_expedient",
        ["provenance_class", "current_version"],
    )

    op.create_table(
        "real_expedient_version",
        sa.Column("expedient_id", sa.String(length=120), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("lifecycle", sa.String(length=30), nullable=False),
        sa.Column("fingerprint", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("version >= 1", name="ck_real_expedient_version_positive"),
        sa.CheckConstraint(
            "lifecycle in ('draft', 'published', 'withdrawn')",
            name="ck_real_expedient_version_lifecycle",
        ),
        sa.ForeignKeyConstraint(
            ["expedient_id"], ["real_expedient.expedient_id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("expedient_id", "version"),
    )
    op.create_index(
        "ix_real_expedient_version_public",
        "real_expedient_version",
        ["lifecycle", "expedient_id", "version"],
    )

    op.create_table(
        "real_expedient_reference",
        sa.Column("expedient_id", sa.String(length=120), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("reference_type", sa.String(length=30), nullable=False),
        sa.Column("reference_id", sa.String(length=255), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.CheckConstraint(
            "reference_type in "
            "('claim', 'evidence', 'relationship', 'entity', 'document', 'source')",
            name="ck_real_expedient_reference_type",
        ),
        sa.CheckConstraint("ordinal >= 0", name="ck_real_expedient_reference_ordinal"),
        sa.ForeignKeyConstraint(
            ["expedient_id", "version"],
            ["real_expedient_version.expedient_id", "real_expedient_version.version"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("expedient_id", "version", "reference_type", "reference_id"),
    )
    op.create_index(
        "ix_real_expedient_reference_reverse",
        "real_expedient_reference",
        ["reference_type", "reference_id"],
    )

    op.create_table(
        "real_expedient_narrative",
        sa.Column("expedient_id", sa.String(length=120), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("statement_id", sa.String(length=120), nullable=False),
        sa.Column("section", sa.String(length=120), nullable=False),
        sa.Column("statement", sa.Text(), nullable=False),
        sa.Column("epistemic_class", sa.String(length=30), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.CheckConstraint(
            "epistemic_class in ('FACT', 'SUPPORTED_INFERENCE', 'OPEN_QUESTION', 'UNKNOWN')",
            name="ck_real_expedient_narrative_epistemic",
        ),
        sa.CheckConstraint("ordinal >= 0", name="ck_real_expedient_narrative_ordinal"),
        sa.ForeignKeyConstraint(
            ["expedient_id", "version"],
            ["real_expedient_version.expedient_id", "real_expedient_version.version"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("expedient_id", "version", "statement_id"),
    )

    op.create_table(
        "real_expedient_narrative_support",
        sa.Column("expedient_id", sa.String(length=120), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("statement_id", sa.String(length=120), nullable=False),
        sa.Column("support_type", sa.String(length=30), nullable=False),
        sa.Column("reference_id", sa.String(length=255), nullable=False),
        sa.CheckConstraint(
            "support_type in ('claim', 'evidence')", name="ck_real_expedient_support_type"
        ),
        sa.ForeignKeyConstraint(
            ["expedient_id", "version", "statement_id"],
            [
                "real_expedient_narrative.expedient_id",
                "real_expedient_narrative.version",
                "real_expedient_narrative.statement_id",
            ],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["expedient_id", "version", "support_type", "reference_id"],
            [
                "real_expedient_reference.expedient_id",
                "real_expedient_reference.version",
                "real_expedient_reference.reference_type",
                "real_expedient_reference.reference_id",
            ],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint(
            "expedient_id", "version", "statement_id", "support_type", "reference_id"
        ),
    )


def downgrade() -> None:
    connection = op.get_bind()
    populated = connection.execute(
        sa.text("select exists(select 1 from real_expedient limit 1)")
    ).scalar_one()
    if populated:
        raise RuntimeError("refusing to remove non-empty REAL expedient persistence tables")

    op.drop_table("real_expedient_narrative_support")
    op.drop_table("real_expedient_narrative")
    op.drop_index("ix_real_expedient_reference_reverse", table_name="real_expedient_reference")
    op.drop_table("real_expedient_reference")
    op.drop_index("ix_real_expedient_version_public", table_name="real_expedient_version")
    op.drop_table("real_expedient_version")
    op.drop_index("ix_real_expedient_provenance_current", table_name="real_expedient")
    op.drop_table("real_expedient")
