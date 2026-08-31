from __future__ import annotations

import json
import os
import re
import zipfile
from datetime import datetime
from pathlib import Path

import pytest
from sqlalchemy import Column, DateTime, MetaData, Table

from datosenorden.application.data_release.contract import (
    BASELINE_CODE_RELEASE,
    CONTENT_CLASSIFICATION,
    CONTRACT_ID,
    REQUIRED_SCHEMA_REVISION,
    TABLE_CONTRACTS,
    PackageIntegrityError,
    canonical_json,
    canonical_value,
    logical_content_hash,
    logical_table_hashes,
    package_id,
)
from datosenorden.application.data_release.importer import _database_row_matches, verify_package
from tests.qa_artifacts import certified_data_package_path


def _first_package() -> tuple[Path, str]:
    path = os.getenv("DEO_FIRST_DATA_PACKAGE")
    digest = os.getenv("DEO_FIRST_DATA_PACKAGE_SHA256")
    if not path or not digest:
        pytest.skip("first production data package is not selected for this test run")
    return Path(path), digest


def _expected_code_release() -> str:
    return os.getenv("DEO_EXPECTED_CODE_RELEASE", BASELINE_CODE_RELEASE)


def test_contract_canonicalization_and_package_id_are_deterministic() -> None:
    left = {"b": [2, 1], "a": {"z": "valor", "x": 1}}
    right = {"a": {"x": 1, "z": "valor"}, "b": [2, 1]}
    assert canonical_json(left) == canonical_json(right)
    assert canonical_value(left) == canonical_value(right)
    digest = logical_content_hash(table_hashes={"b": "2" * 64, "a": "1" * 64})
    assert package_id(1, digest) == f"DEO-PROD-DATA-0001-{digest[:16]}"


def test_logical_hash_ignores_real_expedient_updated_at() -> None:
    first = {"real_expedient": ({"expedient_id": "EXP-REAL", "updated_at": "2026-01-01T00:00:00+00:00"},)}
    second = {"real_expedient": ({"expedient_id": "EXP-REAL", "updated_at": "2026-02-01T00:00:00+00:00"},)}
    first_hash = logical_content_hash(table_hashes=logical_table_hashes(rows=first))
    second_hash = logical_content_hash(table_hashes=logical_table_hashes(rows=second))
    assert first_hash == second_hash


def test_logical_hash_ignores_real_expedient_version_created_at() -> None:
    first = {"real_expedient_version": ({"expedient_id": "EXP-REAL", "version": 2, "created_at": "2026-01-01T00:00:00+00:00"},)}
    second = {"real_expedient_version": ({"expedient_id": "EXP-REAL", "version": 2, "created_at": "2026-02-01T00:00:00+00:00"},)}
    first_hash = logical_content_hash(table_hashes=logical_table_hashes(rows=first))
    second_hash = logical_content_hash(table_hashes=logical_table_hashes(rows=second))
    assert first_hash == second_hash


@pytest.mark.parametrize("table,field", [
    ("real_expedient_version", "title"),
    ("real_expedient_version", "question"),
    ("real_expedient_narrative", "statement"),
    ("real_expedient_reference", "reference_id"),
])
def test_logical_hash_changes_for_semantic_expedient_content(table: str, field: str) -> None:
    base = {table: ({"expedient_id": "EXP", "version": 1, field: "before"},)}
    changed = {table: ({"expedient_id": "EXP", "version": 1, field: "after"},)}
    assert logical_content_hash(table_hashes=logical_table_hashes(rows=base)) != logical_content_hash(table_hashes=logical_table_hashes(rows=changed))


def test_verify_package_rejects_physically_tampered_jsonl(tmp_path: Path) -> None:
    source = certified_data_package_path()
    target = tmp_path / "tampered.zip"
    with zipfile.ZipFile(source) as archive, zipfile.ZipFile(target, "w") as altered:
        for info in archive.infolist():
            payload = archive.read(info.filename)
            if info.filename == "data/real_expedient.jsonl":
                payload = payload.replace(b'"current_version":1', b'"current_version":9', 1)
            altered.writestr(info, payload)
    with pytest.raises(PackageIntegrityError, match="SHA-256 mismatch"):
        verify_package(target, expected_sha256="4de868d6baa5de5be63a3ef2b858c50f5a5c311df8eadf80c6ffda17262cc3b0")


def test_database_timestamp_comparison_uses_the_instant_not_the_rendered_offset() -> None:
    table = Table(
        "timestamp_probe",
        MetaData(),
        Column("observed_at", DateTime(timezone=True), nullable=False),
    )
    assert _database_row_matches(
        table,
        {"observed_at": datetime.fromisoformat("2026-08-13T20:54:03.668541+00:00")},
        {"observed_at": "2026-08-13T16:54:03.668541-04:00"},
    )


def test_first_package_manifest_is_real_only_and_operationally_minimal() -> None:
    path, digest = _first_package()
    package = verify_package(path, expected_sha256=digest)
    manifest = package.manifest
    assert manifest["contract"] == CONTRACT_ID
    assert manifest["required_schema_revision"] == REQUIRED_SCHEMA_REVISION
    assert manifest["content_classification"] == [CONTENT_CLASSIFICATION]
    assert manifest["code_compatibility"]["compatible_code_releases"] == [
        _expected_code_release()
    ]
    assert manifest["operational_data_policy"]["excluded_tables"] == [
        "import_job",
        "change_log",
    ]
    assert manifest["lineage"] == {
        "deletion_policy": "no_deletions_in_v0_1",
        "release_mode": "snapshot",
        "supersedes": [],
    }
    assert set(package.rows) == {table.name for table in TABLE_CONTRACTS}
    assert all(row["status"] != "rejected" for row in package.rows["source_record"])
    assert {row["provenance_class"] for row in package.rows["real_expedient"]} == {"REAL"}
    assert "EXP-001" not in {row["expedient_id"] for row in package.rows["real_expedient"]}
    assert {row["expedient_id"] for row in package.rows["real_expedient"]} == {
        "EXP-REAL-CHILECOMPRA-1000813-247-CM26",
        "EXP-REAL-CHILECOMPRA-1002584-197-CM26",
        "EXP-REAL-CHILECOMPRA-1002772-6758-SE26",
        "EXP-REAL-LEGISLATIVE-15975-25",
    }
    dep = [
        row
        for row in package.rows["real_expedient_version"]
        if row["expedient_id"] == "EXP-REAL-CHILECOMPRA-1002584-197-CM26"
    ]
    assert [row["version"] for row in dep] == [1, 2]


def test_first_package_rejects_wrong_archive_hash() -> None:
    path, _ = _first_package()
    with pytest.raises(PackageIntegrityError, match="SHA-256 mismatch"):
        verify_package(path, expected_sha256="0" * 64)


def test_first_package_security_surface_contains_no_forbidden_material() -> None:
    path, _ = _first_package()
    with zipfile.ZipFile(path) as archive:
        payload = b"\n".join(archive.read(name) for name in archive.namelist())
    text = payload.decode("utf-8")
    assert not re.search(r"(?i)(?:[a-z]:\\|c:/users/|i:/)", text)
    assert not re.search(r"(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", text)
    for table in TABLE_CONTRACTS:
        for row in json.loads(
            "[" + ",".join(line for line in _member_lines(path, table.path)) + "]"
        ):
            assert "DATABASE_URL" not in canonical_json(row).decode("utf-8")
            assert "EXP-001" not in canonical_json(row).decode("utf-8")


def _member_lines(path: Path, member: str) -> list[str]:
    with zipfile.ZipFile(path) as archive:
        return archive.read(member).decode("utf-8").splitlines()
