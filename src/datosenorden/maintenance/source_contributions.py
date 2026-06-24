from __future__ import annotations

from dataclasses import dataclass

from datosenorden.db.session import SessionLocal
from datosenorden.maintenance.dataset_metadata import dataset_citizen_summary
from datosenorden.maintenance.dataset_metadata import dataset_metadata_for_name
from datosenorden.maintenance.dataset_metadata import source_contribution_bullets
from datosenorden.maintenance.entity_comparison import build_entity_comparison
from datosenorden.maintenance.investigation_view import build_investigation_view


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

    dataset_names = list(_field(comparison, "datasets_present", ()))
    profile = _field(view, "profile", {})
    entity = _field(profile, "entity", {})
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


def _field(obj: object, name: str, fallback: object = "") -> object:
    if obj is None:
        return fallback
    if isinstance(obj, dict):
        return obj.get(name, fallback)
    if hasattr(obj, name):
        return getattr(obj, name, fallback)
    for method_name in ("model_dump", "dict"):
        method = getattr(obj, method_name, None)
        if callable(method):
            try:
                dumped = method()
            except TypeError:
                continue
            if isinstance(dumped, dict):
                return dumped.get(name, fallback)
    return fallback
