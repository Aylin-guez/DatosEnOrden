"""Ephemeral PostgreSQL harness for tests that exercise persistence.

The test process never inherits the runtime database as a write target.
"""

from __future__ import annotations

from dataclasses import dataclass
import locale
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import uuid

from sqlalchemy.engine import make_url


TEST_DATABASE_PREFIX = "datosenorden_pytest_"
QA_DATABASE_NAME = "datosenorden_pytest_goldenqa"
QA_DATABASE_PORT = 55432
PROJECT_ROOT = Path(__file__).resolve().parents[1]
EPHEMERAL_ROOT = PROJECT_ROOT / "data" / "tmp" / "ephemeral_postgres"
POSTGRES_UNIX_SOCKET_PATH_MAX_BYTES = 107


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
    if test.port == 5432:
        raise RuntimeError("test database must not use PostgreSQL port 5432")
    if test.database == QA_DATABASE_NAME or test.port == QA_DATABASE_PORT:
        raise RuntimeError("test database must not use the persistent QA database")
    if test == runtime:
        raise RuntimeError("test database identity must not match runtime database")
    if not test.database.startswith(TEST_DATABASE_PREFIX):
        raise RuntimeError("test database name must use the isolated pytest prefix")


@dataclass
class EphemeralPostgres:
    root: Path
    data_dir: Path
    socket_dir: Path | None
    port: int
    database: str
    admin_url: str
    test_url: str
    postgres: Path
    pg_ctl: Path
    process: subprocess.Popen[str]

    @classmethod
    def start(cls, runtime_url: str) -> "EphemeralPostgres":
        from datosenorden.maintenance.db_sync import find_pg_tool

        initdb = find_pg_tool("initdb")
        postgres = find_pg_tool("postgres")
        pg_ctl = find_pg_tool("pg_ctl")
        pg_isready = find_pg_tool("pg_isready")
        psql = find_pg_tool("psql")
        port = _available_port()
        EPHEMERAL_ROOT.mkdir(parents=True, exist_ok=True)
        root = EPHEMERAL_ROOT / f"cluster-{os.getpid()}-{uuid.uuid4().hex}"
        root.mkdir()
        data_dir = root / "data"
        database = f"{TEST_DATABASE_PREFIX}{os.getpid()}_{uuid.uuid4().hex[:8]}"
        process: subprocess.Popen[str] | None = None
        socket_dir: Path | None = None
        try:
            initdb_result = subprocess.run([
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
            ], **_captured_process_options(timeout=30, check=False))
            if initdb_result.returncode and not _is_initialized_cluster(data_dir):
                raise RuntimeError(
                    "temporary PostgreSQL initdb failed before initialization: "
                    f"{initdb_result.stderr.strip()}"
                )
            socket_dir = _create_socket_dir()
            process = _start_postgres(
                postgres, data_dir, port, socket_dir, root / "postgres.log"
            )
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
            _verify_connection(psql, port, username, database)
            return cls(
                root, data_dir, socket_dir, port, database, admin_url, test_url,
                postgres, pg_ctl, process,
            )
        except Exception:
            _stop_owned_cluster(pg_ctl, data_dir, process)
            shutil.rmtree(root, ignore_errors=True)
            _remove_owned_socket_dir(socket_dir)
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
        _stop_owned_cluster(self.pg_ctl, self.data_dir, self.process)
        shutil.rmtree(self.root, ignore_errors=True)
        _remove_owned_socket_dir(self.socket_dir)


def _available_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind(("127.0.0.1", 0))
        return int(probe.getsockname()[1])


def _run(command: list[str], *, quiet: bool = False) -> None:
    options: dict[str, object] = {
        "check": True,
        "timeout": 30,
    }
    if quiet:
        options.update(stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    else:
        options.update(_captured_process_options(timeout=30, check=True))
    subprocess.run(command, **options)


def _captured_process_options(*, timeout: int, check: bool) -> dict[str, object]:
    """Decode Windows PostgreSQL tool output without assuming UTF-8.

    PostgreSQL executables use the active Windows ANSI code page for diagnostics.
    Their output is only used for failure diagnostics, so replacement preserves the
    test lifecycle even if an external tool emits an undecodable byte.
    """
    return {
        "capture_output": True,
        "text": True,
        "encoding": locale.getpreferredencoding(False),
        "errors": "replace",
        "timeout": timeout,
        "check": check,
    }


def _is_initialized_cluster(data_dir: Path) -> bool:
    """Accept Windows error 87 only after initdb produced a complete cluster."""
    return all(
        (data_dir / name).exists()
        for name in ("PG_VERSION", "base", "global", "pg_hba.conf", "postgresql.conf")
    )


def _create_socket_dir() -> Path | None:
    """Create a private, short Unix socket directory for a single test cluster."""
    if os.name == "nt":
        return None
    socket_dir = Path(tempfile.mkdtemp(prefix="deo-pg-"))
    try:
        socket_dir.chmod(0o700)
        socket_path = socket_dir / ".s.PGSQL.65535"
        if len(os.fsencode(socket_path)) > POSTGRES_UNIX_SOCKET_PATH_MAX_BYTES:
            raise RuntimeError("temporary PostgreSQL socket path exceeds the Unix limit")
        return socket_dir
    except Exception:
        _remove_owned_socket_dir(socket_dir)
        raise


def _remove_owned_socket_dir(socket_dir: Path | None) -> None:
    """Best-effort cleanup for the unique directory created by this harness only."""
    if socket_dir is not None:
        shutil.rmtree(socket_dir, ignore_errors=True)


def _start_postgres(
    postgres: Path, data_dir: Path, port: int, socket_dir: Path | None, log_path: Path
) -> subprocess.Popen[str]:
    """Start an owned temporary server without pg_ctl's restricted-token wrapper."""
    command = _postgres_command(postgres, data_dir, port, socket_dir)
    log = log_path.open("w", encoding="utf-8")
    try:
        process = subprocess.Popen(
            command,
            cwd=PROJECT_ROOT,
            stdout=log,
            stderr=subprocess.STDOUT,
            text=True,
        )
    finally:
        log.close()
    return process


def _postgres_command(
    postgres: Path, data_dir: Path, port: int, socket_dir: Path | None
) -> list[str]:
    command = [str(postgres), "-D", str(data_dir), "-p", str(port), "-h", "127.0.0.1"]
    if socket_dir is not None:
        command.extend(["-k", str(socket_dir)])
    return command


def _verify_connection(psql: Path, port: int, username: str, database: str) -> None:
    _run([
        str(psql),
        "--host", "127.0.0.1",
        "--port", str(port),
        "--username", username,
        "--dbname", database,
        "--command", "select current_database(), current_user",
    ])


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


def _stop_owned_process(process: subprocess.Popen[str] | None) -> None:
    """Stop only the server represented by our live Windows process handle."""
    if process is None or process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=15)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=15)


def _stop_owned_cluster(
    pg_ctl: Path, data_dir: Path, process: subprocess.Popen[str] | None
) -> None:
    """Gracefully stop the owned cluster; pg_ctl start is never used."""
    if data_dir.exists():
        subprocess.run(
            [str(pg_ctl), "--pgdata", str(data_dir), "--wait", "stop", "--mode", "fast"],
            **_captured_process_options(timeout=30, check=False),
        )
    _stop_owned_process(process)
