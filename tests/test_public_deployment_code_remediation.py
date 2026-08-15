from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from datosenorden.application.public_deployment.sanitization import public_asset_reference, public_error, public_opaque_reference, public_url
from deployment.production_config import load_production_config
from reflex_app.features.laboratory import state as laboratory_state
from reflex_app.features.laboratory.state import LaboratoryState


@pytest.mark.parametrize("value", (r"C:\\secret\\file.pdf", r"D:\\private\\report.html", r"F:\\private\\report.html", r"I:\\private\\report.html", r"\\\\server\\share\\private.pdf", "/home/app/private.pdf", "/tmp/private.pdf", "file:///tmp/private.pdf"))
def test_public_references_reject_server_paths(value: str) -> None:
    assert public_asset_reference(value) == ""
    assert public_url(value) == ""
    assert public_opaque_reference(value) == ""


def test_public_error_contract_never_reflects_exception_evidence() -> None:
    code, message = public_error()
    evidence = r"InternalParserError SQL password=secret C:\\secret\\file.pdf"
    assert code == "PUBLIC_SERVICE_UNAVAILABLE"
    assert evidence not in message
    assert "InternalParserError" not in message


def test_public_reflex_states_do_not_define_export_paths_or_raw_error_interpolation() -> None:
    state_files = tuple(Path("reflex_app/features").glob("*/state.py"))
    forbidden = ("report_path: str", "demo_report_path: str", "citizen_report_path: str")
    for path in state_files:
        text = path.read_text(encoding="utf-8")
        assert not any(marker in text for marker in forbidden), path


@pytest.mark.parametrize("handler_name, dependency_name", (("load_catalog", "list_public_expedient_catalog"), ("load_expedient", "get_public_expedient")))
def test_laboratory_error_state_keeps_only_the_final_public_contract(monkeypatch, handler_name: str, dependency_name: str) -> None:
    evidence = r"C:\private\secret.pdf; SELECT * FROM users; password=supersecret; InternalRepositoryError"

    def fail(*_args, **_kwargs):
        raise RuntimeError(evidence)

    monkeypatch.setattr(laboratory_state, dependency_name, fail)
    state = SimpleNamespace(
        catalog_rows=[],
        load_status="idle",
        error_message="",
        public_error_code="",
        _clear_expedient=lambda: None,
        router=SimpleNamespace(url=SimpleNamespace(query_parameters={}, raw_path="/laboratory")),
    )

    getattr(LaboratoryState, handler_name).fn(state)

    assert state.load_status == "error"
    assert state.public_error_code == "PUBLIC_SERVICE_UNAVAILABLE"
    assert state.error_message == public_error()[1]
    payload = f"{state.public_error_code} {state.error_message}"
    for marker in (r"C:\private\secret.pdf", "SELECT * FROM users", "password=supersecret", "InternalRepositoryError"):
        assert marker not in payload


@pytest.mark.parametrize("public_url", ("http://localhost:3000", "https://localhost", "not-a-url"))
def test_production_config_rejects_non_public_urls(public_url: str) -> None:
    with pytest.raises(ValueError):
        load_production_config({"DATOSENORDEN_ENV": "production", "DATABASE_URL": "postgresql://secret", "DATOSENORDEN_PUBLIC_BASE_URL": public_url, "API_URL": public_url})


def test_production_config_rejects_debug() -> None:
    with pytest.raises(ValueError):
        load_production_config({"DATOSENORDEN_ENV": "production", "DATABASE_URL": "postgresql://secret", "DATOSENORDEN_PUBLIC_BASE_URL": "https://public.example", "API_URL": "https://public.example", "DATOSENORDEN_DEBUG_INVESTIGATION": "1"})
