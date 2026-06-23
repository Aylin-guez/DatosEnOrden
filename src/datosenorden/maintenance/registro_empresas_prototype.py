from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timezone
import json
from pathlib import Path
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from datosenorden.core.config import PROJECT_ROOT
from datosenorden.etl.core.contracts import (
    ClaimRecord,
    DatasetRecord,
    EntityRecord,
    EntityType,
    EvidenceRecord,
    GraphBatch,
    PublicRelationshipRecord,
    RelationshipType,
    SourceInfo,
    SourceRecordPayload,
    WorkflowStatus,
)
from datosenorden.etl.core.hash import stable_json_hash
from datosenorden.etl.core.text import normalized_key
from datosenorden.etl.loaders.graph_loader import GraphLoader
from datosenorden.models import Claim, Entity, Evidence, RelationshipPublic, SourceRecord

LOCAL_TEST_DATA = "LOCAL_TEST_DATA"
NOT_OFFICIAL_DATA = "NOT_OFFICIAL_DATA"
REGISTRO_SAMPLE_DATASET_NAME = "registro-empresas-sample"
REGISTRO_SAMPLE_SOURCE_NAME = "DatosEnOrden Registro Empresas Sample"
REGISTRO_SAMPLE_SOURCE_URL = "local://sample/registro-empresas"
REGISTRO_SAMPLE_RECORD_TYPE = "registro_empresas:company_sample"
REGISTRO_SAMPLE_PATH = PROJECT_ROOT / "data" / "sample" / "registro_empresas_sample.json"

PERSON_REPRESENTS_COMPANY_PREDICATE = "PERSON_REPRESENTS_COMPANY"
PERSON_OWNS_COMPANY_PREDICATE = "PERSON_OWNS_COMPANY"
COMPANY_REGISTERED_ON_PREDICATE = "COMPANY_REGISTERED_ON"
COMPANY_MODIFIED_ON_PREDICATE = "COMPANY_MODIFIED_ON"


@dataclass(frozen=True)
class RegistroEmpresasImportResult:
    source_records: int
    claims: int
    evidences: int
    entities: int
    relationship_public: int
    companies: int
    people: int
    representatives: int
    owners: int


@dataclass(frozen=True)
class RegistroEmpresasSummaryRow:
    company_id: str
    company_name: str
    company_rut: str
    status: str
    constitution_date: date | None
    modified_date: date | None
    representatives: tuple[str, ...]
    owners: tuple[str, ...]
    ownership_percentages: tuple[str, ...]
    claims: tuple[str, ...]
    relationships: tuple[str, ...]
    evidence: int


@dataclass(frozen=True)
class RegistroEmpresasSummary:
    companies: int
    people: int
    representatives: int
    owners: int
    relationships: int
    evidence: int
    rows: tuple[RegistroEmpresasSummaryRow, ...]


def load_registro_empresas_sample_payload(input_path: Path | None = None) -> dict[str, Any]:
    path = input_path or REGISTRO_SAMPLE_PATH
    payload = json.loads(path.read_text(encoding="utf-8"))
    _validate_sample_payload(payload)
    return payload


def build_registro_empresas_sample_batch(session: Session, payload: dict[str, Any] | None = None) -> GraphBatch:
    _ = session
    sample = payload or load_registro_empresas_sample_payload()
    records = sample.get("records") or []
    if not records:
        raise ValueError("Registro Empresas sample must include at least one record")

    source_records: list[SourceRecordPayload] = []
    entities: list[EntityRecord] = []
    evidence: list[EvidenceRecord] = []
    claims: list[ClaimRecord] = []
    public_relationships: list[PublicRelationshipRecord] = []

    for record in records:
        parsed = _build_record_components(record, sample)
        source_records.extend(parsed.source_records)
        entities.extend(parsed.entities)
        evidence.extend(parsed.evidence)
        claims.extend(parsed.claims)
        public_relationships.extend(parsed.public_relationships)

    source = SourceInfo(
        name=REGISTRO_SAMPLE_SOURCE_NAME,
        publisher="DatosEnOrden",
        url=REGISTRO_SAMPLE_SOURCE_URL,
        license=f"{LOCAL_TEST_DATA} / {NOT_OFFICIAL_DATA}",
        retrieved_at=datetime.now(timezone.utc),
        metadata={
            "dataset": REGISTRO_SAMPLE_DATASET_NAME,
            "classification": sample["classification"],
            "official_status": sample["official_status"],
        },
    )
    dataset = DatasetRecord(
        source_name=REGISTRO_SAMPLE_SOURCE_NAME,
        name=REGISTRO_SAMPLE_DATASET_NAME,
        description=(
            "LOCAL_TEST_DATA / NOT_OFFICIAL_DATA sample used to validate "
            "company registry graph links"
        ),
        version="local-sample-1",
        dataset_url=f"{REGISTRO_SAMPLE_SOURCE_URL}/dataset",
        content_hash=stable_json_hash(sample),
        loaded_at=datetime.now(timezone.utc),
        metadata={
            "dataset": REGISTRO_SAMPLE_DATASET_NAME,
            "classification": sample["classification"],
            "official_status": sample["official_status"],
        },
    )
    return GraphBatch(
        source=source,
        dataset=dataset,
        source_records=tuple(source_records),
        entities=tuple(_unique_records(entities, key=lambda item: (item.entity_type.value, item.external_id))),
        evidence=tuple(_unique_records(evidence, key=lambda item: (item.source_record.external_id, item.url))),
        claims=tuple(
            _unique_records(
                claims,
                key=lambda item: (
                    item.subject_entity.entity_type.value,
                    item.subject_entity.external_id,
                    item.predicate,
                    item.object_entity.entity_type.value if item.object_entity is not None else "",
                    item.object_entity.external_id if item.object_entity is not None else "",
                    json.dumps(item.object_value, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
                    item.source_record.external_id,
                ),
            )
        ),
        public_relationships=tuple(
            _unique_records(
                public_relationships,
                key=lambda item: (
                    item.source_entity.entity_type.value,
                    item.source_entity.external_id,
                    item.target_entity.entity_type.value,
                    item.target_entity.external_id,
                    item.relationship_type.value,
                    item.claim.source_record.external_id,
                ),
            )
        ),
        raw_count=len(records),
        rejected_count=0,
        errors=(),
    )


def persist_registro_empresas_sample(session: Session, input_path: Path | None = None) -> RegistroEmpresasImportResult:
    payload = load_registro_empresas_sample_payload(input_path)
    batch = build_registro_empresas_sample_batch(session, payload)
    GraphLoader(session).load(batch, dry_run=False)

    return RegistroEmpresasImportResult(
        source_records=_count_rows(session, SourceRecord),
        claims=_count_rows(session, Claim),
        evidences=_count_rows(session, Evidence),
        entities=_count_rows(session, Entity),
        relationship_public=_count_rows(session, RelationshipPublic),
        companies=_count_entities(session, EntityType.COMPANY.value),
        people=_count_entities(session, EntityType.PERSON.value),
        representatives=_count_relationships(session, RelationshipType.PERSON_REPRESENTS_COMPANY.value),
        owners=_count_relationships(session, RelationshipType.PERSON_OWNS_COMPANY.value),
    )


def read_registro_empresas_summary(session: Session) -> RegistroEmpresasSummary:
    rows = _load_registro_empresas_rows(session)
    company_groups: dict[str, dict[str, Any]] = {}
    for row in rows:
        company_name = _company_name_for_claim(row)
        if not company_name:
            continue
        bucket = company_groups.setdefault(
            company_name,
            {
                "company_id": _company_id_for_claim(row),
                "company_name": company_name,
                "company_rut": _company_rut_for_claim(row),
                "status": _company_status_for_claim(row),
                "constitution_date": _claim_date_for_predicate(row, COMPANY_REGISTERED_ON_PREDICATE),
                "modified_date": _claim_date_for_predicate(row, COMPANY_MODIFIED_ON_PREDICATE),
                "representatives": set(),
                "owners": set(),
                "ownership_percentages": set(),
                "claims": set(),
                "relationships": set(),
                "evidence": set(),
            },
        )
        bucket["claims"].add(str(row.predicate))
        if row.evidence_id is not None:
            bucket["evidence"].add(str(row.evidence_id))
        if row.predicate == PERSON_REPRESENTS_COMPANY_PREDICATE:
            bucket["representatives"].add(_subject_name(row))
        if row.predicate == PERSON_OWNS_COMPANY_PREDICATE:
            bucket["owners"].add(_subject_name(row))
            percentage = _percentage_from_object_value(row)
            if percentage:
                bucket["ownership_percentages"].add(percentage)
        if row.predicate == COMPANY_REGISTERED_ON_PREDICATE and bucket["constitution_date"] is None:
            bucket["constitution_date"] = _claim_date_for_predicate(row, COMPANY_REGISTERED_ON_PREDICATE)
        if row.predicate == COMPANY_MODIFIED_ON_PREDICATE and bucket["modified_date"] is None:
            bucket["modified_date"] = _claim_date_for_predicate(row, COMPANY_MODIFIED_ON_PREDICATE)

    relationship_rows = _load_registro_empresas_relationship_rows(session)
    for relationship, company_name in relationship_rows:
        if not company_name:
            continue
        bucket = company_groups.setdefault(
            company_name,
            {
                "company_id": _entity_id_for_relationship(relationship),
                "company_name": company_name,
                "company_rut": "",
                "status": "",
                "constitution_date": None,
                "modified_date": None,
                "representatives": set(),
                "owners": set(),
                "ownership_percentages": set(),
                "claims": set(),
                "relationships": set(),
                "evidence": set(),
            },
        )
        bucket["relationships"].add(str(relationship.relationship_type))

    summary_rows = tuple(
        sorted(
            (
                RegistroEmpresasSummaryRow(
                    company_id=str(bucket["company_id"]),
                    company_name=str(bucket["company_name"]),
                    company_rut=str(bucket["company_rut"]),
                    status=str(bucket["status"]),
                    constitution_date=bucket["constitution_date"],
                    modified_date=bucket["modified_date"],
                    representatives=tuple(sorted(str(item) for item in bucket["representatives"])),
                    owners=tuple(sorted(str(item) for item in bucket["owners"])),
                    ownership_percentages=tuple(sorted(str(item) for item in bucket["ownership_percentages"])),
                    claims=tuple(sorted(str(item) for item in bucket["claims"])),
                    relationships=tuple(sorted(str(item) for item in bucket["relationships"])),
                    evidence=len(bucket["evidence"]),
                )
                for bucket in company_groups.values()
            ),
            key=lambda item: (item.company_name.lower(), item.company_rut),
        )
    )
    return RegistroEmpresasSummary(
        companies=len(summary_rows),
        people=_count_entities(session, EntityType.PERSON.value),
        representatives=_count_relationships(session, RelationshipType.PERSON_REPRESENTS_COMPANY.value),
        owners=_count_relationships(session, RelationshipType.PERSON_OWNS_COMPANY.value),
        relationships=_count_rows(session, RelationshipPublic),
        evidence=sum(row.evidence for row in summary_rows),
        rows=summary_rows,
    )


def render_registro_empresas_summary_text(summary: RegistroEmpresasSummary) -> str:
    lines = [
        "registro_empresas_summary:",
        f"  companies={summary.companies}",
        f"  people={summary.people}",
        f"  representatives={summary.representatives}",
        f"  owners={summary.owners}",
        f"  relationships={summary.relationships}",
        f"  evidence={summary.evidence}",
    ]
    if not summary.rows:
        lines.append("  (no registro empresas sample companies found)")
        return "\n".join(lines)
    for row in summary.rows:
        lines.extend(
            [
                "  company:",
                f"    id={row.company_id}",
                f"    name={row.company_name}",
                f"    rut={row.company_rut}",
                f"    status={row.status}",
                f"    constitution_date={row.constitution_date.isoformat() if row.constitution_date else 'None'}",
                f"    modified_date={row.modified_date.isoformat() if row.modified_date else 'None'}",
                f"    representatives={', '.join(row.representatives) if row.representatives else 'None'}",
                f"    owners={', '.join(row.owners) if row.owners else 'None'}",
                f"    ownership_percentages={', '.join(row.ownership_percentages) if row.ownership_percentages else 'None'}",
                f"    claims={', '.join(row.claims) if row.claims else 'None'}",
                f"    relationships={', '.join(row.relationships) if row.relationships else 'None'}",
                f"    evidence={row.evidence}",
            ]
        )
    return "\n".join(lines).rstrip()


def render_registro_empresas_import_result_text(result: RegistroEmpresasImportResult) -> str:
    return "\n".join(
        [
            "registro_empresas_sample_loaded:",
            f"  source_records={result.source_records}",
            f"  claims={result.claims}",
            f"  evidences={result.evidences}",
            f"  entities={result.entities}",
            f"  relationship_public={result.relationship_public}",
            f"  companies={result.companies}",
            f"  people={result.people}",
            f"  representatives={result.representatives}",
            f"  owners={result.owners}",
        ]
    )


def _build_record_components(record: dict[str, Any], sample: dict[str, Any]) -> GraphBatch:
    external_id = str(record["external_id"])
    publication_date = _parse_date(record.get("publication_date"))
    publication_number = str(record["publication_number"])
    publication_title = str(record["publication_title"])
    company_rut = str(record["company_rut"])
    company_name = str(record["company_name"])
    company_status = str(record.get("company_status", "Vigente"))
    constitution_date = _parse_date(record.get("company_constitution_date"))
    modified_date = _parse_date(record.get("company_modified_date"))
    representative_name = str(record.get("representative_name") or "")
    owners = record.get("owners") or []
    if not owners and representative_name:
        owners = [{"name": representative_name, "percentage": 100}]

    registry_entity = EntityRecord(
        entity_type=EntityType.PUBLIC_ORGANIZATION,
        external_id="registro-empresas:registry",
        name="Registro de Empresas",
        description=f"{LOCAL_TEST_DATA} / {NOT_OFFICIAL_DATA} company registry sample source.",
        normalized_key=normalized_key("Registro de Empresas"),
        metadata={
            "dataset": REGISTRO_SAMPLE_DATASET_NAME,
            "record_type": REGISTRO_SAMPLE_RECORD_TYPE,
        },
    )
    company_entity = EntityRecord(
        entity_type=EntityType.COMPANY,
        external_id=_company_external_id(company_rut, company_name),
        name=company_name,
        description=(
            f"{LOCAL_TEST_DATA} / {NOT_OFFICIAL_DATA} company registry sample for {company_name}."
        ),
        normalized_key=normalized_key(f"{company_rut} {company_name}"),
        metadata={
            "dataset": REGISTRO_SAMPLE_DATASET_NAME,
            "company_rut": company_rut,
            "company_status": company_status,
        },
    )
    person_entities = [
        _build_person_entity(str(owner.get("name", "")), company_name)
        for owner in owners
        if str(owner.get("name", "")).strip()
    ]
    if representative_name and representative_name not in {person.name for person in person_entities}:
        person_entities.append(_build_person_entity(representative_name, company_name))

    source_record_payload = {
        **record,
        "sample_markers": [LOCAL_TEST_DATA, NOT_OFFICIAL_DATA],
    }
    source_record = SourceRecordPayload(
        external_id=external_id,
        record_type=REGISTRO_SAMPLE_RECORD_TYPE,
        payload_hash=stable_json_hash(source_record_payload),
        raw_payload=source_record_payload,
        retrieved_at=datetime.now(timezone.utc),
        status=WorkflowStatus.NORMALIZED,
    )

    publication_url = f"{record['source_url']}/publication"
    registration_evidence = _build_evidence(
        source_record,
        external_id=f"{external_id}:registered",
        title=f"Registro Empresas local sample - {company_name} inscription",
        url=f"{publication_url}/registered",
        excerpt=(
            f"{LOCAL_TEST_DATA} / {NOT_OFFICIAL_DATA} company registration sample for {company_name}."
        ),
        published_at=publication_date,
    )
    modification_evidence = _build_evidence(
        source_record,
        external_id=f"{external_id}:modified",
        title=f"Registro Empresas local sample - {company_name} modification",
        url=f"{publication_url}/modified",
        excerpt=(
            f"{LOCAL_TEST_DATA} / {NOT_OFFICIAL_DATA} company modification sample for {company_name}."
        ),
        published_at=modified_date or publication_date,
    )
    representative_evidence = _build_evidence(
        source_record,
        external_id=f"{external_id}:representative",
        title=f"Registro Empresas local sample - representative for {company_name}",
        url=f"{publication_url}/representative",
        excerpt=(
            f"{LOCAL_TEST_DATA} / {NOT_OFFICIAL_DATA} representative sample for {company_name}."
        ),
        published_at=publication_date,
    )
    ownership_evidence = _build_evidence(
        source_record,
        external_id=f"{external_id}:ownership",
        title=f"Registro Empresas local sample - ownership for {company_name}",
        url=f"{publication_url}/ownership",
        excerpt=(
            f"{LOCAL_TEST_DATA} / {NOT_OFFICIAL_DATA} ownership sample for {company_name}."
        ),
        published_at=publication_date,
    )

    registry_registered_claim = ClaimRecord(
        subject_entity=registry_entity,
        predicate=COMPANY_REGISTERED_ON_PREDICATE,
        source_record=source_record,
        evidence=registration_evidence,
        object_entity=company_entity,
        object_value={
            "company_rut": company_rut,
            "company_name": company_name,
            "company_status": company_status,
            "publication_number": publication_number,
            "publication_date": publication_date.isoformat() if publication_date else None,
            "dataset": REGISTRO_SAMPLE_DATASET_NAME,
        },
        valid_from=constitution_date or publication_date,
        confidence=1.0,
        status=WorkflowStatus.VALIDATED,
        metadata={"dataset": REGISTRO_SAMPLE_DATASET_NAME},
    )
    registry_modified_claim = ClaimRecord(
        subject_entity=registry_entity,
        predicate=COMPANY_MODIFIED_ON_PREDICATE,
        source_record=source_record,
        evidence=modification_evidence,
        object_entity=company_entity,
        object_value={
            "company_rut": company_rut,
            "company_name": company_name,
            "company_status": company_status,
            "publication_number": publication_number,
            "publication_date": modified_date.isoformat() if modified_date else None,
            "dataset": REGISTRO_SAMPLE_DATASET_NAME,
        },
        valid_from=modified_date or publication_date,
        confidence=1.0,
        status=WorkflowStatus.VALIDATED,
        metadata={"dataset": REGISTRO_SAMPLE_DATASET_NAME},
    )

    claims: list[ClaimRecord] = [registry_registered_claim, registry_modified_claim]
    public_relationships: list[PublicRelationshipRecord] = [
        PublicRelationshipRecord(
            source_entity=registry_entity,
            target_entity=company_entity,
            relationship_type=RelationshipType.COMPANY_REGISTERED_ON,
            claim=registry_registered_claim,
            published_at=datetime.now(timezone.utc),
            status=WorkflowStatus.PUBLISHED,
            metadata={
                "dataset": REGISTRO_SAMPLE_DATASET_NAME,
                "company_rut": company_rut,
            },
        ),
        PublicRelationshipRecord(
            source_entity=registry_entity,
            target_entity=company_entity,
            relationship_type=RelationshipType.COMPANY_MODIFIED_ON,
            claim=registry_modified_claim,
            published_at=datetime.now(timezone.utc),
            status=WorkflowStatus.PUBLISHED,
            metadata={
                "dataset": REGISTRO_SAMPLE_DATASET_NAME,
                "company_rut": company_rut,
            },
        ),
    ]

    for owner in owners:
        owner_name = str(owner.get("name", "")).strip()
        if not owner_name:
            continue
        percentage = owner.get("percentage")
        person_entity = _build_person_entity(owner_name, company_name)
        person_rep_claim = ClaimRecord(
            subject_entity=person_entity,
            predicate=PERSON_REPRESENTS_COMPANY_PREDICATE,
            source_record=source_record,
            evidence=representative_evidence,
            object_entity=company_entity,
            object_value={
                "representative_name": representative_name or owner_name,
                "company_name": company_name,
                "company_rut": company_rut,
                "publication_number": publication_number,
                "dataset": REGISTRO_SAMPLE_DATASET_NAME,
            },
            valid_from=publication_date,
            confidence=1.0,
            status=WorkflowStatus.VALIDATED,
            metadata={"dataset": REGISTRO_SAMPLE_DATASET_NAME},
        )
        claims.append(person_rep_claim)
        public_relationships.append(
            PublicRelationshipRecord(
                source_entity=person_entity,
                target_entity=company_entity,
                relationship_type=RelationshipType.PERSON_REPRESENTS_COMPANY,
                claim=person_rep_claim,
                published_at=datetime.now(timezone.utc),
                status=WorkflowStatus.PUBLISHED,
                metadata={
                    "dataset": REGISTRO_SAMPLE_DATASET_NAME,
                    "company_rut": company_rut,
                },
            )
        )

        person_owner_claim = ClaimRecord(
            subject_entity=person_entity,
            predicate=PERSON_OWNS_COMPANY_PREDICATE,
            source_record=source_record,
            evidence=ownership_evidence,
            object_entity=company_entity,
            object_value={
                "owner_name": owner_name,
                "company_name": company_name,
                "company_rut": company_rut,
                "percentage_participation": percentage,
                "publication_number": publication_number,
                "dataset": REGISTRO_SAMPLE_DATASET_NAME,
            },
            valid_from=publication_date,
            confidence=1.0,
            status=WorkflowStatus.VALIDATED,
            metadata={"dataset": REGISTRO_SAMPLE_DATASET_NAME},
        )
        claims.append(person_owner_claim)
        public_relationships.append(
            PublicRelationshipRecord(
                source_entity=person_entity,
                target_entity=company_entity,
                relationship_type=RelationshipType.PERSON_OWNS_COMPANY,
                claim=person_owner_claim,
                published_at=datetime.now(timezone.utc),
                status=WorkflowStatus.PUBLISHED,
                metadata={
                    "dataset": REGISTRO_SAMPLE_DATASET_NAME,
                    "company_rut": company_rut,
                    "percentage_participation": percentage,
                },
            )
        )

    source = SourceInfo(
        name=REGISTRO_SAMPLE_SOURCE_NAME,
        publisher="DatosEnOrden",
        url=REGISTRO_SAMPLE_SOURCE_URL,
        license=f"{LOCAL_TEST_DATA} / {NOT_OFFICIAL_DATA}",
        retrieved_at=datetime.now(timezone.utc),
        metadata={
            "dataset": REGISTRO_SAMPLE_DATASET_NAME,
            "publication_number": publication_number,
            "company_rut": company_rut,
        },
    )
    dataset = DatasetRecord(
        source_name=REGISTRO_SAMPLE_SOURCE_NAME,
        name=REGISTRO_SAMPLE_DATASET_NAME,
        description=(
            "LOCAL_TEST_DATA / NOT_OFFICIAL_DATA sample used to validate neutral "
            "company registry links"
        ),
        version="local-sample-1",
        dataset_url=f"{REGISTRO_SAMPLE_SOURCE_URL}/dataset",
        content_hash=stable_json_hash(sample),
        loaded_at=datetime.now(timezone.utc),
        metadata={
            "dataset": REGISTRO_SAMPLE_DATASET_NAME,
            "classification": sample["classification"],
            "official_status": sample["official_status"],
        },
    )
    return GraphBatch(
        source=source,
        dataset=dataset,
        source_records=(source_record,),
        entities=tuple(
            _unique_records(
                [registry_entity, company_entity, *person_entities],
                key=lambda item: (item.entity_type.value, item.external_id),
            )
        ),
        evidence=(registration_evidence, modification_evidence, representative_evidence, ownership_evidence),
        claims=tuple(
            _unique_records(
                claims,
                key=lambda item: (
                    item.subject_entity.entity_type.value,
                    item.subject_entity.external_id,
                    item.predicate,
                    item.object_entity.entity_type.value if item.object_entity is not None else "",
                    item.object_entity.external_id if item.object_entity is not None else "",
                    json.dumps(item.object_value, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
                    item.source_record.external_id,
                ),
            )
        ),
        public_relationships=tuple(
            _unique_records(
                public_relationships,
                key=lambda item: (
                    item.source_entity.entity_type.value,
                    item.source_entity.external_id,
                    item.target_entity.entity_type.value,
                    item.target_entity.external_id,
                    item.relationship_type.value,
                    item.claim.source_record.external_id,
                ),
            )
        ),
        raw_count=1,
        rejected_count=0,
        errors=(),
    )


def render_registro_empresas_summary_text(summary: RegistroEmpresasSummary) -> str:
    lines = [
        "registro_empresas_summary:",
        f"  companies={summary.companies}",
        f"  people={summary.people}",
        f"  representatives={summary.representatives}",
        f"  owners={summary.owners}",
        f"  relationships={summary.relationships}",
        f"  evidence={summary.evidence}",
    ]
    if not summary.rows:
        lines.append("  (no registro empresas sample companies found)")
        return "\n".join(lines)
    for row in summary.rows:
        lines.extend(
            [
                "  company:",
                f"    id={row.company_id}",
                f"    name={row.company_name}",
                f"    rut={row.company_rut}",
                f"    status={row.status}",
                f"    constitution_date={row.constitution_date.isoformat() if row.constitution_date else 'None'}",
                f"    modified_date={row.modified_date.isoformat() if row.modified_date else 'None'}",
                f"    representatives={', '.join(row.representatives) if row.representatives else 'None'}",
                f"    owners={', '.join(row.owners) if row.owners else 'None'}",
                f"    ownership_percentages={', '.join(row.ownership_percentages) if row.ownership_percentages else 'None'}",
                f"    claims={', '.join(row.claims) if row.claims else 'None'}",
                f"    relationships={', '.join(row.relationships) if row.relationships else 'None'}",
                f"    evidence={row.evidence}",
            ]
        )
    return "\n".join(lines).rstrip()


def render_registro_empresas_import_result_text(result: RegistroEmpresasImportResult) -> str:
    return "\n".join(
        [
            "registro_empresas_sample_loaded:",
            f"  source_records={result.source_records}",
            f"  claims={result.claims}",
            f"  evidences={result.evidences}",
            f"  entities={result.entities}",
            f"  relationship_public={result.relationship_public}",
            f"  companies={result.companies}",
            f"  people={result.people}",
            f"  representatives={result.representatives}",
            f"  owners={result.owners}",
        ]
    )


def _validate_sample_payload(payload: dict[str, Any]) -> None:
    if payload.get("classification") != LOCAL_TEST_DATA:
        raise ValueError("Registro Empresas sample must be marked LOCAL_TEST_DATA")
    if payload.get("official_status") != NOT_OFFICIAL_DATA:
        raise ValueError("Registro Empresas sample must be marked NOT_OFFICIAL_DATA")
    if "records" not in payload or not isinstance(payload["records"], list):
        raise ValueError("Registro Empresas sample must include a records array")


def _build_person_entity(name: str, company_name: str) -> EntityRecord:
    cleaned = name.strip()
    return EntityRecord(
        entity_type=EntityType.PERSON,
        external_id=_person_external_id(cleaned),
        name=cleaned,
        description=(
            f"{LOCAL_TEST_DATA} / {NOT_OFFICIAL_DATA} person sample linked to {company_name}."
        ),
        normalized_key=normalized_key(cleaned),
        metadata={
            "dataset": REGISTRO_SAMPLE_DATASET_NAME,
            "company_name": company_name,
        },
    )


def _build_evidence(
    source_record: SourceRecordPayload,
    *,
    external_id: str,
    title: str,
    url: str,
    excerpt: str,
    published_at: date | None,
) -> EvidenceRecord:
    return EvidenceRecord(
        source_record=source_record,
        source_name=REGISTRO_SAMPLE_SOURCE_NAME,
        title=title,
        url=url,
        published_at=published_at,
        excerpt=excerpt,
        metadata={
            "classification": LOCAL_TEST_DATA,
            "official_status": NOT_OFFICIAL_DATA,
            "dataset": REGISTRO_SAMPLE_DATASET_NAME,
            "external_id": external_id,
        },
    )


@dataclass(frozen=True)
class _SummaryRowData:
    company_id: str
    company_name: str
    company_rut: str
    status: str
    constitution_date: date | None
    modified_date: date | None
    representatives: set[str]
    owners: set[str]
    ownership_percentages: set[str]
    claims: set[str]
    relationships: set[str]
    evidence: set[str]


def _load_registro_empresas_rows(session: Session):
    return list(
        session.scalars(
            select(Claim)
            .join(SourceRecord, Claim.source_record_id == SourceRecord.id)
            .options(
                joinedload(Claim.subject_entity),
                joinedload(Claim.object_entity),
                joinedload(Claim.evidence),
                joinedload(Claim.source_record),
            )
            .where(SourceRecord.record_type == REGISTRO_SAMPLE_RECORD_TYPE)
            .order_by(Claim.created_at, Claim.id)
        ).all()
    )


def _load_registro_empresas_relationship_rows(session: Session):
    rows = session.execute(
        select(RelationshipPublic, Entity.name)
        .select_from(RelationshipPublic)
        .join(Claim, RelationshipPublic.claim_id == Claim.id)
        .join(SourceRecord, Claim.source_record_id == SourceRecord.id)
        .join(Entity, RelationshipPublic.target_entity_id == Entity.id)
        .where(SourceRecord.record_type == REGISTRO_SAMPLE_RECORD_TYPE)
        .order_by(RelationshipPublic.created_at, RelationshipPublic.id)
    ).all()
    return [(relationship, str(company_name)) for relationship, company_name in rows]


def _company_name_for_claim(claim: Claim) -> str:
    if claim.object_entity is not None and claim.object_entity.entity_type == EntityType.COMPANY.value:
        return claim.object_entity.name
    if claim.subject_entity is not None and claim.subject_entity.entity_type == EntityType.COMPANY.value:
        return claim.subject_entity.name
    value = claim.object_value or {}
    if isinstance(value, dict):
        company_name = value.get("company_name")
        if company_name:
            return str(company_name)
    return ""


def _company_id_for_claim(claim: Claim) -> str:
    if claim.object_entity is not None and claim.object_entity.entity_type == EntityType.COMPANY.value:
        return str(claim.object_entity.id)
    if claim.subject_entity is not None and claim.subject_entity.entity_type == EntityType.COMPANY.value:
        return str(claim.subject_entity.id)
    return ""


def _company_rut_for_claim(claim: Claim) -> str:
    value = claim.object_value or {}
    if isinstance(value, dict) and value.get("company_rut"):
        return str(value["company_rut"])
    if claim.object_entity is not None:
        metadata = getattr(claim.object_entity, "entity_metadata", {}) or {}
        if metadata.get("company_rut"):
            return str(metadata["company_rut"])
    return ""


def _company_status_for_claim(claim: Claim) -> str:
    value = claim.object_value or {}
    if isinstance(value, dict) and value.get("company_status"):
        return str(value["company_status"])
    if claim.object_entity is not None:
        metadata = getattr(claim.object_entity, "entity_metadata", {}) or {}
        if metadata.get("company_status"):
            return str(metadata["company_status"])
    return ""


def _claim_date_for_predicate(claim: Claim, predicate: str) -> date | None:
    if claim.predicate != predicate:
        return None
    value = claim.object_value or {}
    if isinstance(value, dict) and value.get("publication_date"):
        try:
            return date.fromisoformat(str(value["publication_date"]))
        except ValueError:
            return None
    return claim.valid_from


def _subject_name(row: Claim) -> str:
    return row.subject_entity.name if row.subject_entity is not None else ""


def _percentage_from_object_value(claim: Claim) -> str:
    value = claim.object_value or {}
    if isinstance(value, dict) and value.get("percentage_participation") is not None:
        return str(value["percentage_participation"])
    return ""


def _entity_id_for_relationship(relationship: RelationshipPublic) -> str:
    if relationship.target_entity is not None and relationship.target_entity.entity_type == EntityType.COMPANY.value:
        return str(relationship.target_entity.id)
    if relationship.source_entity is not None and relationship.source_entity.entity_type == EntityType.COMPANY.value:
        return str(relationship.source_entity.id)
    return ""


def _company_external_id(company_rut: str, company_name: str) -> str:
    return f"registro-empresas:company:{normalized_key(company_rut or company_name) or normalized_key(company_name) or company_name.lower()}"


def _person_external_id(person_name: str) -> str:
    return f"registro-empresas:person:{normalized_key(person_name) or person_name.lower()}"


def _count_rows(session: Session, model) -> int:  # type: ignore[no-untyped-def]
    return int(session.scalar(select(func.count()).select_from(model)) or 0)


def _count_entities(session: Session, entity_type: str) -> int:
    return int(
        session.scalar(
            select(func.count()).select_from(Entity).where(Entity.entity_type == entity_type)
        )
        or 0
    )


def _count_relationships(session: Session, relationship_type: str) -> int:
    return int(
        session.scalar(
            select(func.count()).select_from(RelationshipPublic).where(
                RelationshipPublic.relationship_type == relationship_type
            )
        )
        or 0
    )


def _unique_records(records: list[Any], *, key) -> list[Any]:  # noqa: ANN001
    seen: set[Any] = set()
    unique: list[Any] = []
    for record in records:
        value = key(record)
        if value in seen:
            continue
        seen.add(value)
        unique.append(record)
    return unique


def _parse_date(value: object | None) -> date | None:
    if value in (None, ""):
        return None
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value))
    except ValueError:
        return None
