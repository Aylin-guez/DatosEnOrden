from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
import sys

from datosenorden.maintenance.entity_matching import EntityMatchCandidate

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import match_entity


def _session_manager(session):
    @contextmanager
    def _manager():
        yield session

    return _manager()


def test_match_entity_script_prints_ranked_candidates(monkeypatch, capsys) -> None:
    monkeypatch.setattr(match_entity, "SessionLocal", lambda: _session_manager(object()))
    monkeypatch.setattr(
        match_entity,
        "match_entity_candidates",
        lambda session, entity_type, name, limit: (  # noqa: ARG005
            EntityMatchCandidate(
                candidate_entity_id="11111111-1111-1111-1111-111111111111",
                candidate_name="SERVICIO DE SALUD ARAUCO",
                entity_type="PUBLIC_ORGANIZATION",
                score=1.0,
                match_method="exact_normalized_match",
                explanation="Normalized names are identical after accent, punctuation, and stopword removal.",
            ),
            EntityMatchCandidate(
                candidate_entity_id="22222222-2222-2222-2222-222222222222",
                candidate_name="SERVICIO DE SALUD ARAUCO HOSPITAL DE ARAUCO",
                entity_type="PUBLIC_ORGANIZATION",
                score=0.95,
                match_method="contains_normalized_match",
                explanation="One normalized name contains the other after accent, punctuation, and stopword removal.",
            ),
        ),
    )

    exit_code = match_entity.main(["--type", "PUBLIC_ORGANIZATION", "--name", "SERVICIO DE SALUD ARAUCO"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "entity_match_candidates:" in captured.out
    assert "candidate[1]:" in captured.out
    assert "match_method=exact_normalized_match" in captured.out
    assert captured.err == ""
