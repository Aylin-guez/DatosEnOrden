from __future__ import annotations

from dataclasses import asdict, is_dataclass
from datetime import date, datetime

from sqlalchemy import distinct, func, select

from datosenorden.db.session import SessionLocal
from datosenorden.maintenance.cross_dataset_explorer import list_cross_dataset_organizations
from datosenorden.maintenance.dipres_prototype import read_budget_summary
from datosenorden.maintenance.discovery_cases import get_discovery_cases
from datosenorden.models import Claim, Entity


def build_citizen_dashboard() -> dict[str, object]:
    with SessionLocal() as session:
        budget_rows = read_budget_summary(session)
        budget_total = sum(row.executed_budget or row.approved_budget for row in budget_rows)
        budget_currency = _budget_currency(budget_rows)
        organizations = list_cross_dataset_organizations(session)

        return {
            "title": "¿Dónde fue mi plata?",
            "summary": (
                "Una vista ciudadana de muestra que cruza presupuesto, compras, "
                "proveedores, reuniones y autoridades visibles."
            ),
            "metrics": {
                "budget_total": budget_total,
                "budget_currency": budget_currency,
                "contracts": _count_contracts(session),
                "suppliers": _count_entities(session, "COMPANY"),
                "meetings": _count_meetings(session),
                "authorities": _count_authorities(session),
            },
            "budget_rows": [
                {
                    "organization_name": row.organization_name,
                    "budget_entity_name": row.budget_entity_name,
                    "fiscal_year": row.fiscal_year,
                    "approved_budget": row.approved_budget,
                    "executed_budget": row.executed_budget,
                    "purchase_orders": row.purchase_orders,
                    "suppliers": row.suppliers,
                    "currency": row.currency,
                }
                for row in budget_rows
            ],
            "featured_entities": [
                {
                    "organization_id": row.organization_id,
                    "organization_name": row.organization_name,
                    "datasets": list(row.datasets),
                    "contracts": row.contracts,
                    "lobby_meetings": row.lobby_meetings,
                    "evidence": row.evidence,
                    "relationships": row.relationships,
                }
                for row in organizations[:4]
            ],
            "discovery_cases": list(get_discovery_cases().get("cases", []))[:3],
        }


def _budget_currency(rows) -> str:  # noqa: ANN001
    for row in rows:
        currency = getattr(row, "currency", "")
        if currency:
            return str(currency)
    return "CLP"


def _count_contracts(session) -> int:  # noqa: ANN001
    return _safe_scalar_count(
        session,
        select(func.count(distinct(Claim.source_record_id))).where(
            Claim.predicate.in_(("RECEIVES_CONTRACT", "AWARDS_CONTRACT", "ISSUES_PURCHASE_ORDER"))
        ),
    )


def _count_meetings(session) -> int:  # noqa: ANN001
    return _safe_scalar_count(
        session,
        select(func.count(distinct(Claim.source_record_id))).where(
            Claim.predicate.in_(("ORGANIZATION_HELD_LOBBY_MEETING", "COUNTERPARTY_PARTICIPATED_IN_LOBBY"))
        ),
    )


def _count_authorities(session) -> int:  # noqa: ANN001
    return _safe_scalar_count(
        session,
        select(func.count(distinct(Claim.subject_entity_id))).where(
            Claim.predicate.in_(
                (
                    "AUTHORITY_ELECTED_TO_OFFICE",
                    "PERSON_HOLDS_PUBLIC_ROLE",
                    "PERSON_APPOINTED_TO_PUBLIC_OFFICE",
                    "PERSON_REPRESENTS_COMPANY",
                )
            )
        ),
    )


def _count_entities(session, entity_type: str) -> int:  # noqa: ANN001
    return _safe_scalar_count(
        session,
        select(func.count(distinct(Entity.id))).select_from(Entity).where(Entity.entity_type == entity_type),
    )


def _safe_scalar_count(session, statement) -> int:  # noqa: ANN001
    try:
        scalar = session.scalar(statement)
    except AttributeError:
        return 0
    except Exception:
        return 0
    return int(scalar or 0)
