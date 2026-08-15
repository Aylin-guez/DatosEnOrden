"""Map only the certified DIPRES 09/17/01 slice into the established graph contract."""

from __future__ import annotations

from datetime import UTC, datetime

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

from .models import ParsedBudgetCsv


DIPRES_SOURCE_NAME = "DIPRES"
DIPRES_SOURCE_URL = "https://www.dipres.gob.cl/"
DIPRES_DATASET_NAME = "dipres-ejecucion-total-programa"
DIPRES_DATASET_VERSION = "2026-segundo-trimestre-pesos"
DIPRES_RECORD_TYPE = "dipres:execution_total_program"
DEP_EXTERNAL_ID = "chilecompra:buyer:1593363"
DEP_PARTIDA = "09"
DEP_CAPITULO = "17"
DEP_PROGRAMA = "01"


def build_dep_real_batch(parsed: ParsedBudgetCsv, organization: EntityRecord) -> GraphBatch:
    """Build the exact, source-backed graph slice without resolving by name."""
    if organization.entity_type is not EntityType.PUBLIC_ORGANIZATION or organization.external_id != DEP_EXTERNAL_ID:
        raise ValueError("DIPRES DEP ingestion requires the certified ChileCompra organization")
    selected = tuple(
        row.values
        for row in parsed.rows
        if (row.values.get("partida"), row.values.get("capitulo"), row.values.get("programa"))
        == (DEP_PARTIDA, DEP_CAPITULO, DEP_PROGRAMA)
    )
    if not selected:
        raise ValueError("DIPRES resource does not contain the certified 09/17/01 slice")
    resource = parsed.acquisition.resource
    now = datetime.now(UTC)
    record_payload = {
        "partida": DEP_PARTIDA,
        "capitulo": DEP_CAPITULO,
        "programa": DEP_PROGRAMA,
        "period": resource.period,
        "unit": "Pesos",
        "resource_sha256": parsed.acquisition.sha256,
        "official_resource_url": resource.download_url,
        "rows": selected,
    }
    source_record = SourceRecordPayload(
        external_id="dipres:2026:09:17:01:segundo-trimestre:pesos",
        record_type=DIPRES_RECORD_TYPE,
        payload_hash=stable_json_hash(record_payload),
        raw_payload=record_payload,
        retrieved_at=parsed.acquisition.acquired_at,
        status=WorkflowStatus.VALIDATED,
    )
    budget = EntityRecord(
        entity_type=EntityType.BUDGET,
        external_id="dipres:budget:2026:09:17:01:segundo-trimestre:pesos",
        name="Información presupuestaria DIPRES 2026: Dirección de Educación Pública (09/17/01)",
        normalized_key="dipres-2026-09-17-01-segundo-trimestre",
        metadata={"partida": DEP_PARTIDA, "capitulo": DEP_CAPITULO, "programa": DEP_PROGRAMA, "period": resource.period},
    )
    evidence = EvidenceRecord(
        source_record=source_record,
        source_name=DIPRES_SOURCE_NAME,
        title="DIPRES: Ejecución Total 2026, Programa, Segundo Trimestre — Dirección de Educación Pública (09/17/01)",
        url=resource.download_url,
        excerpt="Recurso oficial DIPRES; Partida 09, Capítulo 17, Programa 01; valores según columnas publicadas.",
        metadata={"official_page_url": resource.official_page_url, "period": resource.period, "resource_sha256": parsed.acquisition.sha256, "partida": DEP_PARTIDA, "capitulo": DEP_CAPITULO, "programa": DEP_PROGRAMA},
    )
    claims = tuple(
        ClaimRecord(
            subject_entity=organization,
            predicate=predicate,
            source_record=source_record,
            evidence=evidence,
            object_value={"official_column": column, "values": _column_values(selected, column), "unit": "Pesos", "period": resource.period, "partida": DEP_PARTIDA, "capitulo": DEP_CAPITULO, "programa": DEP_PROGRAMA},
            confidence=1.0,
            status=WorkflowStatus.VALIDATED,
        )
        for predicate, column in (
            ("DIPRES_REPORTS_PRESUPUESTO_INICIAL", "presupuesto_inicial"),
            ("DIPRES_REPORTS_PRESUPUESTO_VIGENTE", "presupuesto_vigente"),
            ("DIPRES_REPORTS_EJECUCION_ACUMULADA_A_SEGUNDO_TRIMESTRE", "ejecucion_acumulada_a_segundo_trimestre"),
        )
    )
    identity_claim = ClaimRecord(
        subject_entity=budget,
        predicate="BUDGET_INFORMATION_FOR_ORGANIZATION",
        source_record=source_record,
        evidence=evidence,
        object_entity=organization,
        object_value={"identity_basis": "exact certified institution label", "partida": DEP_PARTIDA, "capitulo": DEP_CAPITULO, "programa": DEP_PROGRAMA},
        confidence=1.0,
        status=WorkflowStatus.VALIDATED,
    )
    relationship = PublicRelationshipRecord(
        source_entity=budget,
        target_entity=organization,
        relationship_type=RelationshipType.BUDGET_ALLOCATED_TO,
        claim=identity_claim,
        published_at=now,
        status=WorkflowStatus.PUBLISHED,
        metadata={"cross_source_basis": "same certified institution", "source_a": "ChileCompra", "source_b": "DIPRES", "causal_link": False},
    )
    return GraphBatch(
        source=SourceInfo(DIPRES_SOURCE_NAME, "Dirección de Presupuestos", DIPRES_SOURCE_URL, "Datos públicos DIPRES", parsed.acquisition.acquired_at, {"official_page_url": resource.official_page_url}),
        dataset=DatasetRecord(DIPRES_SOURCE_NAME, DIPRES_DATASET_NAME, "Ejecución Total 2026, nivel Programa, Segundo Trimestre, Pesos", DIPRES_DATASET_VERSION, resource.download_url, parsed.acquisition.sha256, parsed.acquisition.acquired_at, {"period": resource.period, "unit": "Pesos", "level": "Programa"}),
        source_records=(source_record,),
        entities=(organization, budget),
        evidence=(evidence,),
        claims=(*claims, identity_claim),
        public_relationships=(relationship,),
        raw_count=1,
    )


def _column_values(rows: tuple[dict[str, str], ...], column: str) -> list[dict[str, str]]:
    """Preserve published row values; aggregation is intentionally out of scope."""
    values = [
        {key: row.get(key, "") for key in ("subtitulo", "item", "asignacion", "denominacion", column)}
        for row in rows
        if row.get(column)
    ]
    if not values:
        raise ValueError(f"DIPRES resource lacks {column}")
    return values
