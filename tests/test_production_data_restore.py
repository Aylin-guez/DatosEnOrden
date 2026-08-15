from __future__ import annotations

import json
import os
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from datosenorden.application.data_release.contract import (
    BASELINE_CODE_RELEASE,
    REQUIRED_SCHEMA_REVISION,
    TABLE_BY_NAME,
    canonical_json,
    logical_content_hash,
    package_id,
    rows_bytes,
    sha256_bytes,
    sha256_file,
    write_deterministic_zip,
)
from datosenorden.application.data_release.importer import (
    PackageCompatibilityError,
    PackageConflictError,
    TargetExpectation,
    import_package,
    verify_package,
)
from datosenorden.application.provenance.service import (
    build_provenance_snapshot,
    build_public_metric_projection,
)
from datosenorden.application.real_expedient.reader import ComposedPublicExpedientReader
from datosenorden.infrastructure.real_expedient.repository import PostgresExpedientRepository
from datosenorden.maintenance.dataset_registry import list_datasets
from datosenorden.maintenance.entity_explorer import list_entities
from datosenorden.maintenance.search_workspace import search_workspace


def _first_package() -> tuple[Path, str]:
    path = os.getenv("DEO_FIRST_DATA_PACKAGE")
    digest = os.getenv("DEO_FIRST_DATA_PACKAGE_SHA256")
    if not path or not digest:
        pytest.skip("first production data package is not selected for this test run")
    return Path(path), digest


@pytest.fixture
def postgres_url(monkeypatch: pytest.MonkeyPatch) -> str:
    url = os.getenv("DEO_EXTERNAL_POSTGRES_URL") or os.environ["TEST_DATABASE_URL"]
    monkeypatch.setenv("DATABASE_URL", url)
    monkeypatch.setenv("TEST_DATABASE_URL", url)
    import datosenorden.db.session as db_session
    from datosenorden.core.config import get_settings

    if db_session._engine is not None:
        db_session._engine.dispose()
    db_session._engine = None
    db_session._session_factory = None
    get_settings.cache_clear()
    return url


def _expected_code_release() -> str:
    return os.getenv("DEO_EXPECTED_CODE_RELEASE", BASELINE_CODE_RELEASE)


def test_first_package_restore_reimport_and_conflict(
    postgres_url: str,
    tmp_path: Path,
) -> None:
    path, digest = _first_package()
    package = verify_package(path, expected_sha256=digest)
    engine = create_engine(postgres_url)
    database = str(make_url(postgres_url).database)
    expected_code_release = _expected_code_release()
    expectation = TargetExpectation(
        database_name=database,
        environment="isolated-test",
        code_release=expected_code_release,
    )

    with engine.connect() as connection:
        server_version_num = int(connection.scalar(text("show server_version_num")))
        expected_major = int(os.getenv("DEO_EXPECTED_POSTGRES_MAJOR", "17"))
        assert server_version_num // 10000 == expected_major
        assert connection.scalar(text("select version_num from alembic_version")) == (
            REQUIRED_SCHEMA_REVISION
        )

    with pytest.raises(PackageCompatibilityError, match="identity mismatch"):
        import_package(
            engine,
            package,
            expectation=TargetExpectation(
                database_name="wrong_database",
                environment="isolated-test",
                code_release=expected_code_release,
            ),
        )
    with pytest.raises(PackageCompatibilityError, match="code release"):
        import_package(
            engine,
            package,
            expectation=TargetExpectation(
                database_name=database,
                environment="isolated-test",
                code_release="0" * 40,
            ),
        )
    with pytest.raises(PackageCompatibilityError, match="production confirmation"):
        import_package(
            engine,
            package,
            expectation=TargetExpectation(
                database_name=database,
                environment="production",
                code_release=expected_code_release,
            ),
        )

    first = import_package(engine, package, expectation=expectation)
    assert first.inserted == package.manifest["row_counts"]
    assert all(value == 0 for value in first.unchanged.values())
    assert first.public_metrics == {
        "authorities": 0,
        "claims": 22,
        "contracts": 7,
        "documents": 1,
        "entities": 15,
        "evidences": 11,
        "expedients": 4,
        "meetings": 0,
        "relationships": 15,
        "source_records": 11,
        "suppliers": 3,
    }
    with engine.connect() as connection:
        assert connection.scalar(text("select count(*) from import_job")) == 0
        assert connection.scalar(text("select count(*) from change_log")) == 0
        assert (
            connection.scalar(text("select count(*) from source_record where status='rejected'"))
            == 0
        )

    second = import_package(engine, package, expectation=expectation)
    assert all(value == 0 for value in second.inserted.values())
    assert second.unchanged == package.manifest["row_counts"]
    assert second.target_counts == first.target_counts
    assert second.public_metrics == first.public_metrics

    with Session(engine) as session:
        snapshot = build_provenance_snapshot(session)
        assert build_public_metric_projection(session) == first.public_metrics
        assert snapshot.lifecycle["source_records"] == {"normalized": 7, "validated": 4}
        assert len(list_entities(session, limit=100)) == 15
        assert sum(int(row["available_real_records"]) for row in snapshot.source_metrics) == 11
        dataset_summaries = list_datasets(session)
        assert sum(item.source_records for item in dataset_summaries) == 7
        assert any(
            item.name == "ChileCompra" and item.source_records == 7 for item in dataset_summaries
        )
        reader = ComposedPublicExpedientReader(PostgresExpedientRepository(session))
        persisted = PostgresExpedientRepository(session).list_public()
        assert len(persisted) == 4
        assert {item.specification.expedient_id for item in persisted} == {
            "EXP-REAL-CHILECOMPRA-1000813-247-CM26",
            "EXP-REAL-CHILECOMPRA-1002584-197-CM26",
            "EXP-REAL-CHILECOMPRA-1002772-6758-SE26",
            "EXP-REAL-LEGISLATIVE-15975-25",
        }
        assert len(reader.list_available()) == 5
        dep = reader.get("EXP-REAL-CHILECOMPRA-1002584-197-CM26")
        assert dep is not None and dep["version"] == 2
        assert len(dep["references"]["sources"]) == 2
        legislative = reader.get("EXP-REAL-LEGISLATIVE-15975-25")
        assert legislative is not None and legislative["status"] == "published"
        search = search_workspace(str(package.rows["entity"][0]["name"]), limit=5)
        assert search["matches"]

    conflict_path = _conflicting_package(path, tmp_path)
    conflict = verify_package(conflict_path, expected_sha256=sha256_file(conflict_path))
    with pytest.raises(PackageConflictError, match="target conflict in source"):
        import_package(engine, conflict, expectation=expectation)
    assert (
        import_package(engine, package, expectation=expectation).target_counts
        == first.target_counts
    )

    environment = os.environ.copy()
    environment["DATABASE_URL"] = postgres_url
    environment["TEST_DATABASE_URL"] = postgres_url
    for script in ("scripts/prelaunch_public_check.py", "scripts/deploy_check.py"):
        result = subprocess.run(
            [sys.executable, script],
            cwd=Path(__file__).resolve().parents[1],
            env=environment,
            capture_output=True,
            text=True,
            check=False,
            timeout=300,
        )
        assert result.returncode == 0, (result.stdout or result.stderr)[-2000:]


def _conflicting_package(source_path: Path, tmp_path: Path) -> Path:
    with zipfile.ZipFile(source_path) as archive:
        members = {name: archive.read(name) for name in archive.namelist()}
    manifest = json.loads(members["manifest.json"])
    source_rows = [json.loads(line) for line in members["data/source.jsonl"].splitlines()]
    source_rows[0]["name"] += " conflict fixture"
    source_rows.sort(key=lambda row: str(row["id"]))
    source_payload = rows_bytes(source_rows)
    members["data/source.jsonl"] = source_payload
    source_hash = sha256_bytes(source_payload)
    manifest["content_hashes"]["source"] = source_hash
    entry = next(item for item in manifest["table_manifest"] if item["table"] == "source")
    entry["sha256"] = source_hash
    logical_hash = logical_content_hash(table_hashes=manifest["content_hashes"])
    manifest["logical_content_hash"] = logical_hash
    manifest["package_id"] = package_id(9999, logical_hash)
    members["manifest.json"] = canonical_json(manifest) + b"\n"
    path = tmp_path / "valid-conflict-package.zip"
    write_deterministic_zip(path, members)
    assert TABLE_BY_NAME["source"].path == "data/source.jsonl"
    return path
