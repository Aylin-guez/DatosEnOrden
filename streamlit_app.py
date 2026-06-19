from __future__ import annotations

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

PAGE_HOME = "Inicio"
PAGE_DATASETS = "Conjuntos de datos"
PAGE_SEARCH = "Buscar"
PAGE_PROFILE = "Entidad"
PAGE_GRAPH = "Grafo"
PAGE_EXPLANATION = "Explicación"

PAGE_ORDER = (
    PAGE_HOME,
    PAGE_DATASETS,
    PAGE_SEARCH,
    PAGE_PROFILE,
    PAGE_GRAPH,
    PAGE_EXPLANATION,
)

GLOBAL_SELECTED_ENTITY_KEY = "selected_entity_id"
ENTITY_SELECTOR_EMPTY_MESSAGE = "Busca una entidad para comenzar."


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
  <div class="entity-card__hint">Ver perfil</div>
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
            button_label="Ver perfil",
        )
    return _render_entity_card_grid(
        st,
        session,
        cards,
        key_prefix=key_prefix,
        heading="Coincidencias",
        button_label="Ver perfil",
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
    if selected is None:
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


def _set_page(st, page_name: str) -> None:  # noqa: ANN001
    st.session_state["page"] = page_name
    rerun = getattr(st, "rerun", None)
    if callable(rerun):
        rerun()


def render_app(st) -> None:  # noqa: ANN001
    st.set_page_config(page_title="DatosEnOrden", layout="wide")
    _inject_css(st)
    st.sidebar.title("DatosEnOrden")
    page = st.sidebar.radio("Secciones", PAGE_ORDER, index=0, key="page")

    with SessionLocal() as session:
        if page == PAGE_HOME:
            render_home_page(st, session)
        elif page == PAGE_DATASETS:
            render_dataset_explorer_page(st, session)
        elif page == PAGE_SEARCH:
            render_entity_search_page(st, session)
        elif page == PAGE_PROFILE:
            render_entity_profile_page(st, session)
        elif page == PAGE_GRAPH:
            render_graph_view_page(st, session)
        elif page == PAGE_EXPLANATION:
            render_human_explanation_page(st, session)


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
  <div class="hero__eyebrow">Explorador local de datos públicos</div>
  <div class="hero__subtitle">Explora cómo se conectan presupuestos, organismos públicos, contratos, proveedores y evidencias.</div>
</section>
""",
        unsafe_allow_html=True,
    )
    _render_value_cards(
        st,
        [
            ("Sigue el dinero público", "Presupuestos, contratos y compras en una sola vista."),
            ("Verifica relaciones con evidencia", "Cada conexión apunta a fuentes y afirmaciones guardadas."),
            ("Conecta fuentes públicas", "Cruza conjuntos de datos sin salir del explorador."),
        ],
    )

    st.subheader("Busca un organismo, proveedor, contrato o presupuesto")
    render_entity_selector(st, session, key_prefix="home_search", label="Busca un organismo, proveedor, contrato o presupuesto")

    st.subheader("Preguntas de ejemplo")
    _render_question_chips(
        st,
        [
            "¿Qué proveedores recibieron contratos?",
            "¿Qué organismos emitieron órdenes de compra?",
            "¿Qué presupuestos están conectados con contratos?",
            "¿Qué evidencia respalda una relación?",
        ],
    )

    st.subheader("Estado actual del prototipo")
    render_metric_cards(
        st,
        [
            ("🗂️ Conjuntos", summary.datasets, "Registrados"),
            ("🟢 Activos", summary.active_datasets, "Listos para explorar"),
            ("📄 Fuentes", summary.source_records, "Registros"),
            ("🏛️ Entidades", summary.entities, "Guardadas"),
            ("✅ Afirmaciones", summary.claims, "Verificables"),
            ("📎 Evidencia", summary.evidence, "Soporte"),
            ("🔗 Relaciones", summary.relationships, "Conexiones"),
        ],
    )

    if active_rows:
        st.subheader("Conjuntos de datos")
        render_dataset_cards(st, active_rows)
    if secondary_rows:
        st.subheader("Conjuntos secundarios")
        render_dataset_cards(st, secondary_rows)
    if planned_rows:
        st.subheader("Próximas fuentes")
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

    details = get_dataset_details(session, selected.slug)
    if details is None:
        st.warning("Conjunto de datos no encontrado.")
        return

    explanation = explain_dataset(details)
    render_dataset_summary_cards(st, details, explanation)
    render_count_cards(st, "Afirmaciones por tipo", details.claims_by_type, empty_message="Todavía no hay evidencias.")
    render_count_cards(st, "Relaciones por tipo", details.relationship_types, empty_message="Todavía no hay relaciones.")


def render_entity_search_page(st, session) -> None:  # noqa: ANN001
    st.title("Buscar")
    render_entity_selector(st, session, key_prefix="entity_search", label="Busca por nombre")


def render_entity_profile_page(st, session) -> None:  # noqa: ANN001
    st.title("Entidad")
    selected = render_entity_selector(st, session, key_prefix="entity_profile", label="Busca por nombre")
    if selected is None:
        st.caption("Busca una entidad para comenzar.")
        return

    try:
        profile = get_entity_profile(session, selected.id)
    except (TypeError, ValueError):
        st.error("Elige una entidad válida desde los resultados de búsqueda.")
        return
    if profile is None:
        st.warning("Entidad no encontrada.")
        return

    tabs = st.tabs(["Resumen", "Relaciones", "Evidencia", "Explicación"])

    with tabs[0]:
        render_entity_profile_cards(st, profile)

    with tabs[1]:
        st.subheader("Conexiones directas")
        render_neighbor_cards(st, profile)
        st.subheader("Relaciones")
        render_relationship_cards(st, profile)

    with tabs[2]:
        st.subheader("Evidencia")
        _render_evidence_links(st, profile)

    with tabs[3]:
        explanation = explain_entity(session, profile.entity.id)
        if explanation is None:
            st.warning("La explicación de la entidad no está disponible.")
            return
        _render_summary_text_block(st, render_entity_explanation_text(explanation), title="Explicación")


def render_graph_view_page(st, session) -> None:  # noqa: ANN001
    st.title("Grafo")
    st.info("Este gráfico muestra cómo se conectan las fuentes públicas.")
    selected = render_entity_selector(st, session, key_prefix="graph_view", label="Busca por nombre")
    depth = st.slider("Profundidad", min_value=1, max_value=4, value=1, step=1)

    if selected is None:
        st.caption("Busca una entidad para ver cómo se relaciona con contratos, organizaciones y proveedores.")
        return

    try:
        graph = build_entity_graph(session, selected.id, depth=depth)
    except (TypeError, ValueError):
        st.error("Elige una entidad válida desde los resultados de búsqueda.")
        return
    if graph is None:
        st.warning("Entidad no encontrada.")
        return

    explanation = explain_graph(graph)
    _render_summary_text_block(st, render_graph_explanation_text(explanation), title="Explicación del grafo")
    _render_summary_text_block(st, render_entity_graph_text(graph, depth), title="Árbol del grafo")


def render_human_explanation_page(st, session) -> None:  # noqa: ANN001
    st.title("Explicación")
    mode = st.selectbox("Qué quieres explicar", ["Conjunto de datos", "Entidad", "Grafo"])

    if mode == "Conjunto de datos":
        rows = list_datasets(session)
        selected = render_dataset_selector(st, session, rows, key_prefix="human_dataset", label="Elige un conjunto de datos")
        if selected is None:
            return
        details = get_dataset_details(session, selected.slug)
        if details is None:
            st.warning("Conjunto de datos no encontrado.")
            return
        _render_summary_text_block(st, render_dataset_explanation_text(explain_dataset(details)), title="Explicación")
        return

    if mode == "Entidad":
        selected = render_entity_selector(st, session, key_prefix="human_entity", label="Busca por nombre")
        if selected is None:
            st.caption("Busca una entidad para comenzar.")
            return
        try:
            explanation = explain_entity(session, selected.id)
        except (TypeError, ValueError):
            st.error("Elige una entidad válida desde los resultados de búsqueda.")
            return
        if explanation is None:
            st.warning("Entidad no encontrada.")
            return
        _render_summary_text_block(st, render_entity_explanation_text(explanation), title="Explicación")
        return

    selected = render_entity_selector(st, session, key_prefix="human_graph", label="Busca por nombre")
    depth = st.slider("Profundidad", min_value=1, max_value=4, value=1, step=1, key="human_graph_depth")
    if selected is None:
        st.caption("Busca una entidad para comenzar.")
        return
    try:
        graph = build_entity_graph(session, selected.id, depth=depth)
    except (TypeError, ValueError):
        st.error("Elige una entidad válida desde los resultados de búsqueda.")
        return
    if graph is None:
        st.warning("Entidad no encontrada.")
        return
    _render_summary_text_block(st, render_graph_explanation_text(explain_graph(graph)), title="Explicación")


def render_entity_details_text(profile: EntityProfile) -> str:
    return render_entity_details(profile)


def _render_evidence_links(st, profile: EntityProfile) -> None:  # noqa: ANN001
    if not profile.evidences:
        st.write("No hay enlaces de evidencia.")
        return
    for evidence in profile.evidences:
        st.markdown(f"- [{evidence.title}]({evidence.url})")


def _render_entity_search_cards(
    st,
    session,  # noqa: ANN001
    *,
    key_prefix: str,
    button_label: str,
) -> None:
    _ = (key_prefix, button_label)
    render_entity_selector(st, session, key_prefix=key_prefix, label="Busca por nombre")


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
  background: #0a1118;
  border-right: 1px solid rgba(123, 224, 208, 0.14);
}

div[data-testid="stSidebar"] * {
  color: var(--ink);
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

.dataset-grid, .entity-grid, .question-chip-grid, .roadmap-grid {
  display: grid;
  gap: 12px;
  margin: 0.25rem 0 0.9rem;
}

.dataset-grid {
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
}

.entity-grid {
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
}

.question-chip-grid {
  grid-template-columns: repeat(auto-fit, minmax(230px, 1fr));
}

.roadmap-grid {
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
}

.dataset-card,
.entity-card,
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
.entity-card__metrics {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.dataset-card__metrics span,
.entity-card__metrics span {
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

.entity-card__hint {
  color: var(--accent-2);
  font-size: 0.78rem;
  font-weight: 700;
  letter-spacing: 0.05em;
  text-transform: uppercase;
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

div[data-testid="stMetric"] label,
div[data-testid="stMetric"] div {
  color: var(--ink);
}

@media (max-width: 720px) {
  section.main > div {
    padding-left: 0.75rem;
    padding-right: 0.75rem;
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
