from __future__ import annotations

from types import SimpleNamespace
from uuid import UUID

from datosenorden.maintenance.entity_matching import EntityMatchCandidate
from datosenorden.maintenance.entity_matching import match_entity_candidates
from datosenorden.maintenance.entity_matching import normalize_entity_name
from datosenorden.maintenance.entity_matching import render_entity_match_candidates_text


class _ScalarResult:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows


class _FakeSession:
    def __init__(self, rows):
        self._rows = rows

    def scalars(self, statement):  # noqa: ANN001
        return _ScalarResult(self._rows)


def test_normalize_entity_name_removes_accents_punctuation_and_stopwords() -> None:
    assert normalize_entity_name("  Dirección, de Compras y Contratación Pública  ") == "DIRECCION COMPRAS Y CONTRATACION PUBLICA"


def test_match_entity_candidates_exact_match() -> None:
    session = _FakeSession(
        [
            SimpleNamespace(
                id=UUID("11111111-1111-1111-1111-111111111111"),
                entity_type="PUBLIC_ORGANIZATION",
                name="SERVICIO DE SALUD ARAUCO",
            )
        ]
    )

    candidates = match_entity_candidates(
        session,
        entity_type="PUBLIC_ORGANIZATION",
        name="Servicio de Salud Arauco",
    )

    assert len(candidates) == 1
    candidate = candidates[0]
    assert candidate.score == 1.0
    assert candidate.match_method == "exact_normalized_match"
    assert candidate.candidate_entity_id == "11111111-1111-1111-1111-111111111111"


def test_match_entity_candidates_contains_match() -> None:
    session = _FakeSession(
        [
            SimpleNamespace(
                id=UUID("22222222-2222-2222-2222-222222222222"),
                entity_type="PUBLIC_ORGANIZATION",
                name="SERVICIO DE SALUD ARAUCO HOSPITAL DE ARAUCO",
            )
        ]
    )

    candidates = match_entity_candidates(
        session,
        entity_type="PUBLIC_ORGANIZATION",
        name="SERVICIO DE SALUD ARAUCO",
    )

    assert len(candidates) == 1
    candidate = candidates[0]
    assert candidate.match_method == "contains_normalized_match"
    assert candidate.score == 0.95
    assert "contains" in candidate.explanation.lower()


def test_match_entity_candidates_token_overlap() -> None:
    session = _FakeSession(
        [
            SimpleNamespace(
                id=UUID("33333333-3333-3333-3333-333333333333"),
                entity_type="PUBLIC_ORGANIZATION",
                name="SERVICIO DE SALUD HOSPITAL ARAUCO",
            )
        ]
    )

    candidates = match_entity_candidates(
        session,
        entity_type="PUBLIC_ORGANIZATION",
        name="SERVICIO DE SALUD ARAUCO",
    )

    assert len(candidates) == 1
    candidate = candidates[0]
    assert candidate.match_method == "token_overlap"
    assert 0.4 <= candidate.score < 1.0
    assert "shared normalized tokens" in candidate.explanation.lower()


def test_match_entity_candidates_returns_no_match_for_unrelated_names() -> None:
    session = _FakeSession(
        [
            SimpleNamespace(
                id=UUID("44444444-4444-4444-4444-444444444444"),
                entity_type="PUBLIC_ORGANIZATION",
                name="MUNICIPALIDAD DE SANTIAGO",
            )
        ]
    )

    candidates = match_entity_candidates(
        session,
        entity_type="PUBLIC_ORGANIZATION",
        name="EMPRESA PORTUARIA DE ANTOFAGASTA",
    )

    assert candidates == ()


def test_render_entity_match_candidates_text_formats_ranked_rows() -> None:
    report = render_entity_match_candidates_text(
        entity_type="PUBLIC_ORGANIZATION",
        name="SERVICIO DE SALUD ARAUCO",
        candidates=(
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

    assert "entity_match_candidates:" in report
    assert "query_type=PUBLIC_ORGANIZATION" in report
    assert "candidate[1]:" in report
    assert "score=1.0000" in report
    assert "match_method=exact_normalized_match" in report
    assert "candidate[2]:" in report
