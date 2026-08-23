from __future__ import annotations

from scripts.qa_runtime_privileges import QA_DATABASE, RUNTIME_ROLE, apply_runtime_privileges


def test_qa_runtime_privileges_are_scoped_to_the_isolated_database() -> None:
    assert QA_DATABASE == "datosenorden_pytest_goldenqa"
    assert RUNTIME_ROLE == "deo_qa_runtime"


def test_qa_runtime_privileges_reject_any_other_database() -> None:
    try:
        apply_runtime_privileges("postgresql+psycopg://user@127.0.0.1:5432/not_qa")
    except ValueError as exc:
        assert "only target" in str(exc)
    else:
        raise AssertionError("non-QA database was accepted")


def test_qa_runtime_privileges_are_idempotent_by_role_name() -> None:
    source = apply_runtime_privileges.__code__.co_consts
    assert any("IF NOT EXISTS (SELECT 1 FROM pg_roles" in value for value in source if isinstance(value, str))
