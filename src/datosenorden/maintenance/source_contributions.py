from __future__ import annotations

from dataclasses import dataclass

from datosenorden.db.session import SessionLocal
from datosenorden.maintenance.complete_demo_case import build_complete_demo_case_summary
from datosenorden.maintenance.complete_demo_case import load_complete_demo_case_payload
from datosenorden.maintenance.dataset_metadata import dataset_citizen_summary
from datosenorden.maintenance.dataset_metadata import dataset_metadata_for_name
from datosenorden.maintenance.dataset_metadata import source_contribution_bullets
from datosenorden.maintenance.entity_comparison import build_entity_comparison
from datosenorden.maintenance.investigation_view import build_investigation_view
from datosenorden.maintenance.safe_access import _field
from datosenorden.maintenance.source_plugins import get_source_plugin
from datosenorden.maintenance.source_plugins import plugin_concept_names
from datosenorden.maintenance.source_plugins import plugin_status_value


@dataclass(frozen=True)
class SourceContribution:
    dataset: str
    category: str
    summary: str
    contributes: tuple[str, ...]
    evidence_count: int
    relationship_count: int
    overlap_note: str


def build_source_contributions(entity_id: str) -> dict[str, object]:
    with SessionLocal() as session:
        view = build_investigation_view(session, entity_id)

    comparison = build_entity_comparison(entity_id)
    if view is None:
        return _empty_source_contributions()

    profile = _field(view, "profile", {})
    entity = _field(profile, "entity", {})
    dataset_names = _dataset_names_for_map(comparison, str(_field(entity, "name", "")))
    source_rows: list[SourceContribution] = []
    for index, dataset_name in enumerate(dataset_names):
        metadata = dataset_metadata_for_name(str(dataset_name))
        if metadata is None:
            continue
        facts = tuple(source_contribution_bullets(metadata.name))
        source_rows.append(
            SourceContribution(
                dataset=metadata.name,
                category=metadata.category,
                summary=dataset_citizen_summary(metadata.name),
                contributes=facts,
                evidence_count=_evidence_for_dataset(view, metadata.name),
                relationship_count=len(_field(profile, "relationships", ())),
                overlap_note=_overlap_note(dataset_names, metadata.name, index),
            )
        )

    return {
        "entity": {
            "id": str(_field(entity, "id", "")),
            "name": _field(entity, "name", ""),
            "type": _field(entity, "entity_type", ""),
        },
        "sources": [
            {
                "dataset": row.dataset,
                "category": row.category,
                "summary": row.summary,
                "contributes": list(row.contributes),
                "evidence_count": row.evidence_count,
                "relationship_count": row.relationship_count,
                "overlap_note": row.overlap_note,
                "status": _plugin_field(row.dataset, "status"),
                "concepts": _plugin_field(row.dataset, "concepts"),
                "concepts_text": " | ".join(_plugin_field(row.dataset, "concepts")),
                "evidence_types": _plugin_field(row.dataset, "evidence_types"),
                "evidence_types_text": " | ".join(_plugin_field(row.dataset, "evidence_types")),
                "timeline_contribution": _plugin_field(row.dataset, "timeline_contribution_text"),
            }
            for row in source_rows
        ],
        "summary": _field(comparison, "coverage_summary", _field(view, "summary", "")),
        "overlap_areas": _field(comparison, "overlap_areas", []),
        "neutrality_notice": "This view is descriptive only.",
    }


def _empty_source_contributions() -> dict[str, object]:
    return {
        "entity": {"id": "", "name": "", "type": ""},
        "sources": [],
        "summary": "No public source records were found for this entity.",
        "overlap_areas": [],
        "neutrality_notice": "This view is descriptive only.",
    }


def _evidence_for_dataset(view, dataset_name: str) -> int:
    total = 0
    for group in _field(view, "evidence_groups", ()):
        if str(_field(group, "dataset", "")) == dataset_name:
            total += len(_field(group, "links", ()))
    return total


def _overlap_note(dataset_names: list[str], dataset_name: str, index: int) -> str:
    if len(dataset_names) == 1:
        return f"{dataset_name} is the only source in the current workspace view."
    if index == 0:
        return f"{dataset_name} overlaps with the other source records in this investigation."
    return f"{dataset_name} adds distinct records to the shared investigation view."


def _dataset_names_for_map(comparison: dict[str, object], entity_name: str) -> list[str]:
    dataset_names = list(str(item) for item in _field(comparison, "datasets_present", ()))
    try:
        summary = build_complete_demo_case_summary(load_complete_demo_case_payload())
    except Exception:  # noqa: BLE001
        return dataset_names
    if entity_name.strip().lower() != summary.main_entity.strip().lower():
        return dataset_names
    for dataset in summary.datasets:
        if dataset not in dataset_names:
            dataset_names.append(dataset)
    return dataset_names


def _plugin_field(dataset_name: str, field: str):
    plugin = get_source_plugin(dataset_name)
    if plugin is None:
        return [] if field in {"concepts", "evidence_types"} else ""
    if field == "status":
        return plugin_status_value(plugin)
    if field == "concepts":
        return list(plugin_concept_names(plugin))
    if field == "evidence_types":
        return list(plugin.evidence_types)
    if field == "timeline_contribution_text":
        return plugin.timeline_contribution
    return ""
