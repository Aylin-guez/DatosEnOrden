from __future__ import annotations

import ast
from dataclasses import FrozenInstanceError, MISSING, dataclass, fields, is_dataclass
from datetime import date, datetime
from enum import Enum, IntEnum
import json
import os
from pathlib import Path
import subprocess
import sys
from types import MappingProxyType
from uuid import UUID

import pytest

from reflex_app.models.document import PDFHighlightTarget
from reflex_app.serialization.json_safe import _json_dict, _json_list, to_json_safe


class _Status(Enum):
    READY = "ready"


class _Priority(IntEnum):
    HIGH = 2


@dataclass
class _NestedPayload:
    label: str
    observed_at: date


class _Dumpable:
    def model_dump(self) -> dict[str, object]:
        return {
            "identifier": UUID("00000000-0000-0000-0000-000000000007"),
            "values": (1, 2),
        }


class _BrokenDumpable:
    def model_dump(self) -> dict:
        raise RuntimeError("current fallback contract")

    def __str__(self) -> str:
        return "broken-dumpable"


class _PublicAttributes:
    def __init__(self) -> None:
        self.visible = _NestedPayload("visible", date(2026, 7, 16))
        self._private = "hidden"
        self.callback = lambda: None


class _Opaque:
    __slots__ = ()

    def __str__(self) -> str:
        return "opaque-value"


def test_pdf_highlight_target_preserves_frozen_dataclass_contract() -> None:
    target = PDFHighlightTarget("fragment-7", 3, "Texto citado")
    equivalent = PDFHighlightTarget("fragment-7", 3, "Texto citado")
    field_specs = fields(PDFHighlightTarget)

    assert is_dataclass(PDFHighlightTarget)
    assert PDFHighlightTarget.__dataclass_params__.frozen is True
    assert [(field.name, field.default) for field in field_specs] == [
        ("fragment_id", MISSING),
        ("page", MISSING),
        ("text_snippet", MISSING),
        ("coordinates", None),
    ]
    assert target.coordinates is None
    assert target == equivalent
    assert hash(target) == hash(equivalent)
    with pytest.raises(FrozenInstanceError):
        target.page = 4
    assert target.to_dict() == {
        "fragment_id": "fragment-7",
        "page": 3,
        "text_snippet": "Texto citado",
        "coordinates": None,
    }
    assert json.loads(json.dumps(target.to_dict())) == target.to_dict()


def test_to_json_safe_preserves_primitives_dates_enums_and_nested_structures() -> None:
    payload = {
        "none": None,
        "bool": True,
        "int": 7,
        "float": 3.5,
        "str": "texto",
        "tuple": ("uno", 2),
        "list": [False, {"nested": _NestedPayload("dato", date(2026, 7, 16))}],
        "date": date(2026, 7, 16),
        "datetime": datetime(2026, 7, 16, 12, 30, 45),
        "uuid": UUID("00000000-0000-0000-0000-000000000001"),
        "enum": _Status.READY,
        "int_enum": _Priority.HIGH,
    }

    assert to_json_safe(payload) == {
        "none": None,
        "bool": True,
        "int": 7,
        "float": 3.5,
        "str": "texto",
        "tuple": ["uno", 2],
        "list": [False, {"nested": {"label": "dato", "observed_at": "2026-07-16"}}],
        "date": "2026-07-16",
        "datetime": "2026-07-16 12:30:45",
        "uuid": "00000000-0000-0000-0000-000000000001",
        "enum": str(_Status.READY),
        "int_enum": 2,
    }


def test_to_json_safe_preserves_mapping_dumpable_public_and_unknown_object_paths() -> None:
    mapping = MappingProxyType({"nested": MappingProxyType({"safe": "yes"})})

    assert to_json_safe(mapping) == {"nested": {"safe": "yes"}}
    assert to_json_safe(_Dumpable()) == {
        "identifier": "00000000-0000-0000-0000-000000000007",
        "values": [1, 2],
    }
    assert to_json_safe(_BrokenDumpable()) == "broken-dumpable"
    assert to_json_safe(_PublicAttributes()) == {
        "visible": {"label": "visible", "observed_at": "2026-07-16"}
    }
    assert to_json_safe(_Opaque()) == "opaque-value"


def test_json_dict_and_list_keep_current_safe_shape_and_fallbacks() -> None:
    assert _json_dict({"target": PDFHighlightTarget("fragment-1", 1, "Texto")}) == {
        "target": {
            "fragment_id": "fragment-1",
            "page": 1,
            "text_snippet": "Texto",
            "coordinates": None,
        }
    }
    assert _json_dict(("not", "a", "dict")) == {}
    assert _json_list((PDFHighlightTarget("fragment-2", 2, "Otro"), "ok")) == [
        {
            "fragment_id": "fragment-2",
            "page": 2,
            "text_snippet": "Otro",
            "coordinates": None,
        },
        "ok",
    ]
    assert _json_list({"not": "a list"}) == []


def test_entrypoint_does_not_reexport_pure_leaf_symbols() -> None:
    entrypoint = __import__("reflex_app.reflex_app", fromlist=["app"])

    assert all(
        not hasattr(entrypoint, name)
        for name in ("PDFHighlightTarget", "to_json_safe", "_json_dict", "_json_list")
    )

def test_pure_leaf_modules_only_import_stdlib_modules() -> None:
    root = Path(__file__).resolve().parents[1]
    module_paths = [
        root / "reflex_app" / "models" / "document.py",
        root / "reflex_app" / "serialization" / "json_safe.py",
    ]
    allowed_roots = {"__future__", "dataclasses", "datetime", "types", "uuid"}

    for module_path in module_paths:
        tree = ast.parse(module_path.read_text(encoding="utf-8"), filename=str(module_path))
        imported_roots = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported_roots.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                assert node.level == 0
                assert node.module is not None
                imported_roots.add(node.module.split(".")[0])

        assert imported_roots <= allowed_roots


def test_fresh_leaf_import_does_not_load_reflex_ui_services_or_private_core() -> None:
    probe = """
import importlib
import json
import sys

document = importlib.import_module(\"reflex_app.models.document\")
serialization = importlib.import_module(\"reflex_app.serialization.json_safe\")
blocked = [
    name for name in sys.modules
    if name == \"reflex\"
    or name.startswith(\"reflex.\")
    or name == \"datosenorden.web\"
    or name.startswith(\"datosenorden.web.\")
    or name == \"deo_core\"
    or name.startswith(\"deo_core.\")
    or name == \"reflex_app.reflex_app\"
]
print(\"PURE_EXTRACTION=\" + json.dumps({
    \"document_module\": document.__name__,
    \"serialization_module\": serialization.__name__,
    \"blocked\": blocked,
}))
"""
    result = subprocess.run(
        [sys.executable, "-c", probe],
        cwd=Path(__file__).resolve().parents[1],
        env=os.environ.copy(),
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    payload_line = next(
        line for line in result.stdout.splitlines() if line.startswith("PURE_EXTRACTION=")
    )
    assert json.loads(payload_line.removeprefix("PURE_EXTRACTION=")) == {
        "document_module": "reflex_app.models.document",
        "serialization_module": "reflex_app.serialization.json_safe",
        "blocked": [],
    }
