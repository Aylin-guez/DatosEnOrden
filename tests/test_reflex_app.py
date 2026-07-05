from __future__ import annotations

from dataclasses import dataclass
import inspect
import pickle
from types import MappingProxyType
from types import SimpleNamespace

import reflex_app.reflex_app as reflex_app
from datosenorden.studio import document_reading_pipeline


@dataclass
class _Dumpable:
    name: str

    def model_dump(self) -> dict[str, str]:
        return {"name": self.name}


def test_field_supports_dicts_and_typed_objects() -> None:
    assert reflex_app._field({"name": "dict-value"}, "name") == "dict-value"
    assert reflex_app._field(SimpleNamespace(name="attr-value"), "name") == "attr-value"
    assert reflex_app._field(_Dumpable("dump-value"), "name") == "dump-value"
    assert reflex_app._field(None, "name", "fallback") == "fallback"


def test_to_json_safe_converts_mappingproxy_and_typed_objects() -> None:
    @dataclass
    class _NestedMappingProxy:
        metadata: object

    payload = MappingProxyType(
        {
            "typed": _Dumpable("demo"),
            "nested": _NestedMappingProxy(MappingProxyType({"safe": "yes"})),
            "values": (1, 2),
        }
    )

    safe = reflex_app.to_json_safe(payload)

    assert safe == {"typed": {"name": "demo"}, "nested": {"metadata": {"safe": "yes"}}, "values": [1, 2]}
    pickle.dumps(safe)


def test_load_home_populates_connection_preview(monkeypatch) -> None:
    state = SimpleNamespace(error_message="old")

    monkeypatch.setattr(
        reflex_app,
        "get_dataset_summary",
        lambda: {
            "datasets": [{"name": "ChileCompra", "health": "active"}],
            "totals": {
                "datasets": 1,
                "active_datasets": 1,
                "claims": 2,
                "relationships": 3,
            },
        },
    )
    monkeypatch.setattr(
        reflex_app,
        "get_cross_dataset_connections",
        lambda: [
            {
                "organization_id": str(index),
                "organization_name": f"Entidad {index}",
                "datasets": ["ChileCompra", "Lobby"],
                "contracts": 1,
                "lobby_meetings": 1,
                "evidence": 2,
                "relationships": 3,
            }
            for index in range(7)
        ],
    )
    monkeypatch.setattr(
        reflex_app,
        "get_demo_status",
        lambda: {"missing": [{"label": "Carga lista"}]},
    )
    monkeypatch.setattr(
        reflex_app,
        "get_current_topics",
        lambda limit=3: [
            {
                "id": "topic-demo",
                "title": "Fortalecimiento Hospitalario Arauco",
                "subtitle": "Tema oficial actualmente analizado.",
                "summary": "Lectura documentada demo.",
                "organization": "Documento oficial",
                "status": "Analizado",
                "updated_at": "2026-04-12",
                "href": "/official-document",
            }
        ],
    )
    monkeypatch.setattr(
        reflex_app,
        "get_guided_questions",
        lambda: {
            "questions": [
                {
                    "id": "who_sells_to_this_body",
                    "title": "¿Quién vende a este organismo?",
                    "description": "Demo.",
                    "concepts": ["Organismo"],
                    "suggested_sources": ["ChileCompra"],
                    "example_query": "Demo",
                    "search_query": "Demo",
                    "cta": "Buscar",
                }
            ],
            "categories": [
                {
                    "id": "public_organizations",
                    "title": "Organismos públicos",
                    "description": "Demo.",
                    "examples": ["Entidad demo"],
                    "suggested_sources": ["ChileCompra"],
                    "search_query": "Entidad demo",
                    "cta": "Explorar",
                }
            ],
        },
    )

    reflex_app.AppState.load_home.fn(state)

    assert state.error_message == ""
    assert len(state.connection_rows) == 7
    assert len(state.connection_rows_preview) == 6
    assert state.connection_rows_preview == state.connection_rows[:6]
    assert state.demo_missing == ["Carga lista"]
    assert state.total_datasets == 1
    assert state.active_datasets == 1
    assert state.total_claims == 2
    assert state.total_relationships == 3
    assert state.guided_question_rows[0]["id"] == "who_sells_to_this_body"
    assert state.guided_category_rows[0]["id"] == "public_organizations"
    assert state.current_topic_rows[0]["title"] == "Fortalecimiento Hospitalario Arauco"
    assert state.current_topic_rows[0]["updated_at"] == "12-04-2026"



def test_home_is_public_topic_entry() -> None:
    source = inspect.getsource(reflex_app.home)

    assert "Pulso del Estado" in source
    assert "Eventos recientes" in source
    assert "Abrir lectura principal" in source
    assert 'rx.redirect("/topic")' in source
    assert "Documento oficial visible en menos de un minuto" in source
    assert "Ver todas las lecturas" not in source
    assert "home_pulse_card" in source
    assert "current_topic_card" not in source
    assert "Microscopio documental" not in source
    assert "Que responde cada lectura" not in source
    assert "Fuentes que sostienen la lectura" not in source
    assert "Proyecto DatosEnOrden" not in source


def test_current_topic_card_links_to_documented_reading() -> None:
    source = inspect.getsource(reflex_app.current_topic_card)

    assert "Documento oficial" in source
    assert "Ultima actualizacion" in source
    assert "Ver lectura documentada" in source
    assert "row[\"href\"]" in source

def test_load_investigation_without_selection_uses_guided_empty_state(monkeypatch) -> None:
    calls: list[str] = []

    def fake_load_home(self) -> None:  # noqa: ANN001
        calls.append("load_home")
        self.connection_rows = [
            {
                "organization_id": str(index),
                "organization_name": f"Entidad {index}",
                "datasets_text": "ChileCompra | Lobby",
                "contracts": 1,
                "lobby_meetings": 1,
                "evidence": 2,
                "relationships": 3,
            }
            for index in range(7)
        ]
        self.connection_rows_preview = self.connection_rows[:6]
        self.demo_missing = ["Carga lista"]
        self.total_datasets = 1
        self.active_datasets = 1
        self.total_claims = 2
        self.total_relationships = 3

    state = SimpleNamespace(
        error_message="old",
        selected_entity_id="",
        selected_entity_name="Old entity",
        router=SimpleNamespace(url=SimpleNamespace(query_parameters={})),
        report_path="reports/old.html",
    )

    state.load_home = lambda: fake_load_home(state)

    reflex_app.AppState.load_investigation.fn(state)

    assert calls == []
    assert state.error_message == ""
    assert state.selected_entity_id == ""
    assert state.selected_entity_name == ""
    assert state.report_path == ""
    assert state.investigation_status == reflex_app.INVESTIGATION_STATUS_EMPTY


def test_investigation_without_id_does_not_load_example(monkeypatch) -> None:
    backend_calls: list[str] = []
    monkeypatch.setattr(reflex_app, "resolve_investigation_target", lambda value: backend_calls.append(str(value)) or {"found": False})
    monkeypatch.setattr(reflex_app, "get_investigation", lambda entity_id: backend_calls.append(str(entity_id)) or {})

    state = SimpleNamespace(
        error_message="",
        selected_entity_id="",
        selected_entity_name="",
        entity_name="",
        evidence_count=0,
        relationship_count=0,
        datasets_involved=0,
        connected_entities=0,
        last_valid_investigation_target="",
        last_loaded_investigation_target="",
        investigation_loaded=False,
        router=SimpleNamespace(url=SimpleNamespace(query_parameters={}, raw_path="/investigation")),
        load_home=lambda: None,
    )

    reflex_app.AppState.load_investigation.fn(state)

    assert backend_calls == []
    assert state.selected_entity_id == ""
    assert state.entity_name == ""
    assert state.evidence_count == 0
    assert state.investigation_loaded is False
    assert state.investigation_status == reflex_app.INVESTIGATION_STATUS_EMPTY


def test_investigation_without_id_shows_welcome_not_loading() -> None:
    source = inspect.getsource(reflex_app.investigation)

    assert "investigation_empty_state()" in source
    assert 'AppState.router.url.query.contains("id=")' not in source
    assert "on_load=AppState.load_investigation" in source


def test_investigation_with_url_id_prefers_loading_or_error_over_welcome() -> None:
    source = inspect.getsource(reflex_app.investigation)

    assert source.index("investigation_error_state()") < source.index("investigation_loading_state()")
    assert source.index("investigation_loading_state()") < source.index("investigation_empty_state()")


def test_open_demo_button_uses_stable_investigation_href() -> None:
    source = inspect.getsource(reflex_app.investigation_empty_state)

    assert "Abrir expediente demo" in source
    assert "_investigation_href(DEMO_INVESTIGATION_TARGET)" in source
    assert "run_search" not in source


def test_investigation_error_state_has_retry_and_demo_actions() -> None:
    source = inspect.getsource(reflex_app.investigation_error_state)

    assert "Reintentar" in source
    assert "Volver al demo" in source
    assert "AppState.load_investigation" in source


def test_loading_state_has_manual_fallback_actions() -> None:
    source = inspect.getsource(reflex_app.investigation_loading_state)

    assert "Reintentar" in source
    assert "Volver al demo" in source
    assert "AppState.load_investigation" in source


def test_nav_expediente_points_to_empty_investigation_and_search_is_header_action() -> None:
    shell_source = inspect.getsource(reflex_app.shell)
    sidebar_source = inspect.getsource(reflex_app.app_sidebar)

    assert 'rx.link("Pulso", href="/"' not in shell_source
    assert 'sidebar_nav_link("Pulso", "/"' in sidebar_source
    assert 'rx.link("Lectura", href="/topic"' not in shell_source
    assert 'sidebar_nav_link("Lectura", "/topic"' in sidebar_source
    assert 'sidebar_nav_link("Expediente", "/investigation"' in sidebar_source
    assert 'sidebar_nav_link("Mas lecturas", "/library"' not in sidebar_source
    assert 'sidebar_nav_link("Cronologia", "/tracking"' in sidebar_source
    assert 'sidebar_nav_link("Informes", "/reports"' in sidebar_source
    assert 'sidebar_nav_link("Proyecto", "/project"' in sidebar_source
    assert 'rx.link("Buscar", href="/search"' not in shell_source
    assert "header_search" in shell_source
    assert "toggle_header_search" in shell_source
    assert "toggle_sidebar" in sidebar_source


def test_router_query_value_reads_raw_path() -> None:
    router = SimpleNamespace(url=SimpleNamespace(query_parameters={}, raw_path="/investigation?id=SERVICIO%20DE%20SALUD"))

    assert reflex_app._router_query_value(router, "id") == "SERVICIO DE SALUD"


def test_router_query_value_reads_url_raw_path_when_query_parameters_are_empty() -> None:
    router = SimpleNamespace(
        url=SimpleNamespace(query_parameters={}, raw_path="/investigation?id=SERVICIO+DE+SALUD+ARAUCO+HOSPITAL+DE+ARAUCO"),
        page=SimpleNamespace(raw_path="/investigation?id=SERVICIO+DE+SALUD+ARAUCO+HOSPITAL+DE+ARAUCO"),
    )

    assert reflex_app._router_query_value(router, "id") == "SERVICIO DE SALUD ARAUCO HOSPITAL DE ARAUCO"


def test_router_query_value_does_not_deepcopy_router_metadata() -> None:
    @dataclass
    class UrlLike:
        query_parameters: dict
        raw_path: str
        metadata: object

    @dataclass
    class RouterLike:
        url: UrlLike
        metadata: object

    router = RouterLike(
        url=UrlLike(query_parameters={}, raw_path="/investigation?id=SERVICIO%20DE%20SALUD", metadata=MappingProxyType({"x": "y"})),
        metadata=MappingProxyType({"router": "internal"}),
    )

    assert reflex_app._router_query_value(router, "id") == "SERVICIO DE SALUD"


def test_load_investigation_without_id_preserves_loaded_state_during_refresh(monkeypatch) -> None:
    calls: list[str] = []
    state = SimpleNamespace(
        error_message="",
        selected_entity_id="11111111-1111-1111-1111-111111111111",
        selected_entity_name="Entidad demo",
        entity_name="Entidad demo",
        evidence_count=2,
        relationship_count=3,
        datasets_involved=2,
        connected_entities=1,
        investigation_loaded=True,
        router=SimpleNamespace(url=SimpleNamespace(query_parameters={})),
        load_home=lambda: calls.append("load_home"),
    )

    reflex_app.AppState.load_investigation.fn(state)

    assert calls == []
    assert state.selected_entity_id == "11111111-1111-1111-1111-111111111111"
    assert state.entity_name == "Entidad demo"
    assert state.evidence_count == 2
    assert state.investigation_status == reflex_app.INVESTIGATION_STATUS_LOADED


def test_investigation_href_encodes_name_target() -> None:
    assert (
        reflex_app._investigation_href("SERVICIO DE SALUD ARAUCO HOSPITAL DE ARAUCO")
        == "/investigation?id=SERVICIO+DE+SALUD+ARAUCO+HOSPITAL+DE+ARAUCO"
    )


def test_load_investigation_stores_pickle_safe_payload(monkeypatch) -> None:
    @dataclass
    class UrlLike:
        query_parameters: dict
        raw_path: str
        metadata: object

    @dataclass
    class RouterLike:
        url: UrlLike
        metadata: object

    state = SimpleNamespace(
        error_message="",
        selected_entity_id="",
        selected_entity_name="",
        entity_name="",
        evidence_count=0,
        last_loaded_investigation_target="",
        last_valid_investigation_target="",
        investigation_loaded=False,
        router=RouterLike(
            url=UrlLike(
                query_parameters={"id": "SERVICIO DE SALUD ARAUCO HOSPITAL DE ARAUCO"},
                raw_path="/investigation?id=SERVICIO%20DE%20SALUD%20ARAUCO%20HOSPITAL%20DE%20ARAUCO",
                metadata=MappingProxyType({"internal": "url"}),
            ),
            metadata=MappingProxyType({"internal": "router"}),
        ),
        load_home=lambda: None,
    )

    monkeypatch.setattr(
        reflex_app,
        "resolve_investigation_target",
        lambda value: MappingProxyType(
            {
                "found": True,
                "entity_id": "11111111-1111-1111-1111-111111111111",
                "entity_name": "SERVICIO DE SALUD ARAUCO HOSPITAL DE ARAUCO",
            }
        ),
    )
    monkeypatch.setattr(
        reflex_app,
        "get_investigation",
        lambda entity_id: MappingProxyType(
            {
                "found": True,
                "entity": MappingProxyType({"name": "SERVICIO DE SALUD ARAUCO HOSPITAL DE ARAUCO"}),
                "narrative_summary": "Resumen demo.",
                "summary": "Resumen demo.",
                "dataset_badges": ("ChileCompra", "DIPRES"),
                "key_metrics": MappingProxyType({"contracts": 1, "suppliers": 1, "lobby_meetings": 1}),
                "compact_metrics": MappingProxyType(
                    {"evidence_count": 2, "relationship_count": 3, "datasets_involved": 2, "connected_entities": 1}
                ),
                "connections": MappingProxyType({"summary": "Conexion demo.", "relationship_cards": []}),
                "contracts_compras": [],
                "lobby": [],
                "transparencia": [],
                "registro_empresas": [],
                "timeline": [],
                "evidence": [],
                "neutral_explanation": "Neutral.",
            }
        ),
    )
    monkeypatch.setattr(reflex_app, "get_entity_comparison", lambda entity_id: MappingProxyType({"coverage_summary": "Coverage.", "overlap_areas": [], "dataset_contributions": []}))
    monkeypatch.setattr(reflex_app, "get_source_trace", lambda entity_id: MappingProxyType({"sources": [], "overlap_summary": "", "neutrality_notice": ""}))
    monkeypatch.setattr(reflex_app, "get_investigation_story", lambda entity_id: MappingProxyType({"headline": "Historia", "summary": "Resumen", "key_findings": [], "important_connections": [], "timeline_highlights": [], "questions_for_citizens": []}))
    monkeypatch.setattr(reflex_app, "get_investigation_graph", lambda entity_id: MappingProxyType({"summary": "Grafo.", "nodes": []}))
    monkeypatch.setattr(reflex_app, "get_investigation_timeline", lambda entity_id: MappingProxyType({"years": []}))
    monkeypatch.setattr(reflex_app, "get_source_contributions", lambda entity_id: MappingProxyType({"sources": []}))
    monkeypatch.setattr(reflex_app, "export_investigation_report", lambda entity_id: "reports/demo.html")

    reflex_app.AppState.load_investigation.fn(state)

    assert state.entity_name == "SERVICIO DE SALUD ARAUCO HOSPITAL DE ARAUCO"
    assert state.evidence_count == 2
    assert state.last_loaded_investigation_target == "11111111-1111-1111-1111-111111111111"
    assert state.last_valid_investigation_target == "SERVICIO DE SALUD ARAUCO HOSPITAL DE ARAUCO"
    assert state.investigation_loaded is True
    payload = {
        key: value
        for key, value in state.__dict__.items()
        if key not in {"router", "load_home"} and not callable(value)
    }
    assert not _contains_mappingproxy(payload)
    pickle.dumps(payload)


def test_load_investigation_reloads_from_url_and_handles_backend_empty(monkeypatch) -> None:
    state = _investigation_state(query="SERVICIO DE SALUD ARAUCO HOSPITAL DE ARAUCO")
    calls = {"investigation": 0}

    _patch_investigation_services(monkeypatch, calls=calls)

    reflex_app.AppState.load_investigation.fn(state)

    assert state.entity_name == "SERVICIO DE SALUD ARAUCO HOSPITAL DE ARAUCO"
    assert state.evidence_count == 2
    assert state.investigation_loaded is True
    assert calls["investigation"] == 1

    state.router = SimpleNamespace(url=SimpleNamespace(query_parameters={}))
    reflex_app.AppState.load_investigation.fn(state)

    assert state.entity_name == "SERVICIO DE SALUD ARAUCO HOSPITAL DE ARAUCO"
    assert state.evidence_count == 2
    assert state.investigation_status == reflex_app.INVESTIGATION_STATUS_LOADED
    assert calls["investigation"] == 1

    state.router = SimpleNamespace(url=SimpleNamespace(query_parameters={"id": "SERVICIO DE SALUD ARAUCO HOSPITAL DE ARAUCO"}))
    reflex_app.AppState.load_investigation.fn(state)

    assert state.entity_name == "SERVICIO DE SALUD ARAUCO HOSPITAL DE ARAUCO"
    assert state.evidence_count == 2
    assert calls["investigation"] == 2

    state.last_loaded_investigation_target = "different-target"
    monkeypatch.setattr(
        reflex_app,
        "get_investigation",
        lambda entity_id: {"found": False, "entity": {"name": ""}, "compact_metrics": {}},
    )
    reflex_app.AppState.load_investigation.fn(state)

    assert state.entity_name == "SERVICIO DE SALUD ARAUCO HOSPITAL DE ARAUCO"
    assert state.evidence_count == 2
    assert state.investigation_loaded is True
    assert state.investigation_status == reflex_app.INVESTIGATION_STATUS_LOADED


def test_refresh_without_id_stays_empty_and_does_not_open_example(monkeypatch) -> None:
    backend_calls: list[str] = []
    monkeypatch.setattr(reflex_app, "resolve_investigation_target", lambda value: backend_calls.append(str(value)) or {"found": True})
    state = _investigation_state(query="")
    state.router = SimpleNamespace(url=SimpleNamespace(query_parameters={}, raw_path="/investigation"))

    reflex_app.AppState.load_investigation.fn(state)
    reflex_app.AppState.load_investigation.fn(state)

    assert backend_calls == []
    assert state.entity_name == ""
    assert state.evidence_count == 0
    assert state.investigation_loaded is False


def test_new_state_with_same_router_id_reloads_non_empty_investigation(monkeypatch) -> None:
    calls = {"investigation": 0}
    _patch_investigation_services(monkeypatch, calls=calls)

    first_state = _investigation_state(query="SERVICIO DE SALUD ARAUCO HOSPITAL DE ARAUCO")
    reflex_app.AppState.load_investigation.fn(first_state)

    assert first_state.entity_name == "SERVICIO DE SALUD ARAUCO HOSPITAL DE ARAUCO"
    assert first_state.evidence_count == 2
    assert calls["investigation"] == 1

    second_state = _investigation_state(query="SERVICIO DE SALUD ARAUCO HOSPITAL DE ARAUCO")
    reflex_app.AppState.load_investigation.fn(second_state)

    assert second_state.entity_name == "SERVICIO DE SALUD ARAUCO HOSPITAL DE ARAUCO"
    assert second_state.evidence_count == 2
    assert second_state.relationship_count == 3
    assert second_state.investigation_loaded is True
    assert calls["investigation"] == 2


def test_name_and_uuid_url_targets_load_same_canonical_investigation(monkeypatch) -> None:
    calls = {"investigation": 0}
    _patch_investigation_services(monkeypatch, calls=calls)

    by_name = _investigation_state(query="SERVICIO DE SALUD ARAUCO HOSPITAL DE ARAUCO")
    by_uuid = _investigation_state(query="11111111-1111-1111-1111-111111111111")

    reflex_app.AppState.load_investigation.fn(by_name)
    reflex_app.AppState.load_investigation.fn(by_uuid)

    assert by_name.selected_entity_id == by_uuid.selected_entity_id == "11111111-1111-1111-1111-111111111111"
    assert by_name.entity_name == by_uuid.entity_name == "SERVICIO DE SALUD ARAUCO HOSPITAL DE ARAUCO"
    assert by_name.evidence_count == by_uuid.evidence_count == 2
    assert by_name.relationship_count == by_uuid.relationship_count == 3
    assert by_name.investigation_status == by_uuid.investigation_status == reflex_app.INVESTIGATION_STATUS_LOADED
    assert by_name.investigation_loading is by_uuid.investigation_loading is False
    assert by_name.requested_investigation_target == by_uuid.requested_investigation_target == ""


def test_loading_is_not_final_state_when_backend_responds(monkeypatch) -> None:
    calls = {"investigation": 0}
    _patch_investigation_services(monkeypatch, calls=calls)
    state = _investigation_state(query="SERVICIO DE SALUD ARAUCO HOSPITAL DE ARAUCO")

    reflex_app.AppState.load_investigation.fn(state)

    assert calls["investigation"] == 1
    assert state.investigation_loading is False
    assert state.investigation_status == reflex_app.INVESTIGATION_STATUS_LOADED
    assert state.requested_investigation_target == ""
    assert state.evidence_count > 0


def test_backend_failure_sets_error_not_loading(monkeypatch) -> None:
    state = _investigation_state(query="SERVICIO DE SALUD ARAUCO HOSPITAL DE ARAUCO")
    monkeypatch.setattr(
        reflex_app,
        "resolve_investigation_target",
        lambda value: {
            "found": True,
            "entity_id": "11111111-1111-1111-1111-111111111111",
            "entity_name": "SERVICIO DE SALUD ARAUCO HOSPITAL DE ARAUCO",
        },
    )
    monkeypatch.setattr(reflex_app, "get_investigation", lambda entity_id: (_ for _ in ()).throw(RuntimeError("backend down")))

    reflex_app.AppState.load_investigation.fn(state)

    assert state.investigation_loading is False
    assert state.investigation_status == reflex_app.INVESTIGATION_STATUS_ERROR
    assert "RuntimeError" in state.investigation_status_message


def test_new_state_reconstructs_from_page_raw_path(monkeypatch) -> None:
    calls = {"investigation": 0}
    _patch_investigation_services(monkeypatch, calls=calls)
    state = _investigation_state(query="")
    state.router = SimpleNamespace(
        url=SimpleNamespace(query_parameters={}, raw_path="/investigation?id=SERVICIO+DE+SALUD+ARAUCO+HOSPITAL+DE+ARAUCO"),
    )

    reflex_app.AppState.load_investigation.fn(state)

    assert state.entity_name == "SERVICIO DE SALUD ARAUCO HOSPITAL DE ARAUCO"
    assert state.evidence_count == 2
    assert state.relationship_count == 3
    assert state.investigation_loaded is True
    assert calls["investigation"] == 1


def test_timer_like_new_state_with_url_id_keeps_non_zero_metrics(monkeypatch) -> None:
    calls = {"investigation": 0}
    _patch_investigation_services(monkeypatch, calls=calls)
    state = _investigation_state(query="SERVICIO DE SALUD ARAUCO HOSPITAL DE ARAUCO")
    state.router = SimpleNamespace(
        url=SimpleNamespace(
            query_parameters={"id": "SERVICIO DE SALUD ARAUCO HOSPITAL DE ARAUCO"},
            raw_path="/investigation?id=SERVICIO+DE+SALUD+ARAUCO+HOSPITAL+DE+ARAUCO",
        ),
    )

    reflex_app.AppState.load_investigation.fn(state)

    assert state.selected_entity_id == "11111111-1111-1111-1111-111111111111"
    assert state.evidence_count > 0
    assert state.relationship_count > 0
    assert state.datasets_involved > 0
    assert state.investigation_status == reflex_app.INVESTIGATION_STATUS_LOADED


def test_backend_empty_after_good_state_does_not_zero_metrics(monkeypatch) -> None:
    calls = {"investigation": 0}
    _patch_investigation_services(monkeypatch, calls=calls)
    state = _investigation_state(query="SERVICIO DE SALUD ARAUCO HOSPITAL DE ARAUCO")

    reflex_app.AppState.load_investigation.fn(state)
    assert state.evidence_count == 2
    assert state.relationship_count == 3

    state.last_loaded_investigation_target = "force-refresh"
    monkeypatch.setattr(reflex_app, "get_investigation", lambda entity_id: {"found": True, "entity": {"name": ""}, "key_metrics": {}, "compact_metrics": {}})

    reflex_app.AppState.load_investigation.fn(state)

    assert state.entity_name == "SERVICIO DE SALUD ARAUCO HOSPITAL DE ARAUCO"
    assert state.evidence_count == 2
    assert state.relationship_count == 3
    assert state.datasets_involved == 2
    assert state.investigation_loaded is True
    assert state.investigation_status == reflex_app.INVESTIGATION_STATUS_LOADED
    assert "conserva el expediente" in state.investigation_status_message


def _investigation_state(query: str):
    return SimpleNamespace(
        error_message="",
        selected_entity_id="",
        selected_entity_name="",
        entity_name="",
        entity_summary="",
        dataset_badges=[],
        contracts=0,
        suppliers=0,
        lobby_meetings=0,
        evidence_count=0,
        relationship_count=0,
        datasets_involved=0,
        connected_entities=0,
        last_loaded_investigation_target="",
        last_valid_investigation_target="",
        requested_investigation_target="",
        investigation_loaded=False,
        investigation_loading=False,
        router=SimpleNamespace(url=SimpleNamespace(query_parameters={"id": query})),
        load_home=lambda: None,
    )


def _patch_investigation_services(monkeypatch, *, calls: dict[str, int]) -> None:  # noqa: ANN001
    monkeypatch.setattr(
        reflex_app,
        "resolve_investigation_target",
        lambda value: {
            "found": True,
            "entity_id": "11111111-1111-1111-1111-111111111111",
            "entity_name": "SERVICIO DE SALUD ARAUCO HOSPITAL DE ARAUCO",
        },
    )

    def get_investigation(entity_id: str) -> dict:
        calls["investigation"] += 1
        return {
            "found": True,
            "entity": {"name": "SERVICIO DE SALUD ARAUCO HOSPITAL DE ARAUCO"},
            "narrative_summary": "Resumen demo.",
            "summary": "Resumen demo.",
            "dataset_badges": ["ChileCompra", "DIPRES"],
            "key_metrics": {"contracts": 1, "suppliers": 1, "lobby_meetings": 1, "evidence": 2, "relationships": 3},
            "compact_metrics": {"datasets_involved": 2, "evidence_count": 2, "relationship_count": 3, "connected_entities": 1},
            "connections": {"summary": "Conexion demo.", "relationship_cards": []},
            "contracts_compras": [],
            "lobby": [],
            "transparencia": [],
            "registro_empresas": [],
            "timeline": [],
            "evidence": [],
            "neutral_explanation": "Neutral.",
        }

    monkeypatch.setattr(reflex_app, "get_investigation", get_investigation)
    monkeypatch.setattr(reflex_app, "get_entity_comparison", lambda entity_id: {"coverage_summary": "Coverage.", "overlap_areas": [], "dataset_contributions": []})
    monkeypatch.setattr(reflex_app, "get_source_trace", lambda entity_id: {"sources": [], "overlap_summary": "", "neutrality_notice": ""})
    monkeypatch.setattr(reflex_app, "get_investigation_story", lambda entity_id: {"headline": "Historia", "summary": "Resumen", "key_findings": [], "important_connections": [], "timeline_highlights": [], "questions_for_citizens": []})
    monkeypatch.setattr(reflex_app, "get_investigation_graph", lambda entity_id: {"summary": "Grafo.", "nodes": []})
    monkeypatch.setattr(reflex_app, "get_investigation_timeline", lambda entity_id: {"years": []})
    monkeypatch.setattr(reflex_app, "get_source_contributions", lambda entity_id: {"sources": []})
    monkeypatch.setattr(reflex_app, "export_investigation_report", lambda entity_id: "reports/demo.html")


def _contains_mappingproxy(value) -> bool:  # noqa: ANN001
    if isinstance(value, MappingProxyType):
        return True
    if isinstance(value, dict):
        return any(_contains_mappingproxy(item) for item in value.values())
    if isinstance(value, list | tuple):
        return any(_contains_mappingproxy(item) for item in value)
    return False


def test_empty_state_helpers_render_without_error() -> None:
    assert reflex_app.search_empty_state() is not None
    assert reflex_app.investigation_empty_state() is not None


def test_load_tracking_populates_demo(monkeypatch) -> None:
    state = SimpleNamespace(error_message="")
    monkeypatch.setattr(
        reflex_app,
        "get_tracking_items",
        lambda: [
            {
                "id": "tracking-demo",
                "title": "Seguimiento demo",
                "summary": "Resumen",
                "item_type": "proposal",
                "current_status": "published",
                "related_expediente_target": "Entidad demo",
            }
        ],
    )
    monkeypatch.setattr(
        reflex_app,
        "get_tracking_demo",
        lambda: {
            "item": {
                "id": "tracking-demo",
                "title": "Seguimiento demo",
                "summary": "Resumen",
                "current_status": "published",
                "related_expediente_target": "Entidad demo",
                "related_sources": ["DIPRES", "ChileCompra"],
            },
            "events": [{"title": "Evento", "date": "2026-01-01", "status": "published", "source": "DIPRES", "description": "Demo"}],
            "documents": [{"title": "Doc"}],
            "evidence": [{"label": "Ev"}],
            "follow_targets": [{"label": "Follow"}],
        },
    )

    reflex_app.AppState.load_tracking.fn(state)

    assert state.tracking_title == "Seguimiento demo"
    assert state.tracking_current_status == "published"
    assert state.tracking_events[0]["title"] == "Evento"
    assert state.tracking_related_sources == ["DIPRES", "ChileCompra"]


def test_tracking_route_is_registered() -> None:
    source = inspect.getsource(reflex_app.tracking)

    assert 'route="/tracking"' in source
    assert "Cronologia" in source


def test_load_reports_populates_demo(monkeypatch) -> None:
    state = SimpleNamespace(error_message="")
    monkeypatch.setattr(
        reflex_app,
        "get_citizen_reports",
        lambda: [
            {
                "id": "report-demo",
                "title": "Reporte demo",
                "subtitle": "Subtitulo",
                "subject": "Entidad demo",
                "summary": "Resumen",
                "current_status": "demo_read_only",
                "related_expediente_target": "Entidad demo",
                "sources": ["ChileCompra"],
                "sections": [],
                "evidence_refs": [],
                "classification": "LOCAL_TEST_DATA",
                "official_status": "NOT_OFFICIAL_DATA",
            }
        ],
    )
    monkeypatch.setattr(
        reflex_app,
        "get_citizen_report_demo",
        lambda: {
            "id": "report-demo",
            "title": "Reporte demo",
            "subtitle": "Subtitulo",
            "subject": "Entidad demo",
            "summary": "Resumen",
            "current_status": "demo_read_only",
            "related_expediente_target": "Entidad demo",
            "sources": ["ChileCompra", "DIPRES"],
            "sections": [{"title": "Seccion", "summary": "Detalle", "evidence_refs": ["ev1"]}],
            "evidence_refs": ["ev1"],
            "classification": "LOCAL_TEST_DATA",
            "official_status": "NOT_OFFICIAL_DATA",
        },
    )
    monkeypatch.setattr(reflex_app, "export_citizen_report_demo", lambda: "reports/citizen_report_arauco.html")

    reflex_app.AppState.load_reports.fn(state)

    assert state.citizen_report_title == "Reporte demo"
    assert state.citizen_report_subject == "Entidad demo"
    assert state.citizen_report_sections[0]["evidence_text"] == "ev1"
    assert state.citizen_report_sources == ["ChileCompra", "DIPRES"]
    assert state.citizen_report_path == "reports/citizen_report_arauco.html"


def test_reports_route_is_registered() -> None:
    source = inspect.getsource(reflex_app.reports)

    assert 'route="/reports"' in source
    assert "Informes ciudadanos" in source


def test_library_and_project_routes_are_registered() -> None:
    library_source = inspect.getsource(reflex_app.library)
    project_source = inspect.getsource(reflex_app.project)

    assert 'route="/library"' in library_source
    assert "Mas lecturas" in library_source
    assert "Preguntas importantes" in library_source
    assert 'route="/project"' in project_source
    assert "Estado del proyecto" in project_source
    assert "Que significa MVP" in project_source
    assert "Revisar Mas lecturas" not in project_source


def test_load_dashboard_populates_summary_metrics(monkeypatch) -> None:
    state = SimpleNamespace(error_message="old")

    monkeypatch.setattr(
        reflex_app,
        "get_citizen_dashboard",
        lambda: {
            "title": "¿Dónde fue mi plata?",
            "summary": "Resumen demo.",
            "metrics": {
                "budget_total": 123,
                "budget_currency": "CLP",
                "contracts": 4,
                "suppliers": 5,
                "meetings": 6,
                "authorities": 7,
            },
            "budget_rows": [
                {
                    "organization_name": "Entidad demo",
                    "budget_entity_name": "Entidad demo",
                    "fiscal_year": 2026,
                    "approved_budget": 10,
                    "executed_budget": 8,
                    "purchase_orders": 2,
                    "suppliers": 1,
                    "currency": "CLP",
                }
            ],
            "featured_entities": [
                {
                    "organization_id": "11111111-1111-1111-1111-111111111111",
                    "organization_name": "Entidad demo",
                    "datasets": ["ChileCompra"],
                    "contracts": 1,
                    "lobby_meetings": 1,
                    "evidence": 2,
                    "relationships": 3,
                }
            ],
            "discovery_cases": [
                {
                    "id": "public_spending",
                    "title": "Demo",
                    "description": "Demo",
                    "concepts": ["Presupuesto"],
                    "suggested_sources": ["DIPRES"],
                    "search_query": "Entidad demo",
                    "example_query": "Entidad demo",
                    "cta": "Explorar",
                }
            ],
        },
    )

    reflex_app.AppState.load_dashboard.fn(state)

    assert state.dashboard_title == "¿Dónde fue mi plata?"
    assert state.dashboard_budget_total == 123
    assert state.dashboard_contracts == 4
    assert state.dashboard_featured_entities[0]["organization_name"] == "Entidad demo"


def test_official_document_route_stays_available_but_not_primary_nav() -> None:
    source = inspect.getsource(reflex_app.app_sidebar)

    assert 'sidebar_nav_link("Documento Fuente", "/official-document"' not in source
    assert 'sidebar_nav_link("Pulso", "/"' in source
    assert 'sidebar_nav_link("Lectura", "/topic"' in source
    assert 'sidebar_nav_link("Buscar", "/search"' in source
    assert 'sidebar_nav_link("Fuentes", "/ecosystem"' in source
    assert 'sidebar_nav_link("Proyecto", "/project"' in source

    page_source = inspect.getsource(reflex_app.official_document)
    assert '@rx.page(route="/official-document"' in page_source
    assert "official_document_viewer" in page_source
    assert "reading_guide_panel" in page_source
    assert "document-main-column" in page_source
    assert "document-side-column" in page_source
    assert "Evidencia dentro del documento" in page_source


def test_topic_route_uses_requested_sections_and_navigation() -> None:
    shell_source = inspect.getsource(reflex_app.shell)
    sidebar_source = inspect.getsource(reflex_app.app_sidebar)
    page_source = inspect.getsource(reflex_app.topic)
    nav_source = inspect.getsource(reflex_app.topic_nav)
    source_panel = inspect.getsource(reflex_app.topic_source_panel)
    reading_source = inspect.getsource(reflex_app.topic_reading_flow)
    evidence_source = inspect.getsource(reflex_app.topic_evidence_card)
    fragment_source = inspect.getsource(reflex_app.document_fragment_card)

    assert 'rx.link("Lectura", href="/topic"' not in shell_source
    assert 'sidebar_nav_link("Lectura", "/topic"' in sidebar_source
    assert "sidebar-ready-nav" not in shell_source
    assert '@rx.page(route="/topic"' in page_source
    assert "topic_mode_selector" in page_source
    assert "topic_mode_body" in page_source
    mode_source = inspect.getsource(reflex_app.topic_mode_body)
    selector_source = inspect.getsource(reflex_app.topic_mode_selector)
    reading_mode_source = inspect.getsource(reflex_app.topic_reading_mode)
    evidence_mode_source = inspect.getsource(reflex_app.topic_evidence_mode)
    assert "topic-document-first-layout" in reading_mode_source
    assert "topic_source_panel" in reading_mode_source
    assert "topic_source_panel" in evidence_mode_source
    assert "topic_reading_flow" in reading_mode_source
    assert "Sistema Vivo" in selector_source
    assert "Documento" not in selector_source
    assert "Evidencia" in selector_source
    assert "Documento Fuente" in source_panel
    assert "Fragmento seleccionado" not in source_panel
    text_viewer_source = inspect.getsource(reflex_app.topic_text_document_viewer)
    assert "topic-source-guidance" in source_panel
    assert "topic_pdf_document_viewer" in source_panel
    assert "topic_text_document_viewer" in source_panel
    assert "knowledge_document_paragraphs" in text_viewer_source
    assert "document_paragraph" in text_viewer_source
    assert "document_fragment_card" not in source_panel
    assert "Recurso oficial" in source_panel
    assert "Vista avanzada" not in source_panel
    assert "Resumen" in reading_source
    assert "Que propone" in reading_source
    assert "Que cambia" in reading_source
    assert "Que NO cambia" in reading_source
    assert "Cronologia" in reading_source
    assert "Evidencia" in reading_source
    assert "Expediente" in reading_source
    assert "rx.tabs" not in reading_source
    assert "select_document_anchor" in evidence_source
    assert "call_script" in evidence_source
    assert "topic_status_card" in reading_source
    assert "topic_answer_card" in reading_source
    assert "topic_evidence_card" in reading_source
    assert "id=row" in fragment_source
    assert "Navegacion relacionada" not in fragment_source
    rail_source = inspect.getsource(reflex_app.topic_context_rail)
    assert "topic_context_rail" in inspect.getsource(reflex_app.topic_reading_mode)
    assert "Documento" in rail_source
    assert "Resumen" in rail_source
    assert "Que propone" in rail_source
    assert "Que cambia" in rail_source
    assert "Que NO cambia" in rail_source
    assert "Cronologia" in rail_source
    assert "Evidencia" in rail_source
    assert "Expediente" in rail_source


def test_load_topic_reuses_existing_knowledge_and_investigation(monkeypatch) -> None:
    state = SimpleNamespace(
        error_message="",
        knowledge_document={
            "title": "Mensaje o mocion: Ley de Presupuestos del sector público para el año 2013.",
            "source": "Senado de la Republica de Chile",
            "document_type": "legislative_mensaje_mocion",
            "published_at": "2026-07-02",
            "official_status": "REAL_OFFICIAL_SOURCE",
            "official_url": "https://senado.cl/doc",
        },
        knowledge_title="Lectura documentada",
        knowledge_summary="Resumen desde documento.",
        knowledge_key_points=[{"title": "Punto", "detail": "Detalle", "page": 1, "fragment_id": "frag-1", "reference_label": "Pagina 1"}],
        knowledge_claims=[{"claim": "Afirmacion", "review_note": "Revisar", "page": 1, "fragment_id": "frag-1", "reference_label": "Pagina 1"}],
        knowledge_notice="No afirma irregularidad.",
        knowledge_evidence=[{"source": "Senado", "label": "Fragmento 1", "excerpt": "Texto", "url": "https://senado.cl/doc#frag-1", "fragment_id": "frag-1", "page": 1}],
        knowledge_fragments=[{"text": "uno dos tres"}],
        knowledge_coverage_text="Fragmentos utilizados: 1 de 1",
    )
    state.load_knowledge = lambda: None
    monkeypatch.setattr(
        reflex_app,
        "get_investigation",
        lambda target: {
            "entity": {"name": "Boletin 8575-05"},
            "narrative_summary": "Expediente legislativo existente.",
            "official_status": "dato oficial cargado",
            "official_source": "Datos Abiertos Legislativos",
            "compact_metrics": {"evidence_count": 224, "relationship_count": 0},
            "timeline": [
                {
                    "event_date": "2012-11-20",
                    "dataset": "DATOS ABIERTOS LEGISLATIVOS",
                    "dataset_name": "congreso-votaciones-boletin",
                    "title": "Votacion asociada al boletin.",
                    "explanation": "Fuente publica.",
                },
                {
                    "event_date": "2012-11-20",
                    "dataset": "DATOS ABIERTOS LEGISLATIVOS",
                    "dataset_name": "congreso-votaciones-boletin",
                    "title": "Votacion asociada al boletin.",
                    "explanation": "Fuente publica.",
                }
            ],
            "legislative": {
                "votes_found": 224,
                "source": "Datos Abiertos Legislativos",
                "source_records": [{"source": "Datos Abiertos Legislativos Congreso Nacional", "retrieved_at": "2026-07-02T09:13:11"}],
            },
        },
    )

    reflex_app.AppState.load_topic.fn(state)

    assert state.topic_title == reflex_app.TOPIC_BUDGET_2013_TITLE
    assert state.topic_document_count == 1
    assert state.topic_vote_count == 224
    assert state.topic_proposes_rows == state.knowledge_key_points[:3]
    assert state.topic_changes_rows[0]["claim"] == "Afirmacion"
    assert state.topic_evidence_rows[0]["href"] == "/official-document?fragment_id=frag-1&page=1"
    assert state.topic_timeline_rows[0]["title"] == "Votacion asociada al boletin. (2 registros agrupados)"
    assert state.topic_timeline_rows[0]["date"] == "20-11-2012"
    assert state.topic_updated_at == "02-07-2026"
    assert state.topic_status_rows[0]["label"] == "Documento fuente disponible"
    assert state.topic_status_rows[2]["ready"] is True
    assert state.topic_hero_answer_rows[0]["title"] == "Qué es"


def test_load_topic_does_not_crash_when_external_target_is_missing(monkeypatch) -> None:
    calls: list[str] = []
    state = SimpleNamespace(
        error_message="",
        knowledge_document={
            "title": "Mensaje o mocion: Ley de Presupuestos del sector publico para el ano 2013.",
            "source": "Senado de la Republica de Chile",
            "document_type": "legislative_mensaje_mocion",
            "published_at": "2026-07-02",
            "official_status": "REAL_OFFICIAL_SOURCE",
            "official_url": "https://senado.cl/doc",
        },
        knowledge_title="Lectura documentada",
        knowledge_summary="Resumen desde documento.",
        knowledge_key_points=[],
        knowledge_claims=[],
        knowledge_notice="No afirma irregularidad.",
        knowledge_evidence=[],
        knowledge_fragments=[],
        knowledge_coverage_text="Fragmentos utilizados: 0 de 0",
    )
    state.load_knowledge = lambda: None
    monkeypatch.setattr(
        reflex_app,
        "get_investigation",
        lambda target: calls.append(str(target)) or {"found": False, "warning": "No se encontro una entidad local."},
    )

    reflex_app.AppState.load_topic.fn(state)

    assert calls == [reflex_app.TOPIC_BUDGET_2013_TARGET]
    assert state.topic_title == reflex_app.TOPIC_BUDGET_2013_TITLE
    assert state.topic_status_rows[1]["ready"] is False
    assert state.topic_vote_count == 0

def test_official_document_components_link_references_to_anchors() -> None:
    viewer_source = inspect.getsource(reflex_app.official_document_viewer)
    reference_source = inspect.getsource(reflex_app.reference_button)
    fragment_source = inspect.getsource(reflex_app.document_fragment_card)
    guide_source = inspect.getsource(reflex_app.reading_guide_panel)

    assert "document_id" in viewer_source
    assert "fragment_id" in viewer_source
    assert "highlight" in viewer_source
    assert "reading_context_bar" in viewer_source
    assert "AppState.select_document_anchor" in reference_source
    assert "Navegacion relacionada" not in fragment_source
    assert "document-fragment-active" in fragment_source
    assert "Punto documentado" in guide_source
    assert "Pregunta derivada del texto" in guide_source
    assert "Afirmacion trazable" in guide_source
    assert "Evidencia utilizada" in guide_source


def test_official_document_v2_uses_human_questions_and_reading_metrics() -> None:
    pipeline_source = inspect.getsource(document_reading_pipeline)
    context_source = inspect.getsource(reflex_app.reading_context_bar)

    assert 'enriched["display_question"] = str(row.get("question", ""))' in pipeline_source
    assert "document_coverage" in pipeline_source
    assert "Fragmentos utilizados:" in pipeline_source
    assert "Cobertura documental" in context_source
    assert "knowledge_coverage_text" in context_source
    assert "preguntas respondidas" in context_source
    assert "afirmaciones verificables" in context_source
    assert "referencias documentales" in context_source


def test_select_document_anchor_updates_reading_context() -> None:
    state = SimpleNamespace(
        knowledge_selected_page=18,
        knowledge_selected_fragment_id="frag-a",
        knowledge_selected_reference_label="",
        knowledge_selected_excerpt="",
        knowledge_key_points=[{"fragment_id": "frag-b", "title": "Punto"}],
        knowledge_questions=[{"fragment_id": "frag-b", "display_question": "Pregunta"}],
        knowledge_claims=[{"fragment_id": "frag-b", "claim": "Claim"}],
        knowledge_evidence=[
            {"page": 18, "fragment_id": "frag-a", "reference_label": "Pagina 18", "excerpt": "A"},
            {"page": 19, "fragment_id": "frag-b", "reference_label": "Pagina 19", "excerpt": "B"},
        ],
        knowledge_fragment_contexts=[
            {
                "page": 19,
                "fragment_id": "frag-b",
                "reference_label": "Pagina 19",
                "excerpt": "B",
                "summary": [{"fragment_id": "frag-b", "title": "Punto"}],
                "questions": [{"fragment_id": "frag-b", "display_question": "Pregunta"}],
                "claims": [{"fragment_id": "frag-b", "claim": "Claim"}],
                "evidence": [{"page": 19, "fragment_id": "frag-b", "reference_label": "Pagina 19", "excerpt": "B"}],
                "connections": [{"label": "Expediente", "href": "/investigation?id=demo", "target_id": "demo"}],
            }
        ],
        knowledge_expediente_target="SERVICIO DE SALUD ARAUCO HOSPITAL DE ARAUCO",
    )
    state._set_document_reading_context = lambda fragment_id: reflex_app.AppState._set_document_reading_context(state, fragment_id)

    reflex_app.AppState.select_document_anchor.fn(state, 19, "frag-b")

    assert state.knowledge_selected_page == 19
    assert state.knowledge_selected_fragment_id == "frag-b"
    assert state.knowledge_selected_reference_label == "Pagina 19"
    assert state.knowledge_selected_excerpt == "B"
    assert state.knowledge_selected_summary[0]["title"] == "Punto"
    assert state.knowledge_selected_questions[0]["display_question"] == "Pregunta"
    assert state.knowledge_selected_claims[0]["claim"] == "Claim"
    assert state.knowledge_selected_evidence[0]["excerpt"] == "B"
    assert state.knowledge_selected_connections[0]["label"] == "Expediente"





def test_topic_prefers_published_document_view_as_continuous_document() -> None:
    paragraphs = reflex_app._load_document_paragraphs([])
    panel_source = inspect.getsource(reflex_app.topic_source_panel)
    text_viewer_source = inspect.getsource(reflex_app.topic_text_document_viewer)

    fragments, source_path, is_fallback = reflex_app._load_document_fragments_with_source([])
    assert reflex_app.PUBLISHED_DOCUMENT_VIEW_PATH.as_posix().endswith("data/official_documents/published/senado-docto-9000-mensaje_mocion/document_view.json")
    assert reflex_app.PUBLISHED_DOCUMENT_PDF_PATH.as_posix().endswith("data/official_documents/published/senado-docto-9000-mensaje_mocion/document.pdf")
    assert reflex_app.PUBLISHED_DOCUMENT_PDF_ASSET_PATH.as_posix().endswith("assets/official_documents/senado-docto-9000-mensaje_mocion/document.pdf")
    assert reflex_app._document_pdf_href(reflex_app.PUBLISHED_DOCUMENT_PDF_PUBLIC_HREF, 19).endswith("document.pdf#page=19")
    assert source_path == str(reflex_app.PUBLISHED_DOCUMENT_VIEW_PATH)
    assert is_fallback is False
    assert len(fragments) > 20
    assert len(paragraphs) > 20
    assert paragraphs[0]["text"]
    assert "topic_text_document_viewer" in panel_source
    assert "topic_pdf_document_viewer" in panel_source
    assert "knowledge_document_paragraphs" in text_viewer_source
    assert "document_paragraph" in text_viewer_source
    assert "Recurso oficial" in panel_source
    assert "Abrir recurso oficial del Senado" in panel_source
    assert "document_fragment_card" not in panel_source


def test_discover_is_search_alias_and_search_is_guided_entry() -> None:
    discover_source = inspect.getsource(reflex_app.discover)
    search_source = inspect.getsource(reflex_app.search)
    guide_source = inspect.getsource(reflex_app.guided_discovery_panel)

    assert "return search()" in discover_source
    assert "Preguntas guia" in guide_source
    assert "guided_discovery_panel" in search_source
    assert "Usar entrada guiada" not in search_source


def test_reports_has_stable_empty_state_until_report_is_loaded() -> None:
    reports_source = inspect.getsource(reflex_app.reports)

    assert "Sin informe seleccionado" in reports_source
    assert 'AppState.citizen_report_title != ""' in reports_source
    assert "reports-empty-section" in reports_source


def test_header_search_replaces_theme_toggle_and_closes_when_empty() -> None:
    shell_source = inspect.getsource(reflex_app.shell)
    submit_source = inspect.getsource(reflex_app.AppState.submit_header_search.fn)

    assert "theme-toggle" not in shell_source
    assert "toggle_theme" not in shell_source
    assert "header-search-popover-open" in shell_source
    assert "header_search_open = False" in submit_source
    assert "return None" in submit_source

def test_sidebar_has_single_hamburger_control() -> None:
    shell_source = inspect.getsource(reflex_app.shell)
    sidebar_source = inspect.getsource(reflex_app.app_sidebar)

    assert "header-menu-icon" not in shell_source
    assert "sidebar-menu-button" in sidebar_source
    assert sidebar_source.index("hamburger_icon()") < sidebar_source.index("sidebar_nav_link(\"Pulso\"")

def test_ecosystem_source_card_shows_population_note() -> None:
    source = inspect.getsource(reflex_app.ecosystem_source_card)

    assert "population_label" in source
    assert "source-population-note" in source

def test_ecosystem_source_card_shows_connector_label() -> None:
    source = inspect.getsource(reflex_app.ecosystem_source_card)
    loader_source = inspect.getsource(reflex_app.AppState.load_ecosystem.fn)

    assert "connector_label" in loader_source
    assert "connector_label" in source



def test_official_document_prefers_published_pdf_when_available() -> None:
    page_source = inspect.getsource(reflex_app.official_document)
    pdf_viewer_source = inspect.getsource(reflex_app.official_document_pdf_viewer)
    load_source = inspect.getsource(reflex_app.AppState.load_knowledge.fn)

    assert "knowledge_document_has_pdf" in page_source
    assert "official_document_pdf_viewer" in page_source
    assert "official_document_viewer" in page_source
    assert "rx.el.iframe" in pdf_viewer_source
    assert "knowledge_document_pdf_page_href" in pdf_viewer_source
    assert "official-document-pdf-frame" in inspect.getsource(reflex_app)
    assert "document_view.json" in str(reflex_app.PUBLISHED_DOCUMENT_VIEW_PATH)
    assert "document.pdf" in str(reflex_app.PUBLISHED_DOCUMENT_PDF_PATH)
    assert "_document_pdf_href(PUBLISHED_DOCUMENT_PDF_PUBLIC_HREF, self.knowledge_selected_page)" in load_source


def test_topic_pdf_viewer_uses_published_pdf_and_fragment_context() -> None:
    viewer_source = inspect.getsource(reflex_app.topic_pdf_document_viewer)
    panel_source = inspect.getsource(reflex_app.topic_source_panel)
    evidence_source = inspect.getsource(reflex_app.topic_evidence_card)

    assert "active_fragment_id" in viewer_source
    assert "rx.el.iframe" in viewer_source
    assert "knowledge_document_pdf_page_href" in viewer_source
    assert "Fragmento citado" in viewer_source
    assert "knowledge_document_has_pdf" in panel_source
    assert "PDF oficial publicado" in panel_source
    assert ".topic-pdf-document-viewer" in evidence_source
    assert ".document-paragraph-block-active" in evidence_source


def test_support_and_studio_routes_are_secondary_public_surfaces() -> None:
    sidebar_source = inspect.getsource(reflex_app.app_sidebar)
    footer_source = inspect.getsource(reflex_app.app_footer)
    home_source = inspect.getsource(reflex_app.home)
    topic_source = inspect.getsource(reflex_app.topic)
    support_source = inspect.getsource(reflex_app.support)
    studio_source = inspect.getsource(reflex_app.studio)
    project_source = inspect.getsource(reflex_app.project)

    assert '@rx.page(route="/support"' in support_source
    assert '@rx.page(route="/studio"' in studio_source
    assert 'sidebar_nav_link("Apoyar", "/support"' not in sidebar_source
    assert 'sidebar_nav_link("Studio", "/studio"' not in sidebar_source
    assert 'footer_text_link("♥", "Apoyar DatosEnOrden", "/support")' in footer_source
    assert 'footer_text_link("+", "Sugerir una fuente", SUPPORT_SOURCE_SUGGESTION_URL)' in footer_source
    assert 'footer_text_link("i", "Sobre el proyecto", "/project")' in footer_source
    assert 'DATOSENORDEN STUDIO' in footer_source
    assert 'Puerta para organizaciones que necesitan expedientes, conectores y evidencia verificable.' in footer_source
    assert 'footer_text_link("☁", "Studio", "/studio")' in footer_source
    assert 'footer_text_link("✉", "Contacto comercial", STUDIO_CONVERSATION_URL)' in footer_source
    assert 'support_cta_block()' not in home_source
    assert 'support_cta_block()' in topic_source
    assert '¿Te resultó útil esta investigación?' in inspect.getsource(reflex_app.support_cta_block)
    assert 'Apoyar el proyecto' in inspect.getsource(reflex_app.support_cta_block)
    assert 'Contactar por colaboración' not in support_source
    assert 'SUPPORT_COLLABORATION_URL' not in inspect.getsource(reflex_app)
    assert reflex_app.SUPPORT_DONATION_URL == "https://link.mercadopago.cl/datosenorden"
    assert 'os.getenv("DATOSENORDEN_SUPPORT_URL", "https://link.mercadopago.cl/datosenorden")' in inspect.getsource(reflex_app)
    assert 'Las donaciones no compran influencia' in support_source
    assert 'Evidencia primero' in support_source
    assert 'Proyecto público' in support_source
    assert 'Apoyar DatosEnOrden' in support_source
    assert 'Sugerir una fuente oficial' in support_source
    assert 'Conocer el proyecto' in support_source
    assert 'No hay pagos reales integrados todavía' in support_source
    assert 'DatosEnOrden Studio' in studio_source
    assert 'forma estructurada y verificable' in studio_source
    assert 'DatosEnOrden Studio se encuentra en desarrollo activo' in studio_source
    assert 'fuentes oficiales' in studio_source
    assert 'Enterprise' in studio_source
    assert 'Solicitar una' in studio_source
    assert 'relaciones documentales' in studio_source
    assert 'Cloud' in studio_source
    assert 'Municipalidades' in studio_source
    assert 'Enviar correo' in studio_source
    assert 'Community' in studio_source
    assert 'sin influencia editorial' in project_source.lower()




def test_state_graph_connection_rows_are_editorial_safe() -> None:
    graph = {
        "entity_id": "organismo:arauco",
        "entity_label": "Servicio de Salud Arauco",
        "nodes": [
            {"id": "organismo:arauco", "label": "Servicio de Salud Arauco", "node_type": "Organismo", "sources": ["ChileCompra"]},
            {"id": "empresa:demo", "label": "Proveedor Demo", "node_type": "Empresa", "sources": ["ChileCompra"]},
        ],
        "edges": [
            {
                "source": "empresa:demo",
                "target": "organismo:arauco",
                "edge_type": "COMPANY_APPEARS_IN_PURCHASES",
                "source_connector": "ChileCompra",
                "confidence": 0.82,
                "evidence": [{"title": "Orden de compra demo"}],
            }
        ],
        "summary": {"nodes": 2, "edges": 1},
    }

    rows = reflex_app._format_state_graph_connection_rows(graph)

    assert rows[0]["title"] == "Proveedor Demo"
    assert rows[0]["relation_type"] == "aparece en compras"
    assert rows[0]["source_connector"] == "ChileCompra"
    assert rows[0]["evidence_text"] == "Orden de compra demo"
    assert rows[0]["confidence_label"] == "confianza 82%"
    rendered_text = " ".join(str(value).lower() for row in rows for value in row.values())
    assert "sospechoso" not in rendered_text
    assert "red de corrupci" not in rendered_text


def test_state_graph_ui_sections_are_exposed() -> None:
    investigation_source = inspect.getsource(reflex_app.state_graph_connections_panel)
    center_source = inspect.getsource(reflex_app.investigation_center_column)
    system_source = inspect.getsource(reflex_app.topic_system_mode)
    card_source = inspect.getsource(reflex_app.state_graph_connection_card)

    assert "Conexiones del Estado" in investigation_source
    assert "state_graph_connections_panel()" in center_source
    assert "Mapa de conexiones" in system_source
    assert "Fuente/conector" in card_source
    assert "confidence_label" in card_source
    assert "evidence_text" in card_source


def test_search_results_show_state_graph_connection_availability() -> None:
    loader_source = inspect.getsource(reflex_app.AppState.run_search.fn)
    card_source = inspect.getsource(reflex_app.workspace_match_card)

    assert "state_graph_badges_text" in loader_source
    assert "Conexiones disponibles" in inspect.getsource(reflex_app._state_graph_badges_for_match)
    assert "state_graph_badges_text" in card_source
    assert reflex_app._state_graph_badges_for_match(
        {"datasets": ["ChileCompra", "InfoLobby"], "entity_type": "Organismo", "relationship_count": 1, "evidence_count": 1}
    ) == "Conexiones disponibles: compras | reuniones | eventos"


def test_sources_show_state_graph_backing_and_language_is_not_accusatory() -> None:
    loader_source = inspect.getsource(reflex_app.AppState.load_ecosystem.fn)
    source_card = inspect.getsource(reflex_app.ecosystem_source_card)
    full_source = inspect.getsource(reflex_app)

    assert "state_graph_contribution_label" in loader_source
    assert "Aporta conexiones al StateGraph" in loader_source
    assert "state_graph_contribution_label" in source_card
    assert "sospechoso" not in full_source.lower()
    assert "red de corrupci" not in full_source.lower()
