"""Pure deterministic ChileCompra-to-REAL-expedient transformation."""

from __future__ import annotations

from datosenorden.application.provenance.models import ProvenanceClass
from datosenorden.application.real_expedient.models import (
    EpistemicClass,
    ExpedientReferences,
    ExpedientSpecification,
    ExpedientStatus,
    NarrativeStatement,
)

from .models import ChileCompraExpedientInput


def build_chilecompra_expedient_candidate(
    value: ChileCompraExpedientInput,
) -> ExpedientSpecification:
    """Build a v1 candidate; persistence and eligibility revalidation stay external."""
    expedition_id = f"EXP-REAL-CHILECOMPRA-{value.order_id}"
    title = f"Orden de compra de {value.public_subject} de {value.buyer_name}"
    question = "¿Qué muestran los registros públicos sobre esta orden de compra?"
    summary = _summary(value)
    references = ExpedientReferences(
        claim_ids=value.claim_ids,
        evidence_ids=value.evidence_ids,
        relationship_ids=value.relationship_ids,
        entity_ids=value.entity_ids,
        source_ids=(value.source_id,),
    )
    statements = _statements(value)
    return ExpedientSpecification(
        expedient_id=expedition_id,
        title=title,
        question=question,
        summary=summary,
        provenance_class=ProvenanceClass.REAL,
        status=ExpedientStatus.PUBLISHED,
        version=1,
        references=references,
        statements=statements,
    )


def _summary(value: ChileCompraExpedientInput) -> str:
    parts = [f"{value.buyer_name} registró una orden de compra de {value.public_subject}"]
    if value.supplier_name:
        parts.append(f"asociada a {value.supplier_name}")
    if value.amount is not None and value.currency:
        parts.append(f"por {_amount(value.amount)} {value.currency}")
    if value.order_date:
        parts.append(f"con fecha {value.order_date.isoformat()}")
    return " ".join(parts) + ", según registros públicos de ChileCompra."


def _amount(value: object) -> str:
    return format(value, "f").rstrip("0").rstrip(".")


def _statements(value: ChileCompraExpedientInput) -> tuple[NarrativeStatement, ...]:
    facts = [
        NarrativeStatement(
            "fact-purchase-order-record",
            "what_is_verified",
            f"Los registros públicos identifican la orden de compra {value.order_id} asociada a {value.buyer_name}.",
            EpistemicClass.FACT,
            value.claim_ids,
            value.evidence_ids,
        )
    ]
    if value.supplier_name:
        facts.append(
            NarrativeStatement(
                "fact-supplier-reference",
                "what_is_verified",
                f"Los registros referenciados identifican a {value.supplier_name} como proveedor asociado.",
                EpistemicClass.FACT,
                value.claim_ids,
                value.evidence_ids,
            )
        )
    facts.append(
        NarrativeStatement(
            "unknown-no-accountability-finding",
            "limitations",
            "Estos registros no determinan por sí solos causalidad, irregularidad, responsabilidad ni intención.",
            EpistemicClass.UNKNOWN,
        )
    )
    return tuple(facts)
