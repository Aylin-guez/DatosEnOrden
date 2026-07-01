from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace


def _load_script_module():
    script_path = Path(__file__).resolve().parents[1] / "scripts" / "load_chilecompra_file.py"
    spec = importlib.util.spec_from_file_location("load_chilecompra_file", script_path)
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


def test_load_chilecompra_file_maps_local_json_without_real_db(monkeypatch, tmp_path, capsys) -> None:
    module = _load_script_module()
    payload_path = tmp_path / "sample.json"
    payload_path.write_text('[{"Codigo": "LOCAL-1", "Comprador": {"NombreOrganismo": "Entidad demo"}}]', encoding="utf-8")
    calls: dict[str, object] = {}

    class FakeNormalizer:
        def normalize(self, response, query_date=None):  # noqa: ANN001
            calls["response_url"] = response.url
            calls["payload_notice"] = response.payload.get("_datosenorden_notice")
            calls["query_date"] = query_date
            return ("normalized", response)

    class FakeMapper:
        def map_purchase_orders(self, normalized):  # noqa: ANN001
            calls["normalized"] = normalized
            return SimpleNamespace(
                raw_count=1,
                rejected_count=0,
                entities=("entity",),
                claims=("claim",),
                evidence=("evidence",),
                public_relationships=("relationship",),
                errors=(),
            )

    class FakeGraphLoader:
        def __init__(self, session):  # noqa: ANN001
            calls["session"] = session

        def load(self, batch, dry_run=False):  # noqa: ANN001
            calls["dry_run"] = dry_run
            calls["batch"] = batch
            return SimpleNamespace(id="job-1")

    monkeypatch.setattr(module, "SessionLocal", lambda: _SessionContext())
    monkeypatch.setattr(module, "ChileCompraNormalizer", FakeNormalizer)
    monkeypatch.setattr(module, "ChileCompraGraphMapper", FakeMapper)
    monkeypatch.setattr(module, "GraphLoader", FakeGraphLoader)

    exit_code = module.main([str(payload_path), "--dry-run"])

    output = capsys.readouterr().out
    assert exit_code == 0
    assert calls["dry_run"] is True
    assert calls["payload_notice"] == "LOCAL_TEST_DATA / NOT_OFFICIAL_DATA unless the operator verifies the source."
    assert "records=1" in output
    assert "import_job_id=job-1" in output
