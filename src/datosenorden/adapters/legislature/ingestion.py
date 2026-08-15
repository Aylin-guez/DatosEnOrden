"""Map verified normalized legislative observations to existing graph contracts."""

from __future__ import annotations

from datosenorden.etl.core.contracts import ClaimRecord, DatasetRecord, EntityRecord, EntityType, EvidenceRecord, GraphBatch, SourceInfo, SourceRecordPayload, WorkflowStatus
from datosenorden.etl.core.hash import stable_json_hash
from datosenorden.etl.core.text import normalized_key

from .normalization import LegislativeEvent, NormalizedLegislativeMatter, SourceObservation


SOURCE_NAMES = {"senado": "Senado de Chile", "camara": "Camara de Diputadas y Diputados"}
SOURCE_URLS = {"senado": "https://www.senado.cl/", "camara": "https://www.camara.cl/"}


def build_observation_batch(matter: NormalizedLegislativeMatter, observation: SourceObservation, events: tuple[LegislativeEvent, ...]) -> GraphBatch:
    if observation.source_id not in SOURCE_NAMES:
        raise ValueError("unsupported official legislative source")
    entity = EntityRecord(EntityType.PUBLIC_PROJECT, matter.matter.title, matter.matter.canonical_identifier, normalized_key=normalized_key(matter.matter.bulletin_number), metadata={"bulletin_number": matter.matter.bulletin_number, "jurisdiction": matter.matter.jurisdiction, "matter_type": matter.matter.matter_type})
    payload = {"matter": {"bulletin_number": matter.matter.bulletin_number, "canonical_identifier": matter.matter.canonical_identifier, "title": matter.matter.title, "origin_chamber": matter.matter.origin_chamber}, "observation": {"resource_type": observation.resource_type.value, "resource_identity": observation.resource_identity, "matter_status": observation.matter_status.value, "current_stage": observation.current_stage, "manifest": {"url": observation.manifest.official_url, "sha256": observation.manifest.sha256, "content_type": observation.manifest.content_type, "byte_count": observation.manifest.byte_count, "retrieved_at": observation.manifest.retrieved_at.isoformat(), "http_status": observation.manifest.http_status}}}
    record = SourceRecordPayload(f"{observation.source_id}:{observation.resource_identity}", "legislature:matter_observation", stable_json_hash(payload), payload, observation.manifest.retrieved_at, status=WorkflowStatus.VALIDATED)
    evidence = EvidenceRecord(record, SOURCE_NAMES[observation.source_id], observation.title, observation.manifest.official_url, published_at=observation.manifest.retrieved_at.date(), excerpt=f"Observacion oficial del boletin {matter.matter.bulletin_number}.", metadata={"artifact_sha256": observation.manifest.sha256, "resource_identity": observation.resource_identity, "resource_type": observation.resource_type.value})
    claims = [ClaimRecord(entity, "LEGISLATIVE_MATTER_HAS_BULLETIN", record, evidence, object_value={"bulletin_number": matter.matter.bulletin_number, "canonical_identifier": matter.matter.canonical_identifier}, status=WorkflowStatus.VALIDATED, metadata={"source_observation": observation.source_id})]
    for event in events:
        claims.append(ClaimRecord(entity, "LEGISLATIVE_MATTER_HAS_VERIFIED_EVENT", record, evidence, object_value={"event_type": event.event_type.value, "event_date": event.event_date.isoformat() if event.event_date else None, "source": event.source_id, "source_resource_id": event.source_resource_id}, valid_from=event.event_date, status=WorkflowStatus.VALIDATED, metadata={"source_observation": observation.source_id}))
    source = SourceInfo(SOURCE_NAMES[observation.source_id], SOURCE_NAMES[observation.source_id], SOURCE_URLS[observation.source_id], license="Official public legislative resource", retrieved_at=observation.manifest.retrieved_at, metadata={"source_id": observation.source_id, "provenance": "REAL"})
    dataset_name = f"{observation.source_id}-legislative-matter"
    dataset = DatasetRecord(SOURCE_NAMES[observation.source_id], dataset_name, "Verified official legislative matter observations.", matter.matter.bulletin_number, observation.manifest.official_url, observation.manifest.sha256, observation.manifest.retrieved_at, metadata={"bulletin_number": matter.matter.bulletin_number, "provenance": "REAL"})
    return GraphBatch(source, dataset, (record,), (entity,), (evidence,), tuple(claims), (), 1)
