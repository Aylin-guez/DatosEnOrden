from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime
from html import escape
from typing import Any
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload

from datosenorden.etl.core.time import parse_chilecompra_date
from datosenorden.maintenance.entity_explorer import EntitySummary
from datosenorden.models import Claim, Dataset, Entity, Evidence, RelationshipPublic, SourceRecord


DATASET_LABELS = {
    "chilecompra-licitaciones": "CHILECOMPRA",
    "chilecompra-ordenes-compra": "CHILECOMPRA",
    "dipres-budget-sample": "DIPRES",
    "lobby-meeting-sample": "LOBBY",
    "transparencia-activa-sample": "TRANSPARENCIA",
}

EVENT_LABELS = {
    "ISSUES_PURCHASE_ORDER": "Purchase order",
    "RECEIVES_CONTRACT": "Purchase order",
    "HAS_APPROVED_BUDGET": "Budget assigned",
    "HAS_EXECUTED_BUDGET": "Budget execution recorded",
    "MATCHED_TO_ORGANIZATION": "Budget assigned",
    "ORGANIZATION_HELD_LOBBY_MEETING": "Lobby meeting",
    "COUNTERPARTY_PARTICIPATED_IN_LOBBY": "Lobby meeting",
    "LOBBY_MEETING_ABOUT_SUBJECT": "Lobby meeting",
    "ORGANIZATION_HAS_PUBLIC_ROLE": "Role period",
    "PERSON_HOLDS_PUBLIC_ROLE": "Role period",
    "ROLE_BELONGS_TO_ORGANIZATION": "Role period",
}


@dataclass(frozen=True)
class TimelineEvent:
    event_date: date
    dataset: str
    dataset_name: str
    title: str
    explanation: str
    claim_id: str
    predicate: str
    source_record_id: str
    evidence_count: int
    relationship_count: int


@dataclass(frozen=True)
class EntityTimeline:
    entity: EntitySummary
    events: tuple[TimelineEvent, ...]
    explanation: str
    caution: str


@dataclass(frozen=True)
class TimelineClaimRow:
    claim: Claim
    dataset_name: str
    evidence_dates: tuple[date, ...]
    relationship_dates: tuple[date, ...]
    evidence_count: int
    relationship_count: int


def build_entity_timeline(session: Session, entity_id: str) -> EntityTimeline | None:
    entity = session.get(Entity, UUID(entity_id))
    if entity is None:
        return None

    events = [_event_from_claim_row(row) for row in _load_timeline_claim_rows(session, entity.id)]
    dated_events = [event for event in events if event is not None]
    dated_events.sort(
        key=lambda event: (
            event.event_date,
            event.dataset,
            event.title,
            event.claim_id,
        )
    )
    return EntityTimeline(
        entity=_summarize_entity(entity),
        events=tuple(dated_events),
        explanation=timeline_explanation_text(),
        caution=timeline_caution_text(),
    )


def render_entity_timeline_text(timeline: EntityTimeline) -> str:
    lines = [
        "entity_timeline:",
        "",
        "entity:",
        timeline.entity.name,
        "",
    ]
    if not timeline.events:
        lines.append("(no timeline events)")
        return "\n".join(lines)

    for event in timeline.events:
        lines.extend(
            [
                event.event_date.isoformat(),
                f"[{event.dataset}]",
                event.title,
                f"evidence_count={event.evidence_count}",
                f"relationship_count={event.relationship_count}",
                "",
            ]
        )
    lines.extend([timeline.explanation, timeline.caution])
    return "\n".join(lines).rstrip()


def render_entity_timeline_html(timeline: EntityTimeline) -> str:
    title = f"Entity timeline: {timeline.entity.name}"
    grouped = _events_by_year(timeline.events)
    body = "".join(_render_year_group_html(year, events) for year, events in grouped.items())
    if not body:
        body = '<p class="empty">No timeline events found for this entity.</p>'
    return f"""<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{escape(title)}</title>
  <style>
    :root {{
      --bg: #f7f7f5;
      --panel: #ffffff;
      --ink: #1f2933;
      --muted: #52616b;
      --line: #d8dee4;
      --accent: #0f766e;
      --accent-soft: rgba(15, 118, 110, 0.08);
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background: var(--bg);
      color: var(--ink);
      font-family: "Segoe UI", Arial, sans-serif;
    }}
    main {{
      width: min(1000px, 92vw);
      margin: 0 auto;
      padding: 28px 0 48px;
    }}
    header {{
      border-bottom: 1px solid var(--line);
      margin-bottom: 24px;
      padding-bottom: 16px;
    }}
    h1, h2, h3, p {{ margin-top: 0; }}
    h1 {{ margin-bottom: 8px; font-size: 2rem; }}
    .muted {{ color: var(--muted); }}
    .explain {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 14px 16px;
      margin-bottom: 24px;
    }}
    .year {{ margin: 26px 0 14px; }}
    .timeline {{
      border-left: 3px solid var(--accent);
      display: grid;
      gap: 14px;
      margin-left: 10px;
      padding-left: 22px;
    }}
    .event {{
      position: relative;
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 14px 16px;
    }}
    .event::before {{
      content: "";
      position: absolute;
      left: -31px;
      top: 20px;
      width: 14px;
      height: 14px;
      border-radius: 50%;
      border: 3px solid var(--accent);
      background: var(--bg);
    }}
    .event-date {{ color: var(--muted); font-weight: 700; }}
    .event-title {{ font-size: 1.05rem; font-weight: 800; margin: 5px 0 8px; }}
    .badges {{ display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 8px; }}
    .badge {{
      display: inline-flex;
      border-radius: 999px;
      padding: 4px 9px;
      background: var(--accent-soft);
      color: var(--accent);
      font-size: 0.78rem;
      font-weight: 800;
      letter-spacing: 0.04em;
    }}
    .counts {{ color: var(--muted); font-size: 0.9rem; }}
    .empty {{ color: var(--muted); }}
  </style>
</head>
<body>
  <main>
    <header>
      <h1>{escape(timeline.entity.name)}</h1>
      <div class="muted">id={escape(timeline.entity.id)} | type={escape(timeline.entity.entity_type)}</div>
    </header>
    <section class="explain">
      <p>{escape(timeline.explanation)}</p>
      <p><strong>Nota:</strong> {escape(timeline.caution)}</p>
    </section>
    {body}
  </main>
</body>
</html>
"""


def timeline_explanation_text() -> str:
    return (
        "Esta cronologia reune los eventos publicos encontrados para esta entidad "
        "en distintas fuentes de informacion."
    )


def timeline_caution_text() -> str:
    return "El orden temporal no implica relacion causal."


def _load_timeline_claim_rows(session: Session, entity_id: UUID) -> tuple[TimelineClaimRow, ...]:
    claims = session.scalars(
        select(Claim)
        .where(or_(Claim.subject_entity_id == entity_id, Claim.object_entity_id == entity_id))
        .options(joinedload(Claim.source_record).joinedload(SourceRecord.dataset))
        .order_by(Claim.valid_from.asc().nullslast(), Claim.created_at.asc(), Claim.id.asc())
    ).all()
    if not claims:
        return ()

    claim_ids = tuple(claim.id for claim in claims)
    evidence_dates_by_claim: dict[UUID, list[date]] = defaultdict(list)
    evidence_counts = {
        claim_id: 0
        for claim_id in claim_ids
    }
    evidence_rows = session.execute(
        select(Evidence.claim_id, Evidence.published_at, func.count(Evidence.id))
        .where(Evidence.claim_id.in_(claim_ids))
        .group_by(Evidence.claim_id, Evidence.published_at)
    ).all()
    for claim_id, published_at, count in evidence_rows:
        if claim_id is None:
            continue
        evidence_counts[claim_id] = evidence_counts.get(claim_id, 0) + int(count or 0)
        if published_at is not None:
            evidence_dates_by_claim[claim_id].append(published_at)

    relationship_dates_by_claim: dict[UUID, list[date]] = defaultdict(list)
    relationship_counts = {
        claim_id: 0
        for claim_id in claim_ids
    }
    relationship_rows = session.execute(
        select(RelationshipPublic.claim_id, RelationshipPublic.published_at, func.count(RelationshipPublic.id))
        .where(RelationshipPublic.claim_id.in_(claim_ids))
        .group_by(RelationshipPublic.claim_id, RelationshipPublic.published_at)
    ).all()
    for claim_id, published_at, count in relationship_rows:
        relationship_counts[claim_id] = relationship_counts.get(claim_id, 0) + int(count or 0)
        if published_at is not None:
            relationship_dates_by_claim[claim_id].append(published_at.date())

    rows: list[TimelineClaimRow] = []
    for claim in claims:
        dataset = getattr(claim.source_record, "dataset", None)
        rows.append(
            TimelineClaimRow(
                claim=claim,
                dataset_name=dataset.name if isinstance(dataset, Dataset) else "",
                evidence_dates=tuple(evidence_dates_by_claim.get(claim.id, ())),
                relationship_dates=tuple(relationship_dates_by_claim.get(claim.id, ())),
                evidence_count=evidence_counts.get(claim.id, 0),
                relationship_count=relationship_counts.get(claim.id, 0),
            )
        )
    return tuple(rows)


def _event_from_claim_row(row: TimelineClaimRow) -> TimelineEvent | None:
    claim = row.claim
    event_date = _best_event_date(claim, row.evidence_dates, row.relationship_dates)
    if event_date is None:
        return None
    dataset = _dataset_badge(row.dataset_name)
    title = _event_title(claim.predicate, row.dataset_name)
    return TimelineEvent(
        event_date=event_date,
        dataset=dataset,
        dataset_name=row.dataset_name,
        title=title,
        explanation=_event_explanation(claim.predicate, dataset),
        claim_id=str(claim.id),
        predicate=claim.predicate,
        source_record_id=str(claim.source_record_id),
        evidence_count=row.evidence_count,
        relationship_count=row.relationship_count,
    )


def _best_event_date(
    claim: Claim,
    evidence_dates: tuple[date, ...],
    relationship_dates: tuple[date, ...],
) -> date | None:
    if claim.valid_from is not None:
        return claim.valid_from
    if evidence_dates:
        return min(evidence_dates)
    if relationship_dates:
        return min(relationship_dates)
    source_record = getattr(claim, "source_record", None)
    payload = getattr(source_record, "raw_payload", None) or {}
    if isinstance(payload, dict):
        payload_date = _date_from_payload(payload)
        if payload_date is not None:
            return payload_date
    return None


def _date_from_payload(payload: dict[str, Any]) -> date | None:
    fiscal_year = payload.get("fiscal_year")
    if fiscal_year is not None:
        return date(int(fiscal_year), 1, 1)
    period = payload.get("period")
    if period is not None:
        parsed_period = _period_start(str(period))
        if parsed_period is not None:
            return parsed_period
    for key in ("meeting_date", "FechaEnvio", "FechaCreacion", "FechaContrato", "FechaPublicacion"):
        value = payload.get(key)
        parsed = _parse_any_date(value)
        if parsed is not None:
            return parsed
    return None


def _parse_any_date(value: object | None) -> date | None:
    if value is None:
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    text = str(value).strip()
    if not text:
        return None
    parsed = parse_chilecompra_date(text)
    if parsed is not None:
        return parsed
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        return None


def _period_start(period: str) -> date | None:
    parts = period.split("-")
    if len(parts) < 2:
        return None
    try:
        return date(int(parts[0]), int(parts[1]), 1)
    except ValueError:
        return None


def _event_title(predicate: str, dataset_name: str) -> str:
    if dataset_name in {"chilecompra-ordenes-compra", "chilecompra-licitaciones"}:
        return EVENT_LABELS.get(predicate, "ChileCompra event")
    return EVENT_LABELS.get(predicate, predicate.replace("_", " ").title())


def _event_explanation(predicate: str, dataset: str) -> str:
    if dataset == "DIPRES":
        return "Registro presupuestario asociado a la entidad."
    if dataset == "LOBBY":
        return "Registro de reunion de lobby asociado a la entidad."
    if dataset == "CHILECOMPRA":
        return "Registro de compra publica asociado a la entidad."
    if dataset == "TRANSPARENCIA":
        return "Registro administrativo de cargo o periodo asociado a la entidad."
    return f"Evento derivado de la afirmacion {predicate}."


def _dataset_badge(dataset_name: str) -> str:
    return DATASET_LABELS.get(dataset_name, dataset_name.upper() if dataset_name else "UNKNOWN")


def _events_by_year(events: tuple[TimelineEvent, ...]) -> dict[int, tuple[TimelineEvent, ...]]:
    grouped: dict[int, list[TimelineEvent]] = {}
    for event in events:
        grouped.setdefault(event.event_date.year, []).append(event)
    return {year: tuple(grouped[year]) for year in sorted(grouped)}


def _render_year_group_html(year: int, events: tuple[TimelineEvent, ...]) -> str:
    cards = "".join(_render_event_card_html(event) for event in events)
    return f'<section><h2 class="year">{year}</h2><div class="timeline">{cards}</div></section>'


def _render_event_card_html(event: TimelineEvent) -> str:
    return (
        '<article class="event">'
        f'<div class="event-date">{escape(event.event_date.isoformat())}</div>'
        f'<div class="event-title">{escape(event.title)}</div>'
        '<div class="badges">'
        f'<span class="badge">{escape(event.dataset)}</span>'
        f'<span class="badge">evidence {event.evidence_count}</span>'
        f'<span class="badge">relationships {event.relationship_count}</span>'
        "</div>"
        f'<p class="muted">{escape(event.explanation)}</p>'
        f'<div class="counts">claim_id={escape(event.claim_id)}</div>'
        "</article>"
    )


def _summarize_entity(entity: Entity) -> EntitySummary:
    return EntitySummary(
        id=str(entity.id),
        entity_type=entity.entity_type,
        name=entity.name,
        external_id=entity.external_id,
    )
