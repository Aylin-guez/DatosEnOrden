from __future__ import annotations

from collections import defaultdict

from datosenorden.db.session import SessionLocal
from datosenorden.maintenance.dataset_metadata import dataset_category
from datosenorden.maintenance.dataset_metadata import dataset_metadata_for_name
from datosenorden.maintenance.explanations import event_explanation
from datosenorden.maintenance.timeline_explorer import build_entity_timeline


TIMELINE_CATEGORIES = ("Budget", "Procurement", "Lobby", "Transparency", "Authorities", "Audits", "Company Registry")


def build_investigation_timeline(entity_id: str) -> dict[str, object]:
    with SessionLocal() as session:
        timeline = build_entity_timeline(session, entity_id)

    if timeline is None:
        return _empty_timeline()

    years: dict[int, dict[str, list[dict[str, object]]]] = defaultdict(lambda: {category: [] for category in TIMELINE_CATEGORIES})
    for event in timeline.events:
        category = _event_category(event.dataset_name, event.predicate)
        years[event.event_date.year][category].append(
            {
                "date": event.event_date.isoformat(),
                "label": event.title,
                "dataset": event.dataset,
                "dataset_name": event.dataset_name,
                "category": category,
                "explanation": event.explanation or event_explanation(event.predicate),
                "origin": "derived_from_expediente",
                "source_id": str(event.source_record_id),
                "source_record_id": str(event.source_record_id),
                "evidence_id": "",
                "claim_id": str(event.claim_id),
                "predicate": event.predicate,
                "technical": [
                    f"claim_id={event.claim_id}",
                    f"predicate={event.predicate}",
                    f"source_record_id={event.source_record_id}",
                ],
            }
        )

    grouped_years = [
        {
            "year": year,
            "categories": [
                {
                    "category": category,
                    "items": items,
                }
                for category, items in groups.items()
                if items
            ],
        }
        for year, groups in sorted(years.items(), key=lambda item: item[0], reverse=True)
    ]

    return {
        "entity": {
            "id": str(timeline.entity.id),
            "name": timeline.entity.name,
            "type": timeline.entity.entity_type,
        },
        "years": grouped_years,
        "summary": str(getattr(timeline, "explanation", "Timeline summary.")),
    }


def _event_category(dataset_name: str, predicate: str) -> str:
    dataset = dataset_metadata_for_name(dataset_name)
    category = dataset.category if dataset is not None else dataset_category(dataset_name)
    predicate_upper = predicate.upper()
    if category == "budget" or "BUDGET" in predicate_upper:
        return "Budget"
    if category == "procurement" or any(marker in predicate_upper for marker in ("PURCHASE_ORDER", "CONTRACT", "TENDER")):
        return "Procurement"
    if category == "lobby" or "LOBBY" in predicate_upper:
        return "Lobby"
    if category == "transparency" or any(marker in predicate_upper for marker in ("PUBLIC_ROLE", "ROLE_BELONGS")):
        return "Transparency"
    if category == "authorities" or any(marker in predicate_upper for marker in ("AUTHORITY", "ELECTORAL_PERIOD", "OFFICE_BELONGS")):
        return "Authorities"
    if category == "audits" or any(marker in predicate_upper for marker in ("CONTROL_REPORT", "OBSERVATION")):
        return "Audits"
    if category == "company_registry" or any(marker in predicate_upper for marker in ("COMPANY_REGISTERED_ON", "COMPANY_MODIFIED_ON", "PERSON_REPRESENTS_COMPANY", "PERSON_OWNS_COMPANY")):
        return "Company Registry"
    return "Budget"


def _empty_timeline() -> dict[str, object]:
    return {"entity": {"id": "", "name": "", "type": ""}, "years": [], "summary": "No timeline records were found."}
