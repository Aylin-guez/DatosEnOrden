from __future__ import annotations

import os
import shutil
import subprocess
import sys
import uuid
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

from datosenorden.application.data_release.importer import (
    PackageConflictError,
    TargetExpectation,
    import_package,
    verify_package,
)
from datosenorden.application.data_release.materialization import APPROVED_REAL_IDS
from scripts.release_pair_config import (
    database_identity,
    release_database_name,
    render_candidate_environment,
)
from scripts.verify_production_snapshot import validate_approved_real_ids

ROOT = Path(__file__).resolve().parents[1]
OLD = "1" * 40
NEW = "2" * 40
PACKAGE_ID = "DEO-PROD-DATA-0004-" + "a" * 16


def _env_text(database: str) -> str:
    url = f"postgresql+psycopg://service:secret@127.0.0.1:5432/{database}"
    return f"DATABASE_URL={url}\nDATOSENORDEN_DATABASE_URL={url}\nDATOSENORDEN_ENV=production\n"


def test_release_database_name_is_deterministic_and_bounded() -> None:
    assert release_database_name(NEW) == "datosenorden_rel_2222222222222222"
    with pytest.raises(ValueError):
        release_database_name("../unsafe")


def test_candidate_config_switch_is_atomic_and_preserves_non_database_values(
    tmp_path: Path,
) -> None:
    source = tmp_path / "beta.env"
    destination = tmp_path / "pairs" / f"{NEW}.env"
    source.write_text(
        _env_text("datosenorden_beta") + "API_URL=https://beta.example\n", encoding="utf-8"
    )

    render_candidate_environment(
        source,
        destination,
        expected_current_database="datosenorden_beta",
        target_database=release_database_name(NEW),
    )

    assert database_identity(source)["database"] == "datosenorden_beta"
    assert database_identity(destination)["database"] == release_database_name(NEW)
    assert "API_URL=https://beta.example" in destination.read_text(encoding="utf-8")
    assert "secret" in destination.read_text(encoding="utf-8")
    with pytest.raises(FileExistsError):
        render_candidate_environment(
            source,
            destination,
            expected_current_database="datosenorden_beta",
            target_database=release_database_name(NEW),
        )


@pytest.mark.parametrize(
    "url",
    (
        "postgresql+psycopg://service:secret@db.example/prod",
        "sqlite:///local.db",
    ),
)
def test_candidate_config_rejects_non_loopback_or_non_postgres(url: str, tmp_path: Path) -> None:
    source = tmp_path / "beta.env"
    source.write_text(f"DATABASE_URL={url}\nDATOSENORDEN_DATABASE_URL={url}\n", encoding="utf-8")
    with pytest.raises(ValueError):
        database_identity(source)


def test_snapshot_prepare_is_fail_closed_and_never_mutates_current_database() -> None:
    script = (ROOT / "scripts" / "prepare_data_snapshot_ubuntu.sh").read_text(encoding="utf-8")
    assert "Target release database already exists; refusing reuse" in script
    assert "DATA package SHA-256 mismatch" in script
    assert "--plan" in script
    assert "prepare + plan == 1" in script
    assert "--target-environment production" in script
    assert '--code-release "$release_id"' in script
    assert "scripts/verify_production_snapshot.py" in script
    assert "scripts/deploy_check.py" in script
    assert "scripts/prelaunch_public_check.py --read-only" in script
    assert "dropdb" not in script.lower()
    assert "truncate" not in script.lower()
    assert "DROP DATABASE" not in script
    assert "current_database" in script and "target_database" in script


def test_snapshot_verifier_uses_exact_canonical_registry() -> None:
    rows = tuple({"expedient_id": value} for value in APPROVED_REAL_IDS)
    assert validate_approved_real_ids(rows) == tuple(sorted(APPROVED_REAL_IDS))
    with pytest.raises(RuntimeError, match="missing="):
        validate_approved_real_ids(rows[:-1])
    with pytest.raises(RuntimeError, match="unexpected="):
        validate_approved_real_ids(rows + ({"expedient_id": "EXP-REAL-UNEXPECTED"},))
    with pytest.raises(RuntimeError, match="duplicates="):
        validate_approved_real_ids(rows + (rows[0],))


def _write_executable(path: Path, text: str) -> None:
    path.write_text("#!/usr/bin/env bash\nset -euo pipefail\n" + text, encoding="utf-8")
    path.chmod(0o755)


def _pair_fixture(tmp_path: Path) -> tuple[dict[str, str], Path, Path]:
    app_root = tmp_path / "app"
    pair_root = tmp_path / "pairs"
    env_file = tmp_path / "beta.env"
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    pair_root.mkdir()
    (app_root / "releases").mkdir(parents=True)
    old = app_root / "releases" / OLD
    new = app_root / "releases" / NEW
    for release in (old, new):
        (release / "scripts").mkdir(parents=True)
        (release / ".venv" / "bin").mkdir(parents=True)
        (release / ".deo-release-ready").write_text("ready\n", encoding="utf-8")
        (release / ".venv" / "bin" / "python").symlink_to(Path(sys.executable))
        _write_executable(
            release / "scripts" / "post_deploy_smoke.sh",
            'release="$1"\n'
            '[[ "$(basename "$(readlink -f "$APP_ROOT/current")")" == "$release" ]]\n'
            '[[ "$release" != "${FAIL_SMOKE_RELEASE:-}" ]]\n',
        )
    shutil.copy2(
        ROOT / "scripts" / "release_pair_config.py", new / "scripts" / "release_pair_config.py"
    )
    (app_root / "current").symlink_to(old, target_is_directory=True)
    env_file.write_text(_env_text("datosenorden_beta"), encoding="utf-8")
    candidate = pair_root / f"{NEW}.env"
    candidate.write_text(_env_text(release_database_name(NEW)), encoding="utf-8")
    (pair_root / f"{NEW}.ready").write_text(
        f"release_id={NEW}\ntarget_database={release_database_name(NEW)}\npackage_id={PACKAGE_ID}\n"
        f"package_sha256={'a' * 64}\nprevious_release={OLD}\nprevious_database=datosenorden_beta\n",
        encoding="utf-8",
    )
    _write_executable(
        fake_bin / "systemctl",
        'case "${1:-}" in is-active) exit 0 ;; *) exit 0 ;; esac\n',
    )
    _write_executable(fake_bin / "systemd-analyze", "exit 0\n")
    _write_executable(
        fake_bin / "mv",
        'if [[ -n "${FAIL_MV_MATCH:-}" && "$*" == *"$FAIL_MV_MATCH"* ]]; then exit 73; fi\n'
        'exec /usr/bin/mv "$@"\n',
    )
    environment = os.environ.copy()
    environment.update(
        {
            "APP_ROOT": str(app_root),
            "APP_USER": "root",
            "ENV_FILE": str(env_file),
            "PAIR_ROOT": str(pair_root),
            "SERVICE": "datosenorden",
            "PATH": f"{fake_bin}:{environment.get('PATH', '')}",
        }
    )
    return environment, app_root, env_file


@pytest.mark.skipif(os.name == "nt", reason="requires POSIX symlink and ownership semantics")
def test_pair_switch_and_rollback_restore_both_code_and_database(tmp_path: Path) -> None:
    environment, app_root, env_file = _pair_fixture(tmp_path)
    activated = subprocess.run(
        [
            "bash",
            str(ROOT / "scripts" / "activate_release_pair_ubuntu.sh"),
            "--release-id",
            NEW,
            "--package-id",
            PACKAGE_ID,
            "--confirm-ready",
            NEW,
        ],
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    assert activated.returncode == 0, activated.stderr
    assert Path(os.path.realpath(app_root / "current")).name == NEW
    assert database_identity(env_file)["database"] == release_database_name(NEW)

    rolled_back = subprocess.run(
        ["bash", str(ROOT / "scripts" / "rollback_release_pair_ubuntu.sh"), OLD],
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    assert rolled_back.returncode == 0, rolled_back.stderr
    assert Path(os.path.realpath(app_root / "current")).name == OLD
    assert Path(os.path.realpath(app_root / "previous")).name == NEW
    assert database_identity(env_file)["database"] == "datosenorden_beta"


@pytest.mark.skipif(os.name == "nt", reason="requires POSIX symlink and ownership semantics")
def test_readiness_failure_restores_old_pair(tmp_path: Path) -> None:
    environment, app_root, env_file = _pair_fixture(tmp_path)
    environment["FAIL_SMOKE_RELEASE"] = NEW
    failed = subprocess.run(
        [
            "bash",
            str(ROOT / "scripts" / "activate_release_pair_ubuntu.sh"),
            "--release-id",
            NEW,
            "--package-id",
            PACKAGE_ID,
            "--confirm-ready",
            NEW,
        ],
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    assert failed.returncode != 0
    assert "old pair was restored" in failed.stderr
    assert Path(os.path.realpath(app_root / "current")).name == OLD
    assert database_identity(env_file)["database"] == "datosenorden_beta"


@pytest.mark.parametrize("failure_match", ("beta.env.new", "current.new"))
@pytest.mark.skipif(os.name == "nt", reason="requires POSIX symlink and ownership semantics")
def test_partial_pair_switch_failure_never_leaves_mixed_pair(
    tmp_path: Path, failure_match: str
) -> None:
    environment, app_root, env_file = _pair_fixture(tmp_path)
    environment["FAIL_MV_MATCH"] = failure_match
    failed = subprocess.run(
        [
            "bash",
            str(ROOT / "scripts" / "activate_release_pair_ubuntu.sh"),
            "--release-id",
            NEW,
            "--package-id",
            PACKAGE_ID,
            "--confirm-ready",
            NEW,
        ],
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    assert failed.returncode != 0
    assert Path(os.path.realpath(app_root / "current")).name == OLD
    assert database_identity(env_file)["database"] == "datosenorden_beta"


def test_partial_failure_contracts_are_explicit() -> None:
    prepare = (ROOT / "scripts" / "prepare_data_snapshot_ubuntu.sh").read_text(encoding="utf-8")
    activate = (ROOT / "scripts" / "activate_release_pair_ubuntu.sh").read_text(encoding="utf-8")
    assert "Target release database already exists" in prepare
    assert "DATA package SHA-256 mismatch" in prepare
    assert "code release is not explicitly compatible" in (
        ROOT / "scripts" / "verify_production_snapshot.py"
    ).read_text(encoding="utf-8")
    assert "restored database does not exactly match package snapshot" in (
        ROOT / "scripts" / "verify_production_snapshot.py"
    ).read_text(encoding="utf-8")
    assert "restore_old_pair" in activate
    assert "service restart failed" in activate
    assert "pair smoke failed" in activate
    assert 'mv -T "$ENV_FILE.new" "$ENV_FILE"' in activate
    assert 'mv -Tf "$APP_ROOT/current.new" "$APP_ROOT/current"' in activate


def test_real_snapshot_transition_uses_new_database_and_preserves_old() -> None:
    runtime_url = os.getenv("DEO_EXTERNAL_POSTGRES_URL")
    old_path = os.getenv("DEO_OLD_DATA_PACKAGE")
    old_sha = os.getenv("DEO_OLD_DATA_PACKAGE_SHA256")
    new_path = os.getenv("DEO_NEW_DATA_PACKAGE")
    new_sha = os.getenv("DEO_NEW_DATA_PACKAGE_SHA256")
    if not all((runtime_url, old_path, old_sha, new_path, new_sha)):
        pytest.skip("certified old/new snapshots and isolated PostgreSQL are not selected")
    old_package = verify_package(
        Path(old_path), expected_sha256=old_sha, allow_lossy_historical_recovery=True
    )
    new_package = verify_package(Path(new_path), expected_sha256=new_sha)
    base_url = make_url(runtime_url)
    old_name = f"datosenorden_pytest_snapshot_old_{uuid.uuid4().hex[:8]}"
    new_name = f"datosenorden_pytest_snapshot_new_{uuid.uuid4().hex[:8]}"
    admin_engine = create_engine(base_url.set(database="postgres"), isolation_level="AUTOCOMMIT")
    with admin_engine.connect() as connection:
        connection.execute(text(f'create database "{old_name}"'))
        connection.execute(text(f'create database "{new_name}"'))
    old_url = base_url.set(database=old_name).render_as_string(hide_password=False)
    new_url = base_url.set(database=new_name).render_as_string(hide_password=False)
    try:
        for database_url in (old_url, new_url):
            environment = os.environ.copy()
            environment.update({"DATABASE_URL": database_url, "TEST_DATABASE_URL": database_url})
            migrated = subprocess.run(
                [sys.executable, "-m", "alembic", "upgrade", "head"],
                cwd=ROOT,
                env=environment,
                capture_output=True,
                text=True,
                check=False,
            )
            assert migrated.returncode == 0, migrated.stdout + migrated.stderr
        old_engine = create_engine(old_url)
        new_engine = create_engine(new_url)
        old_expectation = TargetExpectation(
            old_name,
            "isolated-test",
            old_package.manifest["code_compatibility"]["compatible_code_releases"][0],
        )
        new_expectation_on_old = TargetExpectation(
            old_name,
            "isolated-test",
            new_package.manifest["code_compatibility"]["compatible_code_releases"][0],
        )
        new_expectation = TargetExpectation(
            new_name,
            "isolated-test",
            new_package.manifest["code_compatibility"]["compatible_code_releases"][0],
        )
        before = import_package(old_engine, old_package, expectation=old_expectation)
        with pytest.raises(PackageConflictError, match="target conflict"):
            import_package(old_engine, new_package, expectation=new_expectation_on_old)
        after = import_package(old_engine, old_package, expectation=old_expectation)
        restored = import_package(new_engine, new_package, expectation=new_expectation)
        assert before.target_counts == after.target_counts
        assert after.unchanged == old_package.manifest["row_counts"]
        assert restored.target_counts == new_package.manifest["row_counts"]
        with new_engine.connect() as connection:
            assert (
                connection.execute(text("SELECT count(*) FROM real_expedient")).scalar_one() == 10
            )
            assert (
                connection.execute(text("SELECT count(*) FROM real_expedient_version")).scalar_one()
                == 14
            )
        verifier_environment = os.environ.copy()
        verifier_environment.update(
            {
                "DATABASE_URL": new_url,
                "DATOSENORDEN_DATABASE_URL": new_url,
            }
        )
        verified = subprocess.run(
            [
                sys.executable,
                "scripts/verify_production_snapshot.py",
                "--package",
                str(new_path),
                "--sha256",
                new_sha,
                "--expected-database",
                new_name,
                "--code-release",
                new_package.manifest["code_compatibility"]["compatible_code_releases"][0],
            ],
            cwd=ROOT,
            env=verifier_environment,
            capture_output=True,
            text=True,
            check=False,
        )
        assert verified.returncode == 0, verified.stdout + verified.stderr
        assert '"real_count": 10' in verified.stdout
    finally:
        for engine in (locals().get("old_engine"), locals().get("new_engine")):
            if engine is not None:
                engine.dispose()
        with admin_engine.connect() as connection:
            for database_name in (old_name, new_name):
                connection.execute(
                    text(
                        "select pg_terminate_backend(pid) from pg_stat_activity where datname=:name"
                    ),
                    {"name": database_name},
                )
                connection.execute(text(f'drop database if exists "{database_name}"'))
        admin_engine.dispose()
