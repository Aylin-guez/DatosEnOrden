"""Pytest-wide runtime database isolation."""

from __future__ import annotations

import os

import pytest

from datosenorden.core.config import get_settings
from tests.postgres_isolation import EphemeralPostgres


_RUNTIME_DATABASE_URL = get_settings().database_url
_POSTGRES: EphemeralPostgres | None = None


def pytest_configure(config: pytest.Config) -> None:
    global _POSTGRES
    _POSTGRES = EphemeralPostgres.start(_RUNTIME_DATABASE_URL)
    _POSTGRES.migrate_to_head()
    os.environ["TEST_DATABASE_URL"] = _POSTGRES.test_url
    os.environ["DATABASE_URL"] = _POSTGRES.test_url
    os.environ["REAL_EXPEDIENT_TEST_ADMIN_URL"] = _POSTGRES.admin_url
    _reset_database_runtime()


def pytest_unconfigure(config: pytest.Config) -> None:
    global _POSTGRES
    if _POSTGRES is not None:
        _POSTGRES.close()
        _POSTGRES = None


@pytest.fixture(autouse=True)
def reset_database_runtime() -> None:
    _reset_database_runtime()
    yield
    _reset_database_runtime()


def _reset_database_runtime() -> None:
    from datosenorden.core.config import get_settings
    import datosenorden.db.session as db_session

    if db_session._engine is not None:
        db_session._engine.dispose()
    db_session._engine = None
    db_session._session_factory = None
    get_settings.cache_clear()
