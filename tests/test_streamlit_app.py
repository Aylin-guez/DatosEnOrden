from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
import sys

from datosenorden.maintenance.dataset_registry import DatasetCountRow
from datosenorden.maintenance.dataset_registry import DatasetDetails
from datosenorden.maintenance.dataset_registry import DatasetSummary
from datosenorden.maintenance.cross_dataset_explorer import CrossDatasetConnection
from datosenorden.maintenance.cross_dataset_explorer import CrossDatasetOrganizationSummary
from datosenorden.maintenance.entity_explorer import EntitySearchResult
from datosenorden.maintenance.human_readable import DatasetExplanation
from datosenorden.maintenance.human_readable import EntityExplanation
from datosenorden.maintenance.human_readable import GraphExplanation

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import streamlit_app


@dataclass
class _FakeColumn:
    metrics: list[tuple[str, object]]
    captions: list[str]
    button_values: dict[str, bool] | None = None

    def metric(self, label, value):  # noqa: ANN001
        self.metrics.append((label, value))

    def caption(self, text):  # noqa: ANN001
        self.captions.append(text)

    def button(self, label, key=None):  # noqa: ANN001
        _ = label
        return bool((self.button_values or {}).get(key, False))


class _FakeTab:
    def __enter__(self):  # noqa: ANN001
        return self

    def __exit__(self, exc_type, exc, tb):  # noqa: ANN001
        _ = (exc_type, exc, tb)
        return False


class _FakeSidebar:
    def __init__(self):
        self.radio_value = streamlit_app.PAGE_HOME
        self.markdowns: list[tuple[str, bool]] = []
        self.radio_calls: list[tuple[str, tuple[str, ...], int, str | None]] = []

    def title(self, text):  # noqa: ANN001
        self.title_text = text

    def radio(self, label, options, index=0, key=None):  # noqa: ANN001
        self.radio_calls.append((label, tuple(options), index, key))
        return self.radio_value

    def markdown(self, text, unsafe_allow_html=False):  # noqa: ANN001
        self.markdowns.append((text, unsafe_allow_html))


class _FakeStreamlit:
    def __init__(self):
        self.sidebar = _FakeSidebar()
        self.session_state = {}
        self.tables: list[object] = []
        self.codes: list[tuple[str, str | None]] = []
        self.titles: list[str] = []
        self.writes: list[object] = []
        self.subheaders: list[str] = []
        self.infos: list[str] = []
        self.warnings: list[str] = []
        self.errors: list[str] = []
        self.markdowns: list[tuple[str, bool]] = []
        self.columns_created: list[list[_FakeColumn]] = []
        self.page_config = None
        self.captions: list[str] = []
        self.text_input_values: dict[str, str] = {}
        self.selectbox_values: dict[str, object | None] = {}
        self.button_values: dict[str, bool] = {}
        self.tab_labels: list[str] = []
        self.spinners: list[str] = []
        self.expander_labels: list[str] = []

    def set_page_config(self, **kwargs):  # noqa: ANN001
        self.page_config = kwargs

    def title(self, text):  # noqa: ANN001
        self.titles.append(text)

    def write(self, text):  # noqa: ANN001
        self.writes.append(text)

    def subheader(self, text):  # noqa: ANN001
        self.subheaders.append(text)

    def caption(self, text):  # noqa: ANN001
        self.captions.append(text)

    def table(self, data):  # noqa: ANN001
        self.tables.append(data)

    def code(self, text, language=None):  # noqa: ANN001
        self.codes.append((text, language))

    def info(self, text):  # noqa: ANN001
        self.infos.append(text)

    def warning(self, text):  # noqa: ANN001
        self.warnings.append(text)

    def error(self, text):  # noqa: ANN001
        self.errors.append(text)

    def markdown(self, text, unsafe_allow_html=False):  # noqa: ANN001
        self.markdowns.append((text, unsafe_allow_html))

    def columns(self, count):  # noqa: ANN001
        columns = [_FakeColumn(metrics=[], captions=[], button_values=self.button_values) for _ in range(count)]
        self.columns_created.append(columns)
        return columns

    def tabs(self, labels):  # noqa: ANN001
        self.tab_labels = list(labels)
        return [_FakeTab() for _ in labels]

    def selectbox(self, label, options, index=0, key=None, format_func=None, placeholder=None):  # noqa: ANN001
        _ = (label, placeholder, format_func)
        if key in self.selectbox_values:
            return self.selectbox_values[key]
        if index is None:
            return None
        return options[index]

    def text_input(self, label, value="", key=None, placeholder=None):  # noqa: ANN001
        _ = (label, placeholder)
        if key in self.text_input_values:
            return self.text_input_values[key]
        return value

    def slider(self, label, min_value, max_value, value, step, key=None):  # noqa: ANN001
        _ = (label, min_value, max_value, step, key)
        return value

    def button(self, label, key=None):  # noqa: ANN001
        _ = label
        return self.button_values.get(key, False)

    def spinner(self, text):  # noqa: ANN001
        self.spinners.append(text)
        return _FakeTab()

    def expander(self, label):  # noqa: ANN001
        self.expander_labels.append(label)
        return _FakeTab()


def _profile(entity_id: str = "11111111-1111-1111-1111-111111111111"):
    entity = SimpleNamespace(entity_type="PUBLIC_ORGANIZATION", name="SERVICIO DE SALUD ARAUCO", id=entity_id, external_id="buyer-1")
    return SimpleNamespace(
        entity=entity,
        claims=(),
        relationships=(),
        evidences=(),
        related_entities=(),
        direct_neighbors=(),
    )


def _cross_dataset_summary() -> CrossDatasetOrganizationSummary:
    return CrossDatasetOrganizationSummary(
        organization_id="11111111-1111-1111-1111-111111111111",
        organization_name="SERVICIO DE SALUD ARAUCO",
        datasets=("chilecompra", "lobby"),
        contracts=4,
        lobby_meetings=1,
        evidence=5,
        relationships=6,
        lobby_connections=(
            CrossDatasetConnection(
                entity_id="22222222-2222-2222-2222-222222222222",
                entity_type="COMPANY",
                name="MARLENE FLORES PATINO",
                relationship_type="COUNTERPARTY_PARTICIPATED_IN_LOBBY",
            ),
        ),
        procurement_connections=(
            CrossDatasetConnection(
                entity_id="33333333-3333-3333-3333-333333333333",
                entity_type="COMPANY",
                name="SKY AIRLINE S.A.",
                relationship_type="RECEIVES_CONTRACT",
            ),
        ),
        explanation="This organization appears in more than one public dataset.",
    )


def test_build_home_summary_aggregates_dataset_counts() -> None:
    rows = (
        DatasetSummary("chilecompra", "ChileCompra", 10, 20, 30, 40, 50, "active", False),
        DatasetSummary("dipres-prototype", "DIPRES Prototype", 1, 2, 3, 4, 5, "active", False),
    )

    summary = streamlit_app.build_home_summary(rows)

    assert summary.datasets == 2
    assert summary.active_datasets == 2
    assert summary.source_records == 11
    assert summary.entities == 22
    assert summary.claims == 33
    assert summary.evidence == 44
    assert summary.relationships == 55


def test_build_entity_card_html_is_public_facing() -> None:
    html = streamlit_app.build_entity_card_html(
        streamlit_app.SearchCard(
            id="11111111-1111-1111-1111-111111111111",
            name="SERVICIO DE SALUD ARAUCO",
            entity_type="PUBLIC_ORGANIZATION",
            external_id="buyer-1",
            purchase_orders=4,
            claims=8,
            relationships=8,
        )
    )

    assert "SERVICIO DE SALUD ARAUCO" in html
    assert "Organismo" in html
    assert "Contratos: 4" in html
    assert "Relaciones: 8" in html
    assert "Ver perfil" not in html


def test_dataset_options_returns_label_slug_pairs() -> None:
    options = streamlit_app.dataset_options(
        (
            DatasetSummary("chilecompra", "ChileCompra", 1, 2, 3, 4, 5, "active", False),
            DatasetSummary("dipres-prototype", "DIPRES Prototype", 0, 0, 0, 0, 0, "empty", False),
        )
    )

    assert options == [
        ("ChileCompra (active)", "chilecompra"),
        ("DIPRES Prototype (empty)", "dipres-prototype"),
    ]


def test_search_cards_normalizes_results() -> None:
    cards = streamlit_app.search_cards(
        [
            EntitySearchResult(
                id="11111111-1111-1111-1111-111111111111",
                entity_type="PUBLIC_ORGANIZATION",
                name="SERVICIO DE SALUD ARAUCO",
                external_id="buyer-1",
                purchase_orders=4,
                claims=8,
                relationships=8,
            )
        ]
    )

    assert cards == [
        streamlit_app.SearchCard(
            id="11111111-1111-1111-1111-111111111111",
            name="SERVICIO DE SALUD ARAUCO",
            entity_type="PUBLIC_ORGANIZATION",
            external_id="buyer-1",
            purchase_orders=4,
            claims=8,
            relationships=8,
        )
    ]


def test_render_app_uses_sidebar_only_navigation(monkeypatch) -> None:
    fake_st = _FakeStreamlit()
    fake_st.sidebar.radio_value = streamlit_app.PAGE_SEARCH
    calls: list[str] = []

    class _SessionContext:
        def __enter__(self):  # noqa: ANN001
            return object()

        def __exit__(self, exc_type, exc, tb):  # noqa: ANN001
            _ = (exc_type, exc, tb)
            return False

    monkeypatch.setattr(streamlit_app, "SessionLocal", lambda: _SessionContext())
    monkeypatch.setattr(streamlit_app, "render_home_page", lambda st, session: calls.append(streamlit_app.PAGE_HOME))
    monkeypatch.setattr(streamlit_app, "render_dataset_explorer_page", lambda st, session: calls.append(streamlit_app.PAGE_DATASETS))
    monkeypatch.setattr(streamlit_app, "render_entity_search_page", lambda st, session: calls.append(streamlit_app.PAGE_SEARCH))
    monkeypatch.setattr(streamlit_app, "render_entity_profile_page", lambda st, session: calls.append(streamlit_app.PAGE_PROFILE))
    monkeypatch.setattr(streamlit_app, "render_graph_view_page", lambda st, session: calls.append(streamlit_app.PAGE_GRAPH))
    monkeypatch.setattr(streamlit_app, "render_human_explanation_page", lambda st, session: calls.append(streamlit_app.PAGE_EXPLANATION))

    streamlit_app.render_app(fake_st)

    assert calls == [streamlit_app.PAGE_SEARCH]
    assert fake_st.sidebar.radio_calls == [("Secciones", streamlit_app.PAGE_ORDER, 0, "page")]
    assert not any("top-nav" in markdown for markdown, _ in fake_st.markdowns)
    assert fake_st.columns_created == []


def test_render_home_page_shows_cards_and_questions(monkeypatch) -> None:
    fake_st = _FakeStreamlit()
    datasets = (
        DatasetSummary("chilecompra", "ChileCompra", 10, 20, 30, 40, 50, "active", False),
        DatasetSummary("dipres-prototype", "DIPRES Prototype", 1, 2, 3, 4, 5, "empty", False),
    )
    monkeypatch.setattr(streamlit_app, "list_datasets", lambda session: datasets)
    monkeypatch.setattr(streamlit_app, "suggested_entity_cards", lambda session: [])
    monkeypatch.setattr(streamlit_app, "search_entity_cards", lambda session, query: [])

    streamlit_app.render_home_page(fake_st, object())

    assert fake_st.titles == ["DatosEnOrden"]
    assert any("Explora cómo se conectan presupuestos" in markdown for markdown, _ in fake_st.markdowns)
    assert fake_st.subheaders == [
        "Preguntas de ejemplo",
        "Estado actual del prototipo",
        "Busca un organismo, proveedor, contrato o presupuesto",
        "Conjuntos de datos",
        "Conjuntos secundarios",
        "Hoja de ruta",
    ]
    assert any("ChileCompra" in markdown for markdown, _ in fake_st.markdowns)
    assert any("DIPRES Prototype" in markdown for markdown, _ in fake_st.markdowns)
    assert any("roadmap-grid" in markdown for markdown, _ in fake_st.markdowns)
    assert fake_st.infos[0] == "Busca una entidad para comenzar."


def test_render_home_page_clickable_question_shows_supplier_answer(monkeypatch) -> None:
    fake_st = _FakeStreamlit()
    fake_st.button_values[f"home_question_{streamlit_app.QUESTION_SUPPLIERS}"] = True
    datasets = (DatasetSummary("chilecompra", "ChileCompra", 10, 20, 30, 40, 50, "active", False),)
    supplier = SimpleNamespace(name="EMPRESA EJEMPLO SPA", purchase_orders=3)
    monkeypatch.setattr(streamlit_app, "list_datasets", lambda session: datasets)
    monkeypatch.setattr(streamlit_app, "list_suppliers", lambda session, limit=5: (supplier,))
    monkeypatch.setattr(streamlit_app, "suggested_entity_cards", lambda session: [])
    monkeypatch.setattr(streamlit_app, "search_entity_cards", lambda session, query: [])

    streamlit_app.render_home_page(fake_st, object())

    assert fake_st.session_state[streamlit_app.HOME_QUESTION_KEY] == streamlit_app.QUESTION_SUPPLIERS
    assert any("Proveedores con contratos" in markdown for markdown, _ in fake_st.markdowns)
    assert any("EMPRESA EJEMPLO SPA: 3 contrato(s)" in markdown for markdown, _ in fake_st.markdowns)


def test_render_cross_dataset_home_section_shows_only_available_connections(monkeypatch) -> None:
    fake_st = _FakeStreamlit()
    row = _cross_dataset_summary()
    monkeypatch.setattr(streamlit_app, "list_cross_dataset_organizations", lambda session: (row,))

    streamlit_app.render_cross_dataset_home_section(fake_st, object())

    assert "Conexiones entre fuentes" in fake_st.subheaders
    assert any("SERVICIO DE SALUD ARAUCO" in markdown for markdown, _ in fake_st.markdowns)
    assert any("ChileCompra" in markdown for markdown, _ in fake_st.markdowns)
    assert any("Lobby" in markdown for markdown, _ in fake_st.markdowns)
    assert any("Contratos: 4" in markdown for markdown, _ in fake_st.markdowns)
    assert any("Reuniones Lobby: 1" in markdown for markdown, _ in fake_st.markdowns)


def test_render_cross_dataset_profile_block_lists_sources_and_connections(monkeypatch) -> None:
    fake_st = _FakeStreamlit()
    row = _cross_dataset_summary()
    monkeypatch.setattr(streamlit_app, "get_cross_dataset_organization_summary", lambda session, entity_id: row)

    streamlit_app.render_cross_dataset_profile_block(fake_st, object(), _profile())

    assert any("Presente en multiples fuentes" in markdown for markdown, _ in fake_st.markdowns)
    assert any("Conexiones disponibles" in markdown for markdown, _ in fake_st.markdowns)
    assert any("MARLENE FLORES PATINO" in markdown for markdown, _ in fake_st.markdowns)
    assert any("SKY AIRLINE S.A." in markdown for markdown, _ in fake_st.markdowns)


def test_render_entity_search_page_shows_cards(monkeypatch) -> None:
    fake_st = _FakeStreamlit()
    fake_st.text_input_values["entity_search_query"] = "arauco"
    expected = streamlit_app.SearchCard(
        id="11111111-1111-1111-1111-111111111111",
        name="SERVICIO DE SALUD ARAUCO",
        entity_type="PUBLIC_ORGANIZATION",
        external_id="buyer-1",
        purchase_orders=4,
        claims=8,
        relationships=8,
    )
    monkeypatch.setattr(streamlit_app, "search_entity_cards", lambda session, query: [expected])

    streamlit_app.render_entity_search_page(fake_st, object())

    assert fake_st.titles == ["Buscar"]
    assert any("SERVICIO DE SALUD ARAUCO" in markdown for markdown, _ in fake_st.markdowns)
    assert fake_st.errors == []


def test_render_entity_search_page_profile_button_shows_profile(monkeypatch) -> None:
    fake_st = _FakeStreamlit()
    fake_st.text_input_values["entity_search_query"] = "arauco"
    selected = streamlit_app.SearchCard(
        id="11111111-1111-1111-1111-111111111111",
        name="SERVICIO DE SALUD ARAUCO",
        entity_type="PUBLIC_ORGANIZATION",
        external_id="buyer-1",
        purchase_orders=4,
        claims=8,
        relationships=8,
    )
    fake_st.button_values[f"entity_search_profile_{selected.id}"] = True
    monkeypatch.setattr(streamlit_app, "search_entity_cards", lambda session, query: [selected])
    monkeypatch.setattr(streamlit_app, "get_entity_profile", lambda session, entity_id: _profile(entity_id))

    streamlit_app.render_entity_search_page(fake_st, object())

    assert fake_st.session_state[streamlit_app.GLOBAL_SELECTED_ENTITY_KEY] == selected.id
    assert "Perfil seleccionado" in fake_st.subheaders
    assert any("Resumen de la entidad" in markdown for markdown, _ in fake_st.markdowns)


def test_render_entity_profile_page_uses_tabs(monkeypatch) -> None:
    fake_st = _FakeStreamlit()
    fake_st.text_input_values["entity_profile_query"] = "arauco"
    selected = streamlit_app.SearchCard(
        id="11111111-1111-1111-1111-111111111111",
        name="SERVICIO DE SALUD ARAUCO",
        entity_type="PUBLIC_ORGANIZATION",
        external_id="buyer-1",
        purchase_orders=4,
        claims=8,
        relationships=8,
    )
    monkeypatch.setattr(streamlit_app, "search_entity_cards", lambda session, query: [selected])
    fake_st.button_values[f"entity_profile_profile_{selected.id}"] = True
    monkeypatch.setattr(streamlit_app, "get_entity_profile", lambda session, entity_id: _profile(entity_id))
    monkeypatch.setattr(
        streamlit_app,
        "explain_entity",
        lambda session, entity_id: EntityExplanation(
            entity_id=entity_id,
            entity_name="SERVICIO DE SALUD ARAUCO",
            entity_type="PUBLIC_ORGANIZATION",
            public_contracts=4,
            suppliers=3,
            source_names=("ChileCompra",),
        ),
    )
    monkeypatch.setattr(streamlit_app, "suggested_entity_cards", lambda session: [selected])

    streamlit_app.render_entity_profile_page(fake_st, object())

    assert fake_st.tab_labels == ["Resumen", "Relaciones", "Evidencia", "Explicación"]
    assert any("Resumen de la entidad" in markdown for markdown, _ in fake_st.markdowns)
    assert any("¿Qué significa esto?" in markdown for markdown, _ in fake_st.markdowns)


def test_render_graph_view_page_shows_explanation_first(monkeypatch) -> None:
    fake_st = _FakeStreamlit()
    fake_st.text_input_values["graph_view_query"] = "arauco"
    selected = streamlit_app.SearchCard(
        id="11111111-1111-1111-1111-111111111111",
        name="SERVICIO DE SALUD ARAUCO",
        entity_type="PUBLIC_ORGANIZATION",
        external_id="buyer-1",
        purchase_orders=4,
        claims=8,
        relationships=8,
    )
    monkeypatch.setattr(streamlit_app, "search_entity_cards", lambda session, query: [selected])
    fake_st.button_values[f"graph_view_profile_{selected.id}"] = True
    monkeypatch.setattr(
        streamlit_app,
        "build_entity_graph",
        lambda session, entity_id, depth=1: SimpleNamespace(
            entity=SimpleNamespace(entity_type="PUBLIC_ORGANIZATION", name="SERVICIO DE SALUD ARAUCO", id=entity_id),
            children=(
                SimpleNamespace(
                    via_relationship_type="RECEIVES_CONTRACT",
                    via_direction="outgoing",
                    entity=SimpleNamespace(
                        entity_type="COMPANY",
                        name="EMPRESA EJEMPLO SPA",
                        id="22222222-2222-2222-2222-222222222222",
                    ),
                    children=(),
                ),
            ),
        ),
    )
    monkeypatch.setattr(streamlit_app, "get_cross_dataset_organization_summary", lambda session, entity_id: _cross_dataset_summary())

    streamlit_app.render_graph_view_page(fake_st, object())

    assert "Construyendo grafo..." in fake_st.spinners
    assert "Preparando explicación del grafo..." in fake_st.spinners
    assert any("visual-graph" in markdown for markdown, _ in fake_st.markdowns)
    assert any("Entidad inicial" in markdown for markdown, _ in fake_st.markdowns)
    assert any("Relaciones" in markdown for markdown, _ in fake_st.markdowns)
    assert any("Entidad conectada" in markdown for markdown, _ in fake_st.markdowns)
    assert any("Recibe contrato" in markdown for markdown, _ in fake_st.markdowns)
    assert any("ChileCompra" in markdown for markdown, _ in fake_st.markdowns)
    assert any("Lobby" in markdown for markdown, _ in fake_st.markdowns)
    assert fake_st.expander_labels == ["Ver detalles t\u00e9cnicos"]
    assert fake_st.infos[0] == "Este gráfico muestra cómo se conectan las fuentes públicas."
    assert any("Árbol del grafo" in markdown for markdown, _ in fake_st.markdowns)


def test_human_readable_text_uses_conversational_spanish() -> None:
    dataset_text = streamlit_app.render_dataset_explanation_text(
        DatasetExplanation("ChileCompra", "ChileCompra contiene información de compras públicas.", 2, 3, 4)
    )
    dipres_text = streamlit_app.render_dataset_explanation_text(
        DatasetExplanation(
            "DIPRES Prototype",
            "DIPRES Prototype contiene información de presupuesto de muestra. Actualmente incluye ejemplos de ministerios, servicios, presupuestos aprobados, presupuestos ejecutados y año fiscal.",
            2,
            3,
            4,
        )
    )
    entity_text = streamlit_app.render_entity_explanation_text(
        EntityExplanation("1", "SERVICIO DE SALUD ARAUCO", "PUBLIC_ORGANIZATION", 4, 3, ("ChileCompra",))
    )
    graph_text = streamlit_app.render_graph_explanation_text(
        GraphExplanation(("Organismo", "Contrato", "Proveedor"), "La organización emite compras públicas.")
    )

    assert "Fuente" in dataset_text
    assert "Afirmación verificable" in dataset_text
    assert "Relación pública" in dataset_text
    assert "Entidad" in dataset_text
    assert "presupuesto de muestra" in dipres_text
    assert "organismos" in dipres_text
    assert "contratos públicos" in entity_text
    assert "La información proviene de ChileCompra." in entity_text
    assert "Esto significa:" in graph_text
    assert "Este gráfico muestra cómo se conectan las fuentes públicas." in graph_text


def test_build_dataset_rows_preserves_registry_counts() -> None:
    details = DatasetDetails(
        slug="chilecompra",
        name="ChileCompra",
        health="active",
        source_records=10,
        entities=20,
        claims=30,
        evidence=40,
        relationships=50,
        source_names=("ChileCompra API Mercado Publico",),
        dataset_names=("chilecompra-licitaciones", "chilecompra-ordenes-compra"),
        entities_by_type=(DatasetCountRow("PUBLIC_ORGANIZATION", 5),),
        claims_by_type=(DatasetCountRow("ISSUES_PURCHASE_ORDER", 30),),
        relationship_types=(DatasetCountRow("RECEIVES_CONTRACT", 20),),
        ingestion_stats=(DatasetCountRow("source_records", 10),),
        planned=False,
    )

    assert streamlit_app.build_dataset_table_rows(details) == [
        {"label": "PUBLIC_ORGANIZATION", "count": 5},
    ]
    assert streamlit_app.build_claim_rows(details) == [
        {"label": "ISSUES_PURCHASE_ORDER", "count": 30},
    ]
    assert streamlit_app.build_relationship_rows(details) == [
        {"label": "RECEIVES_CONTRACT", "count": 20},
    ]
