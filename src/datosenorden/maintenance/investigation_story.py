from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
from datetime import date

from datosenorden.db.session import SessionLocal
from datosenorden.maintenance.entity_comparison import build_entity_comparison
from datosenorden.maintenance.investigation_view import build_investigation_view


@dataclass(frozen=True)
class _StoryContext:
    entity_name: str
    entity_type: str
    datasets_present: tuple[str, ...]
    summary: str
    key_findings: tuple[str, ...]
    important_connections: tuple[str, ...]
    timeline_highlights: tuple[str, ...]
    sources_consulted: tuple[str, ...]
    questions_for_citizens: tuple[str, ...]


def build_investigation_story(entity_id: str) -> dict[str, object]:
    with SessionLocal() as session:
        view = build_investigation_view(session, entity_id)

    comparison = build_entity_comparison(entity_id)
    if view is None:
        return _empty_story()

    context = _build_story_context(view, comparison)
    return {
        "headline": context.entity_name,
        "summary": context.summary,
        "key_findings": list(context.key_findings),
        "important_connections": list(context.important_connections),
        "timeline_highlights": list(context.timeline_highlights),
        "sources_consulted": list(context.sources_consulted),
        "questions_for_citizens": list(context.questions_for_citizens),
    }


def _build_story_context(view, comparison: dict[str, object]) -> _StoryContext:  # noqa: ANN001
    entity_name = str(view.profile.entity.name)
    entity_type = str(view.profile.entity.entity_type)
    datasets_present = tuple(str(dataset) for dataset in comparison.get("datasets_present", ()))
    summary = _summary_text(entity_name, datasets_present, view.summary)
    key_findings = _key_findings(comparison, view)
    important_connections = _important_connections(view, comparison)
    timeline_highlights = _timeline_highlights(view)
    sources_consulted = _sources_consulted(comparison)
    questions_for_citizens = _questions_for_citizens(view, comparison)
    return _StoryContext(
        entity_name=entity_name,
        entity_type=entity_type,
        datasets_present=datasets_present,
        summary=summary,
        key_findings=key_findings,
        important_connections=important_connections,
        timeline_highlights=timeline_highlights,
        sources_consulted=sources_consulted,
        questions_for_citizens=questions_for_citizens,
    )


def _empty_story() -> dict[str, object]:
    summary = "No public source records were found for this organization."
    return {
        "headline": "Investigation story",
        "summary": summary,
        "key_findings": [summary],
        "important_connections": [],
        "timeline_highlights": [],
        "sources_consulted": [],
        "questions_for_citizens": [
            "Would you like to search another organization?",
            "Would you like to compare information across datasets?",
        ],
    }


def _summary_text(entity_name: str, datasets_present: tuple[str, ...], fallback_summary: str) -> str:
    if not datasets_present:
        return fallback_summary
    if len(datasets_present) == 1:
        return f"{entity_name} appears in {datasets_present[0]} records. The story below organizes what the public records say."
    return (
        f"{entity_name} appears in multiple public datasets: {', '.join(datasets_present)}. "
        "The story below organizes what each source says in neutral terms."
    )


def _key_findings(comparison: dict[str, object], view) -> tuple[str, ...]:  # noqa: ANN001
    findings: list[str] = []
    datasets_present = [str(dataset) for dataset in comparison.get("datasets_present", ())]
    if datasets_present:
        if len(datasets_present) == 1:
            findings.append(f"The organization appears in {datasets_present[0]} records.")
        else:
            findings.append("The organization appears in multiple public datasets.")

    observations = [str(item) for item in comparison.get("consistency_observations", ())]
    findings.extend(observations[:3])

    if getattr(view, "procurement_items", ()):
        findings.append("The organization appears in procurement records.")
    if getattr(view, "lobby_items", ()):
        findings.append("The organization is connected to public meetings.")
    if getattr(view, "role_items", ()):
        findings.append("The organization is connected to public transparency records.")

    deduped = _dedupe_preserve_order(findings)
    if not deduped:
        deduped.append("No public source records were found for this organization.")
    return tuple(deduped)


def _important_connections(view, comparison: dict[str, object]) -> tuple[str, ...]:  # noqa: ANN001
    connections: list[str] = []
    for item in getattr(view, "procurement_items", ()):
        connections.append(
            f"{item.dataset}: {item.contract_name} is linked to {item.supplier}."
        )
    for item in getattr(view, "lobby_items", ()):
        date_text = item.date.isoformat() if isinstance(item.date, date) else "an undated meeting"
        connections.append(
            f"{item.dataset}: {item.organization} appears in public meetings with {item.counterparty} on {date_text}."
        )
    for item in getattr(view, "role_items", ()):
        connections.append(
            f"{item.dataset}: {item.holder} is recorded with {item.role_title} during {item.period}."
        )

    if not connections:
        for fact in comparison.get("dataset_facts", ()):
            dataset = str(fact.get("dataset", ""))
            facts = [str(entry) for entry in fact.get("facts", ())]
            if not facts:
                continue
            connections.append(f"{dataset}: {facts[0]}.")
            if len(connections) >= 3:
                break

    return tuple(_dedupe_preserve_order(connections)[:5])


def _timeline_highlights(view) -> tuple[str, ...]:  # noqa: ANN001
    events = getattr(getattr(view, "timeline", None), "events", ())
    highlights: list[str] = []
    seen: set[tuple[int, str, str]] = set()
    for event in events:
        year = int(event.event_date.year)
        key = (year, str(event.dataset), str(event.title))
        if key in seen:
            continue
        seen.add(key)
        highlights.append(f"{year}: {event.title}")
        if len(highlights) >= 5:
            break
    return tuple(highlights)


def _sources_consulted(comparison: dict[str, object]) -> tuple[str, ...]:
    datasets_present = [str(dataset) for dataset in comparison.get("datasets_present", ())]
    return tuple(datasets_present)


def _questions_for_citizens(view, comparison: dict[str, object]) -> tuple[str, ...]:  # noqa: ANN001
    questions: list[str] = []
    datasets_present = [str(dataset) for dataset in comparison.get("datasets_present", ())]
    normalized = " ".join(datasets_present).lower()

    if len(datasets_present) > 1:
        questions.append("Would you like to compare information across datasets?")
    if getattr(view, "procurement_items", ()):
        questions.append("Would you like to inspect procurement records?")
    if getattr(view, "lobby_items", ()):
        questions.append("Would you like to review related public meetings?")
    if getattr(view, "role_items", ()):
        questions.append("Would you like to inspect transparency records?")
    if "contraloria" in normalized:
        questions.append("Would you like to review control reports?")
    if "municipal" in normalized:
        questions.append("Would you like to inspect municipal records?")

    if not questions:
        questions.extend(
            [
                "Would you like to search another organization?",
                "Would you like to compare information across datasets?",
            ]
        )

    return tuple(_dedupe_preserve_order(questions)[:5])


def _dedupe_preserve_order(values: list[str]) -> list[str]:
    return list(OrderedDict.fromkeys(value for value in values if value))


_ORIGINAL_KEY_FINDINGS = _key_findings
_ORIGINAL_IMPORTANT_CONNECTIONS = _important_connections
_ORIGINAL_QUESTIONS_FOR_CITIZENS = _questions_for_citizens


def _key_findings(comparison: dict[str, object], view) -> tuple[str, ...]:  # type: ignore[override]
    findings = list(_ORIGINAL_KEY_FINDINGS(comparison, view))
    if any(getattr(item, "dataset", "") == "SERVEL" for item in getattr(view, "role_items", ())):
        findings = [
            item
            for item in findings
            if item != "The organization is connected to public transparency records."
        ]
        if "The entity is connected to elected authority records." not in findings:
            findings.append("The entity is connected to elected authority records.")
    return tuple(_dedupe_preserve_order(findings)[:5])


def _important_connections(view, comparison: dict[str, object]) -> tuple[str, ...]:  # type: ignore[override]
    return _ORIGINAL_IMPORTANT_CONNECTIONS(view, comparison)


def _questions_for_citizens(view, comparison: dict[str, object]) -> tuple[str, ...]:  # type: ignore[override]
    questions = list(_ORIGINAL_QUESTIONS_FOR_CITIZENS(view, comparison))
    if any(getattr(item, "dataset", "") == "SERVEL" for item in getattr(view, "role_items", ())):
        questions = [
            item for item in questions if item != "Would you like to inspect transparency records?"
        ]
        questions.append("Would you like to review elected authority records?")
    return tuple(_dedupe_preserve_order(questions)[:5])
