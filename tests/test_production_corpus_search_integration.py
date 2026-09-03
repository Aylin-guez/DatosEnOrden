from __future__ import annotations

import os
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from datosenorden.application.data_release.exporter import build_serialized_public_release_rows
from datosenorden.application.data_release.importer import (
    TargetExpectation,
    import_package,
    verify_package,
)
from datosenorden.application.data_release.materialization import (
    APPROVED_REAL_IDS,
    CorpusMaterializationError,
    assert_approved_corpus_complete,
    materialize_approved_real_corpus,
)
from datosenorden.application.provenance.service import build_public_metric_projection
from datosenorden.infrastructure.real_expedient.repository import PostgresExpedientRepository
from datosenorden.maintenance.search_workspace import search_workspace
from scripts.materialize_production_corpus import _require_base_rows_unchanged
from tests.postgres_isolation import EphemeralPostgres

CODE_RELEASE = "214ba256abe2ac6feca383950737d025a2226abd"


def test_materialized_production_corpus_searches_canonical_content(monkeypatch) -> None:
    package_path = os.getenv("DEO_MATERIALIZATION_BASE_PACKAGE")
    package_sha = os.getenv("DEO_MATERIALIZATION_BASE_PACKAGE_SHA256")
    if not package_path or not package_sha:
        pytest.skip("certified materialization baseline package is not selected")

    ephemeral = EphemeralPostgres.start(
        "postgresql+psycopg://invalid@127.0.0.1:5432/runtime"
    )
    engine = None
    try:
        ephemeral.migrate_to_head()
        engine = create_engine(ephemeral.test_url)
        package = verify_package(Path(package_path), expected_sha256=package_sha)
        import_package(
            engine,
            package,
            expectation=TargetExpectation(
                database_name=str(make_url(ephemeral.test_url).database),
                environment="isolated-test",
                code_release=CODE_RELEASE,
            ),
        )
        with Session(engine) as session:
            baseline_rows = build_serialized_public_release_rows(session)
            before = {
                row.specification.expedient_id: row.content_fingerprint
                for row in PostgresExpedientRepository(session).list_public()
            }
            with pytest.raises(CorpusMaterializationError, match="incomplete"):
                assert_approved_corpus_complete(session)
            first = materialize_approved_real_corpus(session)
            second = materialize_approved_real_corpus(session)
            after = {
                row.specification.expedient_id: row.content_fingerprint
                for row in PostgresExpedientRepository(session).list_public()
            }
            assert tuple(sorted(after)) == tuple(sorted(APPROVED_REAL_IDS))
            assert {key: after[key] for key in before} == before
            assert first.original_unchanged and second.original_unchanged
            reconstruction = next(
                row
                for row in PostgresExpedientRepository(session).list_public()
                if row.specification.expedient_id == "EXP-REAL-LEGISLATIVE-18216-05"
            )
            assert reconstruction.specification.version == 1
            _require_base_rows_unchanged(
                baseline_rows,
                build_serialized_public_release_rows(session),
            )
            assert build_public_metric_projection(session)["expedients"] == 10

        _select_runtime_database(monkeypatch, ephemeral.test_url)
        expected = {
            "trabajo": ("EXP-001", "DEMO"),
            "reconstruccion": ("EXP-REAL-LEGISLATIVE-18216-05", "REAL"),
            "reconstrucción": ("EXP-REAL-LEGISLATIVE-18216-05", "REAL"),
            "Ley 21.719": ("EXP-REAL-DATA-PROTECTION-21719", "REAL"),
            "Ley 21.663": ("EXP-REAL-CYBERSECURITY-14847-06", "REAL"),
            "ANCI": ("EXP-REAL-CYBERSECURITY-14847-06", "REAL"),
            "Democracia Viva": ("EXP-REAL-DEMOCRACIA-VIVA-ANTOFAGASTA", "REAL"),
            "control preventivo": ("EXP-REAL-CONTROL-PREVENTIVO-IDENTIDAD", "REAL"),
            "Escuelas Protegidas": ("EXP-REAL-ESCUELAS-PROTEGIDAS-18156-04", "REAL"),
            "Inteligencia Económica": ("EXP-REAL-LEGISLATIVE-15975-25", "REAL"),
        }
        for query, target in expected.items():
            matches = search_workspace(query, limit=20)["matches"]
            assert (target[0], target[1]) in {
                (str(row["entity_id"]), str(row["classification"])) for row in matches
            }
        for query in (
            "1000813-247-CM26",
            "Dirección de Educación Pública",
            "Félix Bulnes",
        ):
            assert search_workspace(query, limit=20)["matches"]
        assert search_workspace("término ciudadano deliberadamente ausente", limit=20) == {
            "matches": []
        }
    finally:
        _reset_runtime_database()
        if engine is not None:
            engine.dispose()
        ephemeral.close()


def _select_runtime_database(monkeypatch, database_url: str) -> None:  # noqa: ANN001
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("TEST_DATABASE_URL", database_url)
    _reset_runtime_database()


def _reset_runtime_database() -> None:
    import datosenorden.db.session as db_session
    from datosenorden.core.config import get_settings

    if db_session._engine is not None:
        db_session._engine.dispose()
    db_session._engine = None
    db_session._session_factory = None
    get_settings.cache_clear()
