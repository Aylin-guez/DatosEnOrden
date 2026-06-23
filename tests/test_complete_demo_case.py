from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
import sys

from datosenorden.maintenance import complete_demo_case

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import demo_case_summary
import load_complete_demo_case


def _payload() -> dict:
    return complete_demo_case.load_complete_demo_case_payload()


def test_complete_demo_case_payload_is_coherent() -> None:
    payload = _payload()

    assert payload["classification"] == "LOCAL_TEST_DATA"
    assert payload["official_status"] == "NOT_OFFICIAL_DATA"
    assert payload["main_entity"]["name"] == "SERVICIO DE SALUD ARAUCO HOSPITAL DE ARAUCO"
    assert set(payload["datasets"]) == {
        "dipres",
        "registro_empresas",
        "chilecompra",
        "diario_oficial",
        "transparencia",
        "lobby",
        "contraloria",
    }

    buyer_names = {
        record["Comprador"]["NombreOrganismo"]
        for record in payload["datasets"]["chilecompra"]["records"]
    }
    supplier_names = {
        record["Proveedor"]["NombreProveedor"]
        for record in payload["datasets"]["chilecompra"]["records"]
    }
    registry_names = {
        record["company_name"]
        for record in payload["datasets"]["registro_empresas"]["records"]
    }

    assert buyer_names == {"SERVICIO DE SALUD ARAUCO HOSPITAL DE ARAUCO"}
    assert supplier_names == registry_names
    assert payload["datasets"]["diario_oficial"]["records"][0]["person_name"] == "SOFIA RAMOS"
    assert payload["datasets"]["transparencia"]["records"][0]["person_name"] == "SOFIA RAMOS"
    assert payload["datasets"]["lobby"]["records"][0]["counterparty_name"] == "SOFIA RAMOS"


def test_complete_demo_case_summary_tracks_reuse_and_timeline() -> None:
    summary = complete_demo_case.build_complete_demo_case_summary(_payload())

    assert summary.main_entity == "SERVICIO DE SALUD ARAUCO HOSPITAL DE ARAUCO"
    assert summary.datasets == (
        "DIPRES",
        "Registro Empresas",
        "ChileCompra",
        "Diario Oficial",
        "Transparencia Activa",
        "Lobby",
        "Contraloria",
    )
    assert "SERVICIO DE SALUD ARAUCO HOSPITAL DE ARAUCO" in summary.reused_entities
    assert "ACME TECNOLOGIAS SPA" in summary.reused_entities
    assert "SOFIA RAMOS" in summary.reused_entities
    assert summary.relationships_created > 0
    assert summary.evidence_count > 0
    assert summary.timeline_start is not None
    assert summary.timeline_end is not None
    assert summary.timeline_start <= summary.timeline_end
    assert summary.connected_suppliers == (
        "ACME TECNOLOGIAS SPA",
        "CONSULTORA PUBLICA SPA",
        "SERVICIOS NORTE LTDA",
    )
    assert "SOFIA RAMOS" in summary.connected_people
    assert any("N 12.801" in item for item in summary.connected_official_publications)


def test_persist_complete_demo_case_loads_sections_in_dependency_order(monkeypatch) -> None:
    payload = _payload()
    calls: list[str] = []

    def _batch(name: str, *, entities: int = 1, claims: int = 1, evidence: int = 1, relationships: int = 1):
        return SimpleNamespace(
            source_records=(name,),
            claims=tuple(range(claims)),
            evidence=tuple(range(evidence)),
            entities=tuple(
                SimpleNamespace(entity_type=SimpleNamespace(value=name.upper()), external_id=f"{name}-{index}")
                for index in range(entities)
            ),
            public_relationships=tuple(range(relationships)),
        )

    monkeypatch.setattr(complete_demo_case, "build_dipres_sample_batch", lambda session, section: (_ := calls.append("dipres")) or _batch("dipres", claims=2, evidence=3, relationships=1))
    monkeypatch.setattr(complete_demo_case, "build_registro_empresas_sample_batch", lambda session, section: (_ := calls.append("registro_empresas")) or _batch("registro_empresas", claims=4, evidence=4, relationships=4))
    monkeypatch.setattr(complete_demo_case, "_build_chilecompra_demo_batch", lambda session, section: (_ := calls.append("chilecompra")) or _batch("chilecompra", claims=2, evidence=1, relationships=2))
    monkeypatch.setattr(complete_demo_case, "build_diario_oficial_sample_batch", lambda session, section: (_ := calls.append("diario_oficial")) or _batch("diario_oficial", claims=4, evidence=4, relationships=4))
    monkeypatch.setattr(complete_demo_case, "build_transparencia_sample_batch", lambda session, section: (_ := calls.append("transparencia")) or _batch("transparencia", claims=3, evidence=3, relationships=3))
    monkeypatch.setattr(complete_demo_case, "build_lobby_sample_batch", lambda session, section: (_ := calls.append("lobby")) or _batch("lobby", claims=3, evidence=3, relationships=2))
    monkeypatch.setattr(complete_demo_case, "build_contraloria_sample_batch", lambda session, section: (_ := calls.append("contraloria")) or _batch("contraloria", claims=2, evidence=2, relationships=2))

    loaded_batches: list[str] = []

    class _FakeGraphLoader:
        def __init__(self, session):  # noqa: ANN001
            self.session = session

        def load(self, batch, dry_run=False):  # noqa: ANN001
            _ = dry_run
            loaded_batches.append(str(batch.source_records[0]))

    monkeypatch.setattr(complete_demo_case, "GraphLoader", _FakeGraphLoader)

    result = complete_demo_case.persist_complete_demo_case(object(), payload)

    assert calls == [
        "dipres",
        "registro_empresas",
        "chilecompra",
        "diario_oficial",
        "transparencia",
        "lobby",
        "contraloria",
    ]
    assert loaded_batches == calls
    assert result.summary.main_entity == "SERVICIO DE SALUD ARAUCO HOSPITAL DE ARAUCO"
    assert result.source_records == 7
    assert result.claims == 20
    assert result.evidence == 20
    assert result.entities == 7
    assert result.relationships == 18


def test_demo_case_summary_script_prints_summary(monkeypatch, capsys) -> None:
    monkeypatch.setattr(
        demo_case_summary,
        "load_complete_demo_case_payload",
        lambda input_path: _payload(),
    )
    monkeypatch.setattr(
        demo_case_summary,
        "build_complete_demo_case_summary",
        lambda payload: complete_demo_case.build_complete_demo_case_summary(payload),
    )

    exit_code = demo_case_summary.main([])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "complete_demo_case_summary:" in captured.out
    assert "SERVICIO DE SALUD ARAUCO HOSPITAL DE ARAUCO" in captured.out
    assert captured.err == ""


def test_load_complete_demo_case_script_prints_load_result(monkeypatch, capsys) -> None:
    payload = _payload()

    monkeypatch.setattr(
        load_complete_demo_case,
        "load_complete_demo_case_payload",
        lambda input_path: payload,
    )
    monkeypatch.setattr(
        load_complete_demo_case,
        "persist_complete_demo_case",
        lambda session, payload: complete_demo_case.CompleteDemoCaseLoadResult(
            summary=complete_demo_case.build_complete_demo_case_summary(payload),
            source_records=7,
            claims=20,
            evidence=20,
            entities=7,
            relationships=18,
        ),
    )

    class _SessionManager:
        def __enter__(self):  # noqa: ANN001
            return object()

        def __exit__(self, exc_type, exc, tb):  # noqa: ANN001
            _ = (exc_type, exc, tb)
            return False

    monkeypatch.setattr(load_complete_demo_case, "SessionLocal", lambda: _SessionManager())

    exit_code = load_complete_demo_case.main([])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "complete_demo_case_loaded:" in captured.out
    assert "SERVICIO DE SALUD ARAUCO HOSPITAL DE ARAUCO" in captured.out
    assert captured.err == ""
