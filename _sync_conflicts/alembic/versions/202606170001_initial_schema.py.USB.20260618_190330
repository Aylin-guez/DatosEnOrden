"""initial schema

Revision ID: 202606170001
Revises:
Create Date: 2026-06-17 23:30:00
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "202606170001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto"')

    op.create_table(
        "source",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("publisher", sa.String(length=255), nullable=True),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("license", sa.String(length=255), nullable=True),
        sa.Column("retrieved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("source_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("url", name="uq_source_url"),
    )
    op.create_index("ix_source_publisher", "source", ["publisher"])

    op.create_table(
        "entity",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("entity_type", sa.String(length=80), nullable=False),
        sa.Column("name", sa.String(length=500), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("external_id", sa.String(length=255), nullable=True),
        sa.Column("normalized_key", sa.String(length=500), nullable=True),
        sa.Column("status", sa.String(length=30), server_default="active", nullable=False),
        sa.Column("entity_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("status in ('active', 'inactive', 'deprecated')", name="ck_entity_status"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("entity_type", "external_id", name="uq_entity_type_external_id"),
    )
    op.create_index("ix_entity_name", "entity", ["name"])
    op.create_index("ix_entity_type", "entity", ["entity_type"])

    op.create_table(
        "dataset",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("version", sa.String(length=100), nullable=False),
        sa.Column("dataset_url", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.String(length=128), nullable=True),
        sa.Column("loaded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("dataset_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["source_id"], ["source.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_id", "name", "version", name="uq_dataset_source_name_version"),
    )
    op.create_index("ix_dataset_source_id", "dataset", ["source_id"])

    op.create_table(
        "relationship",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("source_entity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("target_entity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("relationship_type", sa.String(length=80), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("relationship_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("source_entity_id <> target_entity_id", name="ck_relationship_no_self_reference"),
        sa.CheckConstraint(
            "end_date is null or start_date is null or end_date >= start_date",
            name="ck_relationship_valid_date_range",
        ),
        sa.ForeignKeyConstraint(["source_entity_id"], ["entity.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["target_entity_id"], ["entity.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "source_entity_id",
            "target_entity_id",
            "relationship_type",
            "start_date",
            "end_date",
            name="uq_relationship_identity",
        ),
    )
    op.create_index("ix_relationship_source_entity_id", "relationship", ["source_entity_id"])
    op.create_index("ix_relationship_target_entity_id", "relationship", ["target_entity_id"])
    op.create_index("ix_relationship_type", "relationship", ["relationship_type"])

    op.create_table(
        "change_log",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("entity_table", sa.String(length=120), nullable=False),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("action", sa.String(length=30), nullable=False),
        sa.Column("previous_value", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("new_value", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("action in ('insert', 'update', 'delete')", name="ck_change_log_action"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_change_log_entity", "change_log", ["entity_table", "entity_id"])

    op.create_table(
        "evidence",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("relationship_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("published_at", sa.Date(), nullable=True),
        sa.Column("excerpt", sa.Text(), nullable=True),
        sa.Column("evidence_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["relationship_id"], ["relationship.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["source_id"], ["source.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("relationship_id", "source_id", "url", name="uq_evidence_relationship_url"),
    )
    op.create_index("ix_evidence_published_at", "evidence", ["published_at"])
    op.create_index("ix_evidence_relationship_id", "evidence", ["relationship_id"])
    op.create_index("ix_evidence_source_id", "evidence", ["source_id"])

    op.create_table(
        "import_job",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("dataset_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=30), server_default="pending", nullable=False),
        sa.Column("records_processed", sa.Integer(), server_default="0", nullable=False),
        sa.Column("error_log", sa.Text(), nullable=True),
        sa.Column("job_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "status in ('pending', 'running', 'succeeded', 'failed', 'cancelled')",
            name="ck_import_job_status",
        ),
        sa.CheckConstraint("records_processed >= 0", name="ck_import_job_records_processed"),
        sa.ForeignKeyConstraint(["dataset_id"], ["dataset.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_import_job_dataset_id", "import_job", ["dataset_id"])
    op.create_index("ix_import_job_status", "import_job", ["status"])


def downgrade() -> None:
    op.drop_index("ix_import_job_status", table_name="import_job")
    op.drop_index("ix_import_job_dataset_id", table_name="import_job")
    op.drop_table("import_job")
    op.drop_index("ix_evidence_source_id", table_name="evidence")
    op.drop_index("ix_evidence_relationship_id", table_name="evidence")
    op.drop_index("ix_evidence_published_at", table_name="evidence")
    op.drop_table("evidence")
    op.drop_index("ix_change_log_entity", table_name="change_log")
    op.drop_table("change_log")
    op.drop_index("ix_relationship_type", table_name="relationship")
    op.drop_index("ix_relationship_target_entity_id", table_name="relationship")
    op.drop_index("ix_relationship_source_entity_id", table_name="relationship")
    op.drop_table("relationship")
    op.drop_index("ix_dataset_source_id", table_name="dataset")
    op.drop_table("dataset")
    op.drop_index("ix_entity_type", table_name="entity")
    op.drop_index("ix_entity_name", table_name="entity")
    op.drop_table("entity")
    op.drop_index("ix_source_publisher", table_name="source")
    op.drop_table("source")
