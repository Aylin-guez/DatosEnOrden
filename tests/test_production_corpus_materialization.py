from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest

import datosenorden.application.data_release.materialization as materialization
from datosenorden.application.data_release.materialization import (
    APPROVED_REAL_CORPUS,
    APPROVED_REAL_IDS,
    BASELINE_REAL_IDS,
    ApprovedRealCorpusEntry,
    CorpusMaterializationError,
    materialize_approved_real_corpus,
    validate_approved_registry,
)
from scripts.materialize_production_corpus import (
    _require_base_rows_unchanged,
    _validate_target_url,
)

EXPECTED_REAL_IDS = (
    "EXP-REAL-CHILECOMPRA-1000813-247-CM26",
    "EXP-REAL-CHILECOMPRA-1002584-197-CM26",
    "EXP-REAL-CHILECOMPRA-1002772-6758-SE26",
    "EXP-REAL-LEGISLATIVE-15975-25",
    "EXP-REAL-ESCUELAS-PROTEGIDAS-18156-04",
    "EXP-REAL-LEGISLATIVE-18216-05",
    "EXP-REAL-CYBERSECURITY-14847-06",
    "EXP-REAL-DATA-PROTECTION-21719",
    "EXP-REAL-DEMOCRACIA-VIVA-ANTOFAGASTA",
    "EXP-REAL-CONTROL-PREVENTIVO-IDENTIDAD",
)


def test_approved_registry_is_explicit_exact_and_deterministic() -> None:
    assert APPROVED_REAL_IDS == EXPECTED_REAL_IDS
    assert tuple(entry.expedient_id for entry in validate_approved_registry()) == (
        EXPECTED_REAL_IDS
    )
    assert tuple(entry.expedient_id for entry in APPROVED_REAL_CORPUS[:4]) == BASELINE_REAL_IDS
    assert all(entry.mode == "baseline-package" for entry in APPROVED_REAL_CORPUS[:4])
    assert all(entry.mode == "provisioner" for entry in APPROVED_REAL_CORPUS[4:])
    assert all(entry.materializer is not None for entry in APPROVED_REAL_CORPUS[4:])


def test_registry_rejects_duplicate_missing_and_non_real_entries() -> None:
    with pytest.raises(CorpusMaterializationError, match="duplicate"):
        validate_approved_registry((*APPROVED_REAL_CORPUS, APPROVED_REAL_CORPUS[0]))
    with pytest.raises(CorpusMaterializationError, match="unavailable"):
        validate_approved_registry((replace(APPROVED_REAL_CORPUS[4], materializer=None),))
    with pytest.raises(CorpusMaterializationError, match="non-REAL"):
        validate_approved_registry(
            (
                ApprovedRealCorpusEntry(
                    "EXP-001",
                    "baseline-package",
                    "Laboratorio",
                    ("demo",),
                ),
            )
        )


def test_materialization_rejects_partial_initial_corpus(monkeypatch) -> None:
    entries = _fake_registry()
    monkeypatch.setattr(
        materialization,
        "_current_real_ids",
        lambda _session: ("EXP-REAL-BASE", "EXP-REAL-PARTIAL"),
    )
    with pytest.raises(CorpusMaterializationError, match="neither the certified baseline"):
        materialize_approved_real_corpus(object(), entries=entries, baseline_ids=("EXP-REAL-BASE",))


def test_materialization_rejects_unexpected_materializer_id(monkeypatch) -> None:
    entries = _fake_registry(actual_id="EXP-REAL-UNEXPECTED")
    monkeypatch.setattr(materialization, "_current_real_ids", lambda _session: ("EXP-REAL-BASE",))
    monkeypatch.setattr(
        materialization,
        "_content_fingerprints",
        lambda _session, _ids: (("EXP-REAL-BASE", "fingerprint"),),
    )
    with pytest.raises(CorpusMaterializationError, match="unexpected ID"):
        materialize_approved_real_corpus(object(), entries=entries, baseline_ids=("EXP-REAL-BASE",))


def test_materialization_failure_is_fail_closed(monkeypatch) -> None:
    def failed(_session):
        raise RuntimeError("fixture failure")

    entries = _fake_registry(materializer=failed)
    monkeypatch.setattr(materialization, "_current_real_ids", lambda _session: ("EXP-REAL-BASE",))
    monkeypatch.setattr(
        materialization,
        "_content_fingerprints",
        lambda _session, _ids: (("EXP-REAL-BASE", "fingerprint"),),
    )
    with pytest.raises(CorpusMaterializationError, match="approved materializer failed"):
        materialize_approved_real_corpus(object(), entries=entries, baseline_ids=("EXP-REAL-BASE",))


def test_complete_corpus_rerun_is_idempotent(monkeypatch) -> None:
    entries = _fake_registry()
    expected = ("EXP-REAL-BASE", "EXP-REAL-NEW")
    monkeypatch.setattr(materialization, "_current_real_ids", lambda _session: expected)
    monkeypatch.setattr(
        materialization,
        "_content_fingerprints",
        lambda _session, _ids: (("EXP-REAL-BASE", "fingerprint"),),
    )
    monkeypatch.setattr(
        materialization,
        "assert_approved_corpus_complete",
        lambda _session, entries: expected,
    )
    result = materialize_approved_real_corpus(
        object(), entries=entries, baseline_ids=("EXP-REAL-BASE",)
    )
    assert result.final_ids == expected
    assert result.original_unchanged
    assert dict(result.statuses) == {
        "EXP-REAL-BASE": "preserved",
        "EXP-REAL-NEW": "preserved",
    }


@pytest.mark.parametrize(
    "url",
    (
        "postgresql+psycopg://user@public.example:55433/datosenorden_materialization_x",
        "postgresql+psycopg://user@127.0.0.1:5432/datosenorden_materialization_x",
        "postgresql+psycopg://user@127.0.0.1:55432/datosenorden_materialization_x",
        "postgresql+psycopg://user@127.0.0.1:55433/datosenorden",
    ),
)
def test_materialization_target_safety_rejects_unsafe_database(url: str) -> None:
    with pytest.raises(RuntimeError):
        _validate_target_url(url, None)


def test_materialization_target_safety_accepts_unique_loopback_staging() -> None:
    _validate_target_url(
        "postgresql+psycopg://user@127.0.0.1:55433/datosenorden_materialization_release",
        "postgresql+psycopg://user@127.0.0.1:3000/datosenorden",
    )


def test_release_entrypoint_checks_completeness_before_export() -> None:
    source = Path("scripts/materialize_production_corpus.py").read_text(encoding="utf-8")
    assert source.index("assert_approved_corpus_complete(session)") < source.index(
        "export_production_data_package("
    )
    assert "pkgutil" not in source
    assert "iter_modules" not in source


def test_base_row_immutability_rejects_graph_mutation() -> None:
    base = {name: () for name in _table_names()}
    current = {name: () for name in _table_names()}
    base["source"] = ({"id": "source-1", "name": "Original"},)
    current["source"] = ({"id": "source-1", "name": "Changed"},)
    with pytest.raises(RuntimeError, match="changed certified base row"):
        _require_base_rows_unchanged(base, current)


def _table_names() -> tuple[str, ...]:
    from datosenorden.application.data_release.contract import TABLE_CONTRACTS

    return tuple(contract.name for contract in TABLE_CONTRACTS)


def _fake_registry(*, actual_id: str = "EXP-REAL-NEW", materializer=None):
    def default_materializer(_session):
        specification = SimpleNamespace(expedient_id=actual_id)
        return SimpleNamespace(
            expedient=SimpleNamespace(specification=specification),
            created=False,
        )

    return (
        ApprovedRealCorpusEntry(
            "EXP-REAL-BASE",
            "baseline-package",
            "baseline",
            ("baseline",),
        ),
        ApprovedRealCorpusEntry(
            "EXP-REAL-NEW",
            "provisioner",
            "new",
            ("new",),
            materializer or default_materializer,
        ),
    )
