"""phase 2.5 claims and traceability

Revision ID: 202606180001
Revises: 202606170001
Create Date: 2026-06-18 00:30:00
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "202606180001"
down_revision: str | None = "202606170001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

STATUS_CHECK = "('ingested', 'normalized', 'validated', 'published', 'rejected', 'disputed', 'withdrawn')"


def upgrade() -> None:
    op.drop_table("evidence")
    op.drop_table("relationship")

    op.create_table(
        "source_record",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("dataset_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("external_id", sa.String(length=255), nullable=False),
        sa.Column("record_type", sa.String(length=120), nullable=False),
        sa.Column("payload_hash", sa.String(length=128), nullable=False),
        sa.Column("raw_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("retrieved_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("error_log", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(f"status in {STATUS_CHECK}", name="ck_source_record_status"),
        sa.ForeignKeyConstraint(["dataset_id"], ["dataset.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["source_id"], ["source.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("dataset_id", "record_type", "external_id", name="uq_source_record_dataset_type_external_id"),
    )
    op.create_index("ix_source_record_dataset_id", "source_record", ["dataset_id"])
    op.create_index("ix_source_record_payload_hash", "source_record", ["payload_hash"])
    op.create_index("ix_source_record_source_id", "source_record", ["source_id"])
    op.create_index("ix_source_record_status", "source_record", ["status"])

    op.create_table(
        "evidence",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("dataset_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("source_record_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("claim_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("published_at", sa.Date(), nullable=True),
        sa.Column("excerpt", sa.Text(), nullable=True),
        sa.Column("evidence_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["dataset_id"], ["dataset.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["source_id"], ["source.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["source_record_id"], ["source_record.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_record_id", "url", name="uq_evidence_source_record_url"),
    )
    op.create_index("ix_evidence_claim_id", "evidence", ["claim_id"])
    op.create_index("ix_evidence_dataset_id", "evidence", ["dataset_id"])
    op.create_index("ix_evidence_published_at", "evidence", ["published_at"])
    op.create_index("ix_evidence_source_id", "evidence", ["source_id"])
    op.create_index("ix_evidence_source_record_id", "evidence", ["source_record_id"])

    op.create_table(
        "claim",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("subject_entity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("predicate", sa.String(length=120), nullable=False),
        sa.Column("object_entity_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("object_value", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("source_record_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("evidence_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("valid_from", sa.Date(), nullable=True),
        sa.Column("valid_to", sa.Date(), nullable=True),
        sa.Column("confidence", sa.Numeric(5, 4), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("confidence >= 0 and confidence <= 1", name="ck_claim_confidence_range"),
        sa.CheckConstraint(f"status in {STATUS_CHECK}", name="ck_claim_status"),
        sa.CheckConstraint("object_entity_id is not null or object_value is not null", name="ck_claim_has_object"),
        sa.CheckConstraint("valid_to is null or valid_from is null or valid_to >= valid_from", name="ck_claim_valid_date_range"),
        sa.ForeignKeyConstraint(["evidence_id"], ["evidence.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["object_entity_id"], ["entity.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["source_record_id"], ["source_record.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["subject_entity_id"], ["entity.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_claim_evidence_id", "claim", ["evidence_id"])
    op.create_index("ix_claim_object_entity_id", "claim", ["object_entity_id"])
    op.create_index("ix_claim_predicate", "claim", ["predicate"])
    op.create_index("ix_claim_source_record_id", "claim", ["source_record_id"])
    op.create_index("ix_claim_status", "claim", ["status"])
    op.create_index("ix_claim_subject_entity_id", "claim", ["subject_entity_id"])

    op.create_foreign_key(
        "fk_evidence_claim",
        "evidence",
        "claim",
        ["claim_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.create_table(
        "relationship_public",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("source_entity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("target_entity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("relationship_type", sa.String(length=80), nullable=False),
        sa.Column("claim_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("relationship_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(f"status in {STATUS_CHECK}", name="ck_relationship_public_status"),
        sa.ForeignKeyConstraint(["claim_id"], ["claim.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["source_entity_id"], ["entity.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["target_entity_id"], ["entity.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("claim_id", name="uq_relationship_public_claim_id"),
    )
    op.create_index("ix_relationship_public_claim_id", "relationship_public", ["claim_id"])
    op.create_index("ix_relationship_public_source_entity_id", "relationship_public", ["source_entity_id"])
    op.create_index("ix_relationship_public_status", "relationship_public", ["status"])
    op.create_index("ix_relationship_public_target_entity_id", "relationship_public", ["target_entity_id"])
    op.create_index("ix_relationship_public_type", "relationship_public", ["relationship_type"])


def downgrade() -> None:
    op.drop_index("ix_relationship_public_type", table_name="relationship_public")
    op.drop_index("ix_relationship_public_target_entity_id", table_name="relationship_public")
    op.drop_index("ix_relationship_public_status", table_name="relationship_public")
    op.drop_index("ix_relationship_public_source_entity_id", table_name="relationship_public")
    op.drop_index("ix_relationship_public_claim_id", table_name="relationship_public")
    op.drop_table("relationship_public")
    op.drop_constraint("fk_evidence_claim", "evidence", type_="foreignkey")
    op.drop_index("ix_claim_subject_entity_id", table_name="claim")
    op.drop_index("ix_claim_status", table_name="claim")
    op.drop_index("ix_claim_source_record_id", table_name="claim")
    op.drop_index("ix_claim_predicate", table_name="claim")
    op.drop_index("ix_claim_object_entity_id", table_name="claim")
    op.drop_index("ix_claim_evidence_id", table_name="claim")
    op.drop_table("claim")
    op.drop_index("ix_evidence_source_record_id", table_name="evidence")
    op.drop_index("ix_evidence_source_id", table_name="evidence")
    op.drop_index("ix_evidence_published_at", table_name="evidence")
    op.drop_index("ix_evidence_dataset_id", table_name="evidence")
    op.drop_index("ix_evidence_claim_id", table_name="evidence")
    op.drop_table("evidence")
    op.drop_index("ix_source_record_status", table_name="source_record")
    op.drop_index("ix_source_record_source_id", table_name="source_record")
    op.drop_index("ix_source_record_payload_hash", table_name="source_record")
    op.drop_index("ix_source_record_dataset_id", table_name="source_record")
    op.drop_table("source_record")

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
        sa.CheckConstraint("end_date is null or start_date is null or end_date >= start_date", name="ck_relationship_valid_date_range"),
        sa.ForeignKeyConstraint(["source_entity_id"], ["entity.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["target_entity_id"], ["entity.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_entity_id", "target_entity_id", "relationship_type", "start_date", "end_date", name="uq_relationship_identity"),
    )
    op.create_index("ix_relationship_source_entity_id", "relationship", ["source_entity_id"])
    op.create_index("ix_relationship_target_entity_id", "relationship", ["target_entity_id"])
    op.create_index("ix_relationship_type", "relationship", ["relationship_type"])

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
