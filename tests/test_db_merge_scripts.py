from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts" / "db"))

import merge_local_db


def test_merge_local_db_requires_known_mode(monkeypatch, tmp_path, capsys) -> None:
    dump_file = tmp_path / "dump.dump"
    dump_file.write_bytes(b"backup")
    monkeypatch.setattr(
        merge_local_db,
        "merge_dump_file_into_current_database",
        lambda dump_file, dry_run: type(  # noqa: ARG005
            "Report",
            (),
            {
                "inserted_source_records": 1,
                "inserted_entities": 2,
                "inserted_claims": 3,
                "inserted_evidences": 4,
                "inserted_relationships": 5,
                "skipped_duplicates": 6,
            },
        )(),
    )

    exit_code = merge_local_db.main(["--file", str(dump_file), "--dry-run"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "WARNING: dry-run" in captured.err
    assert "merge_report:" in captured.out
    assert "mode=dry-run" in captured.out


def test_merge_local_db_confirm_mode_prints_warning(monkeypatch, tmp_path, capsys) -> None:
    dump_file = tmp_path / "dump.dump"
    dump_file.write_bytes(b"backup")
    monkeypatch.setattr(
        merge_local_db,
        "merge_dump_file_into_current_database",
        lambda dump_file, dry_run: type(  # noqa: ARG005
            "Report",
            (),
            {
                "inserted_source_records": 1,
                "inserted_entities": 2,
                "inserted_claims": 3,
                "inserted_evidences": 4,
                "inserted_relationships": 5,
                "skipped_duplicates": 6,
            },
        )(),
    )

    exit_code = merge_local_db.main(["--file", str(dump_file), "--confirm"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "WARNING: el merge insertará" in captured.err
    assert "mode=confirm" in captured.out


def test_merge_local_db_rejects_missing_dump(capsys) -> None:
    exit_code = merge_local_db.main(["--file", "missing.dump", "--dry-run"])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "No existe el dump" in captured.err
