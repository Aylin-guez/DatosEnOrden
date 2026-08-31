from __future__ import annotations

import os
import socket
import stat
from pathlib import Path

import pytest

from tests.postgres_isolation import (
    POSTGRES_UNIX_SOCKET_PATH_MAX_BYTES,
    EphemeralPostgres,
    _postgres_command,
    assert_isolated_test_database,
)


def test_test_database_rejects_runtime_identity() -> None:
    value = "postgresql+psycopg://operator@localhost:55439/datosenorden"

    with pytest.raises(RuntimeError, match="must not match"):
        assert_isolated_test_database(value, value)


def test_test_database_rejects_non_test_name() -> None:
    with pytest.raises(RuntimeError, match="pytest prefix"):
        assert_isolated_test_database(
            "postgresql+psycopg://operator@localhost:55439/other_database",
            "postgresql+psycopg://operator@localhost:5432/datosenorden",
        )


def test_test_database_accepts_distinct_prefixed_identity() -> None:
    assert_isolated_test_database(
        "postgresql+psycopg://operator@localhost:55439/datosenorden_pytest_123",
        "postgresql+psycopg://operator@localhost:5432/datosenorden",
    )


def test_test_database_rejects_postgres_default_port() -> None:
    with pytest.raises(RuntimeError, match="port 5432"):
        assert_isolated_test_database(
            "postgresql+psycopg://operator@127.0.0.1:5432/datosenorden_pytest_123",
            "postgresql+psycopg://operator@127.0.0.1:55439/datosenorden",
        )


def test_test_database_rejects_persistent_qa_identity() -> None:
    with pytest.raises(RuntimeError, match="persistent QA"):
        assert_isolated_test_database(
            "postgresql+psycopg://operator@127.0.0.1:55432/datosenorden_pytest_goldenqa",
            "postgresql+psycopg://operator@127.0.0.1:55439/datosenorden",
        )


def test_ephemeral_postgres_starts_and_cleans_its_owned_process() -> None:
    runtime_url = "postgresql+psycopg://operator@127.0.0.1:55439/datosenorden_runtime"
    ephemeral = EphemeralPostgres.start(runtime_url)
    port = ephemeral.port
    root = ephemeral.root
    socket_dir = ephemeral.socket_dir
    try:
        assert ephemeral.process.poll() is None
        assert ephemeral.database.startswith("datosenorden_pytest_")
        assert port not in (5432, 55432)
        if os.name == "nt":
            assert socket_dir is None
        else:
            assert socket_dir is not None
            assert stat.S_IMODE(socket_dir.stat().st_mode) == 0o700
            assert len(os.fsencode(socket_dir / f".s.PGSQL.{port}")) <= POSTGRES_UNIX_SOCKET_PATH_MAX_BYTES
    finally:
        ephemeral.close()

    assert not root.exists()
    if socket_dir is not None:
        assert not socket_dir.exists()
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        assert probe.connect_ex(("127.0.0.1", port)) != 0


def test_postgres_command_keeps_windows_contract_without_socket_argument() -> None:
    command = _postgres_command(Path("postgres"), Path("data"), 55439, None)

    assert command == ["postgres", "-D", "data", "-p", "55439", "-h", "127.0.0.1"]


def test_postgres_command_uses_private_non_windows_socket_directory() -> None:
    socket_dir = Path("/tmp/deo-pg-example")
    command = _postgres_command(Path("postgres"), Path("data"), 55439, socket_dir)

    assert command[-2:] == ["-k", str(socket_dir)]
