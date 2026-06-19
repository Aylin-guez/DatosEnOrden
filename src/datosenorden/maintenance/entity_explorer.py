from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime, timezone
from html import escape
from uuid import UUID

from sqlalchemy import and_, distinct, func, or_, select
from sqlalchemy.orm import Session, joinedload

from datosenorden.models import Claim, Entity, Evidence, RelationshipPublic

SUPPLIER_ENTITY_TYPE = "COMPANY"
BUYER_ENTITY_TYPE = "PUBLIC_ORGANIZATION"
SUPPLIER_PREDICATE = "RECEIVES_CONTRACT"
BUYER_PREDICATE = "ISSUES_PURCHASE_ORDER"


@dataclass(frozen=True)
class EntitySearchResult:
    id: str
    entity_type: str
    name: str
    external_id: str | None
    purchase_orders: int
    claims: int
    relationships: int


@dataclass(frozen=True)
class EntityPurchaseOrderSummary:
    id: str
    name: str
    purchase_orders: int


@dataclass(frozen=True)
class EntityListSummary:
    id: str
    entity_type: str
    name: str
    external_id: str | None


@dataclass(frozen=True)
class EntitySummary:
    id: str
    entity_type: str
    name: str
    external_id: str | None


@dataclass(frozen=True)
class EntityRelationshipCount:
    relationship_type: str
    count: int


@dataclass(frozen=True)
class EntityNavigationLink:
    label: str
    href: str


@dataclass(frozen=True)
class EntityNeighborSummary:
    relationship_id: str
    relationship_type: str
    direction: str
    neighbor: EntitySummary
    source_entity: EntitySummary
    target_entity: EntitySummary
    profile_link: EntityNavigationLink
    graph_link: EntityNavigationLink


@dataclass(frozen=True)
class EntityGraphNodeSummary:
    entity: EntitySummary
    via_relationship_type: str | None
    via_direction: str | None
    children: tuple["EntityGraphNodeSummary", ...]


@dataclass(frozen=True)
class EntityEvidenceSummary:
    id: str
    title: str
    url: str
    published_at: date | None
    claim_id: str | None


@dataclass(frozen=True)
class EntityClaimSummary:
    id: str
    predicate: str
    status: str
    subject_entity: EntitySummary
    object_entity: EntitySummary | None
    valid_from: date | None
    evidence_count: int
    relationship_count: int


@dataclass(frozen=True)
class EntityRelationshipSummary:
    id: str
    relationship_type: str
    status: str
    source_entity: EntitySummary
    target_entity: EntitySummary
    related_entity: EntitySummary
    claim_id: str


@dataclass(frozen=True)
class EntityProfile:
    generated_at: datetime
    entity: EntitySummary
    claims: tuple[EntityClaimSummary, ...]
    relationships: tuple[EntityRelationshipSummary, ...]
    evidences: tuple[EntityEvidenceSummary, ...]
    related_entities: tuple[EntitySummary, ...]
    direct_neighbors: tuple[EntityNeighborSummary, ...]
    relationship_counts: tuple[EntityRelationshipCount, ...]
    navigation_links: tuple[EntityNavigationLink, ...]


def search_suppliers(session: Session, query: str, limit: int = 20) -> tuple[EntitySearchResult, ...]:
    return _search_entities(
        session=session,
        query=query,
        entity_type=SUPPLIER_ENTITY_TYPE,
        predicate=SUPPLIER_PREDICATE,
        limit=limit,
    )


def search_buyers(session: Session, query: str, limit: int = 20) -> tuple[EntitySearchResult, ...]:
    return _search_entities(
        session=session,
        query=query,
        entity_type=BUYER_ENTITY_TYPE,
        predicate=BUYER_PREDICATE,
        limit=limit,
    )


def list_buyers(session: Session, limit: int | None = None) -> tuple[EntityPurchaseOrderSummary, ...]:
    return _list_entities_by_purchase_orders(session, BUYER_ENTITY_TYPE, BUYER_PREDICATE, limit)


def list_suppliers(session: Session, limit: int | None = None) -> tuple[EntityPurchaseOrderSummary, ...]:
    return _list_entities_by_purchase_orders(session, SUPPLIER_ENTITY_TYPE, SUPPLIER_PREDICATE, limit)


def list_entities(session: Session, limit: int = 50) -> tuple[EntityListSummary, ...]:
    return _list_entities(session, limit=limit)


def list_contracts(session: Session, limit: int | None = None) -> tuple[EntityListSummary, ...]:
    return _list_entities(session, entity_type="CONTRACT", limit=limit)


def get_entity_profile(session: Session, entity_id: str) -> EntityProfile | None:
    entity = session.get(Entity, UUID(entity_id))
    if entity is None:
        return None

    claims = session.scalars(
        select(Claim)
        .where(or_(Claim.subject_entity_id == entity.id, Claim.object_entity_id == entity.id))
        .options(joinedload(Claim.subject_entity), joinedload(Claim.object_entity))
        .order_by(Claim.created_at, Claim.id)
    ).all()
    claim_ids = [claim.id for claim in claims]

    evidences_by_claim: dict[str, list[EntityEvidenceSummary]] = {}
    relationship_count_by_claim: Counter[str] = Counter()

    evidences: list[EntityEvidenceSummary] = []
    if claim_ids:
        evidence_rows = session.scalars(
            select(Evidence).where(Evidence.claim_id.in_(claim_ids)).order_by(Evidence.created_at, Evidence.id)
        ).all()
        for evidence in evidence_rows:
            summary = _summarize_evidence(evidence)
            evidences.append(summary)
            if summary.claim_id is not None:
                evidences_by_claim.setdefault(summary.claim_id, []).append(summary)

    relationships = session.scalars(
        select(RelationshipPublic)
        .where(
            or_(
                RelationshipPublic.source_entity_id == entity.id,
                RelationshipPublic.target_entity_id == entity.id,
            )
        )
        .options(joinedload(RelationshipPublic.source_entity), joinedload(RelationshipPublic.target_entity))
        .order_by(RelationshipPublic.created_at, RelationshipPublic.id)
    ).all()

    relationship_summaries: list[EntityRelationshipSummary] = []
    related_entities: dict[str, EntitySummary] = {}
    direct_neighbors: list[EntityNeighborSummary] = []
    relationship_counts: Counter[str] = Counter()
    navigation_links = _entity_navigation_links(entity.id)
    for relationship in relationships:
        relationship_count_by_claim[str(relationship.claim_id)] += 1
        relationship_counts[relationship.relationship_type] += 1
        related_entity = (
            relationship.target_entity
            if relationship.source_entity_id == entity.id
            else relationship.source_entity
        )
        direction = "outgoing" if relationship.source_entity_id == entity.id else "incoming"
        related_summary = _summarize_entity(related_entity)
        related_entities[related_summary.id] = related_summary
        direct_neighbors.append(
            EntityNeighborSummary(
                relationship_id=str(relationship.id),
                relationship_type=relationship.relationship_type,
                direction=direction,
                neighbor=related_summary,
                source_entity=_summarize_entity(relationship.source_entity),
                target_entity=_summarize_entity(relationship.target_entity),
                profile_link=EntityNavigationLink(
                    label="entity_profile",
                    href=_entity_profile_href(related_summary.id),
                ),
                graph_link=EntityNavigationLink(
                    label="entity_graph",
                    href=_entity_graph_href(related_summary.id),
                ),
            )
        )
        relationship_summaries.append(
            EntityRelationshipSummary(
                id=str(relationship.id),
                relationship_type=relationship.relationship_type,
                status=relationship.status,
                source_entity=_summarize_entity(relationship.source_entity),
                target_entity=_summarize_entity(relationship.target_entity),
                related_entity=related_summary,
                claim_id=str(relationship.claim_id),
            )
        )

    claim_summaries = tuple(
        EntityClaimSummary(
            id=str(claim.id),
            predicate=claim.predicate,
            status=claim.status,
            subject_entity=_summarize_entity(claim.subject_entity),
            object_entity=_summarize_entity(claim.object_entity) if claim.object_entity is not None else None,
            valid_from=claim.valid_from,
            evidence_count=len(evidences_by_claim.get(str(claim.id), ())),
            relationship_count=relationship_count_by_claim[str(claim.id)],
        )
        for claim in claims
    )

    return EntityProfile(
        generated_at=datetime.now(timezone.utc),
        entity=_summarize_entity(entity),
        claims=claim_summaries,
        relationships=tuple(relationship_summaries),
        evidences=tuple(evidences),
        related_entities=tuple(related_entities.values()),
        direct_neighbors=tuple(direct_neighbors),
        relationship_counts=tuple(
            EntityRelationshipCount(relationship_type=relationship_type, count=count)
            for relationship_type, count in sorted(
                relationship_counts.items(), key=lambda item: (-item[1], item[0])
            )
        ),
        navigation_links=_entity_navigation_links(entity.id),
    )


def render_supplier_search(query: str, results: tuple[EntitySearchResult, ...]) -> str:
    return _render_search_results("supplier", query, results)


def render_buyer_search(query: str, results: tuple[EntitySearchResult, ...]) -> str:
    return _render_search_results("buyer", query, results)


def render_entity_details(profile: EntityProfile) -> str:
    lines = [
        "entity:",
        f"id={profile.entity.id}",
        f"type={profile.entity.entity_type}",
        f"name={profile.entity.name}",
        f"external_id={_format_optional(profile.entity.external_id)}",
        "",
        "relationship_counts:",
    ]
    if not profile.relationship_counts:
        lines.append("  (no relationships)")
    for item in profile.relationship_counts:
        lines.append(f"  {item.relationship_type}={item.count}")

    lines.append("")
    lines.append("direct_neighbors:")
    if not profile.direct_neighbors:
        lines.append("  (no neighbors)")
    for index, neighbor in enumerate(profile.direct_neighbors, start=1):
        lines.extend(
            [
                f"  neighbor[{index}]:",
                f"    relationship={neighbor.relationship_type}",
                f"    direction={neighbor.direction}",
                f"    id={neighbor.neighbor.id}",
                f"    type={neighbor.neighbor.entity_type}",
                f"    name={neighbor.neighbor.name}",
                f"    profile_link={neighbor.profile_link.href}",
                f"    graph_link={neighbor.graph_link.href}",
            ]
        )

    lines.append("")
    lines.append("navigation_links:")
    for link in profile.navigation_links:
        lines.append(f"  {link.label}={link.href}")

    lines.append("")
    lines.extend(
        [
            "claims:",
        ]
    )
    if not profile.claims:
        lines.append("  (no claims)")
    for index, claim in enumerate(profile.claims, start=1):
        lines.extend(
            [
                f"  claim[{index}]:",
                f"    id={claim.id}",
                f"    predicate={claim.predicate}",
                f"    status={claim.status}",
                f"    subject={claim.subject_entity.entity_type} | {claim.subject_entity.name}",
                f"    object={_format_entity(claim.object_entity)}",
                f"    evidence_count={claim.evidence_count}",
                f"    relationship_count={claim.relationship_count}",
            ]
        )

    lines.append("")
    lines.append("relationships:")
    if not profile.relationships:
        lines.append("  (no relationships)")
    for index, relationship in enumerate(profile.relationships, start=1):
        lines.extend(
            [
                f"  relationship[{index}]:",
                f"    id={relationship.id}",
                f"    type={relationship.relationship_type}",
                f"    status={relationship.status}",
                f"    related_entity={relationship.related_entity.entity_type} | {relationship.related_entity.name}",
                f"    source={relationship.source_entity.entity_type} | {relationship.source_entity.name}",
                f"    target={relationship.target_entity.entity_type} | {relationship.target_entity.name}",
                f"    claim_id={relationship.claim_id}",
            ]
        )

    lines.append("")
    lines.append("evidence:")
    if not profile.evidences:
        lines.append("  (no evidence)")
    for index, evidence in enumerate(profile.evidences, start=1):
        lines.extend(
            [
                f"  evidence[{index}]:",
                f"    id={evidence.id}",
                f"    title={evidence.title}",
                f"    url={evidence.url}",
                f"    published_at={_format_date(evidence.published_at)}",
                f"    claim_id={_format_optional(evidence.claim_id)}",
            ]
        )

    lines.append("")
    lines.append("related_entities:")
    if not profile.related_entities:
        lines.append("  (no related entities)")
    for index, related in enumerate(profile.related_entities, start=1):
        lines.append(
            f"  related_entity[{index}]={related.entity_type} | {related.name} | id={related.id}"
        )
    return "\n".join(lines)


def render_entity_profile_html(profile: EntityProfile) -> str:
    title = f"Entity profile: {profile.entity.name}"
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
      width: 95%;
      max-width: 1800px;
      margin: 0 auto;
      padding: 28px 0 48px;
    }}
    header {{
      margin-bottom: 22px;
      border-bottom: 1px solid var(--line);
      padding-bottom: 16px;
    }}
    nav {{
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      margin: 14px 0 0;
    }}
    nav a {{
      display: inline-flex;
      align-items: center;
      padding: 8px 12px;
      border-radius: 999px;
      background: var(--accent-soft);
      text-decoration: none;
      color: var(--accent);
      font-weight: 600;
      font-size: 0.92rem;
    }}
    h1, h2 {{ margin: 0; }}
    h1 {{ font-size: 2rem; }}
    h2 {{ font-size: 1.1rem; margin-bottom: 12px; }}
    .muted {{ color: var(--muted); }}
    .metrics {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
      gap: 12px;
      margin-bottom: 20px;
    }}
    @media (min-width: 1280px) {{
      .metrics {{ grid-template-columns: repeat(5, minmax(0, 1fr)); }}
    }}
    .metric, section {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
    }}
    .metric {{ padding: 14px; }}
    .metric strong {{ display: block; font-size: 1.5rem; }}
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
    .wide {{ grid-column: 1 / -1; }}
    .neighbor-cards {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
      gap: 12px;
    }}
    .neighbor-card {{
      border: 1px solid var(--line);
      border-radius: 12px;
      padding: 14px;
      background: linear-gradient(180deg, #fff, #fbfcfd);
      min-height: 150px;
    }}
    .neighbor-card h3 {{
      margin: 0 0 6px;
      font-size: 1rem;
    }}
    .neighbor-card .relationship {{
      font-weight: 700;
      color: var(--accent);
      margin-bottom: 8px;
    }}
    .neighbor-card .meta {{
      display: grid;
      gap: 4px;
      color: var(--muted);
      font-size: 0.92rem;
    }}
    .neighbor-card .links {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin-top: 10px;
    }}
    .neighbor-card .links a {{
      color: var(--accent);
      text-decoration: none;
      font-weight: 600;
      font-size: 0.9rem;
    }}
    .table-wrap {{
      overflow: auto;
      border: 1px solid var(--line);
      border-radius: 8px;
      max-height: 460px;
    }}
    table {{
      width: 100%;
      min-width: 720px;
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
      background: var(--panel);
      color: var(--muted);
      z-index: 1;
    }}
    td {{ overflow-wrap: anywhere; }}
    a {{ color: var(--accent); }}
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
      <h1>{escape(profile.entity.name)}</h1>
      <div class="muted">
        id={escape(profile.entity.id)} | type={escape(profile.entity.entity_type)} |
        external_id={escape(_format_optional(profile.entity.external_id))}
      </div>
      <nav>
        {"".join(f'<a href="{escape(link.href)}">{escape(link.label)}</a>' for link in profile.navigation_links)}
      </nav>
    </header>
    <div class="metrics">
      <div class="metric"><strong>{len(profile.claims)}</strong><span>claims</span></div>
      <div class="metric"><strong>{len(profile.relationships)}</strong><span>relationships</span></div>
      <div class="metric"><strong>{len(profile.evidences)}</strong><span>evidence links</span></div>
      <div class="metric"><strong>{len(profile.related_entities)}</strong><span>related entities</span></div>
      <div class="metric"><strong>{len(profile.direct_neighbors)}</strong><span>direct neighbors</span></div>
    </div>
    <div class="grid">
      <section class="wide">
        <h2>Direct neighbors</h2>
        {_render_neighbors_cards(profile.direct_neighbors)}
      </section>
      <section class="wide">
        <h2>Relationship counts</h2>
        {_render_relationship_counts(profile.relationship_counts)}
      </section>
      <section>{_render_related_entities_table(profile.related_entities)}</section>
      <section class="wide">{_render_claims_table(profile.claims)}</section>
      <section class="wide">{_render_relationships_table(profile.relationships)}</section>
      <section class="wide">{_render_evidence_table(profile.evidences)}</section>
    </div>
    <footer>
      <span>Generated at {escape(profile.generated_at.isoformat())}</span>
      <span>Source: DatosEnOrden local dataset</span>
    </footer>
  </main>
</body>
</html>
"""


def render_buyers_list_text(rows: tuple[EntityPurchaseOrderSummary, ...]) -> str:
    return _render_purchase_order_inventory("buyer", rows)


def render_suppliers_list_text(rows: tuple[EntityPurchaseOrderSummary, ...]) -> str:
    return _render_purchase_order_inventory("supplier", rows)


def render_entities_list_text(rows: tuple[EntityListSummary, ...]) -> str:
    return _render_entity_inventory("entity", rows, include_type=True)


def render_contracts_list_text(rows: tuple[EntityListSummary, ...]) -> str:
    return _render_entity_inventory("contract", rows, include_type=False)


def get_entity_neighbors(session: Session, entity_id: str) -> tuple[EntityNeighborSummary, ...] | None:
    entity = session.get(Entity, UUID(entity_id))
    if entity is None:
        return None
    relationships = _load_entity_relationships(session, entity.id)
    return _build_direct_neighbors(entity.id, relationships)


def build_entity_graph(
    session: Session,
    entity_id: str,
    depth: int = 1,
) -> EntityGraphNodeSummary | None:
    if depth < 0:
        raise ValueError("depth must be greater than or equal to zero")

    entity = session.get(Entity, UUID(entity_id))
    if entity is None:
        return None

    return _build_entity_graph_node(session, entity, depth=depth, path={entity.id})


def summarize_relationship_counts(session: Session) -> tuple[EntityRelationshipCount, ...]:
    statement = (
        select(RelationshipPublic.relationship_type, func.count().label("relationship_count"))
        .select_from(RelationshipPublic)
        .group_by(RelationshipPublic.relationship_type)
        .order_by(func.count().desc(), RelationshipPublic.relationship_type.asc())
    )
    rows = session.execute(statement).all()
    return tuple(EntityRelationshipCount(relationship_type=str(label), count=int(count or 0)) for label, count in rows)


def render_entity_neighbors_text(entity: EntitySummary, neighbors: tuple[EntityNeighborSummary, ...]) -> str:
    lines = [
        "entity:",
        f"id={entity.id}",
        f"name={entity.name}",
        f"type={entity.entity_type}",
        "",
        "neighbors:",
    ]
    if not neighbors:
        lines.append("  (no neighbors)")
    for neighbor in neighbors:
        lines.extend(
            [
                f"  relationship={neighbor.relationship_type}",
                f"  direction={neighbor.direction}",
                f"  id={neighbor.neighbor.id}",
                f"  type={neighbor.neighbor.entity_type}",
                f"  name={neighbor.neighbor.name}",
                f"  profile_link={neighbor.profile_link.href}",
                f"  graph_link={neighbor.graph_link.href}",
                "",
            ]
        )
    return "\n".join(lines).rstrip()


def render_entity_graph_text(root: EntityGraphNodeSummary, depth: int) -> str:
    lines = [f"entity graph: depth={depth}"]
    _append_graph_text(lines, root, prefix=(), is_last=True, is_root=True)
    return "\n".join(lines)


def render_entity_graph_html(root: EntityGraphNodeSummary, depth: int) -> str:
    title = f"Entity graph: {root.entity.name}"
    return f"""<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{escape(title)}</title>
  <style>
    :root {{
      --bg: #f6f4ef;
      --panel: #ffffff;
      --ink: #1f2933;
      --muted: #52616b;
      --line: #d8cfc2;
      --accent: #0f766e;
      --accent-soft: rgba(15, 118, 110, 0.08);
      --shadow: 0 16px 44px rgba(31, 41, 51, 0.12);
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      color: var(--ink);
      font-family: "Segoe UI", Arial, sans-serif;
      background:
        radial-gradient(circle at top left, rgba(15, 118, 110, 0.12), transparent 30%),
        linear-gradient(180deg, #fbf8f2, var(--bg));
    }}
    main {{
      max-width: 1280px;
      margin: 0 auto;
      padding: 32px 20px 48px;
    }}
    header {{
      background: rgba(255, 255, 255, 0.85);
      border: 1px solid rgba(82, 97, 107, 0.14);
      border-radius: 24px;
      box-shadow: var(--shadow);
      padding: 24px 28px;
      margin-bottom: 22px;
    }}
    h1, h2, h3 {{ margin: 0; }}
    h1 {{
      font-size: clamp(28px, 3vw, 40px);
      line-height: 1.1;
      margin-bottom: 8px;
    }}
    .meta {{
      display: flex;
      flex-wrap: wrap;
      gap: 12px 18px;
      color: var(--muted);
      font-size: 0.95rem;
      margin-top: 8px;
    }}
    .graph {{
      display: grid;
      gap: 16px;
    }}
    .node {{
      background: rgba(255, 255, 255, 0.94);
      border: 1px solid rgba(82, 97, 107, 0.14);
      border-radius: 20px;
      box-shadow: var(--shadow);
      padding: 16px 18px;
    }}
    .node.root {{
      border-color: rgba(15, 118, 110, 0.22);
      background: linear-gradient(180deg, #ffffff, #f8fcfb);
    }}
    .node .type {{
      color: var(--accent);
      font-weight: 700;
      letter-spacing: 0.02em;
      margin-bottom: 4px;
    }}
    .node .name {{
      font-size: 1.05rem;
      font-weight: 600;
      margin-bottom: 8px;
    }}
    .node .id {{
      color: var(--muted);
      font-size: 0.92rem;
      overflow-wrap: anywhere;
    }}
    .edge {{
      display: grid;
      grid-template-columns: 24px 1fr;
      gap: 8px;
      align-items: stretch;
      margin-left: 18px;
    }}
    .edge-line {{
      width: 2px;
      background: var(--line);
      margin: 0 auto;
      position: relative;
    }}
    .edge-line::after {{
      content: "";
      position: absolute;
      bottom: -4px;
      left: 50%;
      transform: translateX(-50%);
      border-left: 5px solid transparent;
      border-right: 5px solid transparent;
      border-top: 7px solid var(--line);
    }}
    .edge .label {{
      color: var(--accent);
      font-size: 0.9rem;
      font-weight: 700;
      margin-bottom: 8px;
    }}
    .children {{
      display: grid;
      gap: 14px;
      margin-top: 14px;
    }}
    .children > .node {{
      margin-left: 18px;
    }}
    .empty {{
      color: var(--muted);
      font-size: 0.95rem;
      margin: 0;
    }}
    @media (max-width: 720px) {{
      main {{ padding: 20px 12px 36px; }}
      header {{ padding: 18px 16px; }}
      .children > .node,
      .edge {{ margin-left: 8px; }}
    }}
  </style>
</head>
<body>
  <main>
    <header>
      <h1>{escape(root.entity.name)}</h1>
      <div class="meta">
        <span><strong>depth:</strong> {depth}</span>
        <span><strong>entity_id:</strong> {escape(root.entity.id)}</span>
        <span><strong>type:</strong> {escape(root.entity.entity_type)}</span>
      </div>
    </header>
    <section class="graph">
      {_render_graph_html_node(root, is_root=True)}
    </section>
  </main>
</body>
</html>
"""


def render_relationship_summary_text(rows: tuple[EntityRelationshipCount, ...]) -> str:
    lines = ["relationship_summary:"]
    if not rows:
        lines.append("  (no relationships)")
        return "\n".join(lines)
    for row in rows:
        lines.append(f"  {row.relationship_type} = {row.count}")
    return "\n".join(lines)


def _list_entities_by_purchase_orders(
    session: Session,
    entity_type: str,
    predicate: str,
    limit: int | None,
) -> tuple[EntityPurchaseOrderSummary, ...]:
    if limit is not None and limit < 1:
        raise ValueError("limit must be greater than zero")

    statement = (
        select(
            Entity.id,
            Entity.name,
            func.count(distinct(Claim.source_record_id)).label("purchase_orders"),
        )
        .select_from(Entity)
        .outerjoin(
            Claim,
            and_(
                Claim.subject_entity_id == Entity.id,
                Claim.predicate == predicate,
            ),
        )
        .where(Entity.entity_type == entity_type)
        .group_by(Entity.id, Entity.name)
        .order_by(func.count(distinct(Claim.source_record_id)).desc(), Entity.name.asc(), Entity.id.asc())
    )
    if limit is not None:
        statement = statement.limit(limit)

    rows = session.execute(statement).all()
    return tuple(
        EntityPurchaseOrderSummary(
            id=str(entity_id),
            name=str(name),
            purchase_orders=int(purchase_orders or 0),
        )
        for entity_id, name, purchase_orders in rows
    )


def _list_entities(
    session: Session,
    *,
    limit: int | None,
    entity_type: str | None = None,
) -> tuple[EntityListSummary, ...]:
    if limit is not None and limit < 1:
        raise ValueError("limit must be greater than zero")

    statement = select(Entity.id, Entity.entity_type, Entity.name, Entity.external_id)
    if entity_type is not None:
        statement = statement.where(Entity.entity_type == entity_type)
    statement = statement.order_by(Entity.entity_type.asc(), Entity.name.asc(), Entity.id.asc())
    if limit is not None:
        statement = statement.limit(limit)

    rows = session.execute(statement).all()
    return tuple(
        EntityListSummary(
            id=str(entity_id),
            entity_type=str(entity_type_value),
            name=str(name),
            external_id=str(external_id) if external_id is not None else None,
        )
        for entity_id, entity_type_value, name, external_id in rows
    )


def _render_purchase_order_inventory(kind: str, rows: tuple[EntityPurchaseOrderSummary, ...]) -> str:
    lines: list[str] = []
    for row in rows:
        lines.extend(
            [
                f"{kind}:",
                f"id={row.id}",
                f"name={row.name}",
                f"purchase_orders={row.purchase_orders}",
                "",
            ]
        )
    if not lines:
        lines.append(f"(no {kind}s found)")
    return "\n".join(lines).rstrip()


def _render_entity_inventory(
    kind: str,
    rows: tuple[EntityListSummary, ...],
    *,
    include_type: bool,
) -> str:
    lines: list[str] = []
    for row in rows:
        lines.append(f"{kind}:")
        lines.append(f"id={row.id}")
        if include_type:
            lines.append(f"type={row.entity_type}")
        lines.append(f"name={row.name}")
        lines.append(f"external_id={_format_optional(row.external_id)}")
        lines.append("")
    if not lines:
        lines.append(f"(no {kind}s found)")
    return "\n".join(lines).rstrip()


def _search_entities(
    session: Session,
    query: str,
    entity_type: str,
    predicate: str,
    limit: int,
) -> tuple[EntitySearchResult, ...]:
    cleaned_query = query.strip()
    if not cleaned_query:
        return ()
    if limit < 1:
        raise ValueError("limit must be greater than zero")

    entities = session.scalars(
        select(Entity)
        .where(Entity.entity_type == entity_type, Entity.name.ilike(f"%{cleaned_query}%"))
        .order_by(Entity.name.asc(), Entity.id.asc())
        .limit(limit)
    ).all()
    return tuple(_build_search_result(session, entity, predicate) for entity in entities)


def _build_search_result(session: Session, entity: Entity, predicate: str) -> EntitySearchResult:
    claims_statement = select(func.count()).select_from(Claim).where(
        Claim.subject_entity_id == entity.id,
        Claim.predicate == predicate,
    )
    purchase_orders_statement = select(func.count(distinct(Claim.source_record_id))).where(
        Claim.subject_entity_id == entity.id,
        Claim.predicate == predicate,
    )
    relationships_statement = (
        select(func.count())
        .select_from(RelationshipPublic)
        .join(Claim, RelationshipPublic.claim_id == Claim.id)
        .where(Claim.subject_entity_id == entity.id, Claim.predicate == predicate)
    )
    return EntitySearchResult(
        id=str(entity.id),
        entity_type=entity.entity_type,
        name=entity.name,
        external_id=entity.external_id,
        purchase_orders=_scalar_count(session, purchase_orders_statement),
        claims=_scalar_count(session, claims_statement),
        relationships=_scalar_count(session, relationships_statement),
    )


def _render_search_results(kind: str, query: str, results: tuple[EntitySearchResult, ...]) -> str:
    lines = [f"{kind} search: {query}"]
    for result in results:
        lines.extend(
            [
                "",
                f"{kind}:",
                f"name={result.name}",
                f"external_id={_format_optional(result.external_id)}",
                f"id={result.id}",
                f"purchase_orders={result.purchase_orders}",
                f"claims={result.claims}",
                f"relationships={result.relationships}",
            ]
        )
    if not results:
        lines.extend(["", f"(no {kind}s found)"])
    return "\n".join(lines)


def _summarize_entity(entity: Entity) -> EntitySummary:
    return EntitySummary(
        id=str(entity.id),
        entity_type=entity.entity_type,
        name=entity.name,
        external_id=entity.external_id,
    )


def _summarize_evidence(evidence: Evidence) -> EntityEvidenceSummary:
    return EntityEvidenceSummary(
        id=str(evidence.id),
        title=evidence.title,
        url=evidence.url,
        published_at=evidence.published_at,
        claim_id=str(evidence.claim_id) if evidence.claim_id is not None else None,
    )


def _render_related_entities_table(entities: tuple[EntitySummary, ...]) -> str:
    rows = "".join(
        "<tr>"
        f"<td>{escape(entity.entity_type)}</td>"
        f"<td>{escape(entity.name)}</td>"
        f"<td>{escape(_format_optional(entity.external_id))}</td>"
        f"<td>{escape(entity.id)}</td>"
        "</tr>"
        for entity in entities
    )
    return _render_html_table("Related entities", ("Type", "Name", "External ID", "ID"), rows)


def _render_claims_table(claims: tuple[EntityClaimSummary, ...]) -> str:
    rows = "".join(
        "<tr>"
        f"<td>{escape(claim.predicate)}</td>"
        f"<td>{escape(claim.status)}</td>"
        f"<td>{escape(claim.subject_entity.name)}</td>"
        f"<td>{escape(_format_entity(claim.object_entity))}</td>"
        f"<td>{claim.evidence_count}</td>"
        f"<td>{claim.relationship_count}</td>"
        f"<td>{escape(claim.id)}</td>"
        "</tr>"
        for claim in claims
    )
    return _render_html_table(
        "Claims",
        ("Predicate", "Status", "Subject", "Object", "Evidence", "Relationships", "ID"),
        rows,
    )


def _render_relationships_table(relationships: tuple[EntityRelationshipSummary, ...]) -> str:
    rows = "".join(
        "<tr>"
        f"<td>{escape(relationship.relationship_type)}</td>"
        f"<td>{escape(relationship.status)}</td>"
        f"<td>{escape(relationship.related_entity.name)}</td>"
        f"<td>{escape(relationship.source_entity.name)}</td>"
        f"<td>{escape(relationship.target_entity.name)}</td>"
        f"<td>{escape(relationship.claim_id)}</td>"
        "</tr>"
        for relationship in relationships
    )
    return _render_html_table(
        "Relationships",
        ("Type", "Status", "Related entity", "Source", "Target", "Claim ID"),
        rows,
    )


def _render_evidence_table(evidences: tuple[EntityEvidenceSummary, ...]) -> str:
    rows = "".join(
        "<tr>"
        f"<td>{escape(evidence.title)}</td>"
        f'<td><a href="{escape(evidence.url)}">{escape(evidence.url)}</a></td>'
        f"<td>{escape(_format_date(evidence.published_at))}</td>"
        f"<td>{escape(_format_optional(evidence.claim_id))}</td>"
        "</tr>"
        for evidence in evidences
    )
    return _render_html_table(
        "Evidence links",
        ("Title", "URL", "Published at", "Claim ID"),
        rows,
    )


def _render_html_table(title: str, headers: tuple[str, ...], rows: str) -> str:
    header_cells = "".join(f"<th>{escape(header)}</th>" for header in headers)
    body = rows or f'<tr><td colspan="{len(headers)}">No rows</td></tr>'
    return (
        f"<h2>{escape(title)}</h2>"
        '<div class="table-wrap">'
        f"<table><thead><tr>{header_cells}</tr></thead><tbody>{body}</tbody></table>"
        "</div>"
    )


def _scalar_count(session: Session, statement) -> int:  # type: ignore[no-untyped-def]
    return int(session.scalar(statement) or 0)


def _load_entity_relationships(session: Session, entity_id: UUID) -> list[RelationshipPublic]:
    return list(
        session.scalars(
            select(RelationshipPublic)
            .where(
                or_(
                    RelationshipPublic.source_entity_id == entity_id,
                    RelationshipPublic.target_entity_id == entity_id,
                )
            )
            .options(joinedload(RelationshipPublic.source_entity), joinedload(RelationshipPublic.target_entity))
            .order_by(RelationshipPublic.created_at, RelationshipPublic.id)
        ).all()
    )


def _build_direct_neighbors(entity_id: UUID, relationships: list[RelationshipPublic]) -> tuple[EntityNeighborSummary, ...]:
    neighbors: list[EntityNeighborSummary] = []
    for relationship in relationships:
        neighbor_entity = relationship.target_entity if relationship.source_entity_id == entity_id else relationship.source_entity
        direction = "outgoing" if relationship.source_entity_id == entity_id else "incoming"
        neighbor_summary = _summarize_entity(neighbor_entity)
        neighbors.append(
            EntityNeighborSummary(
                relationship_id=str(relationship.id),
                relationship_type=relationship.relationship_type,
                direction=direction,
                neighbor=neighbor_summary,
                source_entity=_summarize_entity(relationship.source_entity),
                target_entity=_summarize_entity(relationship.target_entity),
                profile_link=EntityNavigationLink(
                    label="entity_profile",
                    href=_entity_profile_href(neighbor_summary.id),
                ),
                graph_link=EntityNavigationLink(
                    label="entity_graph",
                    href=_entity_graph_href(neighbor_summary.id),
                ),
            )
        )
    return tuple(neighbors)


def _build_entity_graph_node(
    session: Session,
    entity: Entity,
    *,
    depth: int,
    path: set[UUID],
) -> EntityGraphNodeSummary:
    if depth == 0:
        return EntityGraphNodeSummary(
            entity=_summarize_entity(entity),
            via_relationship_type=None,
            via_direction=None,
            children=(),
        )

    children: list[EntityGraphNodeSummary] = []
    for relationship in _load_entity_relationships(session, entity.id):
        is_outgoing = relationship.source_entity_id == entity.id
        child_entity = relationship.target_entity if is_outgoing else relationship.source_entity
        if child_entity.id in path:
            continue
        child_node = _build_entity_graph_node(
            session,
            child_entity,
            depth=depth - 1,
            path=path | {child_entity.id},
        )
        children.append(
            EntityGraphNodeSummary(
                entity=child_node.entity,
                via_relationship_type=relationship.relationship_type,
                via_direction="outgoing" if is_outgoing else "incoming",
                children=child_node.children,
            )
        )
    return EntityGraphNodeSummary(
        entity=_summarize_entity(entity),
        via_relationship_type=None,
        via_direction=None,
        children=tuple(children),
    )


def _append_graph_text(
    lines: list[str],
    node: EntityGraphNodeSummary,
    *,
    prefix: tuple[str, ...],
    is_last: bool,
    is_root: bool,
) -> None:
    if is_root:
        lines.append(node.entity.entity_type)
    else:
        connector = "└── " if is_last else "├── "
        label = node.entity.entity_type
        if node.via_relationship_type:
            label = f"{label} [{node.via_relationship_type} {node.via_direction}]"
        lines.append(f"{''.join(prefix)}{connector}{label}")

    child_count = len(node.children)
    for index, child in enumerate(node.children):
        next_prefix = prefix + ("" if is_root else ("    " if is_last else "│   "),)
        _append_graph_text(
            lines,
            child,
            prefix=next_prefix,
            is_last=index == child_count - 1,
            is_root=False,
        )


def _render_graph_html_node(node: EntityGraphNodeSummary, *, is_root: bool = False) -> str:
    node_class = "node root" if is_root else "node"
    header = (
        f'<div class="{node_class}">'
        f'<div class="type">{escape(node.entity.entity_type)}</div>'
        f'<div class="name">{escape(node.entity.name)}</div>'
        f'<div class="id">id={escape(node.entity.id)}</div>'
    )
    if not node.children:
        return header + "</div>"

    child_html = []
    for child in node.children:
        edge_label = child.via_relationship_type or "relationship"
        edge_direction = child.via_direction or "outgoing"
        child_html.append(
            '<div class="edge">'
            '<div class="edge-line"></div>'
            '<div>'
            f'<div class="label">{escape(edge_label)} ({escape(edge_direction)})</div>'
            f'{_render_graph_html_node(child)}'
            "</div>"
            "</div>"
        )
    return header + "".join(child_html) + "</div>"


def _entity_profile_href(entity_id: str) -> str:
    return f"profiles/{entity_id}.html"


def _entity_graph_href(entity_id: str) -> str:
    return f"graph_exports/entity_{entity_id}.html"


def _entity_navigation_links(entity_id: UUID) -> tuple[EntityNavigationLink, ...]:
    entity_id_text = str(entity_id)
    return (
        EntityNavigationLink(label="profile_html", href=_entity_profile_href(entity_id_text)),
        EntityNavigationLink(label="graph_html", href=_entity_graph_href(entity_id_text)),
        EntityNavigationLink(
            label="neighbors_cli",
            href=f"python scripts/entity_neighbors.py --entity-id {entity_id_text}",
        ),
        EntityNavigationLink(
            label="graph_cli",
            href=f"python scripts/entity_graph.py --entity-id {entity_id_text}",
        ),
        EntityNavigationLink(
            label="export_graph_cli",
            href=f"python scripts/export_entity_graph.py --entity-id {entity_id_text}",
        ),
    )


def _render_neighbors_cards(neighbors: tuple[EntityNeighborSummary, ...]) -> str:
    if not neighbors:
        return '<p class="empty">No direct neighbors</p>'
    cards = []
    for neighbor in neighbors:
        cards.append(
            '<article class="neighbor-card">'
            f'<div class="relationship">{escape(neighbor.relationship_type)}'
            f' ({escape(neighbor.direction)})</div>'
            f'<h3>{escape(neighbor.neighbor.entity_type)} | {escape(neighbor.neighbor.name)}</h3>'
            '<div class="meta">'
            f'<span>id={escape(neighbor.neighbor.id)}</span>'
            f'<span>source={escape(neighbor.source_entity.name)}</span>'
            f'<span>target={escape(neighbor.target_entity.name)}</span>'
            "</div>"
            '<div class="links">'
            f'<a href="{escape(neighbor.profile_link.href)}">{escape(neighbor.profile_link.label)}</a>'
            f'<a href="{escape(neighbor.graph_link.href)}">{escape(neighbor.graph_link.label)}</a>'
            "</div>"
            "</article>"
        )
    return f'<div class="neighbor-cards">{"".join(cards)}</div>'


def _render_relationship_counts(rows: tuple[EntityRelationshipCount, ...]) -> str:
    if not rows:
        return '<p class="empty">No relationship counts</p>'
    cards = "".join(
        f'<div class="metric"><strong>{row.count}</strong><span>{escape(row.relationship_type)}</span></div>'
        for row in rows
    )
    return f'<div class="metrics">{cards}</div>'


def _format_entity(entity: EntitySummary | None) -> str:
    if entity is None:
        return "None"
    return f"{entity.entity_type} | {entity.name}"


def _format_date(value: date | None) -> str:
    return value.isoformat() if value is not None else "None"


def _format_optional(value: object | None) -> str:
    return "None" if value is None else str(value)
