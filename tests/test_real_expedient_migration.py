from __future__ import annotations

import os
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path
from uuid import uuid4

import psycopg
import pytest
from psycopg import sql
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url

from datosenorden.maintenance.db_sync import (
    build_pg_dump_command,
    build_pg_restore_command,
    find_pg_tool,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ADMIN_ENV = "REAL_EXPEDIENT_TEST_ADMIN_URL"


def _admin_url() -> str:
    value = os.getenv(ADMIN_ENV, "")
    if not value:
        pytest.skip(f"{ADMIN_ENV} is required for isolated PostgreSQL migration tests")
    parsed = make_url(value)
    if parsed.database != "postgres":
        pytest.fail(f"{ADMIN_ENV} must target the postgres maintenance database")
    return value


def _psycopg_url(value: str) -> str:
    return value.replace("postgresql+psycopg://", "postgresql://", 1)


@pytest.fixture
def temporary_database() -> Iterator[str]:
    admin_url = _admin_url()
    database_name = f"datosenorden_exp_test_{uuid4().hex[:12]}"
    parsed = make_url(admin_url)
    database_url = str(parsed.set(database=database_name))
    with psycopg.connect(_psycopg_url(admin_url), autocommit=True) as connection:
        connection.execute(sql.SQL("create database {}").format(sql.Identifier(database_name)))
    try:
        yield database_url
    finally:
        with psycopg.connect(_psycopg_url(admin_url), autocommit=True) as connection:
            connection.execute(
                "select pg_terminate_backend(pid) from pg_stat_activity "
                "where datname = %s and pid <> pg_backend_pid()",
                (database_name,),
            )
            connection.execute(sql.SQL("drop database {}").format(sql.Identifier(database_name)))


def _alembic(
    database_url: str, *arguments: str, succeeds: bool = True
) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment["DATABASE_URL"] = database_url
    result = subprocess.run(
        [sys.executable, "-m", "alembic", *arguments],
        cwd=PROJECT_ROOT,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )
    if succeeds and result.returncode != 0:
        pytest.fail(result.stdout + result.stderr)
    return result


def test_migration_up_is_additive_constrained_and_versioned(temporary_database: str) -> None:
    _alembic(temporary_database, "upgrade", "202606180001")
    baseline_engine = create_engine(temporary_database)
    baseline_tables = set(inspect(baseline_engine).get_table_names())
    baseline_engine.dispose()

    _alembic(temporary_database, "upgrade", "head")
    _alembic(temporary_database, "upgrade", "head")

    engine = create_engine(temporary_database)
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    assert baseline_tables <= tables
    assert {
        "real_expedient",
        "real_expedient_version",
        "real_expedient_reference",
        "real_expedient_narrative",
        "real_expedient_narrative_support",
    } <= tables
    assert {
        item["name"] for item in inspector.get_check_constraints("real_expedient_reference")
    } >= {
        "ck_real_expedient_reference_type",
        "ck_real_expedient_reference_ordinal",
    }
    assert {item["name"] for item in inspector.get_indexes("real_expedient_reference")} >= {
        "ix_real_expedient_reference_reverse"
    }
    with engine.connect() as connection:
        assert connection.scalar(text("select version_num from alembic_version")) == "202608120001"
    engine.dispose()


def test_empty_migration_can_rollback_cleanly(temporary_database: str) -> None:
    _alembic(temporary_database, "upgrade", "head")
    _alembic(temporary_database, "downgrade", "202606180001")
    engine = create_engine(temporary_database)
    tables = set(inspect(engine).get_table_names())
    engine.dispose()
    assert "real_expedient" not in tables
    assert "source_record" in tables


def test_populated_migration_refuses_destructive_rollback(temporary_database: str) -> None:
    _alembic(temporary_database, "upgrade", "head")
    engine = create_engine(temporary_database)
    with engine.begin() as connection:
        connection.execute(
            text(
                "insert into real_expedient "
                "(expedient_id, provenance_class, current_version) values "
                "('EXP-ROLLBACK-GUARD', 'REAL', 1)"
            )
        )
    result = _alembic(temporary_database, "downgrade", "202606180001", succeeds=False)
    assert result.returncode != 0
    assert "refusing to remove non-empty REAL expedient persistence tables" in result.stderr
    assert "real_expedient" in inspect(engine).get_table_names()
    engine.dispose()


def test_temporary_backup_migrate_restore_preserves_baseline(
    temporary_database: str, tmp_path: Path
) -> None:
    admin_url = _admin_url()
    parsed = make_url(admin_url)
    restore_name = f"datosenorden_exp_test_{uuid4().hex[:12]}"
    restore_url = str(parsed.set(database=restore_name))
    dump_path = tmp_path / "baseline.dump"
    _alembic(temporary_database, "upgrade", "202606180001")

    subprocess.run(
        build_pg_dump_command(temporary_database, dump_path, find_pg_tool("pg_dump")),
        check=True,
        capture_output=True,
        text=True,
    )
    _alembic(temporary_database, "upgrade", "head")

    with psycopg.connect(_psycopg_url(admin_url), autocommit=True) as connection:
        connection.execute(sql.SQL("create database {}").format(sql.Identifier(restore_name)))
    try:
        subprocess.run(
            build_pg_restore_command(
                restore_url,
                dump_path,
                find_pg_tool("pg_restore"),
                clean=False,
            ),
            check=True,
            capture_output=True,
            text=True,
        )
        engine = create_engine(restore_url)
        with engine.connect() as connection:
            restored_revision = connection.scalar(text("select version_num from alembic_version"))
            assert restored_revision == "202606180001"
        assert "real_expedient" not in inspect(engine).get_table_names()
        engine.dispose()
    finally:
        with psycopg.connect(_psycopg_url(admin_url), autocommit=True) as connection:
            connection.execute(
                "select pg_terminate_backend(pid) from pg_stat_activity "
                "where datname = %s and pid <> pg_backend_pid()",
                (restore_name,),
            )
            connection.execute(sql.SQL("drop database {}").format(sql.Identifier(restore_name)))
