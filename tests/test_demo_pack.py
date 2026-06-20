from __future__ import annotations

from datetime import date
from pathlib import Path
from types import SimpleNamespace
import sys

from datosenorden.maintenance.dataset_registry import DatasetSummary
from datosenorden.maintenance.demo_pack import DemoDatasetStatus
from datosenorden.maintenance.demo_pack import build_demo_status
from datosenorden.maintenance.demo_pack import render_demo_seed_text
from datosenorden.maintenance.demo_pack import render_demo_status_text
from datosenorden.maintenance.demo_pack import resolve_demo_entity_profile
from datosenorden.maintenance.demo_pack import seed_demo_data
from datosenorden.maintenance.timeline_explorer import TimelineEvent

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import demo_seed
import demo_status


class _FakeSessionManager:
    def __init__(self, session):
        self.session = session

    def __enter__(self):  # noqa: ANN001
        return self.session

    def __exit__(self, exc_type, exc, tb):  # noqa: ANN001
        _ = (exc_type, exc, tb)
        return False


def _demo_profile(entity_id: str = "11111111-1111-1111-1111-111111111111"):
    entity = SimpleNamespace(
        id=entity_id,
        entity_type="PUBLIC_ORGANIZATION",
        name="DIVISION LOGISTICA DEL EJERCITO",
    )
    return SimpleNamespace(
        entity=entity,
        claims=(1, 2),
        relationships=(1,),
        evidences=(1,),
        related_entities=(),
        direct_neighbors=(),
    )


def _demo_timeline(entity_id: str = "11111111-1111-1111-1111-111111111111"):
    return SimpleNamespace(
        entity=SimpleNamespace(
            id=entity_id,
            entity_type="PUBLIC_ORGANIZATION",
            name="DIVISION LOGISTICA DEL EJERCITO",
            external_id="buyer-1",
        ),
        events=(
            TimelineEvent(
                event_date=date(2026, 3, 15),
                dataset="LOBBY",
                dataset_name="lobby-meeting-sample",
                title="Lobby meeting",
                explanation="Registro de reunion de lobby asociado a la entidad.",
                claim_id="22222222-2222-2222-2222-222222222222",
                predicate="ORGANIZATION_HELD_LOBBY_MEETING",
                source_record_id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
                evidence_count=1,
                relationship_count=1,
            ),
        ),
        explanation="Esta cronologia reune los eventos publicos encontrados para esta entidad en distintas fuentes de informacion.",
        caution="El orden temporal no implica relacion causal.",
    )


def test_seed_demo_data_runs_loaders_in_safe_order_and_repeats_cleanly(monkeypatch) -> None:
    calls: list[str] = []

    monkeypatch.setattr("datosenorden.maintenance.demo_pack.persist_local_traceability_seed", lambda session: calls.append("local"))
    monkeypatch.setattr("datosenorden.maintenance.demo_pack.persist_dipres_sample", lambda session: calls.append("dipres"))
    monkeypatch.setattr("datosenorden.maintenance.demo_pack.align_lobby_sample_to_existing_org", lambda session: calls.append("align"))
    monkeypatch.setattr("datosenorden.maintenance.demo_pack.persist_lobby_sample", lambda session: calls.append("lobby"))
    monkeypatch.setattr("datosenorden.maintenance.demo_pack.persist_transparencia_sample", lambda session: calls.append("transparencia"))

    seed_demo_data(object())
    seed_demo_data(object())

    assert calls == ["local", "dipres", "align", "lobby", "transparencia", "local", "dipres", "align", "lobby", "transparencia"]


def test_build_demo_status_ready_state_has_no_repairs(monkeypatch) -> None:
    monkeypatch.setattr(
        "datosenorden.maintenance.demo_pack.list_datasets",
        lambda session: (
            DatasetSummary("chilecompra", "ChileCompra", 1, 1, 1, 1, 1, "active", False),
            DatasetSummary("dipres-prototype", "DIPRES Prototype", 1, 1, 1, 1, 1, "active", False),
            DatasetSummary("lobby", "Lobby", 1, 1, 1, 1, 1, "active", False),
            DatasetSummary("transparencia", "Transparencia Activa", 1, 1, 1, 1, 1, "active", False),
        ),
    )
    monkeypatch.setattr(
        "datosenorden.maintenance.demo_pack.list_cross_dataset_organizations",
        lambda session: (SimpleNamespace(organization_name="DIVISION LOGISTICA DEL EJERCITO"),),
    )
    monkeypatch.setattr("datosenorden.maintenance.demo_pack.resolve_demo_entity_profile", lambda session, entity_name="DIVISION LOGISTICA DEL EJERCITO": _demo_profile())  # noqa: E501
    monkeypatch.setattr("datosenorden.maintenance.demo_pack.build_entity_timeline", lambda session, entity_id: _demo_timeline(entity_id))
    monkeypatch.setattr("datosenorden.maintenance.demo_pack._streamlit_app_available", lambda streamlit_app_path: True)

    report = build_demo_status(object())

    assert report.database_connected is True
    assert report.required_datasets_loaded is True
    assert report.cross_dataset_organization == "DIVISION LOGISTICA DEL EJERCITO"
    assert report.timeline_entity == "DIVISION LOGISTICA DEL EJERCITO"
    assert report.streamlit_app_available is True
    assert report.repairs == ()
    text = render_demo_status_text(report)
    assert "Ready:" in text
    assert "database connected" in text
    assert "Missing:" not in text


def test_build_demo_status_missing_state_lists_repairs(monkeypatch) -> None:
    monkeypatch.setattr(
        "datosenorden.maintenance.demo_pack.list_datasets",
        lambda session: (
            DatasetSummary("chilecompra", "ChileCompra", 1, 1, 1, 1, 1, "active", False),
            DatasetSummary("dipres-prototype", "DIPRES Prototype", 1, 1, 1, 1, 1, "active", False),
            DatasetSummary("lobby", "Lobby", 0, 0, 0, 0, 0, "empty", False),
            DatasetSummary("transparencia", "Transparencia Activa", 1, 1, 1, 1, 1, "active", False),
        ),
    )
    monkeypatch.setattr("datosenorden.maintenance.demo_pack.list_cross_dataset_organizations", lambda session: ())
    monkeypatch.setattr("datosenorden.maintenance.demo_pack.resolve_demo_entity_profile", lambda session, entity_name="DIVISION LOGISTICA DEL EJERCITO": None)
    monkeypatch.setattr("datosenorden.maintenance.demo_pack.build_entity_timeline", lambda session, entity_id: None)
    monkeypatch.setattr("datosenorden.maintenance.demo_pack._streamlit_app_available", lambda streamlit_app_path: False)

    report = build_demo_status(object())

    assert report.required_datasets_loaded is False
    assert report.cross_dataset_organization is None
    assert report.timeline_entity is None
    assert report.streamlit_app_available is False
    assert [repair.label for repair in report.repairs] == [
        "Lobby sample.",
        "Cross-dataset organization.",
        "Timeline available.",
        "Streamlit app available.",
    ]
    text = render_demo_status_text(report)
    assert "Missing:" in text
    assert "python scripts/load_lobby_sample.py" in text
    assert "python scripts/align_lobby_sample_to_existing_org.py" in text
    assert "streamlit run streamlit_app.py" in text


def test_render_demo_seed_text_reports_all_summary_counts() -> None:
    result = SimpleNamespace(
        datasets=(
            DemoDatasetStatus("chilecompra", "ChileCompra", True, "active"),
            DemoDatasetStatus("dipres-prototype", "DIPRES Prototype", True, "active"),
        ),
        entities=12,
        relationships=34,
        evidence=56,
        cross_dataset_organizations=1,
        timeline_ready_entities=1,
    )

    text = render_demo_seed_text(result)

    assert "demo_seed_complete:" in text
    assert "chilecompra: active" in text
    assert "dipres-prototype: active" in text
    assert "entities=12" in text
    assert "timeline_ready_entities=1" in text


def test_resolve_demo_entity_profile_uses_matching_layer(monkeypatch) -> None:
    candidate = SimpleNamespace(candidate_entity_id="11111111-1111-1111-1111-111111111111")
    calls: list[tuple[str, object]] = []

    class _FakeSession:
        def get(self, model, identity):  # noqa: ANN001
            calls.append(("get", identity))
            return SimpleNamespace(id=identity, entity_type="PUBLIC_ORGANIZATION", name="DIVISION LOGISTICA DEL EJERCITO")

    monkeypatch.setattr(
        "datosenorden.maintenance.demo_pack.match_entity_candidates",
        lambda session, entity_type, name, limit: (calls.append(("match", (entity_type, name, limit))) or [candidate]),
    )
    monkeypatch.setattr(
        "datosenorden.maintenance.demo_pack.get_entity_profile",
        lambda session, entity_id: SimpleNamespace(entity=SimpleNamespace(id=entity_id, name="DIVISION LOGISTICA DEL EJERCITO")),
    )

    profile = resolve_demo_entity_profile(_FakeSession())

    assert profile is not None
    assert calls[0] == ("match", ("PUBLIC_ORGANIZATION", "DIVISION LOGISTICA DEL EJERCITO", 1))
    assert calls[1][0] == "get"


def test_demo_walkthrough_docs_exist_and_describe_neutral_demo_pack() -> None:
    path = Path("docs/DEMO_WALKTHROUGH.md")
    assert path.exists()
    text = path.read_text(encoding="utf-8")
    assert "What DatosEnOrden is" in text
    assert "How to run the demo locally" in text
    assert "No corruption claims" in text


def test_demo_seed_script_reports_completion(monkeypatch, capsys) -> None:
    monkeypatch.setattr(demo_seed, "_run_alembic_upgrade", lambda: None)
    monkeypatch.setattr(demo_seed, "SessionLocal", lambda: _FakeSessionManager(object()))
    monkeypatch.setattr(demo_seed, "seed_demo_data", lambda session: None)
    monkeypatch.setattr(
        demo_seed,
        "build_demo_seed_result",
        lambda session: SimpleNamespace(
            datasets=(SimpleNamespace(slug="chilecompra", health="active"),),
            entities=1,
            relationships=2,
            evidence=3,
            cross_dataset_organizations=1,
            timeline_ready_entities=1,
        ),
    )

    exit_code = demo_seed.main([])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "demo_seed_complete:" in captured.out
    assert "chilecompra: active" in captured.out
    assert captured.err == ""


def test_demo_status_script_reports_missing_database_connection(monkeypatch, capsys) -> None:
    class _BrokenSession:
        def __enter__(self):  # noqa: ANN001
            raise RuntimeError("database unavailable")

        def __exit__(self, exc_type, exc, tb):  # noqa: ANN001
            _ = (exc_type, exc, tb)
            return False

    monkeypatch.setattr(demo_status, "SessionLocal", lambda: _BrokenSession())

    exit_code = demo_status.main([])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "DatosEnOrden demo status" in captured.out
    assert "database connected" in captured.out
    assert "check DATABASE_URL and PostgreSQL" in captured.out
    assert "database unavailable" in captured.err
