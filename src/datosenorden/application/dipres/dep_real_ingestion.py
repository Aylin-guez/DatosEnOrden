"""One approved DIPRES slice and its non-causal REAL-expedient revision."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from datosenorden.adapters.dipres.ingestion import DEP_EXTERNAL_ID, DIPRES_RECORD_TYPE, build_dep_real_batch
from datosenorden.adapters.dipres.models import ResourceDefinition
from datosenorden.adapters.dipres.parser import parse_budget_csv
from datosenorden.application.provenance.models import ProvenanceClass
from datosenorden.application.real_expedient.eligibility import ProvenanceReferenceEligibility
from datosenorden.application.real_expedient.models import EpistemicClass, ExpedientReferences, ExpedientSpecification, ExpedientStatus, NarrativeStatement
from datosenorden.application.real_expedient.service import ExpedientProvisioningService
from datosenorden.etl.core.contracts import EntityRecord, EntityType
from datosenorden.etl.loaders.graph_loader import GraphLoader
from datosenorden.infrastructure.real_expedient.repository import PostgresExpedientRepository
from datosenorden.models import Claim, Entity, Evidence, RelationshipPublic, Source, SourceRecord


TARGET_EXPEDIENT_ID = "EXP-REAL-CHILECOMPRA-1002584-197-CM26"
EXPECTED_RESOURCE_SHA256 = "d5ff03c5c950656751b057e344142b7eb6e29b7b6a1876fe415c380e560d82ba"
RESOURCE = ResourceDefinition("https://www.dipres.gob.cl/597/w3-multipropertyvalues-25910-37782.html", "https://www.dipres.gob.cl/597/articles-421187_doc_csv.csv?ts=1785519425", "Segundo Trimestre 2026")


class DipresRealIngestionConflictError(RuntimeError):
    pass


@dataclass(frozen=True)
class DipresRealIngestionResult:
    graph_loaded: bool
    expedient_version: int
    expedient_fingerprint: str


def ingest_dep_second_quarter_2026(session: Session, staged_csv: Path) -> DipresRealIngestionResult:
    """Load the certified CSV once, then append/reopen its deterministic v2."""
    parsed = parse_budget_csv(_acquisition_from_staged_csv(staged_csv))
    if parsed.acquisition.sha256 != EXPECTED_RESOURCE_SHA256:
        raise DipresRealIngestionConflictError("DIPRES resource hash differs from the certified slice")
    organization = session.scalar(select(Entity).where(Entity.entity_type == EntityType.PUBLIC_ORGANIZATION.value, Entity.external_id == DEP_EXTERNAL_ID))
    if organization is None:
        raise DipresRealIngestionConflictError("certified ChileCompra organization is unavailable")
    organization_record = EntityRecord(EntityType.PUBLIC_ORGANIZATION, organization.name, organization.external_id, organization.description, organization.normalized_key, organization.status, dict(organization.entity_metadata or {}))
    batch = build_dep_real_batch(parsed, organization_record)
    source_payload = batch.source_records[0]
    existing_record = session.scalar(select(SourceRecord).where(SourceRecord.record_type == DIPRES_RECORD_TYPE, SourceRecord.external_id == source_payload.external_id))
    graph_loaded = False
    if existing_record is None:
        GraphLoader(session).load(batch)
        graph_loaded = True
    elif existing_record.payload_hash != source_payload.payload_hash:
        raise DipresRealIngestionConflictError("DIPRES slice exists with incompatible content")
    service = ExpedientProvisioningService(PostgresExpedientRepository(session), ProvenanceReferenceEligibility(session))
    current = service.get(TARGET_EXPEDIENT_ID)
    if current is None or current.specification.provenance_class is not ProvenanceClass.REAL:
        raise DipresRealIngestionConflictError("target REAL expedient is unavailable")
    if current.specification.version == 2:
        return DipresRealIngestionResult(graph_loaded, current.specification.version, current.content_fingerprint)
    specification = _v2_specification(session)
    if current.specification.version == 1:
        stored = service.revise(specification, expected_current_version=1)
    else:
        raise DipresRealIngestionConflictError("target expedient has incompatible current content")
    return DipresRealIngestionResult(graph_loaded, stored.specification.version, stored.content_fingerprint)


def _acquisition_from_staged_csv(staged_csv: Path):
    from datetime import UTC, datetime
    from hashlib import sha256
    from datosenorden.adapters.dipres.models import AcquiredResource

    return AcquiredResource(RESOURCE, datetime.now(UTC), sha256(staged_csv.read_bytes()).hexdigest(), staged_csv.stat().st_size, "text/csv", staged_csv, True)


def _v2_specification(session: Session) -> ExpedientSpecification:
    v1 = PostgresExpedientRepository(session).get(TARGET_EXPEDIENT_ID)
    if v1 is None or v1.specification.version != 1:
        raise DipresRealIngestionConflictError("target expedient is not at certified v1")
    record = session.scalar(select(SourceRecord).where(SourceRecord.record_type == DIPRES_RECORD_TYPE))
    evidence = session.scalar(select(Evidence).where(Evidence.source_record_id == record.id)) if record else None
    source = session.scalar(select(Source).where(Source.url == "https://www.dipres.gob.cl/"))
    budget = session.scalar(select(Entity).where(Entity.external_id == "dipres:budget:2026:09:17:01:segundo-trimestre:pesos"))
    claims = session.scalars(select(Claim).where(Claim.source_record_id == record.id).order_by(Claim.predicate)).all() if record else []
    relationship = session.scalar(select(RelationshipPublic).join(Claim).where(Claim.source_record_id == record.id)) if record else None
    if not all((record, evidence, source, budget, relationship)) or len(claims) != 4:
        raise DipresRealIngestionConflictError("DIPRES graph did not persist the expected references")
    prior = v1.specification
    references = ExpedientReferences(prior.references.claim_ids + tuple(str(item.id) for item in claims), prior.references.evidence_ids + (str(evidence.id),), prior.references.relationship_ids + (str(relationship.id),), prior.references.entity_ids + (str(budget.id),), source_ids=prior.references.source_ids + (str(source.id),))
    ids = {item.predicate: str(item.id) for item in claims}
    statements = prior.statements + (
        NarrativeStatement("fact-dipres-institution-budget", "budget_context", "DIPRES publica información presupuestaria para la Dirección de Educación Pública, identificada como Partida 09, Capítulo 17 y Programa 01.", EpistemicClass.FACT, (ids["BUDGET_INFORMATION_FOR_ORGANIZATION"],), (str(evidence.id),)),
        NarrativeStatement("fact-dipres-published-columns", "budget_context", "El recurso DIPRES de Ejecución Total 2026, nivel Programa, Segundo Trimestre, publica valores en las columnas presupuesto_inicial, presupuesto_vigente y ejecucion_acumulada_a_segundo_trimestre para la clasificación 09/17/01.", EpistemicClass.FACT, tuple(ids[key] for key in sorted(ids) if key != "BUDGET_INFORMATION_FOR_ORGANIZATION"), (str(evidence.id),)),
        NarrativeStatement("unknown-no-purchase-budget-attribution", "what_is_missing", "La información disponible no permite atribuir esta orden de compra a una línea presupuestaria específica.", EpistemicClass.UNKNOWN),
    )
    return ExpedientSpecification(prior.expedient_id, prior.title, prior.question, prior.summary, ProvenanceClass.REAL, ExpedientStatus.PUBLISHED, 2, references, statements)
