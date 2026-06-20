from __future__ import annotations

from contextlib import nullcontext
from dataclasses import asdict, dataclass
from html import escape
from pathlib import Path
import sys
from typing import Sequence

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from datosenorden.db.session import SessionLocal
from datosenorden.maintenance.dataset_registry import DatasetDetails
from datosenorden.maintenance.dataset_registry import DatasetSummary
from datosenorden.maintenance.dataset_registry import get_dataset_details
from datosenorden.maintenance.dataset_registry import list_datasets
from datosenorden.maintenance.cross_dataset_explorer import CrossDatasetOrganizationSummary
from datosenorden.maintenance.cross_dataset_explorer import get_cross_dataset_organization_summary
from datosenorden.maintenance.cross_dataset_explorer import list_cross_dataset_organizations
from datosenorden.maintenance.entity_explorer import EntityProfile
from datosenorden.maintenance.entity_explorer import list_buyers
from datosenorden.maintenance.entity_explorer import list_entities
from datosenorden.maintenance.entity_explorer import list_suppliers
from datosenorden.maintenance.entity_explorer import build_entity_graph
from datosenorden.maintenance.entity_explorer import get_entity_profile
from datosenorden.maintenance.entity_explorer import render_entity_details
from datosenorden.maintenance.entity_explorer import render_entity_graph_text
from datosenorden.maintenance.entity_explorer import search_buyers
from datosenorden.maintenance.entity_explorer import search_suppliers
from datosenorden.maintenance.human_readable import explain_dataset
from datosenorden.maintenance.human_readable import explain_entity
from datosenorden.maintenance.human_readable import explain_graph
from datosenorden.maintenance.human_readable import entity_type_display_label
from datosenorden.maintenance.human_readable import human_label
from datosenorden.maintenance.human_readable import render_dataset_explanation_text
from datosenorden.maintenance.human_readable import render_entity_explanation_text
from datosenorden.maintenance.human_readable import render_graph_explanation_text
from datosenorden.maintenance.demo_pack import demo_mode_enabled
from datosenorden.maintenance.demo_pack import resolve_demo_entity_profile
from datosenorden.maintenance.investigation_view import build_investigation_view
from datosenorden.maintenance.investigation_view import investigation_explanation_text
from datosenorden.maintenance.timeline_explorer import EntityTimeline
from datosenorden.maintenance.timeline_explorer import build_entity_timeline

PAGE_HOME = "Inicio"
PAGE_DATASETS = "Conjuntos de datos"
PAGE_SEARCH = "Buscar"
PAGE_INVESTIGATION = "Investigación"
PAGE_PROFILE = PAGE_INVESTIGATION
PAGE_GRAPH = "Grafo"
PAGE_EXPLANATION = "Explicación"

PAGE_ORDER = (
    PAGE_HOME,
    PAGE_DATASETS,
    PAGE_SEARCH,
    PAGE_INVESTIGATION,
)

GLOBAL_SELECTED_ENTITY_KEY = "selected_entity_id"
ENTITY_SELECTOR_EMPTY_MESSAGE = "Busca una entidad para comenzar."
HOME_QUESTION_KEY = "home_example_question"

QUESTION_SUPPLIERS = "suppliers_with_contracts"
QUESTION_BUYERS = "organizations_with_orders"
QUESTION_BUDGETS = "budgets_connected_to_contracts"
QUESTION_EVIDENCE = "relationship_evidence"

EXAMPLE_QUESTIONS = (
    (QUESTION_SUPPLIERS, "Â¿QuÃ© proveedores recibieron contratos?"),
    (QUESTION_BUYERS, "Â¿QuÃ© organismos emitieron Ã³rdenes de compra?"),
    (QUESTION_BUDGETS, "Â¿QuÃ© presupuestos estÃ¡n conectados con contratos?"),
    (QUESTION_EVIDENCE, "Â¿QuÃ© evidencia respalda una relaciÃ³n?"),
)

RELATIONSHIP_LABELS = {
    "BUDGET_ALLOCATED_TO": "Presupuesto asignado a",
    "ISSUES_PURCHASE_ORDER": "Emite orden de compra",
    "RECEIVES_CONTRACT": "Recibe contrato",
    "PUBLISHED_TENDER": "Publica licitaciÃ³n",
    "AWARDS_CONTRACT": "Adjudica contrato",
    "ORGANIZATION_HELD_LOBBY_MEETING": "ReuniÃ³n de lobby registrada",
    "COUNTERPARTY_PARTICIPATED_IN_LOBBY": "Contraparte participÃ³",
    "LOBBY_MEETING_ABOUT_SUBJECT": "Materia tratada en reuniÃ³n",
}


@dataclass(frozen=True)
class HomeSummary:
    datasets: int
    active_datasets: int
    source_records: int
    entities: int
    claims: int
    evidence: int
    relationships: int


@dataclass(frozen=True)
class SearchCard:
    id: str
    name: str
    entity_type: str
    external_id: str | None
    purchase_orders: int
    claims: int
    relationships: int


def build_home_summary(rows: Sequence[DatasetSummary]) -> HomeSummary:
    return HomeSummary(
        datasets=len(rows),
        active_datasets=sum(1 for row in rows if row.health == "active"),
        source_records=sum(row.source_records for row in rows),
        entities=sum(row.entities for row in rows),
        claims=sum(row.claims for row in rows),
        evidence=sum(row.evidence for row in rows),
        relationships=sum(row.relationships for row in rows),
    )


def dataset_options(rows: Sequence[DatasetSummary]) -> list[tuple[str, str]]:
    return [(f"{row.name} ({row.health})", row.slug) for row in rows]


def dataset_selector_options(rows: Sequence[DatasetSummary]) -> tuple[DatasetSummary, ...]:
    return tuple(rows)


def search_cards(results: Sequence[object]) -> list[SearchCard]:
    return [
        SearchCard(
            id=str(getattr(result, "id")),
            name=str(getattr(result, "name")),
            entity_type=str(getattr(result, "entity_type")),
            external_id=getattr(result, "external_id"),
            purchase_orders=int(getattr(result, "purchase_orders")),
            claims=int(getattr(result, "claims")),
            relationships=int(getattr(result, "relationships")),
        )
        for result in results
    ]


def search_entity_cards(session, query: str) -> list[SearchCard]:  # noqa: ANN001
    cleaned = query.strip()
    if not cleaned:
        return []

    merged: dict[str, SearchCard] = {}
    for result in tuple(search_suppliers(session, cleaned)) + tuple(search_buyers(session, cleaned)):
        card = SearchCard(
            id=str(result.id),
            name=str(result.name),
            entity_type=str(result.entity_type),
            external_id=result.external_id,
            purchase_orders=int(result.purchase_orders),
            claims=int(result.claims),
            relationships=int(result.relationships),
        )
        existing = merged.get(card.id)
        if existing is None:
            merged[card.id] = card
            continue
        merged[card.id] = SearchCard(
            id=existing.id,
            name=existing.name,
            entity_type=existing.entity_type,
            external_id=existing.external_id,
            purchase_orders=max(existing.purchase_orders, card.purchase_orders),
            claims=max(existing.claims, card.claims),
            relationships=max(existing.relationships, card.relationships),
        )
    return sorted(merged.values(), key=lambda card: (-card.purchase_orders, card.name.lower(), card.id))


def suggested_entity_cards(session, limit: int = 6) -> list[SearchCard]:  # noqa: ANN001
    seen: set[str] = set()
    cards: list[SearchCard] = []
    for entity_type, summaries in (
        ("PUBLIC_ORGANIZATION", list_buyers(session, limit=limit)),
        ("COMPANY", list_suppliers(session, limit=limit)),
    ):
        for summary in summaries:
            if summary.id in seen:
                continue
            profile = get_entity_profile(session, summary.id)
            if profile is None:
                continue
            cards.append(_search_card_from_profile(profile, purchase_orders=summary.purchase_orders, entity_type=entity_type))
            seen.add(summary.id)
            if len(cards) >= limit:
                return sorted(cards, key=lambda card: (-card.purchase_orders, card.name.lower(), card.id))

    if len(cards) < limit:
        for row in list_entities(session, limit=limit * 2):
            if row.id in seen:
                continue
            profile = get_entity_profile(session, row.id)
            if profile is None:
                continue
            cards.append(_search_card_from_profile(profile))
            seen.add(row.id)
            if len(cards) >= limit:
                break
    return sorted(cards, key=lambda card: (-card.purchase_orders, card.name.lower(), card.id))


def build_entity_card_html(card: SearchCard, *, highlighted: bool = False) -> str:
    return f"""
<article class="entity-card{' is-active' if highlighted else ''}">
  <div class="entity-card__type">{escape(entity_type_display_label(card.entity_type))}</div>
  <div class="entity-card__name">{escape(card.name)}</div>
  <div class="entity-card__metrics">
    <span>Contratos: {card.purchase_orders}</span>
    <span>Relaciones: {card.relationships}</span>
    <span>Evidencia: {card.claims}</span>
  </div>
</article>
"""


def build_dataset_table_rows(details: DatasetDetails) -> list[dict[str, object]]:
    return [asdict(row) for row in details.entities_by_type]


def build_claim_rows(details: DatasetDetails) -> list[dict[str, object]]:
    return [asdict(row) for row in details.claims_by_type]


def build_relationship_rows(details: DatasetDetails) -> list[dict[str, object]]:
    return [asdict(row) for row in details.relationship_types]


def render_metric_cards(st, metrics: Sequence[tuple[str, object, str | None]]):  # noqa: ANN001
    if not metrics:
        return
    columns = st.columns(len(metrics))
    for column, (label, value, note) in zip(columns, metrics, strict=False):
        column.metric(str(label), value)
        if note is not None and str(note).strip():
            column.caption(str(note))


def render_dataset_cards(st, rows: Sequence[DatasetSummary]):  # noqa: ANN001
    if not rows:
        st.info("Todavía no hay conjuntos de datos registrados.")
        return
    cards = "".join(_dataset_card_html(row) for row in rows)
    st.markdown(f'<div class="dataset-grid">{cards}</div>', unsafe_allow_html=True)


def render_count_cards(st, title: str, rows: Sequence[object], *, empty_message: str = "Sin registros"):  # noqa: ANN001
    st.subheader(title)
    if not rows:
        st.info(empty_message)
        return
    render_metric_cards(
        st,
        [
            (getattr(row, "label", getattr(row, "name", "")), getattr(row, "count", getattr(row, "value", 0)), None)
            for row in rows
        ],
    )


def render_entity_selector(
    st,
    session,  # noqa: ANN001
    *,
    key_prefix: str,
    label: str,
) -> SearchCard | None:
    query = st.text_input(label, value="", key=f"{key_prefix}_query", placeholder="Escribe un nombre")
    cleaned = query.strip()
    cards = suggested_entity_cards(session) if not cleaned else search_entity_cards(session, cleaned)
    if not cleaned:
        st.info(ENTITY_SELECTOR_EMPTY_MESSAGE)
        if not cards:
            return None
        return _render_entity_card_grid(
            st,
            session,
            cards,
            key_prefix=key_prefix,
            heading="Sugerencias",
            button_label="Ver investigación",
        )
    return _render_entity_card_grid(
        st,
        session,
        cards,
        key_prefix=key_prefix,
        heading="Coincidencias",
        button_label="Ver investigación",
    )


def render_dataset_selector(
    st,
    session,  # noqa: ANN001
    rows: Sequence[DatasetSummary],
    *,
    key_prefix: str,
    label: str,
) -> DatasetSummary | None:
    _ = session
    if not rows:
        st.info("Todavía no hay conjuntos de datos registrados.")
        return None

    st.markdown('<div class="section-chip">Conjunto de datos</div>', unsafe_allow_html=True)
    selected = st.selectbox(
        label,
        list(rows),
        index=None,
        key=f"{key_prefix}_select",
        format_func=_dataset_option_label,
        placeholder="Elige un conjunto de datos",
    )
    if selected_entity_id is None:
        st.info("Elige un conjunto de datos para ver los detalles.")
        return None
    return selected


def render_dataset_summary_cards(st, details: DatasetDetails, explanation) -> None:  # noqa: ANN001
    st.subheader("Resumen del conjunto")
    render_metric_cards(
        st,
        [
            ("🗂️ Conjunto", 1, "Activo"),
            ("📄 " + human_label("source_record"), details.source_records, "Fuentes"),
            ("🏛️ " + human_label("entity"), details.entities, "Entidades"),
            ("✅ " + human_label("claim"), details.claims, "Afirmaciones"),
            ("🔗 Relaciones", details.relationships, "Conexiones"),
        ],
    )
    _render_detail_card(
        st,
        "Información del conjunto",
        [
            f"Estado: {details.health}",
            f"Fuentes: {', '.join(details.source_names) if details.source_names else 'Ninguna'}",
        ],
    )
    st.subheader("¿Qué significa esto?")
    _render_summary_text_block(st, render_dataset_explanation_text(explanation), title="Explicación")


def render_entity_profile_cards(st, profile: EntityProfile) -> None:  # noqa: ANN001
    render_metric_cards(
        st,
        [
            ("Afirmaciones", len(profile.claims), "Evidencias verificables"),
            ("Relaciones", len(profile.relationships), "Conexiones públicas"),
            ("Evidencia", len(profile.evidences), "Fuentes"),
            ("Vecinos", len(profile.direct_neighbors), "Entidades conectadas"),
        ],
    )
    _render_detail_card(
        st,
        "Resumen de la entidad",
        [
            f"Tipo: {entity_type_display_label(profile.entity.entity_type)}",
            f"Nombre: {profile.entity.name}",
            f"Identificador: {profile.entity.id}",
        ],
    )


def render_entity_timeline_cards(st, timeline: EntityTimeline) -> None:  # noqa: ANN001
    st.subheader("Cronologia")
    _render_summary_text_block(st, timeline.explanation, title="Explicacion ciudadana")
    st.caption(timeline.caution)
    if not timeline.events:
        st.info("No hay eventos fechados para esta entidad.")
        return

    cards = []
    for event in timeline.events:
        cards.append(
            f"""
<article class="timeline-card">
  <div class="timeline-card__date">{escape(event.event_date.isoformat())}</div>
  <div class="dataset-badge-row"><span class="dataset-badge">{escape(event.dataset)}</span></div>
  <div class="timeline-card__title">{escape(event.title)}</div>
  <div class="timeline-card__body">{escape(event.explanation)}</div>
  <div class="timeline-card__counts">
    <span>Evidencia: {event.evidence_count}</span>
    <span>Relaciones: {event.relationship_count}</span>
  </div>
</article>
"""
    )
    st.markdown(f'<div class="timeline-card-grid">{"".join(cards)}</div>', unsafe_allow_html=True)


def _render_investigation_procurement_section(st, view) -> None:  # noqa: ANN001
    if not view.procurement_items:
        st.info("No hay contratos o compras públicas asociados a esta entidad.")
        return
    for item in view.procurement_items:
        _render_detail_card(
            st,
            item.contract_name,
            [
                f"Proveedor: {item.supplier}",
                f"Fuente: {item.dataset}",
                f"Evidencia: {item.evidence_count}",
            ],
        )
        _render_investigation_links(st, item.evidence_links)


def _render_investigation_lobby_section(st, view) -> None:  # noqa: ANN001
    if not view.lobby_items:
        st.info("No hay reuniones de lobby disponibles para esta entidad.")
        st.caption("Esto no implica irregularidad; solo muestra registros disponibles.")
        return
    st.caption("Esto no implica irregularidad; solo muestra registros disponibles.")
    for item in view.lobby_items:
        title = item.subject or "Reunión de lobby"
        _render_detail_card(
            st,
            title,
            [
                f"Organismo: {item.organization}",
                f"Contraparte: {item.counterparty}",
                f"Fecha: {item.date.isoformat() if item.date is not None else 'Sin fecha'}",
                f"Fuente: {item.dataset}",
                f"Evidencia: {item.evidence_count}",
            ],
        )
        _render_investigation_links(st, item.evidence_links)


def _render_investigation_role_section(st, view) -> None:  # noqa: ANN001
    if not view.role_items:
        st.info("No hay roles públicos disponibles para esta entidad.")
        return
    for item in view.role_items:
        _render_detail_card(
            st,
            item.role_title,
            [
                f"Titular: {item.holder}",
                f"Periodo: {item.period}",
                f"Fuente: {item.dataset}",
                f"Evidencia: {item.evidence_count}",
            ],
        )
        _render_investigation_links(st, item.evidence_links)


def _render_investigation_evidence_section(st, view) -> None:  # noqa: ANN001
    if not view.evidence_groups:
        st.info("No hay evidencia enlazada para esta entidad.")
        return
    for group in view.evidence_groups:
        body = [f"{link.title} ({link.published_at.isoformat() if link.published_at is not None else 'Sin fecha'})" for link in group.links]
        _render_detail_card(st, group.dataset, body or ["Sin evidencia disponible"])
        _render_investigation_links(st, group.links)


def _render_investigation_links(st, links) -> None:  # noqa: ANN001
    if not links:
        return
    body = "\n".join(
        f"- [{escape(link.title)}]({escape(link.url)})"
        for link in links
    )
    st.markdown(body)


def render_cross_dataset_home_section(st, session) -> None:  # noqa: ANN001
    try:
        rows = list_cross_dataset_organizations(session)
    except Exception:  # noqa: BLE001
        return
    if not rows:
        return
    st.subheader("Conexiones entre fuentes")
    cards = "".join(_cross_dataset_card_html(row) for row in rows)
    st.markdown(f'<div class="cross-dataset-grid">{cards}</div>', unsafe_allow_html=True)
    for row in rows:
        if st.button("Ver conexiones", key=f"cross_dataset_{row.organization_id}"):
            st.session_state[GLOBAL_SELECTED_ENTITY_KEY] = row.organization_id
            render_cross_dataset_detail(st, row)


def render_cross_dataset_detail(st, row: CrossDatasetOrganizationSummary) -> None:  # noqa: ANN001
    _render_detail_card(
        st,
        "Conexiones disponibles",
        [
            f"Organizacion: {row.organization_name}",
            f"Fuentes: {', '.join(_dataset_display_name(dataset) for dataset in row.datasets)}",
            f"Contratos: {row.contracts}",
            f"Reuniones Lobby: {row.lobby_meetings}",
            f"Relaciones publicas: {row.relationships}",
            f"Evidencia: {row.evidence}",
        ],
    )
    _render_detail_card(
        st,
        "Conexiones Lobby",
        [connection.name for connection in row.lobby_connections] or ["Sin conexiones Lobby disponibles"],
    )
    _render_detail_card(
        st,
        "Conexiones ChileCompra",
        [connection.name for connection in row.procurement_connections] or ["Sin conexiones ChileCompra disponibles"],
    )
    _render_summary_text_block(st, row.explanation, title="Explicacion ciudadana")


def render_cross_dataset_profile_block(st, session, profile: EntityProfile) -> None:  # noqa: ANN001
    try:
        summary = get_cross_dataset_organization_summary(session, profile.entity.id)
    except Exception:  # noqa: BLE001
        return
    if summary is None:
        return
    _render_detail_card(
        st,
        "Presente en multiples fuentes",
        [_dataset_display_name(dataset) for dataset in summary.datasets],
    )
    render_cross_dataset_detail(st, summary)


def render_claim_cards(st, profile: EntityProfile) -> None:  # noqa: ANN001
    if not profile.claims:
        st.info("No hay evidencias registradas todavía.")
        return
    for claim in profile.claims:
        _render_detail_card(
            st,
            f"Evidencia {claim.id}",
            [
                f"Tipo: {claim.predicate}",
                f"Estado: {claim.status}",
                f"Origen: {claim.subject_entity.entity_type} | {claim.subject_entity.name}",
                f"Destino: {claim.object_entity.entity_type + ' | ' + claim.object_entity.name if claim.object_entity else 'None'}",
                f"Evidencias: {claim.evidence_count}",
                f"Conexiones públicas: {claim.relationship_count}",
            ],
        )


def render_relationship_cards(st, profile: EntityProfile) -> None:  # noqa: ANN001
    if not profile.relationships:
        st.info("No hay conexiones públicas todavía.")
        return
    for relationship in profile.relationships:
        _render_detail_card(
            st,
            f"Conexión {relationship.id}",
            [
                f"Tipo: {relationship.relationship_type}",
                f"Estado: {relationship.status}",
                f"Entidad relacionada: {relationship.related_entity.entity_type} | {relationship.related_entity.name}",
                f"Origen: {relationship.source_entity.entity_type} | {relationship.source_entity.name}",
                f"Destino: {relationship.target_entity.entity_type} | {relationship.target_entity.name}",
                f"Evidencia vinculada: {relationship.claim_id}",
            ],
        )


def render_neighbor_cards(st, profile: EntityProfile) -> None:  # noqa: ANN001
    if not profile.direct_neighbors:
        st.info("No hay entidades conectadas directamente.")
        return
    for neighbor in profile.direct_neighbors:
        _render_detail_card(
            st,
            f"Vecino {neighbor.neighbor.name}",
            [
                f"Conexión pública: {neighbor.relationship_type}",
                f"Dirección: {neighbor.direction}",
                f"Entidad: {neighbor.neighbor.entity_type} | {neighbor.neighbor.name}",
                f"ID: {neighbor.neighbor.id}",
            ],
        )


def _cross_dataset_card_html(row: CrossDatasetOrganizationSummary) -> str:
    dataset_items = "".join(
        f'<span class="dataset-badge">&#10003; {escape(_dataset_display_name(dataset))}</span>'
        for dataset in row.datasets
    )
    return f"""
<article class="cross-dataset-card">
  <div class="cross-dataset-card__title">{escape(row.organization_name)}</div>
  <div class="dataset-badge-row">{dataset_items}</div>
  <div class="cross-dataset-card__metrics">
    <span>Contratos: {row.contracts}</span>
    <span>Reuniones Lobby: {row.lobby_meetings}</span>
  </div>
  <div class="cross-dataset-card__note">Informacion publica disponible, sin inferencias.</div>
</article>
"""


def _dataset_badges_html(datasets: Sequence[str]) -> str:
    if not datasets:
        return ""
    badges = "".join(
        f'<span class="dataset-badge">{escape(_dataset_display_name(dataset))}</span>'
        for dataset in datasets
    )
    return f'<div class="dataset-badge-row">{badges}</div>'


def _badge_row_html(labels: Sequence[str]) -> str:
    if not labels:
        return ""
    badges = "".join(f'<span class="dataset-badge">{escape(label)}</span>' for label in labels)
    return f'<div class="dataset-badge-row">{badges}</div>'


def _dataset_display_name(dataset: str) -> str:
    labels = {
        "chilecompra": "ChileCompra",
        "dipres": "DIPRES",
        "dipres-prototype": "DIPRES",
        "lobby": "Lobby",
        "transparencia": "Transparencia",
    }
    return labels.get(dataset, dataset)


def _dataset_card_html(row: DatasetSummary) -> str:
    if row.slug == "chilecompra":
        metrics = (
            f"<span>Organismos: {row.entities}</span>"
            f"<span>Contratos: {row.claims}</span>"
            f"<span>Proveedores: {row.relationships}</span>"
        )
    elif row.slug == "dipres-prototype":
        metrics = (
            f"<span>Presupuestos: {row.claims}</span>"
            f"<span>Organismos: {row.entities}</span>"
            f"<span>Conexiones: {row.relationships}</span>"
        )
    else:
        metrics = (
            f"<span>Fuentes: {row.source_records}</span>"
            f"<span>Entidades: {row.entities}</span>"
            f"<span>Afirmaciones: {row.claims}</span>"
        )
    status_class = "is-active" if row.health == "active" else "is-muted" if row.health == "empty" else "is-next"
    status_label = {
        "active": "Activo",
        "empty": "Vacío",
        "partially_loaded": "En carga",
    }.get(row.health, row.health.title())
    return f"""
<article class="dataset-card {status_class}">
  <div class="dataset-card__header">
    <div class="dataset-card__title">{escape(row.name)}</div>
    <span class="dataset-card__status">{escape(status_label)}</span>
  </div>
  <div class="dataset-card__subtitle">{escape('Conjunto disponible para explorar')}</div>
  <div class="dataset-card__metrics">{metrics}</div>
</article>
"""


def _entity_option_label(card: SearchCard) -> str:
    return f"{card.name} ({entity_type_display_label(card.entity_type)})"


def _dataset_option_label(row: DatasetSummary) -> str:
    return f"{row.name} ({row.health})"


def _render_detail_card(st, title: str, lines: Sequence[str]) -> None:  # noqa: ANN001
    body = "".join(f"<div class='detail-card__line'>{escape(line)}</div>" for line in lines)
    st.markdown(
        f"""
<section class="detail-card">
  <div class="detail-card__title">{escape(title)}</div>
  <div class="detail-card__body">{body}</div>
</section>
""",
        unsafe_allow_html=True,
    )


def _render_summary_text_block(st, text: str, title: str = "Resumen") -> None:  # noqa: ANN001
    st.markdown(
        f"""
<section class="summary-block">
  <div class="summary-block__title">{escape(title)}</div>
  <pre class="summary-block__body">{escape(text)}</pre>
</section>
""",
        unsafe_allow_html=True,
    )


def _search_card_from_profile(
    profile: EntityProfile,
    *,
    purchase_orders: int | None = None,
    entity_type: str | None = None,
) -> SearchCard:
    resolved_type = entity_type or profile.entity.entity_type
    resolved_purchase_orders = purchase_orders if purchase_orders is not None else _profile_purchase_order_count(profile)
    return SearchCard(
        id=profile.entity.id,
        name=profile.entity.name,
        entity_type=resolved_type,
        external_id=profile.entity.external_id,
        purchase_orders=resolved_purchase_orders,
        claims=len(profile.claims),
        relationships=len(profile.relationships),
    )


def _profile_purchase_order_count(profile: EntityProfile) -> int:
    if profile.entity.entity_type == "PUBLIC_ORGANIZATION":
        predicate = "ISSUES_PURCHASE_ORDER"
    elif profile.entity.entity_type == "COMPANY":
        predicate = "RECEIVES_CONTRACT"
    else:
        predicate = None
    if predicate is None:
        return len(profile.claims)
    return sum(1 for claim in profile.claims if claim.predicate == predicate)


def _render_entity_card_grid(
    st,
    session,  # noqa: ANN001
    cards: Sequence[SearchCard],
    *,
    key_prefix: str,
    heading: str,
    button_label: str,
) -> SearchCard | None:
    if not cards:
        st.warning("No encontramos coincidencias.")
        return None

    highlighted_id = st.session_state.get(GLOBAL_SELECTED_ENTITY_KEY)
    st.markdown(f'<div class="section-chip">{escape(heading)}</div>', unsafe_allow_html=True)
    st.markdown('<div class="entity-grid">', unsafe_allow_html=True)

    clicked_card: SearchCard | None = None
    for card in cards:
        st.markdown(build_entity_card_html(card, highlighted=card.id == highlighted_id), unsafe_allow_html=True)
        if st.button(button_label, key=f"{key_prefix}_profile_{card.id}"):
            st.session_state[GLOBAL_SELECTED_ENTITY_KEY] = card.id
            if key_prefix == "entity_search":
                _navigate_to_page(st, PAGE_INVESTIGATION)
            clicked_card = card
    st.markdown("</div>", unsafe_allow_html=True)

    if clicked_card is not None:
        return clicked_card

    selected_id = st.session_state.get(GLOBAL_SELECTED_ENTITY_KEY)
    if not selected_id:
        return None
    for card in cards:
        if card.id == selected_id:
            return card

    profile = get_entity_profile(session, selected_id)
    if profile is None:
        return None
    return _search_card_from_profile(profile)


def _navigate_to_page(st, page_name: str) -> None:  # noqa: ANN001
    st.session_state["page"] = page_name
    rerun = getattr(st, "rerun", None)
    if callable(rerun):
        rerun()


def _selected_entity_id(st) -> str | None:  # noqa: ANN001
    selected_id = st.session_state.get(GLOBAL_SELECTED_ENTITY_KEY)
    if selected_id is None:
        return None
    cleaned = str(selected_id).strip()
    return cleaned or None


def _render_go_to_search_empty_state(st, message: str) -> None:  # noqa: ANN001
    st.info(message)
    if st.button("Ir a Buscar", key="go_to_search"):
        _navigate_to_page(st, PAGE_SEARCH)


def render_demo_banner(st) -> None:  # noqa: ANN001
    st.markdown(
        """
<div class="demo-banner">
  Modo demo: contiene datos reales y datos de muestra claramente identificados.
</div>
""",
        unsafe_allow_html=True,
    )


def render_demo_start_panel(st, session) -> None:  # noqa: ANN001
    demo_profile = resolve_demo_entity_profile(session)
    st.subheader("Comenzar demo")
    if demo_profile is None:
        st.info("Todavia no encontramos la entidad recomendada para la demo.")
        return

    _render_detail_card(
        st,
        "Entidad recomendada",
        [
            f"Nombre: {demo_profile.entity.name}",
            f"Tipo: {entity_type_display_label(demo_profile.entity.entity_type)}",
            f"Contratos: {len(demo_profile.claims)}",
            f"Relaciones: {len(demo_profile.relationships)}",
            f"Evidencia: {len(demo_profile.evidences)}",
        ],
    )

    step_columns = st.columns(4)
    step_specs = (
        ("Ver entidad", "Abre la investigación con evidencia, relaciones y resumen.", "demo_step_entity", PAGE_INVESTIGATION),
        (
            "Ver conexiones entre fuentes",
            "Abre la sección de conexiones dentro de la investigación.",
            "demo_step_graph",
            PAGE_INVESTIGATION,
        ),
        (
            "Ver cronología",
            "Abre la secuencia temporal dentro de la investigación.",
            "demo_step_timeline",
            PAGE_INVESTIGATION,
        ),
        (
            "Ver evidencia",
            "Abre la investigación para revisar las fuentes vinculadas.",
            "demo_step_evidence",
            PAGE_INVESTIGATION,
        ),
    )

    for column, (title, body, key, target_page) in zip(step_columns, step_specs, strict=False):
        column.markdown(
            f"""
<div class="demo-step-card">
  <div class="demo-step-card__title">{escape(title)}</div>
  <div class="demo-step-card__body">{escape(body)}</div>
</div>
""",
            unsafe_allow_html=True,
        )
        if column.button(title, key=key):
            st.session_state[GLOBAL_SELECTED_ENTITY_KEY] = demo_profile.entity.id
            _navigate_to_page(st, target_page)


def render_app(st) -> None:  # noqa: ANN001
    st.set_page_config(page_title="DatosEnOrden", layout="wide")
    _inject_css(st)
    st.markdown('<div id="top"></div>', unsafe_allow_html=True)
    st.sidebar.title("DatosEnOrden")
    selected_page = st.session_state.get("page", PAGE_HOME)
    selected_index = PAGE_ORDER.index(selected_page) if selected_page in PAGE_ORDER else 0
    page = st.sidebar.radio("Secciones", PAGE_ORDER, index=selected_index, key="page")
    st.session_state["page"] = page
    sidebar_markdown = getattr(st.sidebar, "markdown", None)
    if callable(sidebar_markdown):
        sidebar_markdown(
            '<div class="sidebar-note">Explorador local</div><a class="sidebar-top-link" href="#top">Volver arriba</a>',
            unsafe_allow_html=True,
        )
    if demo_mode_enabled():
        render_demo_banner(st)

    with SessionLocal() as session:
        if page == PAGE_HOME:
            render_home_page(st, session)
        elif page == PAGE_DATASETS:
            render_dataset_explorer_page(st, session)
        elif page == PAGE_SEARCH:
            render_entity_search_page(st, session)
        elif page == PAGE_INVESTIGATION:
            render_investigation_page(st, session)


def render_home_page(st, session) -> None:  # noqa: ANN001
    rows = list_datasets(session)
    summary = build_home_summary(rows)
    active_rows = [row for row in rows if row.health == "active" and not row.planned]
    planned_rows = [row for row in rows if row.planned]
    secondary_rows = [row for row in rows if row.health != "active" and not row.planned]

    st.title("DatosEnOrden")
    st.markdown(
        """
<section class="hero">
  <div class="hero__eyebrow">Explorador local de datos p\u00fablicos</div>
  <div class="hero__subtitle">Explora c\u00f3mo se conectan presupuestos, organismos p\u00fablicos, contratos, proveedores y evidencias.</div>
</section>
""",
        unsafe_allow_html=True,
    )
    _render_value_cards(
        st,
        [
            ("Sigue el dinero p\u00fablico", "Presupuestos, contratos y compras en una sola vista."),
            ("Verifica relaciones con evidencia", "Cada conexi\u00f3n apunta a fuentes y afirmaciones guardadas."),
            ("Conecta fuentes p\u00fablicas", "Cruza conjuntos de datos sin salir del explorador."),
        ],
    )

    if demo_mode_enabled():
        render_demo_start_panel(st, session)

    st.subheader("Preguntas de ejemplo")
    render_example_questions(st, session)

    st.subheader("Estado actual del prototipo")
    render_metric_cards(
        st,
        [
            ("Conjuntos", summary.datasets, "Registrados"),
            ("Activos", summary.active_datasets, "Listos para explorar"),
            ("Fuentes", summary.source_records, "Registros"),
            ("Entidades", summary.entities, "Guardadas"),
            ("Afirmaciones", summary.claims, "Verificables"),
            ("Evidencia", summary.evidence, "Soporte"),
            ("Relaciones", summary.relationships, "Conexiones"),
        ],
    )

    render_cross_dataset_home_section(st, session)

    st.subheader("Explorar entidades")
    st.info("Usa la pestaña Buscar para seleccionar un organismo, proveedor, contrato o presupuesto.")
    if st.button("Ir a Buscar", key="home_go_to_search"):
        _navigate_to_page(st, PAGE_SEARCH)

    if active_rows:
        st.subheader("Conjuntos de datos")
        render_dataset_cards(st, active_rows)
    if secondary_rows:
        st.subheader("Conjuntos secundarios")
        render_dataset_cards(st, secondary_rows)
    if planned_rows:
        st.subheader("Pr\u00f3ximas fuentes")
        render_dataset_cards(st, planned_rows)

    st.subheader("Hoja de ruta")
    _render_roadmap(st)

def render_dataset_explorer_page(st, session) -> None:  # noqa: ANN001
    rows = list_datasets(session)
    st.title("Conjuntos de datos")
    if not rows:
        st.info("Todavía no hay conjuntos de datos registrados.")
        return

    selected = render_dataset_selector(st, session, rows, key_prefix="dataset_explorer", label="Elige un conjunto de datos")
    if selected is None:
        return

    with _spinner(st, "Cargando detalles del conjunto de datos..."):
        details = get_dataset_details(session, selected.slug)
    if details is None:
        st.warning("Conjunto de datos no encontrado.")
        return

    with _spinner(st, "Preparando explicación del conjunto..."):
        explanation = explain_dataset(details)
    render_dataset_summary_cards(st, details, explanation)
    render_count_cards(st, "Afirmaciones por tipo", details.claims_by_type, empty_message="Todavía no hay evidencias.")
    render_count_cards(st, "Relaciones por tipo", details.relationship_types, empty_message="Todavía no hay relaciones.")


def render_entity_search_page(st, session) -> None:  # noqa: ANN001
    st.title("Buscar")
    render_entity_selector(st, session, key_prefix="entity_search", label="Busca por nombre")


def render_investigation_page(st, session) -> None:  # noqa: ANN001
    st.title("Investigación")
    render_entity_selector(st, session, key_prefix="investigation", label="Busca por nombre")

    selected_entity_id = _selected_entity_id(st)
    if selected_entity_id is None:
        st.info("Selecciona una entidad para ver todo su contexto en una sola página.")
        return

    try:
        with _spinner(st, "Cargando investigación de la entidad..."):
            view = build_investigation_view(session, selected_entity_id)
    except (TypeError, ValueError):
        st.error("Elige una entidad válida desde los resultados de búsqueda.")
        return
    if view is None:
        st.warning("Entidad no encontrada.")
        return

    st.markdown(
        f"""
<section class="detail-card investigation-header">
  <div class="detail-card__title">{escape(view.profile.entity.name)}</div>
  <div class="detail-card__line">Tipo: {escape(view.entity_type_label)}</div>
  <div class="detail-card__line">{escape(view.summary)}</div>
</section>
""",
        unsafe_allow_html=True,
    )
    if view.dataset_badges:
        st.markdown(_badge_row_html(view.dataset_badges), unsafe_allow_html=True)

    st.subheader("Métricas clave")
    render_metric_cards(
        st,
        [
            ("Contratos", view.metrics.contracts, "Registro de compras"),
            ("Proveedores", view.metrics.suppliers, "Entidades vinculadas"),
            ("Reuniones Lobby", view.metrics.lobby_meetings, "Eventos fechados"),
            ("Roles públicos", view.metrics.public_roles, "Transparencia Activa"),
            ("Evidencia", view.metrics.evidence, "Enlaces disponibles"),
            ("Relaciones", view.metrics.relationships, "Conexiones publicas"),
        ],
    )

    st.subheader("Cronología")
    if view.timeline is None or not view.timeline.events:
        st.info("No hay cronología disponible para esta entidad.")
    else:
        render_entity_timeline_cards(st, view.timeline)

    st.subheader("Conexiones")
    _render_summary_text_block(st, view.graph_explanation, title="Resumen de conexiones")
    if view.graph is None:
        st.info("No hay grafo disponible para esta entidad.")
    else:
        render_visual_graph(st, view.graph, dataset_badges=view.dataset_badges)

    st.subheader("Contratos y compras")
    _render_investigation_procurement_section(st, view)

    st.subheader("Lobby")
    _render_investigation_lobby_section(st, view)

    st.subheader("Transparencia")
    _render_investigation_role_section(st, view)

    st.subheader("Evidencia")
    _render_investigation_evidence_section(st, view)

    st.subheader("Explicación")
    _render_summary_text_block(st, investigation_explanation_text(), title="Qué muestra esta página")


def render_entity_profile_page(st, session) -> None:  # noqa: ANN001
    st.title("Entidad")
    selected_entity_id = _selected_entity_id(st)
    if selected_entity_id is None:
        _render_go_to_search_empty_state(st, "Selecciona una entidad desde la pestaña Buscar.")
        return

    try:
        with _spinner(st, "Cargando perfil de entidad..."):
            profile = get_entity_profile(session, selected_entity_id)
    except (TypeError, ValueError):
        st.error("Elige una entidad válida desde los resultados de búsqueda.")
        return
    if profile is None:
        st.warning("Entidad no encontrada.")
        return

    tabs = st.tabs(["Resumen", "Cronologia", "Relaciones", "Evidencia", "Explicación"])

    with tabs[0]:
        render_entity_profile_cards(st, profile)
        render_cross_dataset_profile_block(st, session, profile)

    with tabs[1]:
        try:
            with _spinner(st, "Construyendo cronologia..."):
                timeline = build_entity_timeline(session, profile.entity.id)
        except Exception:  # noqa: BLE001
            st.info("La cronologia no esta disponible para esta entidad.")
            timeline = None
        if timeline is not None:
            render_entity_timeline_cards(st, timeline)

    with tabs[2]:
        st.subheader("Conexiones directas")
        render_neighbor_cards(st, profile)
        st.subheader("Relaciones")
        render_relationship_cards(st, profile)

    with tabs[3]:
        st.subheader("Evidencia")
        _render_evidence_links(st, profile)

    with tabs[4]:
        with _spinner(st, "Preparando explicación de la entidad..."):
            explanation = explain_entity(session, profile.entity.id)
        if explanation is None:
            st.warning("La explicación de la entidad no está disponible.")
            return
        _render_summary_text_block(st, render_entity_explanation_text(explanation), title="Explicación")


def render_graph_view_page(st, session) -> None:  # noqa: ANN001
    st.title("Grafo")
    st.info("Este gráfico muestra cómo se conectan las fuentes públicas.")
    depth = st.slider("Profundidad", min_value=1, max_value=4, value=1, step=1)
    selected_entity_id = _selected_entity_id(st)

    if selected_entity_id is None:
        _render_go_to_search_empty_state(st, "Selecciona una entidad desde Buscar para ver su grafo.")
        return

    try:
        with _spinner(st, "Construyendo grafo..."):
            graph = build_entity_graph(session, selected_entity_id, depth=depth)
    except (TypeError, ValueError):
        st.error("Elige una entidad válida desde los resultados de búsqueda.")
        return
    if graph is None:
        st.warning("Entidad no encontrada.")
        return

    with _spinner(st, "Preparando explicación del grafo..."):
        explanation = explain_graph(graph)
    try:
        cross_dataset_summary = get_cross_dataset_organization_summary(session, selected_entity_id)
    except Exception:  # noqa: BLE001
        cross_dataset_summary = None
    dataset_badges = cross_dataset_summary.datasets if cross_dataset_summary is not None else ()
    _render_summary_text_block(st, render_graph_explanation_text(explanation), title="Explicación del grafo")
    render_visual_graph(st, graph, dataset_badges=dataset_badges)
    with _expander(st, "Ver detalles t\u00e9cnicos"):
        _render_summary_text_block(st, render_entity_graph_text(graph, depth), title="\u00c1rbol del grafo")


def render_visual_graph(st, graph, *, dataset_badges: Sequence[str] = ()) -> None:  # noqa: ANN001
    edges = _collect_graph_edges(graph)
    badge_html = _dataset_badges_html(dataset_badges)
    flow_rows = "".join(
        f"""
<article class="graph-flow-row">
  <div class="graph-flow-node">
    <span>Entidad inicial</span>
    <strong>{escape(edge['source_type'])}</strong>
    <small>{escape(edge['source_name'])}</small>
  </div>
  <div class="graph-flow-arrow">&rarr;</div>
  <div class="graph-flow-relation">
    <span>RelaciÃ³n</span>
    <strong>{escape(edge['relationship_label'])}</strong>
    <small>{escape(edge['relationship'])}</small>
  </div>
  <div class="graph-flow-arrow">&rarr;</div>
  <div class="graph-flow-node">
    <span>Entidad conectada</span>
    <strong>{escape(edge['target_type'])}</strong>
    <small>{escape(edge['target_name'])}</small>
  </div>
</article>
"""
        for edge in edges
    )
    if not flow_rows:
        flow_rows = '<div class="graph-empty">No hay relaciones visibles para esta profundidad.</div>'

    st.markdown(
        f"""
<section class="visual-graph">
  <div class="visual-graph__title">Grafo visual: Relaciones</div>
  <article class="graph-root-card">
    <div class="graph-root-card__type">{escape(entity_type_display_label(graph.entity.entity_type))}</div>
    <div class="graph-root-card__name">{escape(graph.entity.name)}</div>
    {badge_html}
  </article>
  <div class="graph-flow-grid">
    {flow_rows}
  </div>
</section>
""",
        unsafe_allow_html=True,
    )


def render_human_explanation_page(st, session) -> None:  # noqa: ANN001
    st.title("Explicación")
    mode = st.selectbox("Qué quieres explicar", ["Conjunto de datos", "Entidad"])

    if mode == "Conjunto de datos":
        rows = list_datasets(session)
        selected = render_dataset_selector(st, session, rows, key_prefix="human_dataset", label="Elige un conjunto de datos")
        if selected is None:
            return
        with _spinner(st, "Cargando detalles del conjunto de datos..."):
            details = get_dataset_details(session, selected.slug)
        if details is None:
            st.warning("Conjunto de datos no encontrado.")
            return
        with _spinner(st, "Preparando explicación del conjunto..."):
            explanation = explain_dataset(details)
        _render_summary_text_block(st, render_dataset_explanation_text(explanation), title="Explicación")
        return

    if mode == "Entidad":
        selected_entity_id = _selected_entity_id(st)
        if selected_entity_id is None:
            st.info("Selecciona una entidad desde Buscar para ver su explicación.")
            if st.button("Ir a Buscar", key="explanation_go_to_search"):
                _navigate_to_page(st, PAGE_SEARCH)
            return
        try:
            with _spinner(st, "Preparando explicación de la entidad..."):
                explanation = explain_entity(session, selected_entity_id)
        except (TypeError, ValueError):
            st.error("Elige una entidad válida desde los resultados de búsqueda.")
            return
        if explanation is None:
            st.warning("Entidad no encontrada.")
            return
        _render_summary_text_block(st, render_entity_explanation_text(explanation), title="Explicación")
        return


def render_entity_details_text(profile: EntityProfile) -> str:
    return render_entity_details(profile)


def _spinner(st, text: str):  # noqa: ANN001
    spinner = getattr(st, "spinner", None)
    if callable(spinner):
        return spinner(text)
    return nullcontext()


def _expander(st, label: str):  # noqa: ANN001
    expander = getattr(st, "expander", None)
    if callable(expander):
        return expander(label)
    return nullcontext()


def _collect_graph_edges(graph) -> list[dict[str, str]]:  # noqa: ANN001
    edges: list[dict[str, str]] = []

    def _walk(node) -> None:  # noqa: ANN001
        for child in getattr(node, "children", ()):
            edges.append(
                {
                    "relationship": str(child.via_relationship_type or "RELATIONSHIP"),
                    "relationship_label": _relationship_display_label(str(child.via_relationship_type or "RELATIONSHIP")),
                    "source_raw_type": str(node.entity.entity_type),
                    "source_type": entity_type_display_label(str(node.entity.entity_type)),
                    "source_name": str(node.entity.name),
                    "target_raw_type": str(child.entity.entity_type),
                    "target_type": entity_type_display_label(str(child.entity.entity_type)),
                    "target_name": str(child.entity.name),
                }
            )
            _walk(child)

    _walk(graph)
    return edges


def _relationship_display_label(relationship_type: str) -> str:
    return RELATIONSHIP_LABELS.get(relationship_type, relationship_type.replace("_", " ").title())


def _collect_connected_entities(graph) -> list[dict[str, str]]:  # noqa: ANN001
    entities: dict[str, dict[str, str]] = {}

    def _walk(node) -> None:  # noqa: ANN001
        for child in getattr(node, "children", ()):
            entities[str(child.entity.id)] = {
                "type": str(child.entity.entity_type),
                "name": str(child.entity.name),
            }
            _walk(child)

    _walk(graph)
    return list(entities.values())


def _render_evidence_links(st, profile: EntityProfile) -> None:  # noqa: ANN001
    if not profile.evidences:
        st.write("No hay enlaces de evidencia.")
        return
    for evidence in profile.evidences:
        st.markdown(f"- [{evidence.title}]({evidence.url})")


def render_example_questions(st, session) -> None:  # noqa: ANN001
    st.markdown('<div class="question-action-grid">', unsafe_allow_html=True)
    columns = st.columns(len(EXAMPLE_QUESTIONS))
    for column, (question_key, label) in zip(columns, EXAMPLE_QUESTIONS, strict=False):
        if column.button(label, key=f"home_question_{question_key}"):
            st.session_state[HOME_QUESTION_KEY] = question_key
    st.markdown("</div>", unsafe_allow_html=True)

    selected_question = st.session_state.get(HOME_QUESTION_KEY)
    if selected_question is None:
        st.caption("Elige una pregunta para ver una respuesta basada en los datos cargados.")
        return
    render_example_answer(st, session, str(selected_question))


def render_example_answer(st, session, question_key: str) -> None:  # noqa: ANN001
    if question_key == QUESTION_SUPPLIERS:
        suppliers = list_suppliers(session, limit=5)
        if not suppliers:
            _render_answer_panel(st, "Proveedores con contratos", ["No hay proveedores con contratos cargados todavÃ­a."])
            return
        _render_answer_panel(
            st,
            "Proveedores con contratos",
            [f"{supplier.name}: {supplier.purchase_orders} contrato(s) registrado(s)" for supplier in suppliers],
        )
        return

    if question_key == QUESTION_BUYERS:
        buyers = list_buyers(session, limit=5)
        if not buyers:
            _render_answer_panel(st, "Organismos con Ã³rdenes de compra", ["No hay organismos con Ã³rdenes cargadas todavÃ­a."])
            return
        _render_answer_panel(
            st,
            "Organismos con Ã³rdenes de compra",
            [f"{buyer.name}: {buyer.purchase_orders} orden(es) o contrato(s) relacionado(s)" for buyer in buyers],
        )
        return

    if question_key == QUESTION_BUDGETS:
        lines = _budget_connection_lines(session)
        _render_answer_panel(
            st,
            "Presupuestos conectados con contratos",
            lines or ["No hay rutas presupuesto -> organismo -> contrato disponibles con los datos actuales."],
        )
        return

    if question_key == QUESTION_EVIDENCE:
        lines = _evidence_answer_lines(session)
        _render_answer_panel(
            st,
            "Evidencia que respalda relaciones",
            lines or ["No hay evidencia enlazada disponible con los datos actuales."],
        )
        return

    st.info("Elige una pregunta de ejemplo para comenzar.")


def _render_answer_panel(st, title: str, lines: Sequence[str]) -> None:  # noqa: ANN001
    body = "".join(f"<li>{escape(line)}</li>" for line in lines)
    st.markdown(
        f"""
<section class="answer-panel">
  <div class="answer-panel__title">{escape(title)}</div>
  <ul>{body}</ul>
  <div class="answer-panel__note">Respuesta neutral basada en los datos persistidos y su evidencia disponible.</div>
</section>
""",
        unsafe_allow_html=True,
    )


def _budget_connection_lines(session) -> list[str]:  # noqa: ANN001
    lines: list[str] = []
    for row in list_entities(session, limit=80):
        if row.entity_type != "BUDGET":
            continue
        graph = build_entity_graph(session, row.id, depth=3)
        if graph is None:
            continue
        for edge in _collect_graph_edges(graph):
            if edge["target_raw_type"] in {"CONTRACT", "PURCHASE_ORDER"}:
                lines.append(f"{row.name} -> {edge['source_name']} -> {edge['target_name']}")
            elif edge["target_raw_type"] == "PUBLIC_ORGANIZATION":
                lines.append(f"{row.name} -> {edge['target_name']}")
            if len(lines) >= 5:
                return lines
    return lines


def _evidence_answer_lines(session) -> list[str]:  # noqa: ANN001
    lines: list[str] = []
    for card in suggested_entity_cards(session, limit=8):
        profile = get_entity_profile(session, card.id)
        if profile is None:
            continue
        if profile.evidences:
            first = profile.evidences[0]
            lines.append(f"{profile.entity.name}: {len(profile.evidences)} evidencia(s). Ejemplo: {first.title} ({first.url})")
        elif profile.claims or profile.relationships:
            lines.append(
                f"{profile.entity.name}: {len(profile.claims)} afirmaciÃ³n(es) y {len(profile.relationships)} relaciÃ³n(es) registradas."
            )
        if len(lines) >= 5:
            return lines
    if lines:
        return lines
    return [
        f"{row.name}: {row.evidence} evidencia(s), {row.claims} afirmaciÃ³n(es), {row.relationships} relaciÃ³n(es)"
        for row in list_datasets(session)
        if row.evidence or row.claims or row.relationships
    ][:5]


def _legacy_render_selected_entity_profile(st, session, entity_id: str) -> None:  # noqa: ANN001
    try:
        with _spinner(st, "Cargando perfil de entidad..."):
            profile = get_entity_profile(session, entity_id)
    except (TypeError, ValueError):
        st.error("Elige una entidad vÃ¡lida desde los resultados de bÃºsqueda.")
        return
    if profile is None:
        st.warning("Entidad no encontrada.")
        return
    st.subheader("Perfil seleccionado")
    render_entity_profile_cards(st, profile)


def _render_question_chips(st, questions: Sequence[str]) -> None:  # noqa: ANN001
    chips = "".join(f'<span class="question-chip">{escape(question)}</span>' for question in questions)
    st.markdown(f'<div class="question-chip-grid">{chips}</div>', unsafe_allow_html=True)


def _render_roadmap(st) -> None:  # noqa: ANN001
    items = [
        ("ChileCompra", "active"),
        ("DIPRES Prototype", "active"),
        ("DIPRES Real", "next"),
        ("Lobby", "planned"),
        ("SERVEL", "planned"),
        ("Transparencia", "planned"),
        ("Contraloría", "planned"),
        ("Municipalidades", "planned"),
    ]
    status_labels = {"active": "Activo", "next": "Siguiente", "planned": "Planificado"}
    cards = []
    for name, status in items:
        cards.append(
            f"""
<article class="roadmap-card roadmap-card--{status}">
  <div class="roadmap-card__status">{escape(status_labels[status])}</div>
  <div class="roadmap-card__name">{escape(name)}</div>
</article>
"""
        )
    st.markdown(f'<div class="roadmap-grid">{"".join(cards)}</div>', unsafe_allow_html=True)


def _render_value_cards(st, items: Sequence[tuple[str, str]]) -> None:  # noqa: ANN001
    cards = "".join(
        f"""
<article class="value-card">
  <div class="value-card__title">{escape(title)}</div>
  <div class="value-card__body">{escape(body)}</div>
</article>
"""
        for title, body in items
    )
    st.markdown(f'<div class="value-card-grid">{cards}</div>', unsafe_allow_html=True)


def _inject_css(st) -> None:  # noqa: ANN001
    st.markdown(
        """
<style>
:root {
  --bg: #090d12;
  --panel: #101820;
  --panel-2: #15202a;
  --panel-3: #1b2733;
  --line: rgba(123, 224, 208, 0.18);
  --ink: #f2f7fb;
  --muted: #c0cfdd;
  --accent: #2fb6a5;
  --accent-2: #7be0d0;
  --good: #3ddc97;
  --warn: #f2c94c;
}

div[data-testid="stAppViewContainer"] {
  background:
    radial-gradient(circle at top left, rgba(47, 182, 165, 0.12), transparent 28%),
    linear-gradient(180deg, #090d12 0%, #10171f 100%);
  color: var(--ink);
}

section.main > div {
  max-width: 1280px;
  padding-top: 0.8rem;
  padding-bottom: 1.5rem;
}

div[data-testid="stSidebar"] {
  background:
    radial-gradient(circle at top left, rgba(47, 182, 165, 0.12), transparent 34%),
    linear-gradient(180deg, #071018 0%, #0d1720 100%);
  border-right: 1px solid rgba(123, 224, 208, 0.14);
}

div[data-testid="stSidebar"] * {
  color: var(--ink);
}

div[data-testid="stSidebar"] h1,
div[data-testid="stSidebar"] h2,
div[data-testid="stSidebar"] .st-emotion-cache-10trblm {
  color: var(--accent-2);
}

div[data-testid="stSidebar"] [data-testid="stRadio"] {
  margin-top: 1rem;
}

div[data-testid="stSidebar"] [data-testid="stRadio"] > label {
  color: var(--muted);
  font-size: 0.78rem;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

div[data-testid="stSidebar"] [role="radiogroup"] {
  display: grid;
  gap: 8px;
}

div[data-testid="stSidebar"] [role="radio"] {
  border: 1px solid transparent;
  border-radius: 10px;
  padding: 7px 10px;
  background: rgba(255, 255, 255, 0.025);
}

div[data-testid="stSidebar"] [role="radio"][aria-checked="true"] {
  background: rgba(242, 247, 251, 0.14);
  border-color: rgba(123, 224, 208, 0.46);
  box-shadow: inset 3px 0 0 var(--accent-2);
}

.sidebar-top-link {
  display: inline-flex;
  margin-top: 14px;
  color: var(--accent-2) !important;
  font-size: 0.84rem;
  font-weight: 700;
  text-decoration: none;
}

.sidebar-note {
  margin-top: 10px;
  color: var(--muted);
  font-size: 0.86rem;
  line-height: 1.4;
}

h1, h2, h3, p, li, label, .stMarkdown, .stCaption {
  color: var(--ink);
}

h1 {
  font-size: 2.2rem;
  line-height: 1.05;
  letter-spacing: -0.03em;
  margin-bottom: 0.15rem;
}

h2 {
  font-size: 1.25rem;
  line-height: 1.2;
  margin-top: 1.1rem;
  margin-bottom: 0.4rem;
}

h3 {
  font-size: 1rem;
  line-height: 1.25;
  margin-top: 0.8rem;
  margin-bottom: 0.25rem;
}

.hero {
  display: flex;
  flex-direction: column;
  gap: 0.45rem;
  margin: 0.4rem 0 0.9rem;
}

.hero__eyebrow {
  color: var(--accent-2);
  font-size: 0.82rem;
  font-weight: 800;
  letter-spacing: 0.1em;
  text-transform: uppercase;
}

.hero__subtitle {
  max-width: 920px;
  font-size: 1.08rem;
  line-height: 1.7;
  color: var(--ink);
}

.value-card-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 12px;
  margin: 0.15rem 0 1rem;
}

.value-card {
  background: linear-gradient(180deg, rgba(17, 24, 32, 0.98), rgba(21, 32, 42, 0.98));
  border: 1px solid rgba(123, 224, 208, 0.18);
  border-radius: 18px;
  padding: 14px 16px;
  box-shadow: 0 12px 28px rgba(0, 0, 0, 0.18);
}

.value-card__title {
  font-size: 0.9rem;
  font-weight: 800;
  letter-spacing: 0.03em;
  color: var(--accent-2);
  margin-bottom: 0.35rem;
}

.value-card__body {
  color: var(--ink);
  font-size: 0.95rem;
  line-height: 1.55;
}

div[data-testid="stAlert"] {
  background: rgba(16, 24, 32, 0.92);
  border: 1px solid rgba(123, 224, 208, 0.16);
  color: var(--ink);
}

.stRadio label, .stSelectbox label, .stTextInput label {
  color: var(--muted);
}

div[data-testid="stMetric"] {
  background: linear-gradient(180deg, var(--panel) 0%, var(--panel-2) 100%);
  border: 1px solid rgba(123, 224, 208, 0.16);
  border-radius: 14px;
  padding: 0.8rem 0.9rem;
  box-shadow: 0 10px 24px rgba(0, 0, 0, 0.18);
}

div[data-testid="stMetric"] * {
  color: var(--ink);
}

.dataset-grid, .entity-grid, .question-chip-grid, .roadmap-grid, .cross-dataset-grid, .timeline-card-grid {
  display: grid;
  gap: 12px;
  margin: 0.25rem 0 0.9rem;
}

.dataset-grid, .cross-dataset-grid {
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
}

.timeline-card-grid {
  grid-template-columns: 1fr;
}

.entity-grid {
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
}

.demo-banner {
  margin: 0 0 0.7rem;
  padding: 10px 12px;
  border-radius: 12px;
  border: 1px solid rgba(123, 224, 208, 0.25);
  background: rgba(47, 182, 165, 0.12);
  color: var(--accent-2);
  font-size: 0.9rem;
  font-weight: 700;
}

.demo-step-card {
  min-height: 120px;
  border: 1px solid rgba(123, 224, 208, 0.18);
  border-radius: 14px;
  padding: 12px 14px;
  background: linear-gradient(180deg, var(--panel) 0%, var(--panel-2) 100%);
  margin-bottom: 10px;
}

.demo-step-card__title {
  color: var(--accent-2);
  font-size: 0.84rem;
  font-weight: 800;
  letter-spacing: 0.06em;
  text-transform: uppercase;
}

.demo-step-card__body {
  margin-top: 6px;
  color: var(--ink);
  font-size: 0.92rem;
  line-height: 1.45;
}

.question-chip-grid {
  grid-template-columns: repeat(auto-fit, minmax(230px, 1fr));
}

.question-action-grid {
  margin-bottom: 0.35rem;
}

.answer-panel {
  margin: 0.35rem 0 0.85rem;
  padding: 14px 16px;
  border: 1px solid rgba(123, 224, 208, 0.22);
  border-radius: 12px;
  background: linear-gradient(180deg, rgba(47, 182, 165, 0.12), rgba(255, 255, 255, 0.035));
}

.answer-panel__title {
  color: var(--accent-2);
  font-weight: 800;
  margin-bottom: 8px;
}

.answer-panel ul {
  margin: 0;
  padding-left: 1.1rem;
}

.answer-panel li {
  margin: 4px 0;
  color: var(--ink);
}

.answer-panel__note {
  margin-top: 10px;
  color: var(--muted);
  font-size: 0.82rem;
}

.roadmap-grid {
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
}

.dataset-card,
.entity-card,
.cross-dataset-card,
.timeline-card,
.detail-card,
.summary-block,
.roadmap-card,
.question-chip {
  background: linear-gradient(180deg, var(--panel) 0%, var(--panel-2) 100%);
  border: 1px solid var(--line);
  border-radius: 16px;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.22);
}

.dataset-card,
.entity-card,
.cross-dataset-card,
.timeline-card,
.detail-card,
.summary-block {
  padding: 12px 14px;
}

.dataset-card {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.dataset-card.is-active {
  border-color: rgba(47, 182, 165, 0.36);
  box-shadow: 0 14px 34px rgba(47, 182, 165, 0.10);
}

.dataset-card.is-muted {
  opacity: 0.72;
}

.dataset-card.is-next {
  border-color: rgba(123, 224, 208, 0.24);
}

.dataset-card__header,
.roadmap-card__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.dataset-card__title,
.cross-dataset-card__title,
.detail-card__title,
.summary-block__title {
  font-size: 0.78rem;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--accent-2);
}

.dataset-card__subtitle {
  color: var(--muted);
  font-size: 0.92rem;
}

.dataset-card__status,
.roadmap-card__status,
.section-chip {
  display: inline-flex;
  align-items: center;
  border-radius: 999px;
  padding: 4px 8px;
  font-size: 0.72rem;
  font-weight: 800;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  background: rgba(47, 182, 165, 0.14);
  color: var(--accent-2);
  border: 1px solid rgba(123, 224, 208, 0.18);
}

.dataset-card__metrics,
.entity-card__metrics,
.cross-dataset-card__metrics,
.dataset-badge-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.dataset-card__metrics span,
.entity-card__metrics span,
.cross-dataset-card__metrics span,
.dataset-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  border: 1px solid rgba(125, 211, 252, 0.16);
  border-radius: 999px;
  padding: 4px 10px;
  font-size: 0.84rem;
  color: var(--ink);
  background: rgba(255, 255, 255, 0.03);
}

.cross-dataset-card {
  display: flex;
  flex-direction: column;
  gap: 10px;
  border-color: rgba(47, 182, 165, 0.34);
}

.cross-dataset-card__note {
  color: var(--muted);
  font-size: 0.84rem;
}

.dataset-badge-row {
  margin-top: 8px;
}

.entity-card__type {
  color: var(--accent-2);
  font-size: 0.78rem;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.entity-card__name {
  margin-top: 2px;
  font-size: 1.05rem;
  font-weight: 700;
  line-height: 1.2;
}

.timeline-card {
  display: grid;
  gap: 8px;
  border-left: 4px solid var(--accent-2);
}

.timeline-card__date {
  color: var(--muted);
  font-size: 0.86rem;
  font-weight: 800;
}

.timeline-card__title {
  color: var(--ink);
  font-size: 1rem;
  font-weight: 800;
}

.timeline-card__body {
  color: var(--muted);
  font-size: 0.92rem;
  line-height: 1.45;
}

.timeline-card__counts {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  color: var(--muted);
  font-size: 0.84rem;
}

.detail-card__line {
  color: var(--muted);
  font-size: 0.9rem;
  margin-top: 4px;
  overflow-wrap: anywhere;
}

.entity-card {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.entity-card.is-active {
  border-color: rgba(47, 182, 165, 0.36);
  box-shadow: 0 14px 34px rgba(47, 182, 165, 0.10);
}

.detail-card__body,
.summary-block__body {
  margin-top: 10px;
  white-space: pre-wrap;
  word-break: break-word;
  line-height: 1.45;
  font-size: 0.92rem;
  color: var(--ink);
  font-family: inherit;
}

.summary-block {
  margin-bottom: 0.8rem;
}

.question-chip,
.roadmap-card {
  display: inline-flex;
  align-items: center;
  padding: 8px 12px;
  font-size: 0.9rem;
  color: var(--ink);
}

.question-chip {
  justify-content: center;
  min-height: 54px;
  padding: 10px 14px;
  font-size: 0.95rem;
  border-color: rgba(123, 224, 208, 0.20);
  background: linear-gradient(180deg, rgba(18, 27, 36, 0.98), rgba(23, 35, 46, 0.98));
  cursor: default;
}

.question-chip:hover {
  border-color: rgba(123, 224, 208, 0.36);
  box-shadow: 0 14px 30px rgba(47, 182, 165, 0.10);
}

.roadmap-card {
  width: 100%;
  min-height: 92px;
  align-items: flex-start;
  flex-direction: column;
  gap: 10px;
  padding: 12px 14px;
}

.roadmap-card--active {
  border-color: rgba(47, 182, 165, 0.36);
}

.roadmap-card--next {
  border-color: rgba(123, 224, 208, 0.28);
}

.roadmap-card--planned {
  opacity: 0.76;
}

.roadmap-card__name {
  font-size: 0.98rem;
  font-weight: 700;
  line-height: 1.2;
}

.roadmap-card__status {
  background: rgba(123, 224, 208, 0.14);
}

.section-chip {
  margin: 0 0 0.45rem;
}

.question-chip {
  justify-content: center;
  text-align: center;
  min-height: 48px;
}

.stButton > button {
  border-radius: 999px;
  border: 1px solid rgba(123, 224, 208, 0.24);
  background: rgba(47, 182, 165, 0.14);
  color: var(--ink);
  padding: 0.42rem 0.85rem;
}

.stButton > button:hover {
  border-color: rgba(123, 224, 208, 0.42);
}

.visual-graph {
  display: grid;
  grid-template-columns: minmax(220px, 0.9fr) minmax(260px, 1.2fr) minmax(260px, 1.2fr);
  gap: 14px;
  margin: 0.4rem 0 1rem;
  align-items: stretch;
}

.visual-graph__column {
  background: linear-gradient(180deg, var(--panel) 0%, var(--panel-2) 100%);
  border: 1px solid var(--line);
  border-radius: 16px;
  padding: 14px;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.22);
}

.visual-graph__title {
  color: var(--accent-2);
  font-size: 0.78rem;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  margin-bottom: 10px;
}

.graph-root-card,
.graph-edge-card,
.graph-entity-card {
  border: 1px solid rgba(123, 224, 208, 0.18);
  border-radius: 12px;
  padding: 10px 12px;
  background: rgba(255, 255, 255, 0.035);
}

.graph-root-card {
  border-color: rgba(47, 182, 165, 0.40);
  background: rgba(47, 182, 165, 0.12);
}

.graph-edge-grid,
.graph-entity-grid {
  display: grid;
  gap: 10px;
}

.graph-root-card__type,
.graph-edge-card__label,
.graph-entity-card__type {
  color: var(--accent-2);
  font-size: 0.76rem;
  font-weight: 800;
  letter-spacing: 0.06em;
  text-transform: uppercase;
}

.graph-root-card__name,
.graph-entity-card__name {
  margin-top: 5px;
  font-size: 0.95rem;
  font-weight: 700;
  line-height: 1.25;
}

.graph-edge-card__path {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 6px;
  color: var(--ink);
  font-size: 0.9rem;
}

.graph-edge-card__path strong {
  color: var(--accent-2);
}

.graph-edge-card__names,
.graph-empty {
  margin-top: 6px;
  color: var(--muted);
  font-size: 0.84rem;
  line-height: 1.35;
}

.visual-graph {
  display: grid;
  grid-template-columns: 1fr;
  gap: 12px;
  margin: 0.4rem 0 1rem;
  background: linear-gradient(180deg, var(--panel) 0%, var(--panel-2) 100%);
  border: 1px solid var(--line);
  border-radius: 16px;
  padding: 14px;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.22);
}

.graph-flow-grid {
  display: grid;
  gap: 10px;
}

.graph-flow-row {
  display: grid;
  grid-template-columns: minmax(180px, 1fr) 34px minmax(180px, 1fr) 34px minmax(180px, 1fr);
  gap: 10px;
  align-items: stretch;
}

.graph-flow-node,
.graph-flow-relation {
  border: 1px solid rgba(123, 224, 208, 0.18);
  border-radius: 12px;
  padding: 10px 12px;
  background: rgba(255, 255, 255, 0.035);
}

.graph-flow-node span,
.graph-flow-relation span {
  color: var(--muted);
  display: block;
  font-size: 0.72rem;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.graph-flow-node strong,
.graph-flow-relation strong {
  display: block;
  margin-top: 5px;
  color: var(--accent-2);
  font-size: 0.9rem;
}

.graph-flow-node small,
.graph-flow-relation small {
  display: block;
  margin-top: 5px;
  color: var(--ink);
  font-size: 0.84rem;
  line-height: 1.35;
}

.graph-flow-arrow {
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--accent-2);
  font-size: 1.15rem;
  font-weight: 800;
}

div[data-testid="stMetric"] label,
div[data-testid="stMetric"] div {
  color: var(--ink);
}

@media (max-width: 720px) {
  section.main > div {
    padding-left: 0.75rem;
    padding-right: 0.75rem;
  }

  .visual-graph {
    grid-template-columns: 1fr;
  }

  .graph-flow-row {
    grid-template-columns: 1fr;
  }

  .graph-flow-arrow {
    transform: rotate(90deg);
  }
}
</style>
""",
        unsafe_allow_html=True,
    )


def main(argv: Sequence[str] | None = None) -> int:
    _ = argv
    try:
        import streamlit as st
    except Exception as exc:  # noqa: BLE001
        print("Streamlit is required to run the explorer.", file=sys.stderr)
        print(f"Detalle: {exc}", file=sys.stderr)
        return 1

    try:
        render_app(st)
    except Exception:  # noqa: BLE001
        st.error("The explorer could not load data from PostgreSQL.")
        st.info("Check DATABASE_URL and confirm PostgreSQL is reachable.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
