from __future__ import annotations

import importlib.util
from pathlib import Path


def _load_script_module():
    script_path = Path(__file__).resolve().parents[1] / "scripts" / "validate_chilecompra_file.py"
    spec = importlib.util.spec_from_file_location("validate_chilecompra_file", script_path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_validate_chilecompra_file_accepts_minimal_json(tmp_path, capsys) -> None:
    module = _load_script_module()
    path = tmp_path / "oc.json"
    path.write_text(
        """
        {
          "Listado": [
            {
              "Codigo": "OC-1",
              "Comprador": {"CodigoOrganismo": "B1", "NombreOrganismo": "Comprador demo"},
              "Proveedor": {"CodigoEmpresa": "S1", "NombreEmpresa": "Proveedor demo"}
            }
          ]
        }
        """,
        encoding="utf-8",
    )

    assert module.main([str(path)]) == 0
    output = capsys.readouterr().out
    assert "records=1" in output
    assert "usable_records=1" in output
    assert "status=ok" in output


def test_validate_chilecompra_file_rejects_unusable_json(tmp_path, capsys) -> None:
    module = _load_script_module()
    path = tmp_path / "bad.json"
    path.write_text('{"Listado": [{"Nombre": "Sin codigo"}]}', encoding="utf-8")

    assert module.main([str(path)]) == 1
    output = capsys.readouterr().out
    assert "status=invalid" in output
    assert "missing_fields:" in output
