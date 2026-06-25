from __future__ import annotations

from html import escape
from pathlib import Path
import re

from datosenorden.db.session import SessionLocal
from datosenorden.maintenance.dataset_metadata import dataset_metadata_for_name
from datosenorden.maintenance.investigation_graph import build_investigation_graph
from datosenorden.maintenance.investigation_story import build_investigation_story
from datosenorden.maintenance.investigation_timeline import build_investigation_timeline
from datosenorden.maintenance.investigation_view import build_investigation_view
from datosenorden.maintenance.safe_access import _field
from datosenorden.maintenance.source_contributions import build_source_contributions
from datosenorden.maintenance.source_trace import build_source_trace


def export_investigation_report(entity_id: str) -> str:
    with SessionLocal() as session:
        view = build_investigation_view(session, entity_id)

    if view is None:
        path = Path("reports") / f"investigation_{_slugify(entity_id)}.html"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(_render_empty_report(entity_id), encoding="utf-8")
        return str(path)

    story = build_investigation_story(entity_id)
    trace = build_source_trace(entity_id)
    graph = build_investigation_graph(entity_id)
    timeline = build_investigation_timeline(entity_id)
    contributions = build_source_contributions(entity_id)
    profile = _field(view, "profile", {})
    entity = _field(profile, "entity", {})
    entity_name = str(_field(entity, "name", ""))
    entity_slug = _slugify(entity_name)
    path = Path("reports") / f"investigation_{entity_slug}.html"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        _render_report_html(
            entity_name=entity_name,
            summary=_field(story, "summary", _field(view, "summary", "")),
            trace=trace,
            graph=graph,
            timeline=timeline,
            contributions=contributions,
            view=view,
        ),
        encoding="utf-8",
    )
    return str(path)


def _render_report_html(
    *,
    entity_name: str,
    summary: str,
    trace: dict[str, object],
    graph: dict[str, object],
    timeline: dict[str, object],
    contributions: dict[str, object],
    view,
) -> str:  # noqa: ANN001
    source_rows = tuple(_field(contributions, "sources", ()))
    dataset_sections = []
    for row in source_rows:
        dataset_sections.append(
            f"""
            <section class="card">
              <h3>{escape(str(_field(row, 'dataset', '')))}</h3>
              <p class="muted">{escape(str(_field(row, 'summary', '')))}</p>
              <ul>{''.join(f'<li>{escape(str(item))}</li>' for item in _field(row, 'contributes', ()))}</ul>
              <p class="muted">{escape(str(_field(row, 'overlap_note', '')))}</p>
            </section>
            """
        )

    timeline_blocks = []
    for year in _field(timeline, "years", ()):
        category_blocks = []
        for category in _field(year, "categories", ()):
            items = "".join(
                f"<li><strong>{escape(str(_field(item, 'label', '')))}</strong> "
                f"<span class='muted'>({escape(str(_field(item, 'dataset', '')))}): {escape(str(_field(item, 'explanation', '')))}</span></li>"
                for item in _field(category, "items", ())
            )
            category_blocks.append(
                f"<div><h4>{escape(str(_field(category, 'category', '')))}</h4><ul>{items}</ul></div>"
            )
        timeline_blocks.append(
            f"<section class='card'><h3>{escape(str(_field(year, 'year', '')))}</h3>{''.join(category_blocks)}</section>"
        )

    graph_nodes = "".join(
        f"<li><strong>{escape(str(_field(node, 'label', '')))}</strong> "
        f"<span class='muted'>[{escape(str(_field(node, 'category', '')))}]</span></li>"
        for node in _field(graph, "nodes", ())
    )
    graph_edges = "".join(
        f"<li>{escape(str(_field(edge, 'label', '')))}: {escape(str(_field(edge, 'source', '')))} -> {escape(str(_field(edge, 'target', '')))}</li>"
        for edge in _field(graph, "edges", ())
    )

    sources_consulted = "".join(
        f"<li>{escape(str(_field(source, 'dataset', '')))} - {escape(str(_field(source, 'contribution', '')))}</li>"
        for source in _field(trace, "sources", ())
    )
    evidence_rows = "".join(
        f"<li>{escape(str(_field(link, 'title', '')))} <span class='muted'>{escape(str(_field(link, 'url', '')))}</span></li>"
        for group in _field(view, "evidence_groups", ())
        for link in _field(group, "links", ())
    )
    relationship_rows = "".join(
        f"<li>{escape(str(_field(row, 'relationship_type', '')))}: {escape(str(_field(_field(row, 'related_entity', {}), 'name', '')))}</li>"
        for row in _field(_field(view, "profile", {}), "relationships", ())
    )
    entity = _field(_field(view, "profile", {}), "entity", {})

    return f"""<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Investigation report: {escape(entity_name)}</title>
  <style>
    :root {{
      --bg: #f7f7f5;
      --panel: #ffffff;
      --ink: #13202d;
      --muted: #52616b;
      --line: #d8dee4;
      --accent: #0f766e;
      --shadow: 0 16px 44px rgba(31, 41, 51, 0.12);
    }}
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; color: var(--ink); font-family: "Segoe UI", Arial, sans-serif; background: var(--bg); }}
    main {{ max-width: 1600px; width: 95vw; margin: 0 auto; padding: 28px 0 48px; }}
    .hero, .card {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 20px;
      box-shadow: var(--shadow);
      padding: 18px;
      margin-bottom: 18px;
    }}
    h1, h2, h3, h4 {{ margin: 0 0 10px; }}
    .muted {{ color: var(--muted); }}
    .grid {{ display: grid; gap: 18px; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); }}
    ul {{ margin: 0; padding-left: 20px; }}
    li {{ margin: 0 0 6px; }}
    .wide {{ grid-column: 1 / -1; }}
  </style>
</head>
<body>
  <main>
    <section class="hero">
      <h1>{escape(entity_name)}</h1>
      <p class="muted">{escape(summary)}</p>
      <p class="muted">{escape(str(_field(contributions, 'summary', '')))}</p>
      <p class="muted">{escape(str(_field(trace, 'neutrality_notice', '')))}</p>
    </section>
    <section class="card wide">
      <h2>Source Contributions</h2>
      <div class="grid">{''.join(dataset_sections) or '<p class="muted">No source contributions were found.</p>'}</div>
    </section>
    <section class="card wide">
      <h2>Summary</h2>
      <p>{escape(str(_field(graph, 'summary', '')))}</p>
    </section>
    <section class="grid">
      <section class="card wide">
        <h2>Sources</h2>
        <ul>{sources_consulted or '<li class="muted">No sources were found.</li>'}</ul>
      </section>
      <section class="card wide">
        <h2>Timeline</h2>
        {''.join(timeline_blocks) or '<p class="muted">No timeline records were found.</p>'}
      </section>
      <section class="card wide">
        <h2>Relationships</h2>
        <ul>{relationship_rows or '<li class="muted">No relationships were found.</li>'}</ul>
      </section>
      <section class="card wide">
        <h2>Evidence</h2>
        <ul>{evidence_rows or '<li class="muted">No evidence was found.</li>'}</ul>
      </section>
      <section class="card wide">
        <h2>Graph</h2>
        <h3>Nodes</h3>
        <ul>{graph_nodes or '<li class="muted">No graph nodes were found.</li>'}</ul>
        <h3>Edges</h3>
        <ul>{graph_edges or '<li class="muted">No graph edges were found.</li>'}</ul>
      </section>
        <section class="card wide">
        <h2>Technical Appendix</h2>
        <ul>
          <li>Entity ID: {escape(str(_field(entity, 'id', '')))}</li>
          <li>Entity type: {escape(str(_field(entity, 'entity_type', '')))}</li>
          <li>Trace summary: {escape(str(_field(trace, 'overlap_summary', '')))}</li>
        </ul>
      </section>
    </section>
  </main>
</body>
</html>
"""


def _render_empty_report(entity_id: str) -> str:
    return f"""<!doctype html>
<html lang="es">
<head><meta charset="utf-8" /><title>Investigation report: {escape(entity_id)}</title></head>
<body><p>No public source records were found for this entity.</p></body>
</html>
"""


def _slugify(value: str) -> str:
    text = value.strip().lower()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    text = re.sub(r"_+", "_", text).strip("_")
    return text or "entity"

