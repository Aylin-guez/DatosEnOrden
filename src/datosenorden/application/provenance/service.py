from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict
from typing import Iterable

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from datosenorden.application.provenance.models import (
    ProvenanceClass,
    ProvenanceDecision,
    ProvenanceManifestEntry,
    ProvenanceSnapshot,
)
from datosenorden.models import (
    Claim,
    Dataset,
    Entity,
    Evidence,
    RealExpedientRow,
    RealExpedientVersionRow,
    RelationshipPublic,
    Source,
    SourceRecord,
)


PROVENANCE_MANIFEST: tuple[ProvenanceManifestEntry, ...] = (
    ProvenanceManifestEntry(
        source_name="Senado de Chile", dataset_name="senado-legislative-matter", dataset_version="15975-25",
        provenance_class=ProvenanceClass.REAL, source_label="Senado de Chile",
        dataset_identifier="senado-legislative-matter@15975-25", record_scope="postgresql_dataset",
        public_countable=True, evidence_basis="Verified official Senate resource with canonical bulletin 15975-25 and artifact manifest.",
        reason="Explicit, verified official legislative matter observation.", confidence="HIGH",
    ),
    ProvenanceManifestEntry(
        source_name="Camara de Diputadas y Diputados", dataset_name="camara-legislative-matter", dataset_version="15975-25",
        provenance_class=ProvenanceClass.REAL, source_label="Camara de Diputadas y Diputados",
        dataset_identifier="camara-legislative-matter@15975-25", record_scope="postgresql_dataset",
        public_countable=True, evidence_basis="Verified official Chamber resource with canonical bulletin 15975-25 and artifact manifest.",
        reason="Explicit, verified official legislative matter observation.", confidence="HIGH",
    ),
    ProvenanceManifestEntry(
        source_name="DIPRES",
        dataset_name="dipres-ejecucion-total-programa",
        dataset_version="2026-segundo-trimestre-pesos",
        provenance_class=ProvenanceClass.REAL,
        source_label="DIPRES",
        dataset_identifier="dipres-ejecucion-total-programa@2026-segundo-trimestre-pesos",
        record_scope="postgresql_dataset",
        public_countable=True,
        evidence_basis="Official DIPRES Ejecución Total 2026, Programa, Segundo Trimestre CSV with certified 09/17/01 identity.",
        reason="Operator-loaded official DIPRES programme execution slice for Dirección de Educación Pública.",
        confidence="HIGH",
    ),
    ProvenanceManifestEntry(
        source_name="ChileCompra API Mercado Publico",
        dataset_name="chilecompra-ordenes-compra",
        dataset_version="2026-06-18",
        provenance_class=ProvenanceClass.REAL,
        source_label="ChileCompra",
        dataset_identifier="chilecompra-ordenes-compra@2026-06-18",
        record_scope="postgresql_dataset",
        public_countable=True,
        evidence_basis="Official Mercado Publico API dataset identity recorded at ingestion.",
        reason="Operator-loaded public ChileCompra records with official dataset URL.",
        confidence="HIGH",
    ),
    ProvenanceManifestEntry(
        source_name="ChileCompra API Mercado Publico",
        dataset_name="chilecompra-ordenes-compra",
        dataset_version="adhoc",
        provenance_class=ProvenanceClass.DEMO,
        source_label="ChileCompra demo",
        dataset_identifier="chilecompra-ordenes-compra@adhoc",
        record_scope="postgresql_dataset",
        public_countable=False,
        evidence_basis="Explicit local demo dataset URL and version.",
        reason="Prepared demonstration case, not an operator-loaded public dataset.",
        confidence="HIGH",
    ),
    ProvenanceManifestEntry(
        source_name="DatosEnOrden Local Seed",
        dataset_name="local-seed-traceability-flow",
        dataset_version="local-seed-1",
        provenance_class=ProvenanceClass.TEST,
        source_label="Local technical seed",
        dataset_identifier="local-seed-traceability-flow@local-seed-1",
        record_scope="postgresql_dataset",
        public_countable=False,
        evidence_basis="Explicit technical seed dataset identity.",
        reason="Technical traceability fixture.",
        confidence="HIGH",
    ),
)

_DEMO_DATASET_PREFIXES = (
    "contraloria-control-report-sample",
    "diario-oficial-sample",
    "dipres-budget-sample",
    "lobby-meeting-sample",
    "registro-empresas-sample",
    "sanciones-procedimientos-sample",
    "transparencia-activa-sample",
)


def classify_dataset(dataset: Dataset, source: Source | None = None) -> ProvenanceDecision:
    source_name = source.name if source is not None else ""
    for entry in PROVENANCE_MANIFEST:
        if (source_name, dataset.name, dataset.version) == (entry.source_name, entry.dataset_name, entry.dataset_version):
            return _decision(entry)
    if dataset.name in _DEMO_DATASET_PREFIXES and dataset.version == "local-sample-1":
        return ProvenanceDecision(
            provenance_class=ProvenanceClass.DEMO,
            source_label="DatosEnOrden demo",
            dataset_identifier=f"{dataset.name}@{dataset.version}",
            record_scope="postgresql_dataset",
            public_countable=False,
            evidence_basis="Explicit versioned local sample dataset identity.",
            reason="Demonstration sample; not a public source load.",
            confidence="HIGH",
        )
    return ProvenanceDecision(
        provenance_class=ProvenanceClass.UNKNOWN,
        source_label=source_name or "Unclassified source",
        dataset_identifier=f"{dataset.name}@{dataset.version}",
        record_scope="postgresql_dataset",
        public_countable=False,
        evidence_basis="No exact manifest entry.",
        reason="Fail closed: missing classification is not real.",
        confidence="LOW",
    )


def classify_document_id(document_id: str) -> ProvenanceDecision:
    if document_id == "senado-docto-9000-mensaje_mocion":
        return ProvenanceDecision(ProvenanceClass.REAL, "Senado de Chile", document_id, "published_document", True, "Published official document artifact and Senate source URL.", "Official document.", "HIGH")
    if document_id == "knowledge-doc-arauco-hospital-demo-2026":
        return ProvenanceDecision(ProvenanceClass.DEMO, "DatosEnOrden demo", document_id, "document_catalog", False, "Explicit local demonstration catalog entry.", "Demonstration document.", "HIGH")
    return _unknown("document", document_id)


def classify_expedient_id(expedient_id: str) -> ProvenanceDecision:
    if expedient_id == "EXP-001":
        return ProvenanceDecision(ProvenanceClass.DEMO, "Laboratorio DEO", expedient_id, "application_expedient", False, "Explicit laboratory fixture identifier.", "Demonstration expedition.", "HIGH")
    return _unknown("expedient", expedient_id)


def combine_derived_classes(classes: Iterable[ProvenanceClass]) -> ProvenanceClass:
    values = tuple(classes)
    if not values or ProvenanceClass.UNKNOWN in values:
        return ProvenanceClass.UNKNOWN
    return values[0] if all(value == values[0] for value in values) else ProvenanceClass.UNKNOWN


def build_provenance_snapshot(session: Session) -> ProvenanceSnapshot:
    datasets, records, evidences, claims, relationships, entities, record_classes, evidence_classes, claim_classes, relationship_classes, entity_classes = _classified_content(session)
    counts = _empty_counts()
    _add_decisions(counts["source_records"], (value.provenance_class for value in record_classes.values()))
    _add_decisions(counts["evidences"], (value.provenance_class for value in evidence_classes.values()))
    _add_decisions(counts["claims"], claim_classes.values())
    _add_decisions(counts["relationships"], relationship_classes.values())
    _add_decisions(counts["entities"], (ProvenanceClass.REAL if ProvenanceClass.REAL in entity_classes.get(row.id, set()) else combine_derived_classes(entity_classes.get(row.id, set())) for row in entities))
    _add_decisions(counts["documents"], (classify_document_id("senado-docto-9000-mensaje_mocion").provenance_class, classify_document_id("knowledge-doc-arauco-hospital-demo-2026").provenance_class))
    _add_decisions(
        counts["expedients"],
        (
            classify_expedient_id("EXP-001").provenance_class,
            *(ProvenanceClass(row.provenance_class) for row in session.scalars(select(RealExpedientRow)).all()),
        ),
    )
    lifecycle: dict[str, dict[str, int]] = defaultdict(dict)
    for row in records:
        decision = record_classes[row.id]
        if decision.provenance_class is ProvenanceClass.REAL:
            lifecycle["source_records"][row.status] = lifecycle["source_records"].get(row.status, 0) + 1
    source_metrics = _source_metrics(datasets, records, evidences, claims, relationships, record_classes, claim_classes, evidence_classes, relationship_classes)
    return ProvenanceSnapshot(counts=counts, lifecycle=dict(lifecycle), source_metrics=source_metrics)


def build_public_metric_projection(session: Session) -> dict[str, int]:
    """Return public count metrics from REAL content with usable lifecycle only."""
    content = build_public_usable_content(session)
    usable_claims = content["claims"]
    usable_evidences = content["evidences"]
    usable_relationships = content["relationships"]
    usable_entity_ids = content["entity_ids"]
    entities = content["entities"]
    entity_by_id = {row.id: row for row in entities}
    predicates = {
        "contracts": {"RECEIVES_CONTRACT", "AWARDS_CONTRACT", "ISSUES_PURCHASE_ORDER"},
        "meetings": {"ORGANIZATION_HELD_LOBBY_MEETING", "COUNTERPARTY_PARTICIPATED_IN_LOBBY"},
        "authorities": {"AUTHORITY_ELECTED_TO_OFFICE", "PERSON_HOLDS_PUBLIC_ROLE", "PERSON_APPOINTED_TO_PUBLIC_OFFICE", "PERSON_REPRESENTS_COMPANY"},
    }
    return {
        "source_records": len(content["record_ids"]),
        "claims": len(usable_claims),
        "evidences": len(usable_evidences),
        "relationships": len(usable_relationships),
        "entities": len(usable_entity_ids),
        "suppliers": sum(1 for entity_id in usable_entity_ids if entity_by_id[entity_id].entity_type == "COMPANY"),
        "contracts": len({row.source_record_id for row in usable_claims if row.predicate in predicates["contracts"]}),
        "meetings": len({row.source_record_id for row in usable_claims if row.predicate in predicates["meetings"]}),
        "authorities": len({row.subject_entity_id for row in usable_claims if row.predicate in predicates["authorities"]}),
        "documents": 1,
        "expedients": _count_published_real_expedients(session),
    }


def build_public_usable_content(session: Session) -> dict[str, object]:
    """Single fail-closed eligibility projection for browser-facing REAL content."""
    _, records, evidences, claims, relationships, entities, record_classes, evidence_classes, claim_classes, relationship_classes, _ = _classified_content(session)
    usable_statuses = {"normalized", "validated", "published"}
    usable_record_ids = {
        row.id for row in records
        if record_classes[row.id].provenance_class is ProvenanceClass.REAL and row.status in usable_statuses
    }
    usable_claims = [
        row for row in claims
        if claim_classes[row.id] is ProvenanceClass.REAL
        and row.source_record_id in usable_record_ids
        and row.status in usable_statuses
    ]
    usable_claim_ids = {row.id for row in usable_claims}
    usable_evidences = [
        row for row in evidences
        if evidence_classes[row.id].provenance_class is ProvenanceClass.REAL and row.source_record_id in usable_record_ids
    ]
    usable_relationships = [
        row for row in relationships
        if relationship_classes[row.id] is ProvenanceClass.REAL
        and row.claim_id in usable_claim_ids
        and row.status in usable_statuses
    ]
    usable_entity_ids = {
        entity_id
        for row in usable_claims
        for entity_id in (row.subject_entity_id, row.object_entity_id)
        if entity_id is not None
    }
    return {
        "record_ids": usable_record_ids,
        "claims": usable_claims,
        "evidences": usable_evidences,
        "relationships": usable_relationships,
        "entity_ids": usable_entity_ids,
        "source_ids": {
            source_id
            for row in records
            if row.id in usable_record_ids
            and (source_id := getattr(row, "source_id", None)) is not None
        },
        "entities": entities,
    }


def _count_published_real_expedients(session: Session) -> int:
    scalar = getattr(session, "scalar", None)
    if scalar is None:
        return 0
    return int(
        scalar(
            select(func.count())
        .select_from(RealExpedientRow)
        .join(
            RealExpedientVersionRow,
            (RealExpedientVersionRow.expedient_id == RealExpedientRow.expedient_id)
            & (RealExpedientVersionRow.version == RealExpedientRow.current_version),
        )
        .where(
            RealExpedientRow.provenance_class == ProvenanceClass.REAL.value,
            RealExpedientVersionRow.lifecycle == "published",
        )
        )
        or 0
    )


def _classified_content(session: Session):  # noqa: ANN201
    datasets = session.execute(select(Dataset, Source).join(Source, Dataset.source_id == Source.id)).all()
    dataset_classes = {dataset.id: classify_dataset(dataset, source) for dataset, source in datasets}
    records = session.scalars(select(SourceRecord)).all()
    record_classes = {row.id: dataset_classes.get(row.dataset_id, _unknown("source_record", str(row.id))) for row in records}
    evidences = session.scalars(select(Evidence)).all()
    evidence_classes = {
        row.id: (record_classes.get(row.source_record_id) if row.source_record_id else dataset_classes.get(row.dataset_id)) or _unknown("evidence", str(row.id))
        for row in evidences
    }
    claims = session.scalars(select(Claim)).all()
    claim_classes = {
        row.id: combine_derived_classes((
            record_classes.get(row.source_record_id, _unknown("source_record", str(row.source_record_id))).provenance_class,
            evidence_classes.get(row.evidence_id, _unknown("evidence", str(row.evidence_id))).provenance_class,
        ))
        for row in claims
    }
    relationships = session.scalars(select(RelationshipPublic)).all()
    relationship_classes = {row.id: claim_classes.get(row.claim_id, ProvenanceClass.UNKNOWN) for row in relationships}
    entities = session.scalars(select(Entity)).all()
    entity_classes: dict[object, set[ProvenanceClass]] = defaultdict(set)
    for row in claims:
        entity_classes[row.subject_entity_id].add(claim_classes[row.id])
        if row.object_entity_id is not None:
            entity_classes[row.object_entity_id].add(claim_classes[row.id])
    return datasets, records, evidences, claims, relationships, entities, record_classes, evidence_classes, claim_classes, relationship_classes, entity_classes


def _source_metrics(datasets, records, evidences, claims, relationships, record_classes, claim_classes, evidence_classes, relationship_classes) -> tuple[dict[str, object], ...]:  # noqa: ANN001
    by_dataset: dict[object, list[SourceRecord]] = defaultdict(list)
    for row in records:
        by_dataset[row.dataset_id].append(row)
    rows: list[dict[str, object]] = []
    for dataset, source in datasets:
        decision = classify_dataset(dataset, source)
        source_rows = by_dataset.get(dataset.id, [])
        ids = {row.id for row in source_rows}
        real_records = [row for row in source_rows if record_classes[row.id].provenance_class is ProvenanceClass.REAL]
        real_claim_ids = {
            claim_id for claim_id, value in claim_classes.items()
            if value is ProvenanceClass.REAL and next((claim.source_record_id for claim in claims if claim.id == claim_id), None) in ids
        }
        real_claims = len(real_claim_ids)
        real_entity_ids = {
            entity_id
            for claim in claims
            if claim.id in real_claim_ids
            for entity_id in (claim.subject_entity_id, claim.object_entity_id)
            if entity_id is not None
        }
        real_evidences = sum(
            1 for evidence in evidences
            if evidence.source_record_id in ids and evidence_classes[evidence.id].provenance_class is ProvenanceClass.REAL
        )
        real_relationships = sum(
            1 for relationship_id, value in relationship_classes.items()
            if value is ProvenanceClass.REAL and next((relationship.claim_id for relationship in relationships if relationship.id == relationship_id), None) in real_claim_ids
        )
        # Claims/evidence/relationships are linked to a source record, so only include this dataset's records.
        rows.append({**asdict(decision), "source_name": source.name, "dataset_name": dataset.name, "source_records": len(source_rows), "real_records": len(real_records), "real_entities": len(real_entity_ids) if decision.provenance_class is ProvenanceClass.REAL else 0, "normalized_real_records": sum(row.status == "normalized" for row in real_records), "available_real_records": sum(row.status in {"normalized", "validated", "published"} for row in real_records), "rejected_real_records": sum(row.status == "rejected" for row in real_records), "real_claims": real_claims if decision.provenance_class is ProvenanceClass.REAL else 0, "real_evidence": real_evidences if decision.provenance_class is ProvenanceClass.REAL else 0, "real_relationships": real_relationships if decision.provenance_class is ProvenanceClass.REAL else 0})
    return tuple(rows)


def _empty_counts() -> dict[str, dict[str, int]]:
    return {name: {item.value: 0 for item in ProvenanceClass} for name in ("source_records", "claims", "evidences", "relationships", "entities", "documents", "expedients")}


def _add_decisions(target: dict[str, int], classes: Iterable[ProvenanceClass]) -> None:
    for provenance_class in classes:
        target[provenance_class.value] += 1


def _decision(entry: ProvenanceManifestEntry) -> ProvenanceDecision:
    return ProvenanceDecision(
        provenance_class=entry.provenance_class,
        source_label=entry.source_label,
        dataset_identifier=entry.dataset_identifier,
        record_scope=entry.record_scope,
        public_countable=entry.public_countable,
        evidence_basis=entry.evidence_basis,
        reason=entry.reason,
        confidence=entry.confidence,
    )


def _unknown(scope: str, identifier: str) -> ProvenanceDecision:
    return ProvenanceDecision(ProvenanceClass.UNKNOWN, "Unclassified", identifier, scope, False, "No exact manifest entry.", "Fail closed: missing classification is not real.", "LOW")
