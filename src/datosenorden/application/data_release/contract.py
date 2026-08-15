from __future__ import annotations

import hashlib
import json
import zipfile
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any
from uuid import UUID

CONTRACT_ID = "DEO_PRODUCTION_DATA_PACKAGE_V0_1"
CONTRACT_VERSION = "0.1"
EXPORT_TOOL_VERSION = "0.1.0"
PROVENANCE_POLICY_VERSION = "T1_PUBLIC_PROVENANCE_AUTHORITY_V1"
REQUIRED_SCHEMA_REVISION = "202608120001"
BASELINE_CODE_RELEASE = "9569f0535b7de011bdddccfd42f88dee24b5c102"
CONTENT_CLASSIFICATION = "REAL_PUBLIC_USABLE"
PACKAGE_PREFIX = "DEO-PROD-DATA"


class DataPackageError(RuntimeError):
    """Base fail-closed error for data-package operations."""


class PackageIntegrityError(DataPackageError):
    """The archive or manifest does not match the contract."""


class PackageCompatibilityError(DataPackageError):
    """The package is incompatible with the target schema or code."""


class PackageConflictError(DataPackageError):
    """The target contains different content under a package identity."""


@dataclass(frozen=True)
class TableContract:
    name: str
    primary_key: tuple[str, ...]
    dependencies: tuple[str, ...]

    @property
    def path(self) -> str:
        return f"data/{self.name}.jsonl"


TABLE_CONTRACTS: tuple[TableContract, ...] = (
    TableContract("source", ("id",), ()),
    TableContract("dataset", ("id",), ("source",)),
    TableContract("source_record", ("id",), ("source", "dataset")),
    TableContract("entity", ("id",), ()),
    # evidence.claim_id is restored in a second pass after claim insertion.
    TableContract("evidence", ("id",), ("source", "dataset", "source_record")),
    TableContract("claim", ("id",), ("entity", "source_record", "evidence")),
    TableContract(
        "relationship_public",
        ("id",),
        ("entity", "claim"),
    ),
    TableContract("real_expedient", ("expedient_id",), ()),
    TableContract(
        "real_expedient_version",
        ("expedient_id", "version"),
        ("real_expedient",),
    ),
    TableContract(
        "real_expedient_reference",
        ("expedient_id", "version", "reference_type", "reference_id"),
        ("real_expedient_version",),
    ),
    TableContract(
        "real_expedient_narrative",
        ("expedient_id", "version", "statement_id"),
        ("real_expedient_version",),
    ),
    TableContract(
        "real_expedient_narrative_support",
        ("expedient_id", "version", "statement_id", "support_type", "reference_id"),
        ("real_expedient_narrative", "real_expedient_reference"),
    ),
)
TABLE_BY_NAME = {item.name: item for item in TABLE_CONTRACTS}


@dataclass(frozen=True)
class VerifiedPackage:
    path: Path
    archive_sha256: str
    manifest: dict[str, Any]
    rows: dict[str, tuple[dict[str, Any], ...]]


def canonical_value(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, bool)):
        return value
    if isinstance(value, float):
        return format(value, ".17g")
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Mapping):
        return {
            str(key): canonical_value(nested)
            for key, nested in sorted(value.items(), key=lambda item: str(item[0]))
        }
    if isinstance(value, (list, tuple)):
        return [canonical_value(item) for item in value]
    raise TypeError(f"unsupported canonical value: {type(value).__name__}")


def canonical_json(value: Any) -> bytes:
    return json.dumps(
        canonical_value(value),
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def rows_bytes(rows: Iterable[Mapping[str, Any]]) -> bytes:
    return b"".join(canonical_json(row) + b"\n" for row in rows)


def logical_content_hash(
    *,
    table_hashes: Mapping[str, str],
    required_schema_revision: str = REQUIRED_SCHEMA_REVISION,
) -> str:
    payload = {
        "content_classification": CONTENT_CLASSIFICATION,
        "contract": CONTRACT_ID,
        "provenance_policy_version": PROVENANCE_POLICY_VERSION,
        "required_schema_revision": required_schema_revision,
        "table_hashes": dict(sorted(table_hashes.items())),
    }
    return sha256_bytes(canonical_json(payload))


def package_id(release_number: int, logical_hash: str) -> str:
    if release_number < 1:
        raise ValueError("release number must be positive")
    return f"{PACKAGE_PREFIX}-{release_number:04d}-{logical_hash[:16]}"


def write_deterministic_zip(path: Path, members: Mapping[str, bytes]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name in sorted(members):
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 3
            info.external_attr = 0o100600 << 16
            archive.writestr(info, members[name])


def parse_jsonl(payload: bytes, *, path: str) -> tuple[dict[str, Any], ...]:
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(payload.splitlines(), start=1):
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            raise PackageIntegrityError(f"invalid JSON in {path}:{line_number}") from exc
        if not isinstance(value, dict):
            raise PackageIntegrityError(f"row must be an object in {path}:{line_number}")
        rows.append(value)
    return tuple(rows)
