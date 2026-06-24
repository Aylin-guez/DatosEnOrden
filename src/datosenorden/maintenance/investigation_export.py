from __future__ import annotations

from datosenorden.db.session import SessionLocal
from datosenorden.maintenance.investigation_story import build_investigation_story
from datosenorden.maintenance.investigation_view import build_investigation_view
from datosenorden.maintenance.source_trace import build_source_trace


def export_investigation_markdown(entity_id: str) -> str:
    with SessionLocal() as session:
        view = build_investigation_view(session, entity_id)

    if view is None:
        return _empty_markdown()

    story = build_investigation_story(entity_id)
    trace = build_source_trace(entity_id)
    profile = _field(view, "profile", {})
    entity = _field(profile, "entity", {})
    sources = tuple(_field(trace, "sources", ()))

    lines: list[str] = [f"# {_field(entity, 'name', '')}", ""]
    lines.extend(["## Neutral Summary", "", str(_field(story, "summary", _field(view, "summary", ""))), ""])

    lines.extend(["## Sources Consulted", ""])
    if sources:
        for source in sources:
            lines.append(
                f"- {_field(source, 'dataset', '')}: {_field(source, 'contribution', '')} "
                f"({_field(source, 'evidence_count', 0)} evidence, {_field(source, 'relationship_count', 0)} relationships)"
            )
    else:
        lines.append("- No public source records were found.")
    lines.append("")

    lines.extend(["## What Each Source Contributes", ""])
    if sources:
        for source in sources:
            lines.append(f"### {_field(source, 'dataset', '')}")
            lines.append(str(_field(source, "contribution", "")))
            for fact in _field(source, "facts", ()):
                lines.append(f"- {fact}")
            lines.append("")
    else:
        lines.append("No source contributions were found.")
        lines.append("")

    lines.extend(["## Timeline Highlights", ""])
    timeline_highlights = tuple(str(item) for item in _field(story, "timeline_highlights", ()))
    if timeline_highlights:
        for item in timeline_highlights:
            lines.append(f"- {item}")
    else:
        lines.append("- No timeline highlights were found.")
    lines.append("")

    lines.extend(["## Important Connections", ""])
    important_connections = tuple(str(item) for item in _field(story, "important_connections", ()))
    if important_connections:
        for item in important_connections:
            lines.append(f"- {item}")
    else:
        lines.append("- No important connections were found.")
    lines.append("")

    lines.extend(["## Evidence Summary", ""])
    metrics = _field(view, "metrics", {})
    lines.append(f"- Total evidence items: {_field(metrics, 'evidence', 0)}")
    lines.append(f"- Total relationships: {_field(metrics, 'relationships', 0)}")
    lines.append(
        "- Sources consulted: "
        + (", ".join(str(_field(source, "dataset", "")) for source in sources) if sources else "none")
    )
    lines.append("")

    lines.extend(["## Technical Appendix", ""])
    lines.append(f"- Entity ID: {_field(entity, 'id', '')}")
    lines.append(f"- Entity type: {_field(entity, 'entity_type', '')}")
    lines.append(f"- Overlap summary: {_field(trace, 'overlap_summary', '')}")
    lines.append(f"- Neutrality notice: {_field(trace, 'neutrality_notice', '')}")

    timeline = _field(view, "timeline", None)
    for event in _field(timeline, "events", ()):
        lines.append(f"- Timeline event claim_id: {_field(event, 'claim_id', '')}")
        lines.append(f"  - dataset: {_field(event, 'dataset', '')}")
        lines.append(f"  - dataset_name: {_field(event, 'dataset_name', '')}")
        lines.append(f"  - predicate: {_field(event, 'predicate', '')}")
        lines.append(f"  - source_record_id: {_field(event, 'source_record_id', '')}")

    for group in _field(view, "evidence_groups", ()):
        for link in _field(group, "links", ()):
            published_at = _field(link, "published_at", None)
            lines.append(f"- Evidence URL: {_field(link, 'url', '')}")
            lines.append(f"  - title: {_field(link, 'title', '')}")
            lines.append(f"  - published_at: {published_at.isoformat() if published_at else ''}")

    for row in _field(_field(view, "profile", {}), "direct_neighbors", ()):
        lines.append(f"- Relationship: {_field(row, 'relationship_id', '')}")
        lines.append(f"  - relationship_type: {_field(row, 'relationship_type', '')}")
        lines.append(f"  - direction: {_field(row, 'direction', '')}")
        lines.append(f"  - neighbor_id: {_field(_field(row, 'neighbor', {}), 'id', '')}")

    return "\n".join(lines).rstrip() + "\n"


def _empty_markdown() -> str:
    return (
        "# Investigation\n\n"
        "## Neutral Summary\n\n"
        "No public source records were found for this entity.\n\n"
        "## Sources Consulted\n\n"
        "- No public source records were found.\n\n"
        "## What Each Source Contributes\n\n"
        "No source contributions were found.\n\n"
        "## Timeline Highlights\n\n"
        "- No timeline highlights were found.\n\n"
        "## Important Connections\n\n"
        "- No important connections were found.\n\n"
        "## Evidence Summary\n\n"
        "- Total evidence items: 0\n"
        "- Total relationships: 0\n"
        "- Sources consulted: none\n\n"
        "## Technical Appendix\n\n"
        "- Entity ID: \n"
        "- Entity type: \n"
        "- Overlap summary: No public source records were found for this entity.\n"
        "- Neutrality notice: This trace is descriptive only. It presents public records without judgment or inference.\n"
    )


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
