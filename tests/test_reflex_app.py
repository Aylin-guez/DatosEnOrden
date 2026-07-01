from __future__ import annotations

from dataclasses import dataclass
import inspect
import pickle
from types import MappingProxyType
from types import SimpleNamespace

import reflex_app.reflex_app as reflex_app


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


def test_nav_expediente_points_to_empty_investigation_and_search_is_header_action() -> None:
    source = inspect.getsource(reflex_app.shell)

    assert 'rx.link("Expediente", href="/investigation"' in source
    assert 'rx.link("Biblioteca", href="/library"' in source
    assert 'rx.link("Seguimiento", href="/tracking"' in source
    assert 'rx.link("Reportes", href="/reports"' in source
    assert 'rx.link("Proyecto", href="/project"' in source
    assert 'rx.link("Buscar", href="/search"' not in source
    assert source.index('rx.link("Expediente"') < source.index('rx.link("Reportes"') < source.index('rx.link("Biblioteca"') < source.index('rx.link("Seguimiento"')
    assert "header_search" in source
    assert "toggle_header_search" in source


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
    assert "Sigue la historia de una propuesta publica" in source


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
    assert "Reportes ciudadanos" in source


def test_library_and_project_routes_are_registered() -> None:
    library_source = inspect.getsource(reflex_app.library)
    project_source = inspect.getsource(reflex_app.project)

    assert 'route="/library"' in library_source
    assert "Biblioteca Oficial" in library_source
    assert "Preguntas importantes" in library_source
    assert 'route="/project"' in project_source
    assert "Estado del proyecto" in project_source
    assert "Que significa MVP" in project_source


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
