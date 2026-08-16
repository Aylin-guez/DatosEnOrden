from __future__ import annotations

import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SHELL_SUFFIXES = {".bash", ".dash", ".ksh", ".sh", ".zsh"}


def _release_shell_paths() -> list[str]:
    tracked = subprocess.run(
        ["git", "ls-files"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.splitlines()
    result: list[str] = []
    for relative in tracked:
        path = ROOT / relative
        payload = path.read_bytes()
        first_line = payload.split(b"\n", 1)[0]
        if path.suffix in SHELL_SUFFIXES or first_line.startswith(b"#!") and any(
            interpreter in first_line
            for interpreter in (b"/sh", b"/bash", b"/dash", b"/ksh", b"/zsh")
        ):
            result.append(relative)
    return sorted(result)


def test_release_shell_scripts_are_lf_and_git_enforces_it() -> None:
    paths = _release_shell_paths()
    assert paths
    for relative in paths:
        assert b"\r" not in (ROOT / relative).read_bytes(), relative

    attributes = subprocess.run(
        ["git", "check-attr", "eol", "--", *paths],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.splitlines()
    assert attributes == [f"{path}: eol: lf" for path in paths]
