from __future__ import annotations

from types import SimpleNamespace

from datosenorden.maintenance.safe_access import _as_list, _as_text, _field
from datosenorden.web import app_services


MAIN_ID = "11111111-1111-1111-1111-111111111111"
MAIN_NAME = "SERVICIO DE SALUD ARAUCO HOSPITAL DE ARAUCO"


def test_resolve_investigation_target_exact_id(monkeypatch) -> None:
    monkeypatch.setattr(app_services, "_resolve_canonical_expediente_target", lambda value: _canonical(value, "entity_id"))

    result = app_services.resolve_investigation_target(MAIN_ID)

    assert result["found"] is True
    assert result["entity_id"] == MAIN_ID
    assert result["entity_name"] == MAIN_NAME
    assert result["matched_by"] == "entity_id"


def test_resolve_investigation_target_exact_name(monkeypatch) -> None:
    monkeypatch.setattr(app_services, "_resolve_canonical_expediente_target", lambda value: _canonical(value, "exact_name"))

    result = app_services.resolve_investigation_target(MAIN_NAME)

    assert result["found"] is True
    assert result["entity_id"] == MAIN_ID
    assert result["matched_by"] == "exact_name"


def test_resolve_investigation_target_case_insensitive_name(monkeypatch) -> None:
    monkeypatch.setattr(app_services, "_resolve_canonical_expediente_target", lambda value: _canonical(value, "case_insensitive_name"))

    result = app_services.resolve_investigation_target(MAIN_NAME.lower())

    assert result["found"] is True
    assert result["entity_id"] == MAIN_ID
    assert result["matched_by"] == "case_insensitive_name"


def test_resolve_investigation_target_bad_id_returns_helpful_failure(monkeypatch) -> None:
    monkeypatch.setattr(
        app_services,
        "_resolve_canonical_expediente_target",
        lambda value: {"found": False, "original_entity_name": value, "warning": "No se encontro una entidad local."},
    )

    result = app_services.resolve_investigation_target("22222222-2222-2222-2222-222222222222")

    assert result["found"] is False
    assert "No se encontro" in result["warning"]


def test_search_workspace_includes_canonical_target(monkeypatch) -> None:
    monkeypatch.setattr(
        app_services,
        "_search_workspace",
        lambda query: {"matches": [{"entity_id": "record-1", "entity_name": "DIPRES budget", "entity_type": "BUDGET", "datasets": [], "evidence_count": 1, "relationship_count": 1}]},
    )
    monkeypatch.setattr(app_services, "_resolve_canonical_expediente_target", lambda value: _canonical(value, "entity_id", original_type="BUDGET", is_record=True))
    monkeypatch.setattr(app_services, "_get_record_context", lambda value: {"related_label": f"Relacionado con: {MAIN_NAME}"})

    result = app_services.search_workspace("presupuesto")

    match = result["matches"][0]
    assert match["canonical_entity_id"] == MAIN_ID
    assert match["canonical_entity_name"] == MAIN_NAME
    assert match["is_record"] is True
    assert match["related_label"] == f"Relacionado con: {MAIN_NAME}"


def test_safe_access_supports_dict_and_typed_objects() -> None:
    typed = SimpleNamespace(title="Evidence", values=("a", "b"))

    assert _field({"title": "Dict evidence"}, "title") == "Dict evidence"
    assert _field(typed, "title") == "Evidence"
    assert _field(typed, "missing", "fallback") == "fallback"
    assert _as_text("  value  ") == "value"
    assert _as_text("", "fallback") == "fallback"
    assert _as_list(("a", "b")) == ["a", "b"]
    assert _as_list(None) == []


def _canonical(value: str, matched_by: str, *, original_type: str = "PUBLIC_ORGANIZATION", is_record: bool = False) -> dict:
    return {
        "found": True,
        "canonical_entity_id": MAIN_ID,
        "canonical_entity_name": MAIN_NAME,
        "canonical_entity_type": "PUBLIC_ORGANIZATION",
        "original_entity_id": value,
        "original_entity_name": MAIN_NAME if not is_record else "DIPRES budget",
        "original_entity_type": original_type,
        "relation_to_original": "self" if not is_record else "BUDGET_ALLOCATED_TO",
        "matched_by": matched_by,
        "is_record": is_record,
        "record_label": "Registro especifico" if is_record else "Organismo publico",
        "warning": "",
    }
