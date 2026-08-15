"""Ephemeral PostgreSQL harness for tests that exercise persistence.

The test process never inherits the runtime database as a write target.
"""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import tempfile
import time

from sqlalchemy.engine import make_url


TEST_DATABASE_PREFIX = "datosenorden_pytest_"


@dataclass(frozen=True)
class DatabaseIdentity:
    host: str
    port: int
    database: str


def database_identity(url: str) -> DatabaseIdentity:
    parsed = make_url(url)
    return DatabaseIdentity(
        host=(parsed.host or "localhost").lower(),
        port=parsed.port or 5432,
        database=str(parsed.database or ""),
    )


def assert_isolated_test_database(test_url: str, runtime_url: str) -> None:
    test = database_identity(test_url)
    runtime = database_identity(runtime_url)
    if test == runtime:
        raise RuntimeError("test database identity must not match runtime database")
    if not test.database.startswith(TEST_DATABASE_PREFIX):
        raise RuntimeError("test database name must use the isolated pytest prefix")


@dataclass
class EphemeralPostgres:
    root: Path
    data_dir: Path
    port: int
    database: str
    admin_url: str
    test_url: str
    pg_ctl: Path

    @classmethod
    def start(cls, runtime_url: str) -> "EphemeralPostgres":
        from datosenorden.maintenance.db_sync import find_pg_tool

        initdb = find_pg_tool("initdb")
        pg_ctl = find_pg_tool("pg_ctl")
        pg_isready = find_pg_tool("pg_isready")
        psql = find_pg_tool("psql")
        port = _available_port()
        root = Path(tempfile.mkdtemp(prefix="datosenorden-pytest-pg-"))
        data_dir = root / "data"
        database = f"{TEST_DATABASE_PREFIX}{os.getpid()}"
        try:
            _run([
                str(initdb),
                "--pgdata",
                str(data_dir),
                "--username",
                "datosenorden_test",
                "--auth-local",
                "trust",
                "--auth-host",
                "trust",
                "--encoding",
                "UTF8",
            ])
            _run([
                str(pg_ctl),
                "--pgdata",
                str(data_dir),
                "--no-wait",
                "--log",
                str(root / "postgres.log"),
                "start",
                "--options",
                f"-p {port} -h 127.0.0.1",
            ], quiet=True)
            _wait_until_ready(pg_isready, port)
            username = "datosenorden_test"
            _run([
                str(psql),
                "--host",
                "127.0.0.1",
                "--port",
                str(port),
                "--username",
                username,
                "--dbname",
                "postgres",
                "--command",
                f'create database "{database}"',
            ])
            admin_url = f"postgresql+psycopg://{username}@127.0.0.1:{port}/postgres"
            test_url = f"postgresql+psycopg://{username}@127.0.0.1:{port}/{database}"
            assert_isolated_test_database(test_url, runtime_url)
            return cls(root, data_dir, port, database, admin_url, test_url, pg_ctl)
        except Exception:
            _stop_quietly(pg_ctl, data_dir)
            shutil.rmtree(root, ignore_errors=True)
            raise

    def migrate_to_head(self) -> None:
        environment = os.environ.copy()
        environment["DATABASE_URL"] = self.test_url
        environment["TEST_DATABASE_URL"] = self.test_url
        result = subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", "head"],
            cwd=Path(__file__).resolve().parents[1],
            env=environment,
            text=True,
            capture_output=True,
            check=False,
            timeout=120,
        )
        if result.returncode:
            raise RuntimeError("temporary PostgreSQL migration failed")

    def close(self) -> None:
        _stop_quietly(self.pg_ctl, self.data_dir)
        shutil.rmtree(self.root, ignore_errors=True)


def _available_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind(("127.0.0.1", 0))
        return int(probe.getsockname()[1])


def _run(command: list[str], *, quiet: bool = False) -> None:
    options: dict[str, object] = {
        "check": True,
        "text": True,
        "timeout": 30,
    }
    if quiet:
        options.update(stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    else:
        options["capture_output"] = True
    subprocess.run(command, **options)


def _wait_until_ready(pg_isready: Path, port: int) -> None:
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        result = subprocess.run(
            [str(pg_isready), "--host", "127.0.0.1", "--port", str(port)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
            timeout=3,
        )
        if result.returncode == 0:
            return
        time.sleep(0.25)
    raise RuntimeError("temporary PostgreSQL did not become ready")


def _stop_quietly(pg_ctl: Path, data_dir: Path) -> None:
    if data_dir.exists():
        subprocess.run(
            [str(pg_ctl), "--pgdata", str(data_dir), "--wait", "stop", "--mode", "fast"],
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
        )
