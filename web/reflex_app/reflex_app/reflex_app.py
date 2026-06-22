from __future__ import annotations

import reflex as rx

from datosenorden.web.app_services import get_cross_dataset_connections
from datosenorden.web.app_services import get_dataset_summary
from datosenorden.web.app_services import get_demo_status
from datosenorden.web.app_services import get_investigation
from datosenorden.web.app_services import search_entities


GRAPH_EXPLANATION = (
    "Este organismo aparece conectado con contratos, roles publicos y registros de lobby. "
    "Cada conexion proviene de una fuente cargada y evidencia asociada. "
    "Esto no implica causalidad ni irregularidad."
)


def _clean(value: object, fallback: str = "Sin dato") -> str:
    text = "" if value is None else str(value).strip()
    return text or fallback

def _human_label(value: object) -> str:
    labels = {
        "outgoing": "salida",
        "incoming": "entrada",
        "CONTRACT": "contrato",
        "ROLE": "rol público",
        "ISSUES_PURCHASE_ORDER": "emite orden de compra",
        "ORGANIZATION_HELD_LOBBY_MEETING": "registró reunión de lobby",
        "ORGANIZATION_HAS_PUBLIC_ROLE": "tiene rol público registrado",
        "ROLE_BELONGS_TO_ORGANIZATION": "rol pertenece al organismo",
    }
    return labels.get(_clean(value), _clean(value))

def _format_procurement_rows(rows: list[dict]) -> list[dict]:
    return [
        {
            "title": _clean(row.get("contract_name"), "Orden de compra"),
            "dataset": _clean(row.get("dataset"), "ChileCompra"),
            "date": "Sin fecha",
            "explanation": "Registro de compra publica asociado a esta entidad.",
            "evidence": int(row.get("evidence_count", 0)),
            "relationship_type": "Compra publica",
            "facts_text": "\n".join([
                f"Proveedor: {_clean(row.get('supplier'))}",
            ]),
            "technical_text": f"dataset={_clean(row.get('dataset'), 'ChileCompra')}",
            "detail_text": f"dataset={_clean(row.get('dataset'), 'ChileCompra')}",
        }
        for row in rows
    ]


def _format_lobby_rows(rows: list[dict]) -> list[dict]:
    return [
        {
            "title": "Reunion de lobby registrada",
            "dataset": _clean(row.get("dataset"), "Lobby"),
            "date": _clean(row.get("date"), "Sin fecha"),
            "explanation": "Registro de lobby asociado a esta entidad y una contraparte.",
            "evidence": int(row.get("evidence_count", 0)),
            "relationship_type": "Lobby",
            "facts_text": "\n".join([
                f"Organismo: {_clean(row.get('organization'))}",
                f"Contraparte: {_clean(row.get('counterparty'))}",
                f"Materia: {_clean(row.get('subject'))}",
            ]),
            "technical_text": f"dataset={_clean(row.get('dataset'), 'Lobby')}",
            "detail_text": f"dataset={_clean(row.get('dataset'), 'Lobby')}",
        }
        for row in rows
    ]


def _format_transparency_rows(rows: list[dict]) -> list[dict]:
    return [
        {
            "title": "Cargo publico registrado",
            "dataset": _clean(row.get("dataset"), "Transparencia"),
            "date": _clean(row.get("period"), "Sin periodo"),
            "explanation": "Registro administrativo de cargo o periodo publico.",
            "evidence": int(row.get("evidence_count", 0)),
            "relationship_type": "Rol publico",
            "facts_text": "\n".join([
                f"Titular: {_clean(row.get('holder'))}",
                f"Rol: {_clean(row.get('role_title'))}",
                f"Periodo: {_clean(row.get('period'))}",
            ]),
            "technical_text": f"dataset={_clean(row.get('dataset'), 'Transparencia')}",
            "detail_text": f"dataset={_clean(row.get('dataset'), 'Transparencia')}",
        }
        for row in rows
    ]


def _format_relationship_rows(rows: list[dict]) -> list[dict]:
    formatted: list[dict] = []
    for row in rows:
        if "who" in row:
            technical = row.get("technical_details", {})
            formatted.append(
                {
                    "title": _clean(row.get("who"), "Entidad conectada"),
                    "dataset": _clean(row.get("source_dataset"), "Grafo publico local"),
                    "date": "Sin fecha",
                    "explanation": _clean(row.get("relationship_meaning"), "Relacion publica almacenada."),
                    "evidence": 0,
                    "relationship_type": _clean(row.get("entity_type"), "Entidad conectada"),
                    "facts_text": f"Quien: {_clean(row.get('who'))}",
                    "technical_text": "\n".join([
                        f"relationship_id={_clean(technical.get('relationship_id'))}",
                        f"relationship_type={_clean(technical.get('relationship_type'))}",
                        f"direction={_clean(technical.get('direction'))}",
                        f"neighbor_id={_clean(technical.get('neighbor_id'))}",
                    ]),
                    "detail_text": "\n".join([
                        f"relationship_id={_clean(technical.get('relationship_id'))}",
                        f"relationship_type={_clean(technical.get('relationship_type'))}",
                        f"direction={_clean(technical.get('direction'))}",
                        f"neighbor_id={_clean(technical.get('neighbor_id'))}",
                    ]),
                }
            )
            continue
        neighbor = row.get("neighbor", {})
        formatted.append(
            {
                "title": _clean(neighbor.get("name"), "Entidad conectada"),
                "dataset": "Grafo local",
                "date": "Sin fecha",
                "explanation": "Entidad conectada por una relacion publica almacenada.",
                "evidence": 0,
                "relationship_type": _human_label(row.get("relationship_type")),
                "detail_text": "\n".join([
                    f"Tipo de entidad: {_human_label(neighbor.get('entity_type'))}",
                    f"Dirección: {_human_label(row.get('direction'))}",
                ]),
            }
        )
    return formatted


def _format_evidence_rows(rows: list[dict]) -> list[dict]:
    formatted: list[dict] = []
    for group in rows:
        dataset = _clean(group.get("dataset"), "Fuente")
        for link in group.get("links", []):
            formatted.append(
                {
                    "title": _clean(link.get("title"), "Evidencia"),
                    "dataset": dataset,
                    "date": _clean(link.get("published_at"), "Sin fecha"),
                    "explanation": "Enlace de evidencia asociado a registros cargados.",
                    "evidence": 1,
                    "relationship_type": "Evidencia",
                    "facts_text": f"Publicado: {_clean(link.get('published_at'), 'Sin fecha')}",
                    "technical_text": f"url={_clean(link.get('url'))}",
                    "detail_text": f"url={_clean(link.get('url'))}",
                }
            )
    return formatted


def _build_story_cards(
    *,
    transparency: list[dict],
    lobby: list[dict],
    procurement: list[dict],
    relationships: list[dict],
    evidence: list[dict],
) -> list[dict]:
    cards: list[dict] = []
    cards.extend(transparency[:2])
    cards.extend(lobby[:2])
    cards.extend(procurement[:2])
    cards.extend(relationships[:2])
    cards.extend(evidence[:2])
    return cards


class AppState(rx.State):
    query: str = ""
    results: list[dict] = []
    selected_entity_id: str = ""
    selected_entity_name: str = ""
    error_message: str = ""

    dataset_rows: list[dict] = []
    connection_rows: list[dict] = []
    demo_missing: list[str] = []
    total_datasets: int = 0
    active_datasets: int = 0
    total_claims: int = 0
    total_relationships: int = 0

    entity_name: str = ""
    entity_summary: str = ""
    dataset_badges: list[str] = []
    contracts: int = 0
    suppliers: int = 0
    lobby_meetings: int = 0
    evidence_count: int = 0
    relationship_count: int = 0
    datasets_involved: int = 0
    connected_entities: int = 0
    story_cards: list[dict] = []
    connection_summary: str = ""
    procurement_rows: list[dict] = []
    lobby_rows: list[dict] = []
    transparencia_rows: list[dict] = []
    relationship_rows: list[dict] = []
    evidence_rows: list[dict] = []
    technical_details: list[dict] = []
    neutral_explanation: str = ""

    def load_home(self) -> None:
        self.error_message = ""
        try:
            summary = get_dataset_summary()
            totals = summary.get("totals", {})
            self.dataset_rows = summary.get("datasets", [])
            self.connection_rows = [
                {
                    **row,
                    "datasets_text": " · ".join(row.get("datasets", [])),
                }
                for row in get_cross_dataset_connections()
            ]
            demo_status = get_demo_status()
            self.demo_missing = [item.get("label", "") for item in demo_status.get("missing", [])]
            self.total_datasets = int(totals.get("datasets", 0))
            self.active_datasets = int(totals.get("active_datasets", 0))
            self.total_claims = int(totals.get("claims", 0))
            self.total_relationships = int(totals.get("relationships", 0))
        except Exception as exc:  # noqa: BLE001
            self.error_message = f"{type(exc).__name__}: {exc}"

    def set_query(self, value: str) -> None:
        self.query = value

    def run_search(self) -> None:
        self.error_message = ""
        try:
            self.results = [
                {
                    **row,
                    "source_hint": (
                        "Registros con evidencia y relaciones cargadas"
                        if int(row.get("relationships", 0)) or int(row.get("claims", 0))
                        else "Entidad encontrada en la base local"
                    ),
                    "datasets_text": (
                        " / ".join(row.get("datasets_involved", []))
                        if row.get("datasets_involved")
                        else "Fuentes disponibles al abrir la investigacion"
                    ),
                }
                for row in search_entities(self.query, limit=10)
            ]
        except Exception as exc:  # noqa: BLE001
            self.results = []
            self.error_message = f"{type(exc).__name__}: {exc}"

    def select_result(self, entity_id: str):
        self.selected_entity_id = entity_id
        match = next((row for row in self.results if row.get("id") == entity_id), {})
        self.selected_entity_name = str(match.get("name", ""))
        return rx.redirect(f"/investigation?id={entity_id}")

    def open_investigation(self, entity_id: str, entity_name: str):
        self.selected_entity_id = entity_id
        self.selected_entity_name = entity_name
        return rx.redirect(f"/investigation?id={entity_id}")

    def load_investigation(self) -> None:
        self.error_message = ""
        query_id = self.router.url.query_parameters.get("id", "")
        if query_id:
            self.selected_entity_id = str(query_id)
        if not self.selected_entity_id:
            return
        try:
            data = get_investigation(self.selected_entity_id)
        except Exception as exc:  # noqa: BLE001
            self.error_message = f"{type(exc).__name__}: {exc}"
            return
        if not data.get("found", False):
            self.error_message = "Entity not found."
            return

        metrics = data.get("key_metrics", {})
        compact_metrics = data.get("compact_metrics", {})
        self.entity_name = data.get("entity", {}).get("name", "")
        self.selected_entity_name = self.entity_name
        self.entity_summary = data.get("narrative_summary") or data.get("summary", "")
        self.dataset_badges = data.get("dataset_badges", [])
        self.contracts = int(metrics.get("contracts", 0))
        self.suppliers = int(metrics.get("suppliers", 0))
        self.lobby_meetings = int(metrics.get("lobby_meetings", 0))
        self.evidence_count = int(compact_metrics.get("evidence_count", metrics.get("evidence", 0)))
        self.relationship_count = int(compact_metrics.get("relationship_count", metrics.get("relationships", 0)))
        self.datasets_involved = int(compact_metrics.get("datasets_involved", len(self.dataset_badges)))
        self.connected_entities = int(compact_metrics.get("connected_entities", 0))
        self.connection_summary = data.get("connections", {}).get("summary", "")
        self.procurement_rows = _format_procurement_rows(data.get("contracts_compras", []))
        self.lobby_rows = _format_lobby_rows(data.get("lobby", []))
        self.transparencia_rows = _format_transparency_rows(data.get("transparencia", []))
        self.relationship_rows = _format_relationship_rows(
            data.get("connections", {}).get("relationship_cards")
            or data.get("connections", {}).get("direct_neighbors", [])
        )[:5]
        self.evidence_rows = _format_evidence_rows(data.get("evidence", []))
        self.story_cards = _build_story_cards(
            transparency=self.transparencia_rows,
            lobby=self.lobby_rows,
            procurement=self.procurement_rows,
            relationships=self.relationship_rows,
            evidence=self.evidence_rows,
        )
        self.technical_details = [
            *self.procurement_rows,
            *self.lobby_rows,
            *self.transparencia_rows,
            *self.relationship_rows,
            *self.evidence_rows,
        ]
        self.neutral_explanation = data.get("neutral_explanation", "")


def shell(*children: rx.Component, **props) -> rx.Component:
    return rx.box(
        rx.hstack(
            rx.link("Home", href="/"),
            rx.link("Search", href="/search"),
            rx.link("Investigation", href="/investigation"),
            spacing="5",
            class_name="nav",
        ),
        rx.cond(
            AppState.error_message != "",
            rx.box(
                rx.text("Data load issue", class_name="eyebrow"),
                rx.text(AppState.error_message),
                class_name="card error",
            ),
        ),
        rx.vstack(*children, spacing="5", align="stretch", class_name="page"),
        class_name="shell",
        **props,
    )

def metric(label: str, value) -> rx.Component:  # noqa: ANN001
    return rx.box(
        rx.text(value, class_name="metric-value"),
        rx.text(label, class_name="muted"),
        class_name="metric-card",
    )


def dataset_card(row: dict) -> rx.Component:
    return rx.box(
        rx.text(row["name"], class_name="card-title"),
        rx.text(row["health"], class_name="badge"),
        rx.text(f"source records: {row['source_records']}", class_name="muted"),
        rx.text(f"entities: {row['entities']} | claims: {row['claims']}", class_name="muted"),
        rx.text(f"evidence: {row['evidence']} | relationships: {row['relationships']}", class_name="muted"),
        class_name="card",
    )


def connection_card(row: dict) -> rx.Component:
    return rx.box(
        rx.text(row["organization_name"], class_name="card-title"),
        rx.text(row["datasets_text"], class_name="badge"),
        rx.text(f"contracts: {row['contracts']} | lobby meetings: {row['lobby_meetings']}", class_name="muted"),
        rx.text(f"evidence: {row['evidence']} | relationships: {row['relationships']}", class_name="muted"),
        rx.button(
            "Open Investigation",
            on_click=AppState.open_investigation(row["organization_id"], row["organization_name"]),
            class_name="button",
        ),
        class_name="card",
    )


def story_card(row: dict) -> rx.Component:
    return rx.box(
        rx.hstack(
            rx.text(row["dataset"], class_name="badge"),
            rx.text(row["date"], class_name="muted small"),
            justify="between",
            align="center",
        ),
        rx.text(row["title"], class_name="story-title"),
        rx.text(row["explanation"], class_name="muted"),
        rx.text(row["facts_text"], class_name="fact-line"),
        rx.hstack(
            rx.text(f"Evidencia: {row['evidence']}", class_name="mini-pill"),
            rx.text(row["relationship_type"], class_name="mini-pill"),
            spacing="2",
            wrap="wrap",
        ),
        rx.box(
            rx.text("Detalles técnicos", class_name="muted small"),
            rx.text(row["detail_text"], class_name="detail-line"),
            class_name="technical-inline",
        ),
        class_name="story-card",
    )


def context_entity_card(row: dict) -> rx.Component:
    return rx.box(
        rx.text(row["title"], class_name="context-title"),
        rx.text(row["relationship_type"], class_name="mini-pill"),
        rx.text(row["explanation"], class_name="muted small"),
        class_name="context-item",
    )


def technical_detail_card(row: dict) -> rx.Component:
    return rx.box(
        rx.text(row["title"], class_name="context-title"),
        rx.text(row["technical_text"], class_name="mono id-line"),
        class_name="context-item",
    )


@rx.page(route="/", title="DatosEnOrden")
def home() -> rx.Component:
    return shell(
        rx.box(
            rx.text("DatosEnOrden", class_name="title"),
            rx.text(
                "Civic data explorer over local PostgreSQL records. This Reflex prototype reads a frontend-independent service layer.",
                class_name="subtitle",
            ),
            class_name="hero",
        ),
        rx.hstack(
            metric("Datasets", AppState.total_datasets),
            metric("Active", AppState.active_datasets),
            metric("Claims", AppState.total_claims),
            metric("Relationships", AppState.total_relationships),
            spacing="3",
            wrap="wrap",
        ),
        rx.box(
            rx.text("Dataset Summary", class_name="section-title"),
            rx.grid(
                rx.foreach(AppState.dataset_rows, dataset_card),
                columns="3",
                spacing="3",
                class_name="responsive-grid",
            ),
        ),
        rx.box(
            rx.text("Cross-Dataset Connections", class_name="section-title"),
            rx.text(
                "Comienza explorando una entidad presente en varias fuentes.",
                class_name="section-subtitle",
            ),
            rx.grid(
                rx.foreach(AppState.connection_rows, connection_card),
                columns="2",
                spacing="3",
                class_name="responsive-grid",
            ),
        ),
        rx.box(
            rx.text("Demo Status", class_name="section-title"),
            rx.foreach(AppState.demo_missing, lambda item: rx.text(item, class_name="muted")),
            class_name="card",
        ),
        on_mount=AppState.load_home,
    )


def result_card(row: dict) -> rx.Component:
    return rx.box(
        rx.hstack(
            rx.text(row["entity_type"], class_name="badge"),
            rx.text(row["source_hint"], class_name="muted small"),
            justify="between",
            align="center",
        ),
        rx.text(row["name"], class_name="card-title"),
        rx.text(row["explanation"], class_name="muted"),
        rx.text(row["datasets_text"], class_name="muted small"),
        rx.text(f"Afirmaciones: {row['claims']} | Relaciones: {row['relationships']}", class_name="mini-pill"),
        rx.button("Open Investigation", on_click=AppState.select_result(row["id"]), class_name="button"),
        class_name="card",
    )


@rx.page(route="/search", title="Search - DatosEnOrden")
def search() -> rx.Component:
    return shell(
        rx.text("Search", class_name="title"),
        rx.hstack(
            rx.input(
                placeholder="Type an entity name",
                value=AppState.query,
                on_change=AppState.set_query,
                class_name="input",
            ),
            rx.button("Search", on_click=AppState.run_search, class_name="button"),
            spacing="3",
            align="center",
        ),
        rx.grid(
            rx.foreach(AppState.results, result_card),
            columns="2",
            spacing="3",
            class_name="responsive-grid",
        ),
    )


def section(title: str, rows, empty_text: str) -> rx.Component:  # noqa: ANN001
    return rx.box(
        rx.text(title, class_name="section-title"),
        rx.cond(
            rows,
            rx.vstack(
                rx.foreach(rows, story_card),
                spacing="3",
                align="stretch",
            ),
            rx.text(empty_text, class_name="muted"),
        ),
        class_name="card",
    )


@rx.page(route="/investigation", title="Investigation - DatosEnOrden")
def investigation() -> rx.Component:
    return shell(
        rx.cond(
            AppState.selected_entity_id == "",
            rx.box(
                rx.text("Investigation", class_name="title"),
                rx.text("Select an entity from Search or open a cross-dataset connection from Home.", class_name="subtitle"),
                class_name="hero",
            ),
            rx.box(
                rx.vstack(
                    rx.box(
                        rx.text(AppState.entity_name, class_name="title"),
                        rx.text(AppState.entity_summary, class_name="subtitle"),
                        rx.hstack(
                            rx.foreach(AppState.dataset_badges, lambda badge: rx.text(badge, class_name="badge")),
                            spacing="2",
                            wrap="wrap",
                        ),
                        rx.hstack(
                            metric("Contratos", AppState.contracts),
                            metric("Fuentes", AppState.datasets_involved),
                            metric("Evidencia", AppState.evidence_count),
                            metric("Entidades conectadas", AppState.connected_entities),
                            metric("Relaciones", AppState.relationship_count),
                            spacing="3",
                            wrap="wrap",
                            class_name="hero-metrics",
                        ),
                        class_name="hero",
                    ),
                    rx.box(
                        rx.text("Historia de la entidad", class_name="section-title"),
                        rx.text(
                            "Lee esta secuencia como una trazabilidad: entidad, fuentes, eventos, conexiones y evidencia.",
                            class_name="section-subtitle",
                        ),
                        rx.cond(
                            AppState.story_cards,
                            rx.vstack(
                                rx.foreach(AppState.story_cards, story_card),
                                spacing="3",
                                align="stretch",
                                class_name="timeline",
                            ),
                            rx.text("No hay eventos suficientes para construir una historia.", class_name="muted"),
                        ),
                        class_name="card story-flow",
                    ),
                    section("Transparency", AppState.transparencia_rows, "No transparency claims available."),
                    section("Lobby", AppState.lobby_rows, "No lobby meetings available."),
                    section("Procurement", AppState.procurement_rows, "No ChileCompra contracts available."),
                    section("Relationships", AppState.relationship_rows, "No connected entities available."),
                    section("Evidence", AppState.evidence_rows, "No evidence items available."),
                    spacing="5",
                    align="stretch",
                    class_name="story-main",
                ),
                rx.box(
                    rx.text("Contexto", class_name="section-title"),
                    rx.text("Fuentes involucradas", class_name="context-title"),
                    rx.hstack(
                        rx.foreach(AppState.dataset_badges, lambda badge: rx.text(badge, class_name="badge")),
                        spacing="2",
                        wrap="wrap",
                    ),
                    rx.box(
                        rx.hstack(
                            rx.text("Evidencia total:", class_name="muted"),
                            rx.text(AppState.evidence_count, class_name="context-number"),
                            justify="between",
                        ),
                        rx.hstack(
                            rx.text("Entidades conectadas:", class_name="muted"),
                            rx.text(AppState.connected_entities, class_name="context-number"),
                            justify="between",
                        ),
                        rx.hstack(
                            rx.text("Relaciones totales:", class_name="muted"),
                            rx.text(AppState.relationship_count, class_name="context-number"),
                            justify="between",
                        ),
                        class_name="context-block",
                    ),
                    rx.text("Entidades conectadas", class_name="context-title"),
                    rx.cond(
                        AppState.relationship_rows,
                        rx.vstack(
                            rx.foreach(AppState.relationship_rows, context_entity_card),
                            spacing="2",
                            align="stretch",
                        ),
                        rx.text("No hay entidades conectadas disponibles.", class_name="muted"),
                    ),
                    rx.text("Que significa esto", class_name="context-title"),
                    rx.text(GRAPH_EXPLANATION, class_name="muted"),
                    rx.text(AppState.connection_summary, class_name="muted"),
                    rx.text(AppState.neutral_explanation, class_name="muted"),
                    rx.cond(
                        AppState.technical_details,
                        rx.box(
                            rx.text("Detalles tecnicos", class_name="context-title"),
                            rx.text("IDs, URLs y tipos internos se muestran aqui para trazabilidad.", class_name="muted small"),
                            rx.vstack(
                                rx.foreach(AppState.technical_details, technical_detail_card),
                                spacing="2",
                                align="stretch",
                            ),
                        ),
                    ),
                    class_name="card context-panel",
                ),
                class_name="investigation-layout",
            ),
        ),
        on_mount=AppState.load_investigation,
    )


style = {
    "body": {
        "background": "#08111f",
        "color": "#e5eef7",
        "font_family": "Inter, Segoe UI, sans-serif",
    },
    ".shell": {"min_height": "100vh", "padding": "24px"},
    ".page": {"max_width": "1180px", "margin": "0 auto"},
    ".nav": {"max_width": "1180px", "margin": "0 auto 24px", "color": "#5eead4"},
    ".hero": {
        "border": "1px solid #17324a",
        "border_radius": "8px",
        "padding": "28px",
        "background": "#0d1b2d",
    },
    ".title": {"font_size": "32px", "font_weight": "800"},
    ".subtitle": {"color": "#a8b7c7", "max_width": "760px"},
    ".section-title": {"font_size": "20px", "font_weight": "700", "margin_bottom": "12px"},
    ".section-subtitle": {"color": "#a8b7c7", "margin_bottom": "16px"},
    ".card": {
        "border": "1px solid #17324a",
        "border_radius": "8px",
        "padding": "16px",
        "background": "#0d1b2d",
    },
    ".error": {"border_color": "#ef4444"},
    ".metric-card": {
        "min_width": "160px",
        "border": "1px solid #17324a",
        "border_radius": "8px",
        "padding": "14px",
        "background": "#0d1b2d",
    },
    ".metric-value": {"font_size": "26px", "font_weight": "800", "color": "#5eead4"},
    ".hero-metrics": {"margin_top": "20px"},
    ".card-title": {"font_weight": "800", "font_size": "18px"},
    ".muted": {"color": "#a8b7c7"},
    ".small": {"font_size": "13px"},
    ".badge": {
        "display": "inline-flex",
        "border_radius": "999px",
        "padding": "4px 9px",
        "background": "rgba(94, 234, 212, 0.12)",
        "color": "#5eead4",
        "font_size": "13px",
        "font_weight": "700",
    },
    ".button": {"background": "#0f766e", "color": "white", "border_radius": "8px"},
    ".input": {
        "background": "#0d1b2d",
        "border": "1px solid #17324a",
        "color": "#e5eef7",
    },
    ".investigation-layout": {
        "display": "grid",
        "grid_template_columns": "minmax(0, 1fr) minmax(280px, 360px)",
        "gap": "20px",
        "align_items": "start",
    },
    ".story-main": {"min_width": "0"},
    ".context-panel": {"position": "sticky", "top": "18px", "display": "grid", "gap": "14px"},
    ".story-flow": {"padding": "20px"},
    ".timeline": {"border_left": "2px solid rgba(94, 234, 212, 0.32)", "padding_left": "16px"},
    ".story-card": {
        "border": "1px solid #17324a",
        "border_radius": "8px",
        "padding": "14px",
        "background": "#10233a",
        "display": "grid",
        "gap": "10px",
    },
    ".story-title": {"font_size": "18px", "font_weight": "800"},
    ".mini-pill": {
        "border": "1px solid rgba(94, 234, 212, 0.24)",
        "border_radius": "999px",
        "padding": "3px 8px",
        "color": "#d8fff8",
        "font_size": "12px",
    },
    ".detail-line": {
        "border_top": "1px solid rgba(168, 183, 199, 0.14)",
        "padding_top": "7px",
        "color": "#d8e4ef",
    },
    ".technical-inline": {"display": "none"},
    ".fact-line": {
        "white_space": "pre-wrap",
        "color": "#d8e4ef",
        "line_height": "1.55",
    },
    ".context-title": {"font_weight": "800", "color": "#e5eef7"},
    ".context-item": {
        "border": "1px solid #17324a",
        "border_radius": "8px",
        "padding": "10px",
        "display": "grid",
        "gap": "6px",
    },
    ".context-block": {"display": "grid", "gap": "8px"},
    ".context-number": {"font_weight": "800", "color": "#5eead4"},
    ".mono": {"font_family": "Consolas, monospace", "font_size": "13px", "white_space": "pre-wrap"},
    ".id-line": {"color": "#7f93a8", "overflow_wrap": "anywhere"},
    ".responsive-grid": {"width": "100%"},
    "@media (max-width: 900px)": {
        ".investigation-layout": {"grid_template_columns": "1fr"},
        ".context-panel": {"position": "static"},
    },
}


app = rx.App(style=style)
