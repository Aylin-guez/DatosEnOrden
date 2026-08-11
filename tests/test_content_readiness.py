from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
from types import SimpleNamespace


def _load_script():
    path = Path("scripts/content_readiness.py")
    spec = importlib.util.spec_from_file_location("content_readiness", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_real_imports_check_uses_portable_explicit_safe_directory(tmp_path: Path, monkeypatch) -> None:
    module = _load_script()
    calls = []

    def fake_run(command, **kwargs):  # noqa: ANN001
        calls.append((command, kwargs))
        return SimpleNamespace(returncode=0, stdout="data/real_imports/.gitkeep\n", stderr="")

    monkeypatch.setattr(module, "ROOT", tmp_path)
    monkeypatch.setattr(module.subprocess, "run", fake_run)

    assert module._real_imports_not_tracked_check() == ("no real imports tracked", True, "none")
    command, kwargs = calls[0]
    root = tmp_path.resolve()
    assert command[:5] == ["git", "-c", f"safe.directory={root.as_posix()}", "-C", str(root)]
    assert kwargs["cwd"] == root
    source = Path("scripts/content_readiness.py").read_text(encoding="utf-8")
    assert "F:" not in source
    assert "I:" not in source


def test_real_imports_check_keeps_git_failures_as_failures(tmp_path: Path, monkeypatch) -> None:
    module = _load_script()
    monkeypatch.setattr(module, "ROOT", tmp_path)
    monkeypatch.setattr(module.subprocess, "run", lambda *args, **kwargs: SimpleNamespace(returncode=128, stdout="", stderr="git failure"))

    label, ok, detail = module._real_imports_not_tracked_check()
    assert (label, ok, detail) == ("no real imports tracked", False, "git failure")


def test_real_imports_check_rejects_tracked_private_imports(tmp_path: Path, monkeypatch) -> None:
    module = _load_script()
    monkeypatch.setattr(module, "ROOT", tmp_path)
    monkeypatch.setattr(module.subprocess, "run", lambda *args, **kwargs: SimpleNamespace(returncode=0, stdout="data/real_imports/private.json\n", stderr=""))

    label, ok, detail = module._real_imports_not_tracked_check()
    assert label == "no real imports tracked"
    assert ok is False
    assert detail == "data/real_imports/private.json"


def test_main_returns_nonzero_when_a_readiness_subcheck_fails(monkeypatch) -> None:
    module = _load_script()

    def passing(*_args, **_kwargs):
        return ("passing", True, "ok")

    for name in (
        "_platform_compiles_check",
        "_official_document_demo_check",
        "_import_check",
        "_legislative_adapter_check",
        "_directory_check",
        "_official_documents_structure_check",
        "_run_demo_check",
    ):
        monkeypatch.setattr(module, name, passing)
    monkeypatch.setattr(module, "_real_imports_not_tracked_check", lambda: ("no real imports tracked", False, "git failure"))

    assert module.main() == 1
