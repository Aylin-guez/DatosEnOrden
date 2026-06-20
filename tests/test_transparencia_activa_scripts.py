from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
import sys

from datosenorden.maintenance.transparencia_activa_prototype import TransparenciaImportResult
from datosenorden.maintenance.transparencia_activa_prototype import TransparenciaSummary
from datosenorden.maintenance.transparencia_activa_prototype import TransparenciaSummaryRow

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import load_transparencia_sample
import transparencia_summary


def _session_manager(session):
    @contextmanager
    def _manager():
        yield session

    return _manager()


def test_load_transparencia_sample_script_prints_result(monkeypatch, capsys) -> None:
    monkeypatch.setattr(load_transparencia_sample, "SessionLocal", lambda: _session_manager(object()))
    monkeypatch.setattr(
        load_transparencia_sample,
        "persist_transparencia_sample",
        lambda session, input_path: TransparenciaImportResult(  # noqa: ARG005
            source_records=1,
            claims=3,
            evidences=3,
            entities=3,
            relationship_public=3,
            organization_entity_id="11111111-1111-1111-1111-111111111111",
            organization_name="DIVISION LOGISTICA DEL EJERCITO",
            role_entity_id="22222222-2222-2222-2222-222222222222",
            role_name="Cargo de muestra Transparencia Activa",
            person_entity_id="33333333-3333-3333-3333-333333333333",
            person_name="PERSONA DE MUESTRA TRANSPARENCIA",
            organization_match_method="exact_normalized_match",
            organization_match_confidence=1.0,
        ),
    )

    exit_code = load_transparencia_sample.main([])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "transparencia_sample_loaded:" in captured.out
    assert "relationship_public=3" in captured.out
    assert captured.err == ""


def test_transparencia_summary_script_prints_summary(monkeypatch, capsys) -> None:
    monkeypatch.setattr(transparencia_summary, "SessionLocal", lambda: _session_manager(object()))
    monkeypatch.setattr(
        transparencia_summary,
        "read_transparencia_summary",
        lambda session: TransparenciaSummary(  # noqa: ARG005
            organizations=1,
            people=1,
            roles=1,
            claims=3,
            relationships=3,
            evidence=3,
            rows=(
                TransparenciaSummaryRow(
                    organization_id="11111111-1111-1111-1111-111111111111",
                    organization_name="DIVISION LOGISTICA DEL EJERCITO",
                    role_id="22222222-2222-2222-2222-222222222222",
                    role_name="Cargo de muestra Transparencia Activa",
                    person_id="33333333-3333-3333-3333-333333333333",
                    person_name="PERSONA DE MUESTRA TRANSPARENCIA",
                    period="2026-01",
                    unit_name="Unidad de muestra",
                    claims=("ORGANIZATION_HAS_PUBLIC_ROLE",),
                    relationships=("ORGANIZATION_HAS_PUBLIC_ROLE",),
                    evidence=3,
                    organization_match_method="exact_normalized_match",
                    organization_match_confidence=1.0,
                ),
            ),
        ),
    )

    exit_code = transparencia_summary.main([])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "transparencia_summary:" in captured.out
    assert "matched_entities:" in captured.out
    assert "organization_match_method=exact_normalized_match" in captured.out
    assert captured.err == ""
