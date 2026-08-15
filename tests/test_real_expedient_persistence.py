from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from uuid import uuid4

import psycopg
import pytest
from psycopg import sql
from sqlalchemy import create_engine, func, select
from sqlalchemy.engine import make_url
from sqlalchemy.exc import DataError, IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from datosenorden.application.provenance.models import ProvenanceClass
from datosenorden.application.real_expedient import (
    ComposedPublicExpedientReader,
    EpistemicClass,
    ExpedientConflictError,
    ExpedientProvisioningService,
    ExpedientReferences,
    ExpedientSpecification,
    ExpedientStatus,
    NarrativeStatement,
    PublicExpedientUnavailableError,
    ReferenceEligibility,
    ReferenceKind,
)
from datosenorden.infrastructure.real_expedient.models import (
    RealExpedientReferenceRow,
    RealExpedientRow,
    RealExpedientVersionRow,
)
from datosenorden.infrastructure.real_expedient.repository import PostgresExpedientRepository

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ADMIN_ENV = "REAL_EXPEDIENT_TEST_ADMIN_URL"


class AllowRealReferences:
    def classify(self, kind: ReferenceKind, reference_id: str) -> ReferenceEligibility:
        return ReferenceEligibility(ProvenanceClass.REAL, public_usable=True)


def _specification(
    *,
    expedient_id: str = "EXP-PG-TEST",
    version: int = 1,
    status: ExpedientStatus = ExpedientStatus.PUBLISHED,
    provenance: ProvenanceClass = ProvenanceClass.REAL,
    summary: str = "Resumen sintético de contrato.",
    source_id: str = "source-test",
) -> ExpedientSpecification:
    return ExpedientSpecification(
        expedient_id=expedient_id,
        title="Expediente PostgreSQL sintético",
        question="¿Funciona el contrato persistente?",
        summary=summary,
        provenance_class=provenance,
        status=status,
        version=version,
        references=ExpedientReferences(
            claim_ids=("claim-test",),
            evidence_ids=("evidence-test",),
            relationship_ids=("relationship-test",),
            entity_ids=("entity-test",),
            document_ids=("document-test",),
            source_ids=(source_id,),
        ),
        statements=(
            NarrativeStatement(
                "statement-test",
                "what_we_know",
                "Afirmación sintética respaldada.",
                EpistemicClass.FACT,
                claim_ids=("claim-test",),
                evidence_ids=("evidence-test",),
            ),
        ),
    )


@pytest.fixture(scope="module")
def postgres_url() -> str:
    admin_value = os.getenv(ADMIN_ENV, "")
    if not admin_value:
        pytest.skip(f"{ADMIN_ENV} is required for isolated PostgreSQL repository tests")
    parsed = make_url(admin_value)
    if parsed.database != "postgres":
        pytest.fail(f"{ADMIN_ENV} must target the postgres maintenance database")
    database_name = f"datosenorden_exp_test_{uuid4().hex[:12]}"
    value = str(parsed.set(database=database_name))
    psycopg_admin = admin_value.replace("postgresql+psycopg://", "postgresql://", 1)
    with psycopg.connect(psycopg_admin, autocommit=True) as connection:
        connection.execute(sql.SQL("create database {}").format(sql.Identifier(database_name)))
    environment = os.environ.copy()
    environment["DATABASE_URL"] = value
    subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=PROJECT_ROOT,
        env=environment,
        check=True,
        capture_output=True,
        text=True,
    )
    yield value
    with psycopg.connect(psycopg_admin, autocommit=True) as connection:
        connection.execute(
            "select pg_terminate_backend(pid) from pg_stat_activity "
            "where datname = %s and pid <> pg_backend_pid()",
            (database_name,),
        )
        connection.execute(sql.SQL("drop database {}").format(sql.Identifier(database_name)))


def test_postgres_insert_reopen_idempotency_and_conflict(postgres_url: str) -> None:
    engine = create_engine(postgres_url)
    with Session(engine) as session:
        service = ExpedientProvisioningService(
            PostgresExpedientRepository(session), AllowRealReferences()
        )
        first = service.create_if_absent(_specification())
        repeated = service.create_if_absent(_specification())
        assert first.created is True
        assert repeated.created is False
        assert service.get("EXP-PG-TEST") == first.expedient
        assert session.scalar(select(func.count()).select_from(RealExpedientVersionRow)) == 1
        with pytest.raises(ExpedientConflictError, match="incompatible"):
            service.create_if_absent(_specification(summary="Resumen incompatible."))
    engine.dispose()


def test_append_preserves_history_and_optimistic_conflict(postgres_url: str) -> None:
    engine = create_engine(postgres_url)
    first_session = Session(engine)
    second_session = Session(engine)
    try:
        first = ExpedientProvisioningService(
            PostgresExpedientRepository(first_session), AllowRealReferences()
        )
        second = ExpedientProvisioningService(
            PostgresExpedientRepository(second_session), AllowRealReferences()
        )
        assert first.get("EXP-PG-TEST").specification.version == 1  # type: ignore[union-attr]
        assert second.get("EXP-PG-TEST").specification.version == 1  # type: ignore[union-attr]
        first.revise(_specification(version=2, summary="Resumen v2."), expected_current_version=1)
        with pytest.raises(ExpedientConflictError, match="version conflict"):
            second.revise(_specification(version=2, summary="Otra v2."), expected_current_version=1)
        with Session(engine) as verification:
            versions = verification.scalars(
                select(RealExpedientVersionRow.version)
                .where(RealExpedientVersionRow.expedient_id == "EXP-PG-TEST")
                .order_by(RealExpedientVersionRow.version)
            ).all()
            assert versions == [1, 2]
    finally:
        first_session.close()
        second_session.close()
        engine.dispose()


def test_reference_constraints_and_partial_insert_rollback(postgres_url: str) -> None:
    engine = create_engine(postgres_url)
    with Session(engine) as session:
        session.add(
            RealExpedientReferenceRow(
                expedient_id="EXP-PG-TEST",
                version=2,
                reference_type="arbitrary",
                reference_id="invalid",
                ordinal=0,
            )
        )
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()

        service = ExpedientProvisioningService(
            PostgresExpedientRepository(session), AllowRealReferences()
        )
        with pytest.raises(DataError):
            service.create_if_absent(
                _specification(expedient_id="EXP-PARTIAL", source_id="x" * 256)
            )
        assert session.get(RealExpedientRow, "EXP-PARTIAL") is None
        assert (
            session.scalar(
                select(func.count())
                .select_from(RealExpedientVersionRow)
                .where(RealExpedientVersionRow.expedient_id == "EXP-PARTIAL")
            )
            == 0
        )
    engine.dispose()


def test_public_listing_filters_lifecycle_and_provenance(postgres_url: str) -> None:
    engine = create_engine(postgres_url)
    with Session(engine) as session:
        service = ExpedientProvisioningService(
            PostgresExpedientRepository(session), AllowRealReferences()
        )
        service.create_if_absent(_specification(expedient_id="EXP-PUBLISHED"))
        service.create_if_absent(
            _specification(expedient_id="EXP-DRAFT", status=ExpedientStatus.DRAFT)
        )
        service.create_if_absent(
            _specification(expedient_id="EXP-WITHDRAWN", status=ExpedientStatus.WITHDRAWN)
        )
        service.create_if_absent(
            _specification(expedient_id="EXP-TEST", provenance=ProvenanceClass.TEST)
        )
        service.create_if_absent(
            _specification(expedient_id="EXP-UNKNOWN", provenance=ProvenanceClass.UNKNOWN)
        )
        identifiers = {item.specification.expedient_id for item in service.list_public()}
        assert "EXP-PUBLISHED" in identifiers
        assert not {"EXP-DRAFT", "EXP-WITHDRAWN", "EXP-TEST", "EXP-UNKNOWN"} & identifiers
    engine.dispose()


def test_composed_reader_persisted_then_exp001_only(postgres_url: str) -> None:
    engine = create_engine(postgres_url)
    with Session(engine) as session:
        reader = ComposedPublicExpedientReader(PostgresExpedientRepository(session))
        assert reader.get("EXP-PUBLISHED")["id"] == "EXP-PUBLISHED"  # type: ignore[index]
        assert reader.get("EXP-001")["id"] == "EXP-001"  # type: ignore[index]
        assert reader.get("EXP-DOES-NOT-EXIST") is None
        listed = {item["id"] for item in reader.list_available()}
        assert {"EXP-PUBLISHED", "EXP-001"} <= listed
    engine.dispose()


def test_reader_sanitizes_database_failures() -> None:
    class BrokenRepository:
        def get(self, expedient_id: str):  # noqa: ANN202
            raise SQLAlchemyError("postgresql://secret@host/internal")

        def list_public(self):  # noqa: ANN202
            raise SQLAlchemyError("select * from private_table")

    reader = ComposedPublicExpedientReader(BrokenRepository())
    with pytest.raises(PublicExpedientUnavailableError, match="repository unavailable") as error:
        reader.get("EXP-PRIVATE")
    assert "secret" not in str(error.value)
