from __future__ import annotations

from types import SimpleNamespace
from uuid import UUID

from datosenorden.maintenance.safe_access import _as_list, _as_text, _field
from datosenorden.web import app_services


MAIN_ID = "11111111-1111-1111-1111-111111111111"
MAIN_NAME = "SERVICIO DE SALUD ARAUCO HOSPITAL DE ARAUCO"


class _Scalars:
    def __init__(self, rows: list[object]) -> None:
        self._rows = rows

    def all(self) -> list[object]:
        return self._rows


class _Session:
    def __init__(self, *, get_result=None, scalar_results=None) -> None:  # noqa: ANN001
        self.get_result = get_result
        self.scalar_results = list(scalar_results or [])

    def __enter__(self):  # noqa: ANN001
        return self

    def __exit__(self, exc_type, exc, tb):  # noqa: ANN001
        _ = (exc_type, exc, tb)
        return False

    def get(self, model, identity):  # noqa: ANN001
        _ = model
        if identity == UUID(MAIN_ID):
            return self.get_result
        return None

    def scalars(self, statement):  # noqa: ANN001
        _ = statement
        rows = self.scalar_results.pop(0) if self.scalar_results else []
        return _Scalars(rows)


def _entity(entity_id: str = MAIN_ID, name: str = MAIN_NAME):
    return SimpleNamespace(id=UUID(entity_id), name=name, entity_type="PUBLIC_ORGANIZATION")


def test_resolve_investigation_target_exact_id(monkeypatch) -> None:
    monkeypatch.setattr(app_services, "SessionLocal", lambda: _Session(get_result=_entity()))

    result = app_services.resolve_investigation_target(MAIN_ID)

    assert result["found"] is True
    assert result["entity_id"] == MAIN_ID
    assert result["entity_name"] == MAIN_NAME
    assert result["matched_by"] == "entity_id"


def test_resolve_investigation_target_exact_name(monkeypatch) -> None:
    monkeypatch.setattr(app_services, "SessionLocal", lambda: _Session(scalar_results=[[_entity()]]))

    result = app_services.resolve_investigation_target(MAIN_NAME)

    assert result["found"] is True
    assert result["entity_id"] == MAIN_ID
    assert result["matched_by"] == "exact_name"


def test_resolve_investigation_target_case_insensitive_name(monkeypatch) -> None:
    monkeypatch.setattr(app_services, "SessionLocal", lambda: _Session(scalar_results=[[], [_entity()]]))

    result = app_services.resolve_investigation_target(MAIN_NAME.lower())

    assert result["found"] is True
    assert result["entity_id"] == MAIN_ID
    assert result["matched_by"] == "case_insensitive_name"


def test_resolve_investigation_target_bad_id_returns_helpful_failure(monkeypatch) -> None:
    monkeypatch.setattr(app_services, "SessionLocal", lambda: _Session(get_result=None))

    result = app_services.resolve_investigation_target("22222222-2222-2222-2222-222222222222")

    assert result["found"] is False
    assert "No se encontro" in result["warning"]


def test_safe_access_supports_dict_and_typed_objects() -> None:
    typed = SimpleNamespace(title="Evidence", values=("a", "b"))

    assert _field({"title": "Dict evidence"}, "title") == "Dict evidence"
    assert _field(typed, "title") == "Evidence"
    assert _field(typed, "missing", "fallback") == "fallback"
    assert _as_text("  value  ") == "value"
    assert _as_text("", "fallback") == "fallback"
    assert _as_list(("a", "b")) == ["a", "b"]
    assert _as_list(None) == []
