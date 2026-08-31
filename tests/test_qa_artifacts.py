from __future__ import annotations

import pytest

from tests.qa_artifacts import CERTIFIED_DATA_PACKAGE_ENV, certified_data_package_path


def test_certified_data_package_requires_explicit_qa_only_location(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(CERTIFIED_DATA_PACKAGE_ENV, raising=False)

    with pytest.raises(RuntimeError, match=CERTIFIED_DATA_PACKAGE_ENV):
        certified_data_package_path()


def test_certified_data_package_uses_configured_file(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    package = tmp_path / "certified.zip"
    package.write_bytes(b"qa-only")
    monkeypatch.setenv(CERTIFIED_DATA_PACKAGE_ENV, str(package))

    assert certified_data_package_path() == package
