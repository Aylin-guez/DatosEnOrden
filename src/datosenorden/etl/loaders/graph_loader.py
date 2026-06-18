from datetime import datetime, timezone
from decimal import Decimal
import json
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from datosenorden.etl.core.contracts import (
    ClaimRecord,
    DatasetRecord,
    EntityRecord,
    EvidenceRecord,
    GraphBatch,
    PublicRelationshipRecord,
    SourceInfo,
    SourceRecordPayload,
)
from datosenorden.etl.core.errors import LoadError
from datosenorden.models import (
    Claim,
    Dataset,
    Entity,
    Evidence,
    ImportJob,
    RelationshipPublic,
    Source,
    SourceRecord,
)


class GraphLoader:
    def __init__(self, session: Session) -> None:
        self._session = session

    def load(self, batch: GraphBatch, dry_run: bool = False) -> ImportJob | None:
        try:
            source = self._upsert_source(batch.source)
            dataset = self._upsert_dataset(batch.dataset, source.id)
            import_job = self._create_import_job(dataset.id, batch, dry_run)

            source_record_cache = {
                self._source_record_key(record): self._upsert_source_record(record, source.id, dataset.id)
                for record in batch.source_records
            }
            entity_cache = {
                self._entity_key(record): self._upsert_entity(record)
                for record in batch.entities
            }
            evidence_cache = {
                self._evidence_key(record): self._upsert_evidence(
                    record,
                    source.id,
                    dataset.id,
                    source_record_cache,
                )
                for record in batch.evidence
            }
            claim_cache = {
                self._claim_key(record): self._upsert_claim(
                    record,
                    entity_cache,
                    source_record_cache,
                    evidence_cache,
                )
                for record in batch.claims
            }

            for record in batch.public_relationships:
                self._upsert_public_relationship(record, entity_cache, claim_cache)

            import_job.finished_at = datetime.now(timezone.utc)
            import_job.status = "succeeded" if not batch.errors else "failed"
            import_job.records_processed = batch.raw_count - batch.rejected_count

            if dry_run:
                self._session.rollback()
                return None

            self._session.commit()
            return import_job
        except Exception as exc:
            self._session.rollback()
            raise LoadError(str(exc)) from exc

    def _create_import_job(
        self,
        dataset_id: UUID,
        batch: GraphBatch,
        dry_run: bool,
    ) -> ImportJob:
        import_job = ImportJob(
            dataset_id=dataset_id,
            started_at=datetime.now(timezone.utc),
            status="running",
            records_processed=0,
            error_log="\n".join(batch.errors) if batch.errors else None,
            job_metadata={
                "raw_count": batch.raw_count,
                "rejected_count": batch.rejected_count,
                "dry_run": dry_run,
                "schema_phase": "2.5",
            },
        )
        self._session.add(import_job)
        self._session.flush()
        return import_job

    def _upsert_source(self, record: SourceInfo) -> Source:
        source = self._session.scalar(select(Source).where(Source.url == record.url))
        if source is None:
            source = Source(id=None, name=record.name, url=record.url)  # type: ignore[arg-type]
            self._session.add(source)
        source.name = record.name
        source.publisher = record.publisher
        source.license = record.license
        source.retrieved_at = record.retrieved_at
        source.source_metadata = record.metadata
        self._session.flush()
        return source

    def _upsert_dataset(self, record: DatasetRecord, source_id: UUID) -> Dataset:
        dataset = self._session.scalar(
            select(Dataset).where(
                Dataset.source_id == source_id,
                Dataset.name == record.name,
                Dataset.version == record.version,
            )
        )
        if dataset is None:
            dataset = Dataset(id=None, source_id=source_id, name=record.name, version=record.version)  # type: ignore[arg-type]
            self._session.add(dataset)
        dataset.description = record.description
        dataset.dataset_url = record.dataset_url
        dataset.content_hash = record.content_hash
        dataset.loaded_at = record.loaded_at
        dataset.dataset_metadata = record.metadata
        self._session.flush()
        return dataset

    def _upsert_source_record(
        self,
        record: SourceRecordPayload,
        source_id: UUID,
        dataset_id: UUID,
    ) -> SourceRecord:
        source_record = self._session.scalar(
            select(SourceRecord).where(
                SourceRecord.dataset_id == dataset_id,
                SourceRecord.record_type == record.record_type,
                SourceRecord.external_id == record.external_id,
            )
        )
        if source_record is None:
            source_record = SourceRecord(
                id=None,  # type: ignore[arg-type]
                source_id=source_id,
                dataset_id=dataset_id,
                external_id=record.external_id,
                record_type=record.record_type,
                payload_hash=record.payload_hash,
                raw_payload=record.raw_payload,
                retrieved_at=record.retrieved_at,
                status=record.status.value,
            )
            self._session.add(source_record)
        source_record.payload_hash = record.payload_hash
        source_record.raw_payload = record.raw_payload
        source_record.retrieved_at = record.retrieved_at
        source_record.processed_at = record.processed_at
        source_record.status = record.status.value
        source_record.error_log = record.error_log
        self._session.flush()
        return source_record

    def _upsert_entity(self, record: EntityRecord) -> Entity:
        entity = self._session.scalar(
            select(Entity).where(
                Entity.entity_type == record.entity_type.value,
                Entity.external_id == record.external_id,
            )
        )
        if entity is None:
            entity = Entity(
                id=None,  # type: ignore[arg-type]
                entity_type=record.entity_type.value,
                external_id=record.external_id,
                name=record.name,
            )
            self._session.add(entity)
        entity.name = record.name
        entity.description = record.description
        entity.normalized_key = record.normalized_key
        entity.status = record.status
        entity.entity_metadata = record.metadata
        self._session.flush()
        return entity

    def _upsert_evidence(
        self,
        record: EvidenceRecord,
        source_id: UUID,
        dataset_id: UUID,
        source_record_cache: dict[tuple[str, str], SourceRecord],
    ) -> Evidence:
        source_record = source_record_cache[self._source_record_key(record.source_record)]
        evidence = self._session.scalar(
            select(Evidence).where(
                Evidence.source_record_id == source_record.id,
                Evidence.url == record.url,
            )
        )
        if evidence is None:
            evidence = Evidence(
                id=None,  # type: ignore[arg-type]
                source_id=source_id,
                dataset_id=dataset_id,
                source_record_id=source_record.id,
                title=record.title,
                url=record.url,
            )
            self._session.add(evidence)
        evidence.title = record.title
        evidence.published_at = record.published_at
        evidence.excerpt = record.excerpt
        evidence.evidence_metadata = record.metadata
        self._session.flush()
        return evidence

    def _upsert_claim(
        self,
        record: ClaimRecord,
        entity_cache: dict[tuple[str, str], Entity],
        source_record_cache: dict[tuple[str, str], SourceRecord],
        evidence_cache: dict[tuple[str, str, str], Evidence],
    ) -> Claim:
        subject = entity_cache[self._entity_key(record.subject_entity)]
        object_entity = (
            entity_cache[self._entity_key(record.object_entity)] if record.object_entity is not None else None
        )
        source_record = source_record_cache[self._source_record_key(record.source_record)]
        evidence = evidence_cache[self._evidence_key(record.evidence)]
        object_value = self._json_value(record.object_value)

        claim = self._find_claim(record, subject.id, object_entity.id if object_entity else None, source_record.id)
        if claim is None:
            claim = Claim(
                id=None,  # type: ignore[arg-type]
                subject_entity_id=subject.id,
                predicate=record.predicate,
                source_record_id=source_record.id,
                evidence_id=evidence.id,
                confidence=Decimal(str(record.confidence)),
                status=record.status.value,
            )
            self._session.add(claim)
        claim.object_entity_id = object_entity.id if object_entity else None
        claim.object_value = object_value
        claim.evidence_id = evidence.id
        claim.valid_from = record.valid_from
        claim.valid_to = record.valid_to
        claim.confidence = Decimal(str(record.confidence))
        claim.status = record.status.value
        self._session.flush()
        evidence.claim_id = claim.id
        self._session.flush()
        return claim

    def _find_claim(
        self,
        record: ClaimRecord,
        subject_entity_id: UUID,
        object_entity_id: UUID | None,
        source_record_id: UUID,
    ) -> Claim | None:
        statement = select(Claim).where(
            Claim.source_record_id == source_record_id,
            Claim.subject_entity_id == subject_entity_id,
            Claim.predicate == record.predicate,
            Claim.object_entity_id.is_(object_entity_id)
            if object_entity_id is None
            else Claim.object_entity_id == object_entity_id,
        )
        object_value = self._json_value(record.object_value)
        if object_value is None:
            statement = statement.where(Claim.object_value.is_(None))
        else:
            statement = statement.where(Claim.object_value == object_value)
        return self._session.scalar(statement)

    def _upsert_public_relationship(
        self,
        record: PublicRelationshipRecord,
        entity_cache: dict[tuple[str, str], Entity],
        claim_cache: dict[tuple, Claim],
    ) -> RelationshipPublic:
        source = entity_cache[self._entity_key(record.source_entity)]
        target = entity_cache[self._entity_key(record.target_entity)]
        claim = claim_cache[self._claim_key(record.claim)]
        relationship = self._session.scalar(
            select(RelationshipPublic).where(RelationshipPublic.claim_id == claim.id)
        )
        if relationship is None:
            relationship = RelationshipPublic(
                id=None,  # type: ignore[arg-type]
                source_entity_id=source.id,
                target_entity_id=target.id,
                relationship_type=record.relationship_type.value,
                claim_id=claim.id,
                status=record.status.value,
            )
            self._session.add(relationship)
        relationship.published_at = record.published_at
        relationship.status = record.status.value
        relationship.relationship_metadata = record.metadata
        self._session.flush()
        return relationship

    @staticmethod
    def _entity_key(record: EntityRecord) -> tuple[str, str]:
        return (record.entity_type.value, record.external_id)

    @staticmethod
    def _source_record_key(record: SourceRecordPayload) -> tuple[str, str]:
        return (record.record_type, record.external_id)

    @staticmethod
    def _evidence_key(record: EvidenceRecord) -> tuple[str, str, str]:
        return (record.source_record.record_type, record.source_record.external_id, record.url)

    @staticmethod
    def _claim_key(record: ClaimRecord) -> tuple:
        object_entity_key = (
            GraphLoader._entity_key(record.object_entity) if record.object_entity is not None else None
        )
        return (
            GraphLoader._entity_key(record.subject_entity),
            record.predicate,
            object_entity_key,
            GraphLoader._claim_object_key(record.object_value),
            GraphLoader._source_record_key(record.source_record),
            GraphLoader._evidence_key(record.evidence),
        )

    @staticmethod
    def _json_value(value: Any) -> Any:
        if value is None or isinstance(value, dict):
            return value
        return {"value": value}

    @staticmethod
    def _claim_object_key(value: Any) -> str | None:
        json_value = GraphLoader._json_value(value)
        if json_value is None:
            return None
        return json.dumps(json_value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
