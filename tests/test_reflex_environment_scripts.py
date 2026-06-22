from __future__ import annotations

import socket

from scripts.web.check_reflex_environment import CheckResult
from scripts.web.check_reflex_environment import is_port_free
from scripts.web.check_reflex_environment import mask_database_url
from scripts.web.check_reflex_environment import parse_semver
from scripts.web.check_reflex_environment import render_results
from scripts.web.check_reflex_environment import version_at_least


def test_parse_semver_accepts_node_style_versions() -> None:
    assert parse_semver("v22.12.0") == (22, 12, 0)
    assert parse_semver("10.9.2") == (10, 9, 2)
    assert parse_semver("22.12.0\n") == (22, 12, 0)


def test_parse_semver_rejects_unparseable_values() -> None:
    assert parse_semver("not installed") is None
    assert parse_semver("") is None


def test_version_at_least_compares_three_part_versions() -> None:
    assert version_at_least((22, 12, 0), (22, 12, 0)) is True
    assert version_at_least((23, 0, 0), (22, 12, 0)) is True
    assert version_at_least((22, 11, 9), (22, 12, 0)) is False
    assert version_at_least(None, (22, 12, 0)) is False


def test_mask_database_url_hides_password() -> None:
    url = "postgresql+psycopg://user:secret@localhost:5432/db"

    assert mask_database_url(url) == "postgresql+psycopg://user:***@localhost:5432/db"
    assert "secret" not in mask_database_url(url)


def test_render_results_marks_ok_and_failures() -> None:
    text = render_results(
        (
            CheckResult("Python", True, "python.exe"),
            CheckResult("Node", False, "v20.0.0"),
        )
    )

    assert "[OK] Python: python.exe" in text
    assert "[FAIL] Node: v20.0.0" in text


def test_is_port_free_detects_bound_local_port() -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        sock.listen(1)
        port = sock.getsockname()[1]

        assert is_port_free(port) is False
