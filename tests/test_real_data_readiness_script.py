from __future__ import annotations

import importlib.util
from pathlib import Path


def _load_script_module():
    script_path = Path(__file__).resolve().parents[1] / "scripts" / "real_data_readiness.py"
    spec = importlib.util.spec_from_file_location("real_data_readiness", script_path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


class _SessionContext:
    def __enter__(self):  # noqa: ANN001
        return object()

    def __exit__(self, exc_type, exc, tb):  # noqa: ANN001
        _ = (exc_type, exc, tb)
        return False


def test_real_data_readiness_script_prints_groups(monkeypatch, capsys) -> None:
    module = _load_script_module()
    monkeypatch.setattr(module, "SessionLocal", lambda: _SessionContext())
    monkeypatch.setattr(
        module,
        "summarize_real_dataset_registry",
        lambda session: {
            "entries": [
                {
                    "id": "chilecompra",
                    "display_name": "ChileCompra",
                    "status": "connected_file_loader",
                    "loader_script": "scripts/load_chilecompra_file.py",
                    "source_records": 1,
                    "entities": 2,
                    "relationships": 3,
                    "ready_for_real_data": True,
                    "demo_available": True,
                }
            ]
        },
    )

    assert module.main() == 0
    output = capsys.readouterr().out
    assert "real_data_readiness:" in output
    assert "fuentes listas: 1" in output
    assert "chilecompra" in output
