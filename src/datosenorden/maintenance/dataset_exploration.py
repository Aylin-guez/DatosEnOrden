from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from html import escape

from sqlalchemy import distinct, func, select
from sqlalchemy.orm import Session

from datosenorden.models import Claim, Entity, Evidence, RelationshipPublic, SourceRecord

PURCHASE_ORDER_RECORD_TYPE = "chilecompra:purchase_order"
BUYER_PREDICATE = "ISSUES_PURCHASE_ORDER"
SUPPLIER_PREDICATE = "RECEIVES_CONTRACT"
DEFAULT_TOP_LIMIT = 10


@dataclass(frozen=True)
class MetricRow:
    label: str
    count: int


@dataclass(frozen=True)
class DatasetExploration:
    generated_at: datetime
    summary_metrics: tuple[MetricRow, ...]
    top_buyers: tuple[MetricRow, ...]
    top_suppliers: tuple[MetricRow, ...]
    purchase_orders_by_status: tuple[MetricRow, ...]
    rejected_source_records_by_error: tuple[MetricRow, ...]
    claims_by_predicate: tuple[MetricRow, ...]
    relationships_by_type: tuple[MetricRow, ...]


def explore_dataset(session: Session, top_limit: int = DEFAULT_TOP_LIMIT) -> DatasetExploration:
    if top_limit < 1:
        raise ValueError("top_limit must be greater than zero")

    return DatasetExploration(
        generated_at=datetime.now(timezone.utc),
        summary_metrics=_summary_metrics(session),
        top_buyers=_top_entities_by_purchase_orders(session, BUYER_PREDICATE, top_limit),
        top_suppliers=_top_entities_by_purchase_orders(session, SUPPLIER_PREDICATE, top_limit),
        purchase_orders_by_status=_group_source_records_by_status(session),
        rejected_source_records_by_error=_group_rejected_source_records_by_error(session, top_limit),
        claims_by_predicate=_group_claims_by_predicate(session),
        relationships_by_type=_group_relationships_by_type(session),
    )


def render_dataset_exploration_text(exploration: DatasetExploration) -> str:
    sections = [
        ("summary_metrics", exploration.summary_metrics),
        ("top_buyers_by_purchase_orders", exploration.top_buyers),
        ("top_suppliers_by_purchase_orders", exploration.top_suppliers),
        ("purchase_orders_by_status", exploration.purchase_orders_by_status),
        ("rejected_source_records_by_error_log", exploration.rejected_source_records_by_error),
        ("claims_by_predicate", exploration.claims_by_predicate),
        ("relationship_public_by_relationship_type", exploration.relationships_by_type),
    ]
    lines = [f"dataset_exploration: generated_at={exploration.generated_at.isoformat()}"]
    for title, rows in sections:
        lines.append("")
        lines.append(f"{title}:")
        if not rows:
            lines.append("  (no rows)")
            continue
        for row in rows:
            lines.append(f"  {row.label}: {row.count}")
    return "\n".join(lines)


def render_dataset_report_html(exploration: DatasetExploration) -> str:
    sections = [
        ("Top buyers by purchase orders", exploration.top_buyers),
        ("Top suppliers by purchase orders", exploration.top_suppliers),
        ("Purchase orders by status", exploration.purchase_orders_by_status),
        ("Rejected source_records by error_log", exploration.rejected_source_records_by_error, "rejected-records"),
        ("Claims by predicate", exploration.claims_by_predicate),
        ("relationship_public by relationship_type", exploration.relationships_by_type),
    ]

    return f"""<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>DatosEnOrden dataset report</title>
  <style>
    :root {{
      --bg: #f7f7f5;
      --panel: #ffffff;
      --ink: #1f2933;
      --muted: #52616b;
      --line: #d8dee4;
      --accent: #0f766e;
      --bar: #d9f0ec;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background: var(--bg);
      color: var(--ink);
      font-family: "Segoe UI", Arial, sans-serif;
    }}
    main {{
      width: 95%;
      max-width: 1800px;
      margin: 0 auto;
      padding: 28px 0 48px;
    }}
    header {{
      margin-bottom: 24px;
      border-bottom: 1px solid var(--line);
      padding-bottom: 16px;
    }}
    h1, h2 {{ margin: 0; }}
    h1 {{ font-size: 2rem; }}
    h2 {{ font-size: 1.1rem; margin-bottom: 12px; }}
    .timestamp {{ color: var(--muted); margin-top: 8px; }}
    .metrics {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
      gap: 12px;
      margin-bottom: 22px;
    }}
    @media (min-width: 1280px) {{
      .metrics {{ grid-template-columns: repeat(6, minmax(0, 1fr)); }}
    }}
    .metric, section {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
    }}
    .metric {{ padding: 14px; }}
    .metric strong {{ display: block; font-size: 1.6rem; }}
    .metric span {{ color: var(--muted); }}
    .grid {{
      display: grid;
      grid-template-columns: 1fr;
      gap: 18px;
      align-items: start;
    }}
    @media (min-width: 900px) {{
      .grid {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
    }}
    @media (min-width: 1320px) {{
      .grid {{ grid-template-columns: repeat(3, minmax(0, 1fr)); }}
    }}
    section {{ padding: 16px; overflow: hidden; }}
    .table-wrap {{
      width: 100%;
      max-width: 100%;
      overflow: auto;
      border: 1px solid var(--line);
      border-radius: 8px;
      max-height: 420px;
    }}
    .rejected-records .table-wrap {{
      max-height: 320px;
    }}
    table {{
      width: 100%;
      min-width: 560px;
      border-collapse: collapse;
      font-size: 0.92rem;
    }}
    th, td {{
      border-bottom: 1px solid var(--line);
      padding: 8px 6px;
      text-align: left;
      vertical-align: top;
    }}
    th {{
      position: sticky;
      top: 0;
      z-index: 1;
      background: var(--panel);
      color: var(--muted);
      font-weight: 600;
    }}
    td.label {{
      min-width: 260px;
      overflow-wrap: anywhere;
    }}
    .rejected-records td.label {{
      white-space: pre-wrap;
      line-height: 1.35;
    }}
    td.count {{ text-align: right; width: 80px; }}
    .chart {{ display: grid; gap: 10px; margin-bottom: 14px; }}
    .bar-row {{
      display: grid;
      grid-template-columns: minmax(170px, 0.95fr) minmax(220px, 2fr) 60px;
      gap: 10px;
      align-items: center;
      color: var(--muted);
      font-size: 0.9rem;
      min-width: 0;
    }}
    .bar-label {{
      color: var(--ink);
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }}
    .bar-track {{ height: 12px; background: #edf1f4; border-radius: 999px; overflow: hidden; }}
    .bar-fill {{ height: 100%; background: var(--accent); }}
    .empty {{ color: var(--muted); margin: 0; }}
    footer {{
      margin-top: 26px;
      padding-top: 16px;
      border-top: 1px solid var(--line);
      color: var(--muted);
      display: flex;
      flex-wrap: wrap;
      gap: 12px 24px;
      font-size: 0.92rem;
    }}
  </style>
</head>
<body>
  <main>
    <header>
      <h1>DatosEnOrden dataset report</h1>
      <div class="timestamp">Generated at {escape(exploration.generated_at.isoformat())}</div>
    </header>
    <div class="metrics">{_render_metric_cards(exploration.summary_metrics)}</div>
    <div class="grid">{"".join(_render_section(*section) for section in sections)}</div>
    <footer>
      <span>Generated at {escape(exploration.generated_at.isoformat())}</span>
      <span>Source: DatosEnOrden local dataset</span>
    </footer>
  </main>
</body>
</html>
"""


def _summary_metrics(session: Session) -> tuple[MetricRow, ...]:
    return (
        MetricRow("purchase_orders", _count_purchase_orders(session)),
        MetricRow("source_records", _count_purchase_order_source_records(session)),
        MetricRow("rejected_source_records", _count_rejected_purchase_order_source_records(session)),
        MetricRow("claims", _count_purchase_order_claims(session)),
        MetricRow("evidences", _count_purchase_order_evidence(session)),
        MetricRow("relationship_public", _count_purchase_order_relationships(session)),
    )


def _top_entities_by_purchase_orders(
    session: Session,
    predicate: str,
    top_limit: int,
) -> tuple[MetricRow, ...]:
    statement = (
        select(Entity.name, func.count(distinct(Claim.source_record_id)).label("purchase_order_count"))
        .select_from(Claim)
        .join(SourceRecord, Claim.source_record_id == SourceRecord.id)
        .join(Entity, Claim.subject_entity_id == Entity.id)
        .where(SourceRecord.record_type == PURCHASE_ORDER_RECORD_TYPE, Claim.predicate == predicate)
        .group_by(Entity.name)
        .order_by(func.count(distinct(Claim.source_record_id)).desc(), Entity.name.asc())
        .limit(top_limit)
    )
    return _metric_rows(session.execute(statement).all())


def _group_source_records_by_status(session: Session) -> tuple[MetricRow, ...]:
    statement = (
        select(SourceRecord.status, func.count().label("status_count"))
        .where(SourceRecord.record_type == PURCHASE_ORDER_RECORD_TYPE)
        .group_by(SourceRecord.status)
        .order_by(func.count().desc(), SourceRecord.status.asc())
    )
    return _metric_rows(session.execute(statement).all())


def _group_rejected_source_records_by_error(session: Session, top_limit: int) -> tuple[MetricRow, ...]:
    error_label = func.coalesce(SourceRecord.error_log, "(missing error_log)")
    statement = (
        select(error_label, func.count().label("error_count"))
        .where(
            SourceRecord.record_type == PURCHASE_ORDER_RECORD_TYPE,
            SourceRecord.status == "rejected",
        )
        .group_by(error_label)
        .order_by(func.count().desc(), error_label.asc())
        .limit(top_limit)
    )
    return _metric_rows(session.execute(statement).all())


def _group_claims_by_predicate(session: Session) -> tuple[MetricRow, ...]:
    statement = (
        select(Claim.predicate, func.count().label("claim_count"))
        .select_from(Claim)
        .join(SourceRecord, Claim.source_record_id == SourceRecord.id)
        .where(SourceRecord.record_type == PURCHASE_ORDER_RECORD_TYPE)
        .group_by(Claim.predicate)
        .order_by(func.count().desc(), Claim.predicate.asc())
    )
    return _metric_rows(session.execute(statement).all())


def _group_relationships_by_type(session: Session) -> tuple[MetricRow, ...]:
    statement = (
        select(RelationshipPublic.relationship_type, func.count().label("relationship_count"))
        .select_from(RelationshipPublic)
        .join(Claim, RelationshipPublic.claim_id == Claim.id)
        .join(SourceRecord, Claim.source_record_id == SourceRecord.id)
        .where(SourceRecord.record_type == PURCHASE_ORDER_RECORD_TYPE)
        .group_by(RelationshipPublic.relationship_type)
        .order_by(func.count().desc(), RelationshipPublic.relationship_type.asc())
    )
    return _metric_rows(session.execute(statement).all())


def _count_purchase_orders(session: Session) -> int:
    return _scalar_count(
        session,
        select(func.count(distinct(SourceRecord.external_id))).where(
            SourceRecord.record_type == PURCHASE_ORDER_RECORD_TYPE
        ),
    )


def _count_purchase_order_source_records(session: Session) -> int:
    return _scalar_count(
        session,
        select(func.count()).select_from(SourceRecord).where(SourceRecord.record_type == PURCHASE_ORDER_RECORD_TYPE),
    )


def _count_rejected_purchase_order_source_records(session: Session) -> int:
    return _scalar_count(
        session,
        select(func.count()).select_from(SourceRecord).where(
            SourceRecord.record_type == PURCHASE_ORDER_RECORD_TYPE,
            SourceRecord.status == "rejected",
        ),
    )


def _count_purchase_order_claims(session: Session) -> int:
    return _scalar_count(
        session,
        select(func.count())
        .select_from(Claim)
        .join(SourceRecord, Claim.source_record_id == SourceRecord.id)
        .where(SourceRecord.record_type == PURCHASE_ORDER_RECORD_TYPE),
    )


def _count_purchase_order_evidence(session: Session) -> int:
    return _scalar_count(
        session,
        select(func.count())
        .select_from(Evidence)
        .join(SourceRecord, Evidence.source_record_id == SourceRecord.id)
        .where(SourceRecord.record_type == PURCHASE_ORDER_RECORD_TYPE),
    )


def _count_purchase_order_relationships(session: Session) -> int:
    return _scalar_count(
        session,
        select(func.count())
        .select_from(RelationshipPublic)
        .join(Claim, RelationshipPublic.claim_id == Claim.id)
        .join(SourceRecord, Claim.source_record_id == SourceRecord.id)
        .where(SourceRecord.record_type == PURCHASE_ORDER_RECORD_TYPE),
    )


def _metric_rows(rows) -> tuple[MetricRow, ...]:  # noqa: ANN001
    return tuple(MetricRow(str(label), int(count or 0)) for label, count in rows)


def _scalar_count(session: Session, statement) -> int:  # type: ignore[no-untyped-def]
    return int(session.scalar(statement) or 0)


def _render_metric_cards(rows: tuple[MetricRow, ...]) -> str:
    return "".join(
        f'<div class="metric"><strong>{row.count}</strong><span>{escape(row.label)}</span></div>'
        for row in rows
    )


def _render_section(title: str, rows: tuple[MetricRow, ...], class_name: str = "") -> str:
    class_attr = f' class="{escape(class_name)}"' if class_name else ""
    return f"""
      <section{class_attr}>
        <h2>{escape(title)}</h2>
        {_render_chart(rows)}
        {_render_table(rows)}
      </section>
    """


def _render_chart(rows: tuple[MetricRow, ...]) -> str:
    if not rows:
        return '<p class="empty">No rows</p>'
    max_count = max(row.count for row in rows) or 1
    bars = []
    for row in rows[:8]:
        width = max(2, round((row.count / max_count) * 100))
        bars.append(
            '<div class="bar-row">'
            f'<span class="bar-label" title="{escape(row.label)}">{escape(row.label)}</span>'
            '<div class="bar-track">'
            f'<div class="bar-fill" style="width: {width}%"></div>'
            "</div>"
            f"<strong>{row.count}</strong>"
            "</div>"
        )
    return f'<div class="chart">{"".join(bars)}</div>'


def _render_table(rows: tuple[MetricRow, ...]) -> str:
    if not rows:
        return ""
    body = "".join(
        "<tr>"
        f'<td class="label">{escape(row.label)}</td>'
        f'<td class="count">{row.count}</td>'
        "</tr>"
        for row in rows
    )
    return (
        '<div class="table-wrap">'
        f"<table><thead><tr><th>Label</th><th>Count</th></tr></thead><tbody>{body}</tbody></table>"
        "</div>"
    )
