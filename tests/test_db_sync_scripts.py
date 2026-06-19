from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
import sys

from datosenorden.maintenance.db_sync import DatabaseCounts

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts" / "db"))

import export_local_db
import import_local_db
import verify_db_counts


def _session_manager(session):
    @contextmanager
    def _manager():
        yield session

    return _manager()


def test_export_local_db_prints_dump_path(monkeypatch, tmp_path, capsys) -> None:
    backup_dir = tmp_path / "private" / "database" / "backups"
    monkeypatch.setattr(export_local_db, "BACKUPS_DIR", backup_dir)
    monkeypatch.setattr(export_local_db, "get_database_url", lambda: "postgresql+psycopg://sync_user:sync_pass@localhost:5432/datosenorden")
    monkeypatch.setattr(
        export_local_db,
        "get_connection_info",
        lambda database_url: type("Conn", (), {"password": "sync_pass"})(),
    )
    monkeypatch.setattr(export_local_db, "find_pg_tool", lambda tool_name: Path("C:/Program Files/PostgreSQL/16/bin/pg_dump.exe"))
    monkeypatch.setattr(
        export_local_db,
        "build_dump_path",
        lambda timestamp: Path("private/database/backups/datosenorden_local_20260619_120000.dump"),
    )
    called = {}

    def _build_pg_dump_command(database_url, dump_path, pg_dump_path):  # noqa: ANN001
        called["database_url"] = database_url
        called["dump_path"] = dump_path
        called["pg_dump_path"] = pg_dump_path
        return ["pg_dump", "--file", str(dump_path), "datosenorden"]

    monkeypatch.setattr(export_local_db, "build_pg_dump_command", _build_pg_dump_command)
    monkeypatch.setattr(export_local_db, "run_pg_command", lambda command, password: called.update(command=command, password=password))

    exit_code = export_local_db.main([])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert called["dump_path"] == backup_dir / "datosenorden_local_20260619_120000.dump"
    assert called["password"] == "sync_pass"
    assert "local_db_exported: path=" in captured.out
    assert captured.err == ""


def test_export_local_db_reports_missing_pg_dump(monkeypatch, capsys) -> None:
    monkeypatch.setattr(export_local_db, "get_database_url", lambda: "postgresql+psycopg://sync_user:sync_pass@localhost:5432/datosenorden")
    monkeypatch.setattr(export_local_db, "get_connection_info", lambda database_url: type("Conn", (), {"password": "sync_pass"})())
    monkeypatch.setattr(export_local_db, "find_pg_tool", lambda tool_name: (_ for _ in ()).throw(FileNotFoundError("pg_dump was not found. Add the PostgreSQL bin directory to PATH, for example C:\\Program Files\\PostgreSQL\\16\\bin.")))

    exit_code = export_local_db.main([])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "PostgreSQL bin directory" in captured.err


def test_import_local_db_requires_confirmation(monkeypatch, tmp_path, capsys) -> None:
    dump_file = tmp_path / "dump.dump"
    dump_file.write_bytes(b"")

    exit_code = import_local_db.main(["--dump-file", str(dump_file)])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "WARNING" in captured.err


def test_import_local_db_prints_warning_and_runs_restore(monkeypatch, tmp_path, capsys) -> None:
    dump_file = tmp_path / "dump.dump"
    dump_file.write_bytes(b"backup")
    monkeypatch.setattr(import_local_db, "get_database_url", lambda: "postgresql+psycopg://sync_user:sync_pass@localhost:5432/datosenorden")
    monkeypatch.setattr(import_local_db, "get_connection_info", lambda database_url: type("Conn", (), {"password": "sync_pass"})())
    monkeypatch.setattr(import_local_db, "find_pg_tool", lambda tool_name: Path("C:/Program Files/PostgreSQL/16/bin/pg_restore.exe"))
    monkeypatch.setattr(import_local_db, "build_pg_restore_command", lambda database_url, dump_path, pg_restore_path: ["pg_restore", "--clean", str(dump_path)])
    called = {}
    monkeypatch.setattr(import_local_db, "run_pg_command", lambda command, password: called.update(command=command, password=password))

    exit_code = import_local_db.main(["--dump-file", str(dump_file), "--confirm"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert called["password"] == "sync_pass"
    assert "WARNING: restoring this dump" in captured.err
    assert "local_db_imported: dump=" in captured.out


def test_import_local_db_rejects_missing_dump(monkeypatch, capsys) -> None:
    exit_code = import_local_db.main(["--dump-file", "missing.dump", "--confirm"])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "No existe el dump" in captured.err


def test_verify_db_counts_prints_counts(monkeypatch, capsys) -> None:
    monkeypatch.setattr(verify_db_counts, "SessionLocal", lambda: _session_manager(object()))
    monkeypatch.setattr(
        verify_db_counts,
        "collect_database_counts",
        lambda session: DatabaseCounts(entity=8, source_record=4, claim=6, evidence=5, relationship_public=7),
    )

    exit_code = verify_db_counts.main([])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "database_counts:" in captured.out
    assert "source_record=4" in captured.out
    assert "relationship_public=7" in captured.out
    assert captured.err == ""
