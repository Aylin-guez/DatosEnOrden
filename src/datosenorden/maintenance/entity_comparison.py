from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

import datosenorden.datasets as datasets
from datosenorden.db.session import SessionLocal
from datosenorden.models import Claim, Dataset, Entity, Evidence, RelationshipPublic, SourceRecord

PROCUREMENT_MARKERS = (
    "PURCHASE_ORDER",
    "CONTRACT",
    "TENDER",
    "AWARDS_CONTRACT",
    "RECEIVES_CONTRACT",
)
LOBBY_MARKERS = ("LOBBY",)
TRANSPARENCY_MARKERS = (
    "PUBLIC_ROLE",
    "ROLE_BELONGS",
)
CONTRALORIA_MARKERS = (
    "CONTROL_REPORT",
    "OBSERVATION",
)
MUNICIPAL_MARKERS = (
    "MUNICIPALITY",
    "PROJECT",
    "SPENDING",
)
BUDGET_MARKERS = (
    "BUDGET",
)


@dataclass(frozen=True)
class _DatasetBucket:
    dataset: str
    claims: tuple[Claim, ...]
    relationships: tuple[RelationshipPublic, ...]
    evidence_ids: tuple[str, ...]
    source_record_ids: tuple[str, ...]
    predicate_counts: Counter[str]
    relationship_type_counts: Counter[str]


def build_entity_comparison(entity_id: str) -> dict[str, object]:
    with SessionLocal() as session:
        comparison = _build_entity_comparison(session, entity_id)
    return comparison


def _build_entity_comparison(session: Session, entity_id: str) -> dict[str, object]:
    entity = _load_entity(session, entity_id)
    if entity is None:
        return _empty_comparison()

    claim_rows = _load_entity_claim_rows(session, entity.id)
    relationship_rows = _load_entity_relationship_rows(session, entity.id)
    claim_ids = tuple(claim.id for claim, _ in claim_rows)
    evidence_rows = _load_entity_evidence_rows(session, claim_ids)

    buckets = _group_rows_by_dataset(claim_rows, relationship_rows, evidence_rows)
    ordered_buckets = tuple(sorted(buckets.values(), key=lambda item: item.dataset.lower()))

    datasets_present = [bucket.dataset for bucket in ordered_buckets]
    dataset_facts = [_bucket_to_fact(bucket) for bucket in ordered_buckets]
    total_claims = sum(len(bucket.claims) for bucket in ordered_buckets)
    total_relationships = sum(len(bucket.relationships) for bucket in ordered_buckets)
    total_evidence = len({evidence_id for bucket in ordered_buckets for evidence_id in bucket.evidence_ids})

    observations = _consistency_observations(datasets_present, ordered_buckets)
    coverage_summary = _coverage_summary(
        entity.name,
        datasets_present,
        total_claims=total_claims,
        total_relationships=total_relationships,
        total_evidence=total_evidence,
    )

    return {
        "entity_name": entity.name,
        "entity_type": entity.entity_type,
        "datasets_present": datasets_present,
        "dataset_facts": dataset_facts,
        "consistency_observations": observations,
        "coverage_summary": coverage_summary,
    }


def _empty_comparison() -> dict[str, object]:
    summary = "No public source records were found for this organization."
    return {
        "entity_name": "",
        "entity_type": "",
        "datasets_present": [],
        "dataset_facts": [],
        "consistency_observations": [summary],
        "coverage_summary": summary,
    }


def _load_entity(session: Session, entity_id: str) -> Entity | None:
    try:
        entity_uuid = UUID(entity_id)
    except ValueError:
        return None
    return session.get(Entity, entity_uuid)


def _load_entity_claim_rows(session: Session, entity_id: UUID) -> tuple[tuple[Claim, str], ...]:
    rows = session.execute(
        select(Claim, Dataset.name)
        .select_from(Claim)
        .join(SourceRecord, Claim.source_record_id == SourceRecord.id)
        .join(Dataset, SourceRecord.dataset_id == Dataset.id)
        .where(or_(Claim.subject_entity_id == entity_id, Claim.object_entity_id == entity_id))
        .order_by(Claim.created_at, Claim.id)
    ).all()
    return tuple((claim, str(dataset_name)) for claim, dataset_name in rows)


def _load_entity_relationship_rows(
    session: Session,
    entity_id: UUID,
) -> tuple[tuple[RelationshipPublic, str], ...]:
    rows = session.execute(
        select(RelationshipPublic, Dataset.name)
        .select_from(RelationshipPublic)
        .join(Claim, RelationshipPublic.claim_id == Claim.id)
        .join(SourceRecord, Claim.source_record_id == SourceRecord.id)
        .join(Dataset, SourceRecord.dataset_id == Dataset.id)
        .where(or_(RelationshipPublic.source_entity_id == entity_id, RelationshipPublic.target_entity_id == entity_id))
        .order_by(RelationshipPublic.created_at, RelationshipPublic.id)
    ).all()
    return tuple((relationship, str(dataset_name)) for relationship, dataset_name in rows)


def _load_entity_evidence_rows(session: Session, claim_ids: tuple[UUID, ...]) -> tuple[tuple[Evidence, str], ...]:
    if not claim_ids:
        return ()
    rows = session.execute(
        select(Evidence, Dataset.name)
        .select_from(Evidence)
        .join(Claim, Evidence.claim_id == Claim.id)
        .join(SourceRecord, Claim.source_record_id == SourceRecord.id)
        .join(Dataset, SourceRecord.dataset_id == Dataset.id)
        .where(Claim.id.in_(claim_ids))
        .order_by(Evidence.created_at, Evidence.id)
    ).all()
    return tuple((evidence, str(dataset_name)) for evidence, dataset_name in rows)


def _group_rows_by_dataset(
    claim_rows: tuple[tuple[Claim, str], ...],
    relationship_rows: tuple[tuple[RelationshipPublic, str], ...],
    evidence_rows: tuple[tuple[Evidence, str], ...],
) -> dict[str, _DatasetBucket]:
    buckets: dict[str, dict[str, object]] = {}
    for claim, dataset_name in claim_rows:
        dataset_label = _dataset_label(dataset_name)
        bucket = buckets.setdefault(dataset_label, _new_bucket(dataset_label))
        _append_claim(bucket, claim)
    for relationship, dataset_name in relationship_rows:
        dataset_label = _dataset_label(dataset_name)
        bucket = buckets.setdefault(dataset_label, _new_bucket(dataset_label))
        _append_relationship(bucket, relationship)
    for evidence, dataset_name in evidence_rows:
        dataset_label = _dataset_label(dataset_name)
        bucket = buckets.setdefault(dataset_label, _new_bucket(dataset_label))
        _append_evidence(bucket, evidence)
    return {dataset: _freeze_bucket(bucket) for dataset, bucket in buckets.items()}


def _new_bucket(dataset: str) -> dict[str, object]:
    return {
        "dataset": dataset,
        "claims": [],
        "relationships": [],
        "evidence_ids": set(),
        "source_record_ids": set(),
        "predicate_counts": Counter(),
        "relationship_type_counts": Counter(),
    }


def _append_claim(bucket: dict[str, object], claim: Claim) -> None:
    cast_claims = bucket["claims"]
    assert isinstance(cast_claims, list)
    cast_claims.append(claim)
    source_record_ids = bucket["source_record_ids"]
    assert isinstance(source_record_ids, set)
    source_record_ids.add(str(claim.source_record_id))
    predicate_counts = bucket["predicate_counts"]
    assert isinstance(predicate_counts, Counter)
    predicate_counts[claim.predicate] += 1


def _append_relationship(bucket: dict[str, object], relationship: RelationshipPublic) -> None:
    cast_relationships = bucket["relationships"]
    assert isinstance(cast_relationships, list)
    cast_relationships.append(relationship)
    relationship_type_counts = bucket["relationship_type_counts"]
    assert isinstance(relationship_type_counts, Counter)
    relationship_type_counts[relationship.relationship_type] += 1


def _append_evidence(bucket: dict[str, object], evidence: Evidence) -> None:
    evidence_ids = bucket["evidence_ids"]
    assert isinstance(evidence_ids, set)
    evidence_ids.add(str(evidence.id))


def _freeze_bucket(bucket: dict[str, object]) -> _DatasetBucket:
    claims = tuple(bucket["claims"])  # type: ignore[assignment]
    relationships = tuple(bucket["relationships"])  # type: ignore[assignment]
    evidence_ids = tuple(sorted(bucket["evidence_ids"]))  # type: ignore[arg-type]
    source_record_ids = tuple(sorted(bucket["source_record_ids"]))  # type: ignore[arg-type]
    predicate_counts = Counter(bucket["predicate_counts"])  # type: ignore[arg-type]
    relationship_type_counts = Counter(bucket["relationship_type_counts"])  # type: ignore[arg-type]
    return _DatasetBucket(
        dataset=str(bucket["dataset"]),
        claims=claims,
        relationships=relationships,
        evidence_ids=evidence_ids,
        source_record_ids=source_record_ids,
        predicate_counts=predicate_counts,
        relationship_type_counts=relationship_type_counts,
    )


def _bucket_to_fact(bucket: _DatasetBucket) -> dict[str, object]:
    facts = [
        _count_phrase(len(bucket.source_record_ids), "source record"),
        _count_phrase(len(bucket.claims), "claim"),
        _count_phrase(len(bucket.relationships), "public relationship"),
        _count_phrase(len(bucket.evidence_ids), "evidence item"),
    ]
    facts.extend(_activity_sentences(bucket))
    return {
        "dataset": bucket.dataset,
        "headline": f"{bucket.dataset} records",
        "facts": facts,
    }


def _activity_sentences(bucket: _DatasetBucket) -> list[str]:
    categories = _bucket_categories(bucket)
    sentences: list[str] = []
    if "procurement" in categories:
        sentences.append("Records describe procurement activity involving this organization.")
    if "lobby" in categories:
        sentences.append("Records describe registered meetings involving this organization.")
    if "transparency" in categories:
        sentences.append("Records describe public role information associated with this organization.")
    if "contraloria" in categories:
        sentences.append("Records describe control reports or observations linked to this organization.")
    if "municipal" in categories:
        sentences.append("Records describe municipal projects or spending linked to this organization.")
    if "budget" in categories:
        sentences.append("Records describe budget activity linked to this organization.")
    if not sentences:
        sentences.append("Records describe public activity linked to this organization.")
    return sentences[:2]


def _bucket_categories(bucket: _DatasetBucket) -> set[str]:
    categories: set[str] = set()
    names = tuple(bucket.predicate_counts.keys()) + tuple(bucket.relationship_type_counts.keys())
    for name in names:
        upper = name.upper()
        if any(marker in upper for marker in PROCUREMENT_MARKERS):
            categories.add("procurement")
        if any(marker in upper for marker in LOBBY_MARKERS):
            categories.add("lobby")
        if any(marker in upper for marker in TRANSPARENCY_MARKERS):
            categories.add("transparency")
        if any(marker in upper for marker in CONTRALORIA_MARKERS):
            categories.add("contraloria")
        if any(marker in upper for marker in MUNICIPAL_MARKERS):
            categories.add("municipal")
        if any(marker in upper for marker in BUDGET_MARKERS):
            categories.add("budget")
    return categories


def _consistency_observations(datasets_present: list[str], buckets: tuple[_DatasetBucket, ...]) -> list[str]:
    observations: list[str] = []
    if datasets_present:
        observations.append(_dataset_presence_sentence(datasets_present))

    categories = set().union(*(_bucket_categories(bucket) for bucket in buckets)) if buckets else set()
    if "procurement" in categories:
        if categories <= {"procurement"}:
            observations.append("This organization appears only in procurement records.")
        elif {"procurement", "lobby", "transparency"} <= categories:
            observations.append(
                "The organization appears in procurement records, registered meetings, and transparency records."
            )
        elif {"procurement", "lobby"} <= categories:
            observations.append("The organization appears in procurement records and also has registered meetings.")
        elif {"procurement", "transparency"} <= categories:
            observations.append("The organization appears in procurement records and transparency records.")
        else:
            observations.append("The organization appears in procurement records.")
    if "contraloria" in categories:
        observations.append("Contraloria records contain observations related to the organization.")
    if "municipal" in categories:
        observations.append("Municipal records reference the organization.")
    if "budget" in categories:
        observations.append("Budget records reference the organization.")

    if not observations:
        observations.append("This organization appears in multiple public sources.")
    return observations


def _dataset_presence_sentence(datasets_present: list[str]) -> str:
    if len(datasets_present) == 1:
        return f"This organization appears in {datasets_present[0]} records."
    if len(datasets_present) == 2:
        return f"This organization appears in {datasets_present[0]} and {datasets_present[1]} records."
    joined = ", ".join(datasets_present[:-1])
    return f"This organization appears in {joined}, and {datasets_present[-1]} records."


def _coverage_summary(
    entity_name: str,
    datasets_present: list[str],
    *,
    total_claims: int,
    total_relationships: int,
    total_evidence: int,
) -> str:
    if not datasets_present:
        return f"No public source records were found for {entity_name or 'this organization'}."
    dataset_text = _join_names(datasets_present)
    source_word = "public source" if len(datasets_present) == 1 else "public sources"
    return (
        f"{entity_name} appears in {len(datasets_present)} {source_word}: {dataset_text}. "
        f"Across these sources there are {total_claims} claims, {total_relationships} relationships, and "
        f"{total_evidence} evidence items."
    )


def _join_names(values: list[str]) -> str:
    if len(values) == 1:
        return values[0]
    if len(values) == 2:
        return f"{values[0]} and {values[1]}"
    return f"{', '.join(values[:-1])}, and {values[-1]}"


def _dataset_label(dataset_name: str) -> str:
    return datasets.dataset_label_for_name(dataset_name)


def _count_phrase(count: int, noun: str) -> str:
    if count == 1:
        return f"1 {noun}"
    return f"{count} {noun}s"
