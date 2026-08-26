from __future__ import annotations

from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

from datosenorden.application.real_expedient.citizen_projection import citizen_expedient_projection
from datosenorden.application.real_expedient.democracia_viva_antofagasta import (
    democracia_viva_citizen_context,
)
from datosenorden.application.real_expedient.models import (
    ExpedientReferences,
    ExpedientSpecification,
    ExpedientStatus,
    StoredExpedient,
)
from datosenorden.application.provenance.models import ProvenanceClass
from reflex_app.features.laboratory.state import LaboratoryState


ROOT = Path(__file__).parents[1]


def _runtime_projection() -> dict[str, object]:
    specification = ExpedientSpecification(
        "EXP-REAL-DEMOCRACIA-VIVA-ANTOFAGASTA",
        "Democracia Viva y los convenios de Antofagasta",
        "Pregunta",
        "Resumen",
        ProvenanceClass.REAL,
        ExpedientStatus.PUBLISHED,
        1,
        ExpedientReferences((), ()),
        (),
    )
    stored = StoredExpedient(
        specification=specification,
        content_fingerprint="test-public-money-runtime-boundary",
        created_at=datetime(2026, 8, 26),
        updated_at=datetime(2026, 8, 26),
    )
    return citizen_expedient_projection(stored, democracia_viva_citizen_context())


def test_public_money_projection_reaches_the_runtime_payload_boundary() -> None:
    projection = _runtime_projection()
    summary = projection["public_money_summary"]
    assert summary["universe"]["amount"] == 426_000_000
    assert len(summary["instruments"]) == 3
    snapshot = summary["snapshots"][0]
    assert snapshot["as_of_date"] == "2023-06-30"
    assert {item["metric"]: item["amount"] for item in snapshot["observations"]} == {
        "TRANSFERRED": 426_000_000,
        "RENDERED": 116_963_639,
        "APPROVED": 12_146_280,
        "UNRENDERED": 309_036_361,
    }
    actions = {item["metric"]: item for item in summary["subsequent_actions"][0]["observations"]}
    assert actions["RESTITUTION_ORDERED"]["amount"] == 391_768_516
    assert actions["RECOVERED"]["epistemic_status"] == "UNKNOWN"


def test_public_money_projection_reaches_typed_laboratory_state_and_absent_summary_stays_hidden() -> None:
    state = SimpleNamespace()
    LaboratoryState._load_public_money_summary(state, _runtime_projection()["public_money_summary"])

    assert state.citizen_public_money_ready is True
    assert state.citizen_public_money_universe["display_amount"] == "$426.000.000"
    assert len(state.citizen_public_money_instruments) == 3
    assert state.citizen_public_money_snapshots[0]["as_of_date"] == "2023-06-30"
    assert state.citizen_public_money_snapshots[0]["cutoff_label"] == "30 de junio de 2023"
    assert state.citizen_public_money_snapshots[0]["authority"] == "Contraloría General de la República"
    assert state.citizen_public_money_actions[0]["observations"][1]["display_amount"] == "No acreditada en el corpus disponible."

    LaboratoryState._load_public_money_summary(state, None)
    assert state.citizen_public_money_ready is False
    assert state.citizen_public_money_title == ""
    assert state.citizen_public_money_instruments == []


def test_generated_reflex_route_contains_the_public_money_component_boundary() -> None:
    generated_route = ROOT / ".web" / "app" / "routes" / "[laboratory].[expedient]._index.jsx"
    generated_component = ROOT / ".web" / "app_components" / "reflex_app" / "features" / "laboratory" / "pages.jsx"
    component_source = ROOT / "reflex_app" / "features" / "laboratory" / "components.py"
    state_source = ROOT / "reflex_app" / "features" / "laboratory" / "state.py"
    assert generated_route.exists(), "Reflex frontend generation is required before this runtime-boundary test"
    assert generated_component.exists(), "Reflex component generation is required before this runtime-boundary test"
    assert generated_route.stat().st_mtime_ns >= component_source.stat().st_mtime_ns
    assert generated_component.stat().st_mtime_ns >= component_source.stat().st_mtime_ns
    assert generated_route.stat().st_mtime_ns >= state_source.stat().st_mtime_ns
    rendered = generated_route.read_text(encoding="utf-8")
    assert "public-money-total" in rendered
    assert rendered.index("Qu\\u00e9 pas\\u00f3") < rendered.index("public-money-total")
    assert rendered.index("public-money-total") < rendered.index("Materias del proyecto")
    assert "Corte informado por" in generated_component.read_text(encoding="utf-8")
