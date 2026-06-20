from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from uuid import UUID
import sys

from datosenorden.maintenance.cross_dataset_demo import CrossDatasetMatchDiagnostic
from datosenorden.maintenance.cross_dataset_demo import DatasetOrganization
from datosenorden.maintenance.cross_dataset_demo import LobbySampleAlignmentResult

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import align_lobby_sample_to_existing_org
import debug_cross_dataset_matches


def _session_manager(session):
    @contextmanager
    def _manager():
        yield session

    return _manager()


def test_debug_cross_dataset_matches_script_prints_diagnostic(monkeypatch, capsys) -> None:
    diagnostic = CrossDatasetMatchDiagnostic(
        chilecompra_organizations=(
            DatasetOrganization(
                entity_id=str(UUID("11111111-1111-1111-1111-111111111111")),
                name="SERVICIO DE SALUD ARAUCO HOSPITAL DE ARAUCO",
                normalized_name="SERVICIO SALUD ARAUCO HOSPITAL ARAUCO",
                dataset="chilecompra",
            ),
        ),
        lobby_organizations=(),
        shared_organization_ids=(),
        candidate_matches=(),
        reason="No Lobby PUBLIC_ORGANIZATION records were found in stored claims.",
    )
    monkeypatch.setattr(debug_cross_dataset_matches, "SessionLocal", lambda: _session_manager(object()))
    monkeypatch.setattr(debug_cross_dataset_matches, "debug_cross_dataset_matches", lambda session, candidate_limit=3: diagnostic)

    exit_code = debug_cross_dataset_matches.main([])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "cross_dataset_match_diagnostic:" in captured.out
    assert "chilecompra_organizations:" in captured.out
    assert "reason:" in captured.out
    assert captured.err == ""


def test_align_lobby_sample_to_existing_org_script_prints_alignment(monkeypatch, capsys, tmp_path) -> None:
    sample_path = tmp_path / "lobby_meeting_sample.json"
    result = LobbySampleAlignmentResult(
        sample_path=str(sample_path),
        organization_id="11111111-1111-1111-1111-111111111111",
        organization_name="SERVICIO DE SALUD ARAUCO HOSPITAL DE ARAUCO",
        previous_organization_name="SERVICIO DE SALUD ARAUCO",
        changed=True,
        classification="LOCAL_TEST_DATA",
        official_status="NOT_OFFICIAL_DATA",
    )
    monkeypatch.setattr(align_lobby_sample_to_existing_org, "SessionLocal", lambda: _session_manager(object()))
    monkeypatch.setattr(
        align_lobby_sample_to_existing_org,
        "align_lobby_sample_to_existing_org",
        lambda session, sample_path: result,
    )

    exit_code = align_lobby_sample_to_existing_org.main(["--sample-path", str(sample_path)])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "lobby_sample_alignment:" in captured.out
    assert "changed=True" in captured.out
    assert "classification=LOCAL_TEST_DATA" in captured.out
    assert captured.err == ""
