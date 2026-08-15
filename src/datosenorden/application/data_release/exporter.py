from __future__ import annotations

import json
import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.inspection import inspect as sqlalchemy_inspect
from sqlalchemy.orm import Session

from datosenorden.application.provenance.models import ProvenanceClass
from datosenorden.application.provenance.service import build_public_usable_content
from datosenorden.application.real_expedient.eligibility import ProvenanceReferenceEligibility
from datosenorden.application.real_expedient.models import ReferenceKind
from datosenorden.models import (
    Claim,
    Dataset,
    Entity,
    Evidence,
    RealExpedientNarrativeRow,
    RealExpedientNarrativeSupportRow,
    RealExpedientReferenceRow,
    RealExpedientRow,
    RealExpedientVersionRow,
    RelationshipPublic,
    Source,
    SourceRecord,
)

from .contract import (
    BASELINE_CODE_RELEASE,
    CONTENT_CLASSIFICATION,
    CONTRACT_ID,
    CONTRACT_VERSION,
    EXPORT_TOOL_VERSION,
    PROVENANCE_POLICY_VERSION,
    REQUIRED_SCHEMA_REVISION,
    TABLE_CONTRACTS,
    DataPackageError,
    canonical_json,
    canonical_value,
    logical_content_hash,
    package_id,
    rows_bytes,
    sha256_bytes,
    sha256_file,
    write_deterministic_zip,
)

MODEL_BY_TABLE = {
    "source": Source,
    "dataset": Dataset,
    "source_record": SourceRecord,
    "entity": Entity,
    "evidence": Evidence,
    "claim": Claim,
    "relationship_public": RelationshipPublic,
    "real_expedient": RealExpedientRow,
    "real_expedient_version": RealExpedientVersionRow,
    "real_expedient_reference": RealExpedientReferenceRow,
    "real_expedient_narrative": RealExpedientNarrativeRow,
    "real_expedient_narrative_support": RealExpedientNarrativeSupportRow,
}

_EMAIL = re.compile(r"(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b")
_WINDOWS_PATH = re.compile(r"(?i)(?:[a-z]:\\|c:/users/|i:/)")
_SECRET_KEY = re.compile(
    r"(?i)^(?:password|passwd|secret|token|api[_-]?key|database_url|private[_-]?key|session[_-]?id)$"
)
_RAW_PII_KEYS = {
    "cargocontacto",
    "direccion",
    "direccionunidad",
    "fonocontacto",
    "mailcontacto",
    "nombrecontacto",
    "rutsucursal",
    "rutunidad",
}
_METADATA_DROP_KEYS = {"api_created_at", "request_params", "raw", "source_record_snapshot"}


@dataclass(frozen=True)
class ExportResult:
    package_path: Path
    sidecar_path: Path
    package_id: str
    archive_sha256: str
    logical_content_hash: str
    row_counts: dict[str, int]
    manifest: dict[str, Any]


def export_production_data_package(
    session: Session,
    *,
    output_dir: Path,
    release_number: int = 1,
    created_at: datetime | None = None,
    compatible_code_releases: tuple[str, ...] = (BASELINE_CODE_RELEASE,),
) -> ExportResult:
    _validate_code_releases(compatible_code_releases)
    revision = session.scalar(select_alembic_revision())
    if revision != REQUIRED_SCHEMA_REVISION:
        raise DataPackageError(
            f"source schema revision {revision!r} does not match {REQUIRED_SCHEMA_REVISION}"
        )
    selected = _select_rows(session)
    serialized = {
        table.name: tuple(_serialize_row(row, table.name) for row in selected[table.name])
        for table in TABLE_CONTRACTS
    }
    for table in TABLE_CONTRACTS:
        serialized[table.name] = tuple(
            sorted(
                serialized[table.name],
                key=lambda row, pk=table.primary_key: tuple(str(row[name]) for name in pk),
            )
        )
    members = {table.path: rows_bytes(serialized[table.name]) for table in TABLE_CONTRACTS}
    table_hashes = {table.name: sha256_bytes(members[table.path]) for table in TABLE_CONTRACTS}
    logical_hash = logical_content_hash(table_hashes=table_hashes)
    identifier = package_id(release_number, logical_hash)
    source_revision = sha256_bytes(
        canonical_json(
            {
                "required_schema_revision": revision,
                "source": table_hashes["source"],
                "dataset": table_hashes["dataset"],
                "source_record": table_hashes["source_record"],
            }
        )
    )
    timestamp = (created_at or datetime.now(UTC)).astimezone(UTC).isoformat()
    manifest = _build_manifest(
        identifier=identifier,
        created_at=timestamp,
        source_revision=source_revision,
        logical_hash=logical_hash,
        table_hashes=table_hashes,
        rows=serialized,
        compatible_code_releases=compatible_code_releases,
    )
    members["manifest.json"] = canonical_json(manifest) + b"\n"
    _security_scan_members(members)
    package_path = output_dir / f"{identifier.lower()}.zip"
    write_deterministic_zip(package_path, members)
    archive_hash = sha256_file(package_path)
    sidecar_path = package_path.with_suffix(package_path.suffix + ".sha256")
    sidecar_path.write_text(f"{archive_hash}  {package_path.name}\n", encoding="ascii")
    return ExportResult(
        package_path=package_path,
        sidecar_path=sidecar_path,
        package_id=identifier,
        archive_sha256=archive_hash,
        logical_content_hash=logical_hash,
        row_counts={name: len(rows) for name, rows in serialized.items()},
        manifest=manifest,
    )


def select_alembic_revision():  # noqa: ANN201
    from sqlalchemy import text

    return text("select version_num from alembic_version")


def _select_rows(session: Session) -> dict[str, tuple[Any, ...]]:
    content = build_public_usable_content(session)
    record_ids = set(content["record_ids"])
    entity_ids = set(content["entity_ids"])
    records = tuple(
        session.scalars(select(SourceRecord).where(SourceRecord.id.in_(record_ids))).all()
    )
    dataset_ids = {row.dataset_id for row in records}
    source_ids = {row.source_id for row in records}
    roots = tuple(
        session.scalars(
            select(RealExpedientRow)
            .join(
                RealExpedientVersionRow,
                (RealExpedientVersionRow.expedient_id == RealExpedientRow.expedient_id)
                & (RealExpedientVersionRow.version == RealExpedientRow.current_version),
            )
            .where(
                RealExpedientRow.provenance_class == ProvenanceClass.REAL.value,
                RealExpedientVersionRow.lifecycle == "published",
            )
        ).all()
    )
    expedient_ids = {row.expedient_id for row in roots}
    versions = tuple(
        session.scalars(
            select(RealExpedientVersionRow).where(
                RealExpedientVersionRow.expedient_id.in_(expedient_ids),
                RealExpedientVersionRow.lifecycle == "published",
            )
        ).all()
    )
    version_keys = {(row.expedient_id, row.version) for row in versions}
    references = tuple(
        session.scalars(
            select(RealExpedientReferenceRow).where(
                RealExpedientReferenceRow.expedient_id.in_(expedient_ids)
            )
        ).all()
    )
    references = tuple(row for row in references if (row.expedient_id, row.version) in version_keys)
    _verify_reference_closure(session, references)
    narratives = tuple(
        row
        for row in session.scalars(
            select(RealExpedientNarrativeRow).where(
                RealExpedientNarrativeRow.expedient_id.in_(expedient_ids)
            )
        ).all()
        if (row.expedient_id, row.version) in version_keys
    )
    supports = tuple(
        row
        for row in session.scalars(
            select(RealExpedientNarrativeSupportRow).where(
                RealExpedientNarrativeSupportRow.expedient_id.in_(expedient_ids)
            )
        ).all()
        if (row.expedient_id, row.version) in version_keys
    )
    return {
        "source": tuple(session.scalars(select(Source).where(Source.id.in_(source_ids))).all()),
        "dataset": tuple(session.scalars(select(Dataset).where(Dataset.id.in_(dataset_ids))).all()),
        "source_record": records,
        "entity": tuple(session.scalars(select(Entity).where(Entity.id.in_(entity_ids))).all()),
        "evidence": tuple(content["evidences"]),
        "claim": tuple(content["claims"]),
        "relationship_public": tuple(content["relationships"]),
        "real_expedient": roots,
        "real_expedient_version": versions,
        "real_expedient_reference": references,
        "real_expedient_narrative": narratives,
        "real_expedient_narrative_support": supports,
    }


def _verify_reference_closure(
    session: Session, references: Iterable[RealExpedientReferenceRow]
) -> None:
    eligibility = ProvenanceReferenceEligibility(session)
    for row in references:
        decision = eligibility.classify(ReferenceKind(row.reference_type), row.reference_id)
        if decision.provenance_class is not ProvenanceClass.REAL or not decision.public_usable:
            raise DataPackageError(
                f"published REAL expedient has non-public reference: "
                f"{row.expedient_id}@{row.version}:{row.reference_type}"
            )


def _serialize_row(row: Any, table_name: str) -> dict[str, Any]:
    values = {
        column.key: canonical_value(getattr(row, column.key))
        for column in sqlalchemy_inspect(row.__class__).columns
    }
    for key, value in tuple(values.items()):
        if isinstance(value, (dict, list)):
            values[key] = _sanitize_json(value)
    if table_name == "source_record":
        if values.get("error_log"):
            raise DataPackageError("public-usable source record contains operational error_log")
        values["error_log"] = None
        values["processed_at"] = None
    return values


def _sanitize_json(value: Any) -> Any:
    if isinstance(value, dict):
        result: dict[str, Any] = {}
        for key, nested in sorted(value.items(), key=lambda item: str(item[0])):
            normalized = re.sub(r"[^a-z0-9]", "", str(key).casefold())
            if normalized in _RAW_PII_KEYS or str(key) in _METADATA_DROP_KEYS:
                continue
            if _SECRET_KEY.fullmatch(str(key)):
                raise DataPackageError("secret-like JSON key in public content")
            result[str(key)] = _sanitize_json(nested)
        return result
    if isinstance(value, list):
        return [_sanitize_json(item) for item in value]
    if isinstance(value, str):
        return _EMAIL.sub("[redacted-public-contact]", value)
    return value


def _build_manifest(
    *,
    identifier: str,
    created_at: str,
    source_revision: str,
    logical_hash: str,
    table_hashes: Mapping[str, str],
    rows: Mapping[str, tuple[dict[str, Any], ...]],
    compatible_code_releases: tuple[str, ...],
) -> dict[str, Any]:
    table_manifest = [
        {
            "dependencies": list(table.dependencies),
            "path": table.path,
            "primary_key": list(table.primary_key),
            "row_count": len(rows[table.name]),
            "sha256": table_hashes[table.name],
            "table": table.name,
        }
        for table in TABLE_CONTRACTS
    ]
    return {
        "base_package_id": None,
        "code_compatibility": {
            "compatible_code_releases": list(compatible_code_releases),
            "max_code_release": compatible_code_releases[-1],
            "min_code_release": compatible_code_releases[0],
        },
        "content_classification": [CONTENT_CLASSIFICATION],
        "content_hashes": dict(sorted(table_hashes.items())),
        "contract": CONTRACT_ID,
        "contract_version": CONTRACT_VERSION,
        "created_at": created_at,
        "dependencies": {
            "external_documents": ["senado-docto-9000-mensaje_mocion"],
            "schema_managed_by": "alembic",
            "supported_postgresql_majors": [16, 17],
        },
        "export_tool_version": EXPORT_TOOL_VERSION,
        "lineage": {
            "deletion_policy": "no_deletions_in_v0_1",
            "release_mode": "snapshot",
            "supersedes": [],
        },
        "logical_content_hash": logical_hash,
        "operational_data_policy": {
            "excluded_tables": ["import_job", "change_log"],
            "production_import_history_starts_independently": True,
        },
        "package_id": identifier,
        "provenance_policy_version": PROVENANCE_POLICY_VERSION,
        "required_schema_revision": REQUIRED_SCHEMA_REVISION,
        "row_counts": {name: len(value) for name, value in sorted(rows.items())},
        "source_db_revision": f"sha256:{source_revision}",
        "table_manifest": table_manifest,
        "temporal_truth": {
            "acquisition_time_preserved": True,
            "event_time_preserved": True,
            "normalization_time_preserved": True,
            "package_creation_time": created_at,
            "production_import_time": "emitted_by_importer_not_rewritten_into_source_fields",
            "publication_time_preserved": True,
        },
    }


def _validate_code_releases(values: tuple[str, ...]) -> None:
    if not values or len(values) != len(set(values)):
        raise ValueError("compatible code releases must be a non-empty unique sequence")
    if any(
        len(value) != 40 or any(ch not in "0123456789abcdefABCDEF" for ch in value)
        for value in values
    ):
        raise ValueError("compatible code releases must be 40-hex commit IDs")


def _security_scan_members(members: Mapping[str, bytes]) -> None:
    for path, payload in members.items():
        text = payload.decode("utf-8")
        if _WINDOWS_PATH.search(text):
            raise DataPackageError(f"Windows path found in package member {path}")
        if path.startswith("data/") and _EMAIL.search(text):
            raise DataPackageError(f"email found in package member {path}")
        if path.startswith("data/"):
            for line in text.splitlines():
                _scan_secret_keys(json.loads(line), path)


def _scan_secret_keys(value: Any, path: str) -> None:
    if isinstance(value, dict):
        for key, nested in value.items():
            if _SECRET_KEY.fullmatch(str(key)):
                raise DataPackageError(f"secret-like key found in package member {path}")
            _scan_secret_keys(nested, path)
    elif isinstance(value, list):
        for nested in value:
            _scan_secret_keys(nested, path)
