from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from datosenorden.db.session import SessionLocal
from datosenorden.db.session import build_engine
from datosenorden.etl.loaders.graph_loader import GraphLoader
from datosenorden.models import Claim
from datosenorden.models import Dataset
from datosenorden.models import Entity
from datosenorden.models import Evidence
from datosenorden.models import RelationshipPublic
from datosenorden.models import Source
from datosenorden.models import SourceRecord
from datosenorden.maintenance.db_sync import build_createdb_command
from datosenorden.maintenance.db_sync import build_database_url_with_name
from datosenorden.maintenance.db_sync import build_dropdb_command
from datosenorden.maintenance.db_sync import build_pg_restore_command
from datosenorden.maintenance.db_sync import find_pg_tool
from datosenorden.maintenance.db_sync import get_connection_info
from datosenorden.maintenance.db_sync import get_database_url
from datosenorden.maintenance.db_sync import run_pg_command


@dataclass(frozen=True)
class MergeReport:
    inserted_source_records: int
    inserted_entities: int
    inserted_claims: int
    inserted_evidences: int
    inserted_relationships: int
    skipped_duplicates: int


@dataclass(frozen=True)
class MergeSnapshot:
    sources: tuple[Source, ...]
    datasets: tuple[Dataset, ...]
    entities: tuple[Entity, ...]
    source_records: tuple[SourceRecord, ...]
    evidences: tuple[Evidence, ...]
    claims: tuple[Claim, ...]
    relationships: tuple[RelationshipPublic, ...]


@dataclass
class _MutableMergeCounts:
    inserted_source_records: int = 0
    inserted_entities: int = 0
    inserted_claims: int = 0
    inserted_evidences: int = 0
    inserted_relationships: int = 0
    skipped_duplicates: int = 0

    def freeze(self) -> MergeReport:
        return MergeReport(
            inserted_source_records=self.inserted_source_records,
            inserted_entities=self.inserted_entities,
            inserted_claims=self.inserted_claims,
            inserted_evidences=self.inserted_evidences,
            inserted_relationships=self.inserted_relationships,
            skipped_duplicates=self.skipped_duplicates,
        )


def build_merge_temp_database_name(timestamp: datetime | None = None) -> str:
    stamp = (timestamp or datetime.now(timezone.utc)).strftime("%Y%m%d_%H%M%S")
    return f"datosenorden_merge_{stamp}_{uuid4().hex[:8]}"


def render_merge_report_text(report: MergeReport, *, dry_run: bool) -> str:
    mode = "dry-run" if dry_run else "confirm"
    return "\n".join(
        [
            "merge_report:",
            f"mode={mode}",
            f"inserted source_records={report.inserted_source_records}",
            f"inserted entities={report.inserted_entities}",
            f"inserted claims={report.inserted_claims}",
            f"inserted evidences={report.inserted_evidences}",
            f"inserted relationships={report.inserted_relationships}",
            f"skipped duplicates={report.skipped_duplicates}",
        ]
    )


def merge_dump_file_into_current_database(dump_file: Path, *, dry_run: bool) -> MergeReport:
    database_url = get_database_url()
    connection_info = get_connection_info(database_url)
    createdb_path = find_pg_tool("createdb")
    dropdb_path = find_pg_tool("dropdb")
    pg_restore_path = find_pg_tool("pg_restore")

    temp_database_name = build_merge_temp_database_name()
    temp_database_url = build_database_url_with_name(database_url, temp_database_name)
    temp_engine = build_engine(temp_database_url)
    temp_session_factory = sessionmaker(bind=temp_engine, autoflush=False, autocommit=False)
    created_temp_database = False

    try:
        create_command = build_createdb_command(database_url, temp_database_name, createdb_path)
        run_pg_command(create_command, connection_info.password)
        created_temp_database = True

        restore_command = build_pg_restore_command(
            temp_database_url,
            dump_file,
            pg_restore_path,
            clean=False,
        )
        run_pg_command(restore_command, connection_info.password)

        with temp_session_factory() as source_session:
            snapshot = load_merge_snapshot(source_session)

        with SessionLocal() as dest_session:
            try:
                report = merge_snapshot_into_current_database(snapshot, dest_session)
                if dry_run:
                    dest_session.rollback()
                else:
                    dest_session.commit()
            except Exception:
                dest_session.rollback()
                raise
            return report
    finally:
        temp_engine.dispose()
        if created_temp_database:
            try:
                drop_command = build_dropdb_command(database_url, temp_database_name, dropdb_path)
                run_pg_command(drop_command, connection_info.password)
            except Exception as exc:  # noqa: BLE001
                print(f"WARNING: no se pudo eliminar la base temporal {temp_database_name}.", file=sys.stderr)
                print(f"Detalle: {exc}", file=sys.stderr)


def load_merge_snapshot(session: Session) -> MergeSnapshot:
    return MergeSnapshot(
        sources=tuple(session.scalars(select(Source).order_by(Source.id.asc())).all()),
        datasets=tuple(session.scalars(select(Dataset).order_by(Dataset.id.asc())).all()),
        entities=tuple(session.scalars(select(Entity).order_by(Entity.id.asc())).all()),
        source_records=tuple(session.scalars(select(SourceRecord).order_by(SourceRecord.id.asc())).all()),
        evidences=tuple(session.scalars(select(Evidence).order_by(Evidence.id.asc())).all()),
        claims=tuple(session.scalars(select(Claim).order_by(Claim.id.asc())).all()),
        relationships=tuple(session.scalars(select(RelationshipPublic).order_by(RelationshipPublic.id.asc())).all()),
    )


def merge_snapshot_into_current_database(
    snapshot: MergeSnapshot,
    dest_session: Session,
) -> MergeReport:
    counts = _MutableMergeCounts()

    source_id_map = _merge_sources(snapshot.sources, dest_session, counts)
    dataset_id_map = _merge_datasets(snapshot.datasets, dest_session, source_id_map, counts)
    entity_id_map = _merge_entities(snapshot.entities, dest_session, counts)
    source_record_id_map = _merge_source_records(
        snapshot.source_records,
        dest_session,
        source_id_map,
        dataset_id_map,
        counts,
    )
    evidence_id_map = _merge_evidences(
        snapshot.evidences,
        dest_session,
        source_id_map,
        dataset_id_map,
        source_record_id_map,
        counts,
    )
    claim_id_map = _merge_claims(
        snapshot.claims,
        dest_session,
        entity_id_map,
        source_record_id_map,
        evidence_id_map,
        counts,
    )
    _merge_relationships(
        snapshot.relationships,
        dest_session,
        entity_id_map,
        claim_id_map,
        counts,
    )

    return counts.freeze()


def render_merge_snapshot_report(snapshot: MergeSnapshot) -> str:
    return "\n".join(
        [
            "merge_snapshot:",
            f"sources={len(snapshot.sources)}",
            f"datasets={len(snapshot.datasets)}",
            f"entities={len(snapshot.entities)}",
            f"source_records={len(snapshot.source_records)}",
            f"evidences={len(snapshot.evidences)}",
            f"claims={len(snapshot.claims)}",
            f"relationships={len(snapshot.relationships)}",
        ]
    )


def _merge_sources(
    source_rows: tuple[Source, ...],
    dest_session: Session,
    counts: _MutableMergeCounts,
) -> dict[UUID, UUID]:
    existing = {row.url: row for row in dest_session.scalars(select(Source)).all()}
    mapping: dict[UUID, UUID] = {}
    for row in source_rows:
        found = existing.get(row.url)
        if found is not None:
            mapping[row.id] = found.id
            counts.skipped_duplicates += 1
            continue
        dest_session.add(
            Source(
                id=row.id,
                name=row.name,
                publisher=row.publisher,
                url=row.url,
                license=row.license,
                retrieved_at=row.retrieved_at,
                source_metadata=row.source_metadata,
            )
        )
        dest_session.flush()
        mapping[row.id] = row.id
        existing[row.url] = row
    return mapping


def _merge_datasets(
    dataset_rows: tuple[Dataset, ...],
    dest_session: Session,
    source_id_map: dict[UUID, UUID],
    counts: _MutableMergeCounts,
) -> dict[UUID, UUID]:
    existing = {(row.source_id, row.name, row.version): row for row in dest_session.scalars(select(Dataset)).all()}
    mapping: dict[UUID, UUID] = {}
    for row in dataset_rows:
        source_id = source_id_map[row.source_id]
        key = (source_id, row.name, row.version)
        found = existing.get(key)
        if found is not None:
            mapping[row.id] = found.id
            counts.skipped_duplicates += 1
            continue
        dest_session.add(
            Dataset(
                id=row.id,
                source_id=source_id,
                name=row.name,
                description=row.description,
                version=row.version,
                dataset_url=row.dataset_url,
                content_hash=row.content_hash,
                loaded_at=row.loaded_at,
                dataset_metadata=row.dataset_metadata,
            )
        )
        dest_session.flush()
        mapping[row.id] = row.id
        existing[key] = row
    return mapping


def _merge_entities(
    entity_rows: tuple[Entity, ...],
    dest_session: Session,
    counts: _MutableMergeCounts,
) -> dict[UUID, UUID]:
    existing = {
        (row.entity_type, row.external_id): row
        for row in dest_session.scalars(select(Entity)).all()
        if row.external_id is not None
    }
    mapping: dict[UUID, UUID] = {}
    for row in entity_rows:
        if row.external_id is None:
            dest_session.add(
                Entity(
                    id=row.id,
                    entity_type=row.entity_type,
                    name=row.name,
                    description=row.description,
                    external_id=row.external_id,
                    normalized_key=row.normalized_key,
                    status=row.status,
                    entity_metadata=row.entity_metadata,
                )
            )
            dest_session.flush()
            mapping[row.id] = row.id
            counts.inserted_entities += 1
            continue

        key = (row.entity_type, row.external_id)
        found = existing.get(key)
        if found is not None:
            mapping[row.id] = found.id
            counts.skipped_duplicates += 1
            continue
        dest_session.add(
            Entity(
                id=row.id,
                entity_type=row.entity_type,
                name=row.name,
                description=row.description,
                external_id=row.external_id,
                normalized_key=row.normalized_key,
                status=row.status,
                entity_metadata=row.entity_metadata,
            )
        )
        dest_session.flush()
        mapping[row.id] = row.id
        counts.inserted_entities += 1
        existing[key] = row
    return mapping


def _merge_source_records(
    source_record_rows: tuple[SourceRecord, ...],
    dest_session: Session,
    source_id_map: dict[UUID, UUID],
    dataset_id_map: dict[UUID, UUID],
    counts: _MutableMergeCounts,
) -> dict[UUID, UUID]:
    existing = {
        (row.source_id, row.dataset_id, row.external_id, row.record_type): row
        for row in dest_session.scalars(select(SourceRecord)).all()
    }
    mapping: dict[UUID, UUID] = {}
    for row in source_record_rows:
        source_id = source_id_map[row.source_id]
        dataset_id = dataset_id_map[row.dataset_id]
        key = (source_id, dataset_id, row.external_id, row.record_type)
        found = existing.get(key)
        if found is not None:
            mapping[row.id] = found.id
            counts.skipped_duplicates += 1
            continue
        dest_session.add(
            SourceRecord(
                id=row.id,
                source_id=source_id,
                dataset_id=dataset_id,
                external_id=row.external_id,
                record_type=row.record_type,
                payload_hash=row.payload_hash,
                raw_payload=row.raw_payload,
                retrieved_at=row.retrieved_at,
                processed_at=row.processed_at,
                status=row.status,
                error_log=row.error_log,
            )
        )
        dest_session.flush()
        mapping[row.id] = row.id
        counts.inserted_source_records += 1
        existing[key] = row
    return mapping


def _merge_evidences(
    evidence_rows: tuple[Evidence, ...],
    dest_session: Session,
    source_id_map: dict[UUID, UUID],
    dataset_id_map: dict[UUID, UUID],
    source_record_id_map: dict[UUID, UUID],
    counts: _MutableMergeCounts,
) -> dict[UUID, UUID]:
    existing = {
        _evidence_key(row.source_record_id, row.url, row.claim_id, row.title): row
        for row in dest_session.scalars(select(Evidence)).all()
    }
    mapping: dict[UUID, UUID] = {}
    for row in evidence_rows:
        source_record_id = source_record_id_map.get(row.source_record_id) if row.source_record_id is not None else None
        dataset_id = dataset_id_map[row.dataset_id] if row.dataset_id is not None else None
        source_id = source_id_map[row.source_id]
        key = _evidence_key(source_record_id, row.url, row.claim_id, row.title)
        found = existing.get(key)
        if found is not None:
            mapping[row.id] = found.id
            counts.skipped_duplicates += 1
            continue
        dest_session.add(
            Evidence(
                id=row.id,
                source_id=source_id,
                dataset_id=dataset_id,
                source_record_id=source_record_id,
                claim_id=None,
                title=row.title,
                url=row.url,
                published_at=row.published_at,
                excerpt=row.excerpt,
                evidence_metadata=row.evidence_metadata,
            )
        )
        dest_session.flush()
        mapping[row.id] = row.id
        counts.inserted_evidences += 1
        existing[key] = row
    return mapping


def _merge_claims(
    claim_rows: tuple[Claim, ...],
    dest_session: Session,
    entity_id_map: dict[UUID, UUID],
    source_record_id_map: dict[UUID, UUID],
    evidence_id_map: dict[UUID, UUID],
    counts: _MutableMergeCounts,
) -> dict[UUID, UUID]:
    existing = {
        _claim_key(
            row.subject_entity_id,
            row.predicate,
            row.object_entity_id,
            row.object_value,
            row.source_record_id,
        ): row
        for row in dest_session.scalars(select(Claim)).all()
    }
    mapping: dict[UUID, UUID] = {}
    for row in claim_rows:
        subject_id = entity_id_map[row.subject_entity_id]
        object_id = entity_id_map[row.object_entity_id] if row.object_entity_id is not None else None
        source_record_id = source_record_id_map[row.source_record_id]
        evidence_id = evidence_id_map[row.evidence_id]
        key = _claim_key(subject_id, row.predicate, object_id, row.object_value, source_record_id)
        found = existing.get(key)
        if found is not None:
            mapping[row.id] = found.id
            counts.skipped_duplicates += 1
            _link_evidence_if_missing(dest_session, evidence_id, found.id)
            continue
        claim = Claim(
            id=row.id,
            subject_entity_id=subject_id,
            predicate=row.predicate,
            object_entity_id=object_id,
            object_value=row.object_value,
            source_record_id=source_record_id,
            evidence_id=evidence_id,
            valid_from=row.valid_from,
            valid_to=row.valid_to,
            confidence=row.confidence,
            status=row.status,
        )
        dest_session.add(claim)
        dest_session.flush()
        mapping[row.id] = row.id
        counts.inserted_claims += 1
        _link_evidence_if_missing(dest_session, evidence_id, claim.id)
        existing[key] = claim
    return mapping


def _merge_relationships(
    relationship_rows: tuple[RelationshipPublic, ...],
    dest_session: Session,
    entity_id_map: dict[UUID, UUID],
    claim_id_map: dict[UUID, UUID],
    counts: _MutableMergeCounts,
) -> dict[UUID, UUID]:
    existing = {row.claim_id: row for row in dest_session.scalars(select(RelationshipPublic)).all()}
    mapping: dict[UUID, UUID] = {}
    for row in relationship_rows:
        source_entity_id = entity_id_map[row.source_entity_id]
        target_entity_id = entity_id_map[row.target_entity_id]
        claim_id = claim_id_map[row.claim_id]
        found = existing.get(claim_id)
        if found is not None:
            mapping[row.id] = found.id
            counts.skipped_duplicates += 1
            continue
        dest_session.add(
            RelationshipPublic(
                id=row.id,
                source_entity_id=source_entity_id,
                target_entity_id=target_entity_id,
                relationship_type=row.relationship_type,
                claim_id=claim_id,
                published_at=row.published_at,
                status=row.status,
                relationship_metadata=row.relationship_metadata,
            )
        )
        dest_session.flush()
        mapping[row.id] = row.id
        counts.inserted_relationships += 1
        existing[claim_id] = row
    return mapping


def _link_evidence_if_missing(dest_session: Session, evidence_id: UUID, claim_id: UUID) -> None:
    evidence = dest_session.get(Evidence, evidence_id)
    if evidence is not None and evidence.claim_id is None:
        evidence.claim_id = claim_id


def _evidence_key(
    source_record_id: UUID | None,
    url: str,
    claim_id: UUID | None,
    title: str,
) -> tuple[Any, ...]:
    if source_record_id is not None:
        return ("source_record", source_record_id, url)
    if claim_id is not None:
        return ("claim", claim_id, title, url)
    return ("fallback", title, url)


def _claim_key(
    subject_entity_id: UUID,
    predicate: str,
    object_entity_id: UUID | None,
    object_value: Any,
    source_record_id: UUID,
) -> tuple[Any, ...]:
    return (
        source_record_id,
        subject_entity_id,
        predicate,
        object_entity_id,
        _json_key(object_value),
    )


def _json_key(value: Any) -> str | None:
    json_value = GraphLoader._json_value(value)
    if json_value is None:
        return None
    return json.dumps(json_value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))

