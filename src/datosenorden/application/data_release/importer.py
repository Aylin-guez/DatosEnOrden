from __future__ import annotations

import json
import zipfile
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path, PurePosixPath
from typing import Any
from uuid import UUID

from sqlalchemy import MetaData, Table, and_, func, insert, select, text, update
from sqlalchemy.engine import Connection, Engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from datosenorden.application.provenance.service import build_public_metric_projection

from .contract import (
    CONTENT_CLASSIFICATION,
    CONTRACT_ID,
    CONTRACT_VERSION,
    PACKAGE_PREFIX,
    REQUIRED_SCHEMA_REVISION,
    TABLE_CONTRACTS,
    PackageCompatibilityError,
    PackageConflictError,
    PackageIntegrityError,
    VerifiedPackage,
    canonical_value,
    logical_content_hash,
    parse_jsonl,
    rows_bytes,
    sha256_bytes,
    sha256_file,
)
from .exporter import _security_scan_members


@dataclass(frozen=True)
class TargetExpectation:
    database_name: str
    environment: str
    code_release: str
    production_confirmation: str | None = None


@dataclass(frozen=True)
class ImportResult:
    package_id: str
    imported_at: str
    inserted: dict[str, int]
    unchanged: dict[str, int]
    target_counts: dict[str, int]
    public_metrics: dict[str, int]


def verify_package(path: Path, *, expected_sha256: str) -> VerifiedPackage:
    if not path.is_file():
        raise PackageIntegrityError("package file does not exist")
    if len(expected_sha256) != 64 or any(
        ch not in "0123456789abcdefABCDEF" for ch in expected_sha256
    ):
        raise PackageIntegrityError("expected package SHA-256 must be 64 hexadecimal characters")
    archive_hash = sha256_file(path)
    if archive_hash != expected_sha256.lower():
        raise PackageIntegrityError("package SHA-256 mismatch")
    expected_members = {"manifest.json", *(table.path for table in TABLE_CONTRACTS)}
    with zipfile.ZipFile(path, "r") as archive:
        names = archive.namelist()
        if len(names) != len(set(names)):
            raise PackageIntegrityError("archive contains duplicate members")
        for name in names:
            parsed = PurePosixPath(name)
            if parsed.is_absolute() or ".." in parsed.parts:
                raise PackageIntegrityError("archive contains unsafe member path")
        if set(names) != expected_members:
            raise PackageIntegrityError("archive member set does not match contract")
        members = {name: archive.read(name) for name in names}
    _security_scan_members(members)
    try:
        manifest = json.loads(members["manifest.json"])
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PackageIntegrityError("manifest is not valid UTF-8 JSON") from exc
    _verify_manifest_shape(manifest)
    rows: dict[str, tuple[dict[str, Any], ...]] = {}
    hashes: dict[str, str] = {}
    entries = {entry["table"]: entry for entry in manifest["table_manifest"]}
    for table in TABLE_CONTRACTS:
        payload = members[table.path]
        parsed_rows = parse_jsonl(payload, path=table.path)
        if payload != rows_bytes(parsed_rows):
            raise PackageIntegrityError(f"non-canonical JSONL encoding for {table.name}")
        entry = entries.get(table.name)
        if entry is None:
            raise PackageIntegrityError(f"missing table manifest for {table.name}")
        digest = sha256_bytes(payload)
        if entry != {
            "dependencies": list(table.dependencies),
            "path": table.path,
            "primary_key": list(table.primary_key),
            "row_count": len(parsed_rows),
            "sha256": digest,
            "table": table.name,
        }:
            raise PackageIntegrityError(f"table manifest mismatch for {table.name}")
        ordered = tuple(
            sorted(
                parsed_rows,
                key=lambda row, pk=table.primary_key: tuple(str(row[name]) for name in pk),
            )
        )
        if parsed_rows != ordered:
            raise PackageIntegrityError(f"rows are not ordered by primary key for {table.name}")
        keys = [tuple(row[name] for name in table.primary_key) for row in parsed_rows]
        if len(keys) != len(set(keys)):
            raise PackageIntegrityError(f"duplicate primary key in {table.name}")
        rows[table.name] = parsed_rows
        hashes[table.name] = digest
    logical_hash = logical_content_hash(table_hashes=hashes)
    if manifest["logical_content_hash"] != logical_hash:
        raise PackageIntegrityError("logical content hash mismatch")
    if manifest["content_hashes"] != dict(sorted(hashes.items())):
        raise PackageIntegrityError("content hashes mismatch")
    if manifest["row_counts"] != {name: len(value) for name, value in sorted(rows.items())}:
        raise PackageIntegrityError("row counts mismatch")
    identifier = manifest["package_id"]
    if not identifier.startswith(f"{PACKAGE_PREFIX}-") or not identifier.endswith(
        logical_hash[:16]
    ):
        raise PackageIntegrityError("package ID is not derived from logical content")
    return VerifiedPackage(path, archive_hash, manifest, rows)


def import_package(
    engine: Engine,
    package: VerifiedPackage,
    *,
    expectation: TargetExpectation,
) -> ImportResult:
    manifest = package.manifest
    _verify_code_compatibility(manifest, expectation.code_release)
    inserted = {table.name: 0 for table in TABLE_CONTRACTS}
    unchanged = {table.name: 0 for table in TABLE_CONTRACTS}
    try:
        with engine.begin() as connection:
            _verify_target(connection, package, expectation)
            metadata = MetaData()
            metadata.reflect(connection, only=[table.name for table in TABLE_CONTRACTS])
            pending_evidence_claims: list[tuple[dict[str, Any], Any]] = []
            for contract in TABLE_CONTRACTS:
                table = metadata.tables[contract.name]
                for canonical_row in package.rows[contract.name]:
                    existing = _existing_row(connection, table, contract.primary_key, canonical_row)
                    if existing is not None:
                        if not _database_row_matches(table, existing, canonical_row):
                            raise PackageConflictError(
                                f"target conflict in {contract.name} primary key "
                                f"{_primary_key_text(contract.primary_key, canonical_row)}"
                            )
                        unchanged[contract.name] += 1
                        continue
                    values = _decode_row(table, canonical_row)
                    evidence_claim_id = None
                    if contract.name == "evidence":
                        evidence_claim_id = values.get("claim_id")
                        values["claim_id"] = None
                    connection.execute(insert(table).values(**values))
                    inserted[contract.name] += 1
                    if evidence_claim_id is not None:
                        pending_evidence_claims.append((canonical_row, evidence_claim_id))
            evidence = metadata.tables["evidence"]
            for canonical_row, claim_id in pending_evidence_claims:
                connection.execute(
                    update(evidence)
                    .where(evidence.c.id == _decode_value(evidence.c.id, canonical_row["id"]))
                    .values(claim_id=claim_id)
                )
            connection.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))
            for contract in TABLE_CONTRACTS:
                table = metadata.tables[contract.name]
                for canonical_row in package.rows[contract.name]:
                    actual = _existing_row(connection, table, contract.primary_key, canonical_row)
                    if actual is None or not _database_row_matches(
                        table, actual, canonical_row
                    ):
                        raise PackageConflictError(
                            f"post-import verification failed for {contract.name}"
                        )
    except IntegrityError as exc:
        raise PackageConflictError("target constraint conflict; transaction rolled back") from exc
    with engine.connect() as connection:
        metadata = MetaData()
        metadata.reflect(connection, only=[table.name for table in TABLE_CONTRACTS])
        target_counts = {
            table.name: int(
                connection.scalar(select(func.count()).select_from(metadata.tables[table.name]))
                or 0
            )
            for table in TABLE_CONTRACTS
        }
    with Session(engine) as session:
        public_metrics = build_public_metric_projection(session)
    return ImportResult(
        package_id=manifest["package_id"],
        imported_at=datetime.now(UTC).isoformat(),
        inserted=inserted,
        unchanged=unchanged,
        target_counts=target_counts,
        public_metrics=public_metrics,
    )


def _verify_manifest_shape(manifest: Any) -> None:
    if not isinstance(manifest, dict):
        raise PackageIntegrityError("manifest must be an object")
    required = {
        "base_package_id",
        "code_compatibility",
        "content_classification",
        "content_hashes",
        "contract",
        "contract_version",
        "created_at",
        "dependencies",
        "export_tool_version",
        "lineage",
        "logical_content_hash",
        "operational_data_policy",
        "package_id",
        "provenance_policy_version",
        "required_schema_revision",
        "row_counts",
        "source_db_revision",
        "table_manifest",
        "temporal_truth",
    }
    if set(manifest) != required:
        raise PackageIntegrityError("manifest keys do not match contract")
    if manifest["contract"] != CONTRACT_ID or manifest["contract_version"] != CONTRACT_VERSION:
        raise PackageIntegrityError("unsupported data-package contract")
    if manifest["content_classification"] != [CONTENT_CLASSIFICATION]:
        raise PackageIntegrityError("package content classification is not public REAL-only")
    if manifest["required_schema_revision"] != REQUIRED_SCHEMA_REVISION:
        raise PackageIntegrityError("manifest schema revision is not supported")
    if not isinstance(manifest["table_manifest"], list):
        raise PackageIntegrityError("table manifest must be a list")


def _verify_code_compatibility(manifest: Mapping[str, Any], code_release: str) -> None:
    compatibility = manifest["code_compatibility"]
    allowed = compatibility.get("compatible_code_releases", [])
    if code_release not in allowed:
        raise PackageCompatibilityError("code release is not explicitly compatible with package")


def _verify_target(
    connection: Connection,
    package: VerifiedPackage,
    expectation: TargetExpectation,
) -> None:
    actual_database = str(connection.scalar(text("select current_database()")) or "")
    if actual_database != expectation.database_name:
        raise PackageCompatibilityError("target database identity mismatch")
    if actual_database in {"postgres", "template0", "template1"}:
        raise PackageCompatibilityError("administrative database cannot be a data-package target")
    if expectation.environment == "isolated-test":
        if not actual_database.startswith("datosenorden_pytest_"):
            raise PackageCompatibilityError("isolated target must use datosenorden_pytest_ prefix")
    elif expectation.environment == "production":
        if expectation.production_confirmation != package.manifest["package_id"]:
            raise PackageCompatibilityError("production confirmation must equal package ID")
    else:
        raise PackageCompatibilityError("target environment must be isolated-test or production")
    revision = connection.scalar(text("select version_num from alembic_version"))
    if revision != package.manifest["required_schema_revision"]:
        raise PackageCompatibilityError("target Alembic revision mismatch")
    major = int(str(connection.scalar(text("show server_version_num")))[:2])
    supported = package.manifest["dependencies"].get("supported_postgresql_majors", [])
    if major not in supported:
        raise PackageCompatibilityError("target PostgreSQL major is not supported")


def _existing_row(
    connection: Connection,
    table: Table,
    primary_key: tuple[str, ...],
    canonical_row: Mapping[str, Any],
) -> Mapping[str, Any] | None:
    predicates = [
        table.c[name] == _decode_value(table.c[name], canonical_row[name]) for name in primary_key
    ]
    return connection.execute(select(table).where(and_(*predicates))).mappings().one_or_none()


def _decode_row(table: Table, row: Mapping[str, Any]) -> dict[str, Any]:
    if set(row) != {column.name for column in table.columns}:
        raise PackageIntegrityError(f"column set mismatch for {table.name}")
    return {column.name: _decode_value(column, row[column.name]) for column in table.columns}


def _decode_value(column: Any, value: Any) -> Any:
    if value is None:
        return None
    try:
        python_type = column.type.python_type
    except NotImplementedError:
        return value
    if python_type is UUID:
        return UUID(str(value))
    if python_type is datetime:
        return datetime.fromisoformat(str(value))
    if python_type is date:
        return date.fromisoformat(str(value))
    if python_type is Decimal:
        return Decimal(str(value))
    if python_type is float:
        return float(value)
    return value


def _database_row_matches(
    table: Table,
    row: Mapping[str, Any],
    canonical_row: Mapping[str, Any],
) -> bool:
    for column in table.columns:
        actual = row[column.name]
        expected = _decode_value(column, canonical_row[column.name])
        if isinstance(actual, datetime) and isinstance(expected, datetime):
            if actual != expected:
                return False
        elif canonical_value(actual) != canonical_value(expected):
            return False
    return True


def _primary_key_text(primary_key: tuple[str, ...], row: Mapping[str, Any]) -> str:
    return ",".join(f"{name}={row[name]}" for name in primary_key)
