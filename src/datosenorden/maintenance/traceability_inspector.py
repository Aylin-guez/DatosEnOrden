from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from datosenorden.models import Claim, Evidence, RelationshipPublic, SourceRecord


@dataclass(frozen=True)
class TraceEntitySummary:
    entity_type: str
    name: str
    external_id: str | None


@dataclass(frozen=True)
class TraceEvidenceSummary:
    id: str
    title: str
    url: str
    published_at: date | None
    claim_id: str | None


@dataclass(frozen=True)
class TraceRelationshipSummary:
    id: str
    relationship_type: str
    status: str
    source_entity: TraceEntitySummary
    target_entity: TraceEntitySummary
    claim_id: str


@dataclass(frozen=True)
class TraceClaimSummary:
    id: str
    predicate: str
    status: str
    subject_entity: TraceEntitySummary
    object_entity: TraceEntitySummary | None
    valid_from: date | None
    evidences: tuple[TraceEvidenceSummary, ...]
    relationship_public: tuple[TraceRelationshipSummary, ...]


@dataclass(frozen=True)
class TraceSourceRecordSummary:
    id: str
    status: str
    record_type: str
    external_id: str
    claims: tuple[TraceClaimSummary, ...]


def inspect_traceability_chain(session: Session, external_id: str) -> tuple[TraceSourceRecordSummary, ...]:
    source_records = session.scalars(
        select(SourceRecord)
        .where(SourceRecord.external_id == external_id)
        .order_by(SourceRecord.created_at, SourceRecord.id)
    ).all()

    traces: list[TraceSourceRecordSummary] = []
    for source_record in source_records:
        claims = session.scalars(
            select(Claim)
            .where(Claim.source_record_id == source_record.id)
            .options(joinedload(Claim.subject_entity), joinedload(Claim.object_entity))
            .order_by(Claim.created_at, Claim.id)
        ).all()
        claim_ids = [claim.id for claim in claims]

        evidences_by_claim: dict[str, list[TraceEvidenceSummary]] = defaultdict(list)
        relationships_by_claim: dict[str, list[TraceRelationshipSummary]] = defaultdict(list)

        if claim_ids:
            evidence_rows = session.scalars(
                select(Evidence)
                .where(Evidence.claim_id.in_(claim_ids))
                .order_by(Evidence.created_at, Evidence.id)
            ).all()
            for evidence in evidence_rows:
                if evidence.claim_id is None:
                    continue
                evidences_by_claim[str(evidence.claim_id)].append(_summarize_evidence(evidence))

            relationship_rows = session.scalars(
                select(RelationshipPublic)
                .where(RelationshipPublic.claim_id.in_(claim_ids))
                .options(joinedload(RelationshipPublic.source_entity), joinedload(RelationshipPublic.target_entity))
                .order_by(RelationshipPublic.created_at, RelationshipPublic.id)
            ).all()
            for relationship in relationship_rows:
                relationships_by_claim[str(relationship.claim_id)].append(_summarize_relationship(relationship))

        trace_claims = []
        for claim in claims:
            claim_key = str(claim.id)
            trace_claims.append(
                TraceClaimSummary(
                    id=claim_key,
                    predicate=claim.predicate,
                    status=claim.status,
                    subject_entity=_summarize_entity(claim.subject_entity),
                    object_entity=_summarize_entity(claim.object_entity) if claim.object_entity is not None else None,
                    valid_from=claim.valid_from,
                    evidences=tuple(evidences_by_claim.get(claim_key, ())),
                    relationship_public=tuple(relationships_by_claim.get(claim_key, ())),
                )
            )

        traces.append(
            TraceSourceRecordSummary(
                id=str(source_record.id),
                status=source_record.status,
                record_type=source_record.record_type,
                external_id=source_record.external_id,
                claims=tuple(trace_claims),
            )
        )

    return tuple(traces)


def render_traceability_chain(traces: tuple[TraceSourceRecordSummary, ...], external_id: str) -> str:
    lines = [f"traceability_inspection: external_id={external_id} source_records={len(traces)}"]
    for index, source_record in enumerate(traces, start=1):
        lines.append("")
        lines.append(f"source_record[{index}]:")
        lines.append(f"  id={source_record.id}")
        lines.append(f"  status={source_record.status}")
        lines.append(f"  record_type={source_record.record_type}")
        lines.append(f"  external_id={source_record.external_id}")
        lines.append(f"  claims={len(source_record.claims)}")
        for claim_index, claim in enumerate(source_record.claims, start=1):
            lines.append(f"  claim[{claim_index}]:")
            lines.append(f"    id={claim.id}")
            lines.append(f"    predicate={claim.predicate}")
            lines.append(f"    status={claim.status}")
            lines.append(f"    valid_from={_format_date(claim.valid_from)}")
            lines.append(
                "    subject_entity="
                f"{claim.subject_entity.entity_type} | {claim.subject_entity.name}"
                f" | external_id={_format_optional(claim.subject_entity.external_id)}"
            )
            if claim.object_entity is not None:
                lines.append(
                    "    object_entity="
                    f"{claim.object_entity.entity_type} | {claim.object_entity.name}"
                    f" | external_id={_format_optional(claim.object_entity.external_id)}"
                )
            else:
                lines.append("    object_entity=None")

            lines.append(f"    evidences={len(claim.evidences)}")
            for evidence_index, evidence in enumerate(claim.evidences, start=1):
                lines.append(f"    evidence[{evidence_index}]:")
                lines.append(f"      id={evidence.id}")
                lines.append(f"      title={evidence.title}")
                lines.append(f"      url={evidence.url}")
                lines.append(f"      published_at={_format_date(evidence.published_at)}")
                lines.append(f"      claim_id={_format_optional(evidence.claim_id)}")

            lines.append(f"    relationship_public={len(claim.relationship_public)}")
            for relationship_index, relationship in enumerate(claim.relationship_public, start=1):
                lines.append(f"    relationship_public[{relationship_index}]:")
                lines.append(f"      id={relationship.id}")
                lines.append(f"      relationship_type={relationship.relationship_type}")
                lines.append(f"      status={relationship.status}")
                lines.append(f"      claim_id={relationship.claim_id}")
                lines.append(
                    "      source_entity="
                    f"{relationship.source_entity.entity_type} | {relationship.source_entity.name}"
                    f" | external_id={_format_optional(relationship.source_entity.external_id)}"
                )
                lines.append(
                    "      target_entity="
                    f"{relationship.target_entity.entity_type} | {relationship.target_entity.name}"
                    f" | external_id={_format_optional(relationship.target_entity.external_id)}"
                )
    return "\n".join(lines)


def _summarize_entity(entity) -> TraceEntitySummary:  # type: ignore[no-untyped-def]
    return TraceEntitySummary(
        entity_type=entity.entity_type,
        name=entity.name,
        external_id=entity.external_id,
    )


def _summarize_evidence(evidence) -> TraceEvidenceSummary:  # type: ignore[no-untyped-def]
    return TraceEvidenceSummary(
        id=str(evidence.id),
        title=evidence.title,
        url=evidence.url,
        published_at=evidence.published_at,
        claim_id=str(evidence.claim_id) if evidence.claim_id is not None else None,
    )


def _summarize_relationship(relationship) -> TraceRelationshipSummary:  # type: ignore[no-untyped-def]
    return TraceRelationshipSummary(
        id=str(relationship.id),
        relationship_type=relationship.relationship_type,
        status=relationship.status,
        source_entity=_summarize_entity(relationship.source_entity),
        target_entity=_summarize_entity(relationship.target_entity),
        claim_id=str(relationship.claim_id),
    )


def _format_date(value: date | None) -> str:
    return value.isoformat() if value is not None else "None"


def _format_optional(value: object | None) -> str:
    return "None" if value is None else str(value)
