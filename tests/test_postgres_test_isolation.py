from __future__ import annotations

import pytest

from tests.postgres_isolation import assert_isolated_test_database


def test_test_database_rejects_runtime_identity() -> None:
    value = "postgresql+psycopg://operator@localhost:5432/datosenorden"

    with pytest.raises(RuntimeError, match="must not match"):
        assert_isolated_test_database(value, value)


def test_test_database_rejects_non_test_name() -> None:
    with pytest.raises(RuntimeError, match="pytest prefix"):
        assert_isolated_test_database(
            "postgresql+psycopg://operator@localhost:55439/other_database",
            "postgresql+psycopg://operator@localhost:5432/datosenorden",
        )


def test_test_database_accepts_distinct_prefixed_identity() -> None:
    assert_isolated_test_database(
        "postgresql+psycopg://operator@localhost:55439/datosenorden_pytest_123",
        "postgresql+psycopg://operator@localhost:5432/datosenorden",
    )
