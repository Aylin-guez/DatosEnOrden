from __future__ import annotations

from pathlib import Path

import datosenorden.maintenance.db_sync as db_sync
from datosenorden.maintenance.db_sync import DatabaseCounts
from datosenorden.maintenance.db_sync import build_dump_path
from datosenorden.maintenance.db_sync import build_pg_dump_command
from datosenorden.maintenance.db_sync import build_pg_restore_command
from datosenorden.maintenance.db_sync import find_pg_tool
from datosenorden.maintenance.db_sync import render_database_counts_text


def test_build_pg_dump_command_uses_connection_details() -> None:
    command = build_pg_dump_command(
        "postgresql+psycopg://sync_user:sync_pass@localhost:5432/datosenorden",
        Path("private/database/backups/datosenorden_local_20260619_120000.dump"),
        Path("C:/Program Files/PostgreSQL/16/bin/pg_dump.exe"),
    )

    assert command[0].endswith("pg_dump.exe")
    assert "--format=custom" in command
    assert "--file" in command
    assert "--host" in command and "localhost" in command
    assert "--port" in command and "5432" in command
    assert "--username" in command and "sync_user" in command
    assert "sync_pass" not in command
    assert command[-1] == "datosenorden"


def test_build_pg_restore_command_uses_connection_details() -> None:
    command = build_pg_restore_command(
        "postgresql+psycopg://sync_user:sync_pass@localhost:5432/datosenorden",
        Path("private/database/backups/datosenorden_local_20260619_120000.dump"),
        Path("C:/Program Files/PostgreSQL/16/bin/pg_restore.exe"),
    )

    assert command[0].endswith("pg_restore.exe")
    assert "--clean" in command
    assert "--if-exists" in command
    assert "--single-transaction" in command
    assert "--dbname" in command
    assert command[-1].endswith(".dump")
    assert "sync_pass" not in command


def test_build_dump_path_uses_private_backup_folder() -> None:
    path = build_dump_path()

    assert path.parent.parts[-3:] == ("private", "database", "backups")
    assert path.name.startswith("datosenorden_local_")
    assert path.suffix == ".dump"


def test_find_pg_tool_missing_shows_bin_path_guidance(monkeypatch) -> None:
    monkeypatch.setattr(db_sync.shutil, "which", lambda tool: None)
    monkeypatch.setattr(db_sync.os, "getenv", lambda name: None)

    try:
        find_pg_tool("pg_dump")
    except FileNotFoundError as exc:
        message = str(exc)
    else:  # pragma: no cover - defensive
        raise AssertionError("Expected FileNotFoundError")

    assert "PostgreSQL" in message
    assert "PATH" in message


def test_render_database_counts_text_formats_counts() -> None:
    text = render_database_counts_text(
        DatabaseCounts(entity=7, source_record=3, claim=4, evidence=5, relationship_public=6)
    )

    assert "database_counts:" in text
    assert "entity=7" in text
    assert "source_record=3" in text
    assert "relationship_public=6" in text
