from __future__ import annotations

from collections import OrderedDict, defaultdict
from dataclasses import dataclass

from datosenorden.db.session import SessionLocal
from datosenorden.maintenance.dataset_metadata import dataset_citizen_summary
from datosenorden.maintenance.dataset_metadata import dataset_metadata_for_name
from datosenorden.maintenance.complete_demo_case import build_complete_demo_case_summary
from datosenorden.maintenance.complete_demo_case import load_complete_demo_case_payload
from datosenorden.maintenance.entity_comparison import build_entity_comparison
from datosenorden.maintenance.explanations import dataset_display_name
from datosenorden.maintenance.investigation_story import build_investigation_story
from datosenorden.maintenance.investigation_view import build_investigation_view
from datosenorden.maintenance.safe_access import _field


NEUTRALITY_NOTICE = (
    "This trace is descriptive only. It presents public records without judgment or inference."
)


@dataclass(frozen=True)
class _SourceCard:
    dataset: str
    contribution: str
    evidence_count: int
    relationship_count: int
    facts: tuple[str, ...]
    technical: tuple[str, ...]


def build_source_trace(entity_id: str) -> dict[str, object]:
    with SessionLocal() as session:
        view = build_investigation_view(session, entity_id)

    comparison = build_entity_comparison(entity_id)
    story = build_investigation_story(entity_id)
    if view is None:
        return _empty_trace()

    sources = _build_sources(view, comparison, story)
    profile = _field(view, "profile", {})
    entity = _field(profile, "entity", {})
    entity_name = str(_field(entity, "name", ""))
    connections = [
        {
            "from_source": source.dataset,
            "to_entity": entity_name,
            "meaning": source.contribution,
            "evidence_count": source.evidence_count,
        }
        for source in sources
    ]
    return {
        "entity": {
            "id": str(_field(entity, "id", "")),
            "name": entity_name,
            "type": _field(entity, "entity_type", ""),
        },
        "sources": [
            {
                "dataset": source.dataset,
                "contribution": source.contribution,
                "evidence_count": source.evidence_count,
                "relationship_count": source.relationship_count,
                "facts": list(source.facts),
                "technical": list(source.technical),
            }
            for source in sources
        ],
        "connections": connections,
        "overlap_summary": _overlap_summary(entity_name, comparison, sources),
        "overlap_areas": list(_field(comparison, "overlap_areas", [])),
        "neutrality_notice": NEUTRALITY_NOTICE,
    }


def render_source_trace_text(trace: dict[str, object]) -> str:
    lines = [
        "source_trace:",
        f"entity: {_field(_field(trace, 'entity', {}), 'name', '')}",
        "",
        "sources:",
    ]
    for source in _field(trace, "sources", []):
        lines.extend(
            [
                f"- {_field(source, 'dataset', '')}",
                f"  contribution: {_field(source, 'contribution', '')}",
                f"  evidence_count: {_field(source, 'evidence_count', 0)}",
                f"  relationship_count: {_field(source, 'relationship_count', 0)}",
                f"  facts: {' | '.join(str(item) for item in _field(source, 'facts', []))}",
            ]
        )
        technical = _field(source, "technical", [])
        if technical:
            lines.append(f"  technical: {' | '.join(str(item) for item in technical)}")
    lines.extend(
        [
            "",
            f"overlap_summary: {_field(trace, 'overlap_summary', '')}",
            f"neutrality_notice: {_field(trace, 'neutrality_notice', '')}",
        ]
    )
    return "\n".join(lines).rstrip()


def _build_sources(view, comparison: dict[str, object], story: dict[str, object]) -> tuple[_SourceCard, ...]:  # noqa: ANN001
    dataset_facts = {
        str(_field(item, "dataset", "")): tuple(str(fact) for fact in _field(item, "facts", ()))
        for item in _field(comparison, "dataset_facts", ())
    }
    labels = _ordered_labels(view, comparison)
    grouped = {label: _empty_source(label) for label in labels}

    for dataset, facts in dataset_facts.items():
        grouped.setdefault(dataset, _empty_source(dataset)).facts.extend(facts)  # type: ignore[attr-defined]

    for item in _field(view, "procurement_items", ()):
        label = str(_field(item, "dataset", ""))
        bucket = grouped.setdefault(label, _empty_source(label))
        bucket.relationship_count += 1
        bucket.evidence_count += int(_field(item, "evidence_count", 0))
        bucket.facts.extend([
            f"Procurement item: {_field(item, 'contract_name', '')}",
            f"Supplier: {_field(item, 'supplier', '')}",
        ])
        bucket.technical.extend([
            f"procurement_items={bucket.relationship_count}",
            f"dataset={label}",
        ])

    for item in _field(view, "lobby_items", ()):
        label = str(_field(item, "dataset", ""))
        bucket = grouped.setdefault(label, _empty_source(label))
        bucket.relationship_count += 1
        bucket.evidence_count += int(_field(item, "evidence_count", 0))
        bucket.facts.extend([
            f"Meeting date: {_field(item, 'date', '')}",
            f"Organization: {_field(item, 'organization', '')}",
            f"Counterparty: {_field(item, 'counterparty', '')}",
            f"Subject: {_field(item, 'subject', '')}",
        ])
        bucket.technical.extend([
            f"lobby_items={bucket.relationship_count}",
            f"dataset={label}",
        ])

    for item in _field(view, "role_items", ()):
        label = str(_field(item, "dataset", ""))
        bucket = grouped.setdefault(label, _empty_source(label))
        bucket.relationship_count += 1
        bucket.evidence_count += int(_field(item, "evidence_count", 0))
        bucket.facts.extend([
            f"Holder: {_field(item, 'holder', '')}",
            f"Role: {_field(item, 'role_title', '')}",
            f"Period: {_field(item, 'period', '')}",
        ])
        bucket.technical.extend([
            f"role_items={bucket.relationship_count}",
            f"dataset={label}",
        ])

    for group in _field(view, "evidence_groups", ()):
        label = str(_field(group, "dataset", ""))
        bucket = grouped.setdefault(label, _empty_source(label))
        links = tuple(_field(group, "links", ()))
        bucket.evidence_count += len(links)
        bucket.facts.extend(
            f"Evidence: {_field(link, 'title', '')}" for link in links[:3]
        )
        if links:
            bucket.technical.append(f"evidence_links={len(links)}")

    timeline = _field(view, "timeline", None)
    for event in _field(timeline, "events", ()):
        label = dataset_display_name(str(_field(event, "dataset_name", "")))
        bucket = grouped.setdefault(label, _empty_source(label))
        bucket.relationship_count += 1
        bucket.evidence_count += int(_field(event, "evidence_count", 0))
        bucket.facts.append(str(_field(event, "title", "")))
        bucket.technical.extend(
            [
                f"timeline_event={_field(event, 'claim_id', '')}",
                f"predicate={_field(event, 'predicate', '')}",
            ]
        )

    story_sources = tuple(str(dataset) for dataset in _field(story, "sources_consulted", ()))
    for dataset in story_sources:
        grouped.setdefault(dataset, _empty_source(dataset))

    return tuple(
        _finalize_source(bucket)
        for bucket in grouped.values()
        if bucket.dataset
    )


def _ordered_labels(view, comparison: dict[str, object]) -> tuple[str, ...]:  # noqa: ANN001
    labels = list(OrderedDict.fromkeys(str(item) for item in _field(comparison, "datasets_present", ())))
    for badge in _field(view, "dataset_badges", ()):
        badge_text = str(badge)
        if badge_text not in labels:
            labels.append(badge_text)
    timeline = _field(view, "timeline", None)
    for event in _field(timeline, "events", ()):
        label = dataset_display_name(str(_field(event, "dataset_name", "")))
        if label not in labels:
            labels.append(label)
    entity_name = str(_field(_field(_field(view, "profile", {}), "entity", {}), "name", ""))
    for label in _complete_demo_labels(entity_name):
        if label not in labels:
            labels.append(label)
    return tuple(labels)


def _complete_demo_labels(entity_name: str) -> tuple[str, ...]:
    try:
        summary = build_complete_demo_case_summary(load_complete_demo_case_payload())
    except Exception:  # noqa: BLE001
        return ()
    if entity_name.strip().lower() != summary.main_entity.strip().lower():
        return ()
    return summary.datasets


def _empty_source(dataset: str) -> _MutableSourceCard:
    return _MutableSourceCard(dataset=dataset, contribution=_contribution_for(dataset), evidence_count=0, relationship_count=0)


@dataclass
class _MutableSourceCard:
    dataset: str
    contribution: str
    evidence_count: int
    relationship_count: int
    facts: list[str]
    technical: list[str]

    def __init__(self, dataset: str, contribution: str, evidence_count: int, relationship_count: int) -> None:
        self.dataset = dataset
        self.contribution = contribution
        self.evidence_count = evidence_count
        self.relationship_count = relationship_count
        self.facts = []
        self.technical = []


def _finalize_source(bucket: _MutableSourceCard) -> _SourceCard:
    facts = tuple(_dedupe(bucket.facts))
    technical = tuple(_dedupe(bucket.technical))
    return _SourceCard(
        dataset=bucket.dataset,
        contribution=bucket.contribution,
        evidence_count=bucket.evidence_count,
        relationship_count=bucket.relationship_count,
        facts=facts,
        technical=technical,
    )


def _contribution_for(dataset: str) -> str:
    metadata = dataset_metadata_for_name(dataset)
    if metadata is None:
        return "Public records associated with this entity."
    return dataset_citizen_summary(metadata.name)


def _overlap_summary(entity_name: str, comparison: dict[str, object], sources: tuple[_SourceCard, ...]) -> str:
    if not sources:
        return f"No public source records were found for {entity_name or 'this entity'}."
    datasets = [source.dataset for source in sources if source.evidence_count or source.relationship_count or source.facts]
    if not datasets:
        return f"{entity_name} is listed in the comparison set, but no public source records were found."
    if len(datasets) == 1:
        return f"{entity_name} is represented in {datasets[0]}. The trace is descriptive and neutral."
    return (
        f"{entity_name} appears across multiple public sources: {', '.join(datasets)}. "
        "The overlap is descriptive and neutral."
    )


def _dedupe(values: list[str]) -> list[str]:
    return list(OrderedDict.fromkeys(value for value in values if value))


def _empty_trace() -> dict[str, object]:
    return {
        "entity": {"id": "", "name": "", "type": ""},
        "sources": [],
        "connections": [],
        "overlap_summary": "No public source records were found for this entity.",
        "neutrality_notice": NEUTRALITY_NOTICE,
    }
