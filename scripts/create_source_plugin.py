from __future__ import annotations

from argparse import ArgumentParser
from pathlib import Path
import re
import sys
from typing import Sequence

ROOT = Path(__file__).resolve().parents[1]


def create_source_scaffold(
    source_id: str,
    *,
    display_name: str,
    status: str,
    root: Path = ROOT,
    force: bool = False,
    dry_run: bool = False,
) -> dict[str, str]:
    normalized_id = _normalize_source_id(source_id)
    files = _scaffold_files(normalized_id, display_name=display_name, status=status, root=root)
    results: dict[str, str] = {}
    for path, content in files.items():
        if path.exists() and not force:
            results[str(path)] = "exists"
            continue
        results[str(path)] = "would_write" if dry_run else "written"
        if dry_run:
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    return results


def main(argv: Sequence[str] | None = None) -> int:
    parser = ArgumentParser(description="Create safe local scaffolding for a DatosEnOrden public source plugin")
    parser.add_argument("source_id")
    parser.add_argument("--display-name", required=True)
    parser.add_argument("--status", choices=("active", "prototype", "planned"), default="prototype")
    parser.add_argument("--force", action="store_true", help="Overwrite generated files if they already exist")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be generated without writing files")
    args = parser.parse_args(argv)

    results = create_source_scaffold(
        args.source_id,
        display_name=args.display_name,
        status=args.status,
        force=args.force,
        dry_run=args.dry_run,
    )
    print("source_scaffold:")
    for path, action in results.items():
        print(f"  {action}: {path}")
    if any(action == "exists" for action in results.values()) and not args.force:
        print("  note: existing files were not overwritten; pass --force to replace generated scaffold files")
    return 0


def _scaffold_files(source_id: str, *, display_name: str, status: str, root: Path) -> dict[Path, str]:
    title_constant = source_id.upper()
    return {
        root / "src" / "datosenorden" / "datasets" / source_id / "__init__.py": _dataset_init(source_id, display_name),
        root / "src" / "datosenorden" / "maintenance" / f"{source_id}_prototype.py": _prototype_module(source_id, display_name, title_constant),
        root / "data" / "sample" / f"{source_id}_sample.json": _sample_json(source_id, display_name),
        root / "scripts" / f"load_{source_id}_sample.py": _loader_script(source_id, display_name),
        root / "scripts" / f"{source_id}_summary.py": _summary_script(source_id, display_name),
        root / "tests" / f"test_{source_id}_prototype.py": _test_file(source_id),
        root / "docs" / "sources" / f"{source_id}.md": _docs_file(source_id, display_name, status),
    }


def _dataset_init(source_id: str, display_name: str) -> str:
    return f'''"""Local scaffold dataset for {display_name}.

This package contains only LOCAL_TEST_DATA / NOT_OFFICIAL_DATA scaffolding.
"""

SOURCE_ID = "{source_id}"
DISPLAY_NAME = "{display_name}"
'''


def _prototype_module(source_id: str, display_name: str, title_constant: str) -> str:
    return f'''from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from datosenorden.core.config import PROJECT_ROOT

LOCAL_TEST_DATA = "LOCAL_TEST_DATA"
NOT_OFFICIAL_DATA = "NOT_OFFICIAL_DATA"
{title_constant}_SAMPLE_PATH = PROJECT_ROOT / "data" / "sample" / "{source_id}_sample.json"


def load_{source_id}_sample_payload(input_path: Path | None = None) -> dict[str, Any]:
    path = input_path or {title_constant}_SAMPLE_PATH
    payload = json.loads(path.read_text(encoding="utf-8"))
    validate_{source_id}_sample_payload(payload)
    return payload


def validate_{source_id}_sample_payload(payload: dict[str, Any]) -> None:
    if payload.get("classification") != LOCAL_TEST_DATA:
        raise ValueError("{display_name} sample must be marked LOCAL_TEST_DATA")
    if payload.get("official_status") != NOT_OFFICIAL_DATA:
        raise ValueError("{display_name} sample must be marked NOT_OFFICIAL_DATA")
    if not isinstance(payload.get("records"), list):
        raise ValueError("{display_name} sample must include records")


def render_{source_id}_summary_text(payload: dict[str, Any]) -> str:
    records = payload.get("records", [])
    return "\\n".join([
        "{source_id}_summary:",
        f"  records={{len(records)}}",
        "  status=local scaffold only",
    ])
'''


def _sample_json(source_id: str, display_name: str) -> str:
    return f'''{{
  "classification": "LOCAL_TEST_DATA",
  "official_status": "NOT_OFFICIAL_DATA",
  "source_id": "{source_id}",
  "display_name": "{display_name}",
  "records": []
}}
'''


def _loader_script(source_id: str, display_name: str) -> str:
    return f'''from pathlib import Path
import sys
from typing import Sequence

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from datosenorden.maintenance.{source_id}_prototype import load_{source_id}_sample_payload


def main(argv: Sequence[str] | None = None) -> int:
    _ = argv
    payload = load_{source_id}_sample_payload()
    print("{source_id}_sample_loaded:")
    print(f"  records={{len(payload.get('records', []))}}")
    print("  note=LOCAL_TEST_DATA / NOT_OFFICIAL_DATA scaffold; implement persistence when ready")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''


def _summary_script(source_id: str, display_name: str) -> str:
    return f'''from pathlib import Path
import sys
from typing import Sequence

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from datosenorden.maintenance.{source_id}_prototype import load_{source_id}_sample_payload
from datosenorden.maintenance.{source_id}_prototype import render_{source_id}_summary_text


def main(argv: Sequence[str] | None = None) -> int:
    _ = argv
    print(render_{source_id}_summary_text(load_{source_id}_sample_payload()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''


def _test_file(source_id: str) -> str:
    return f'''from datosenorden.maintenance.{source_id}_prototype import load_{source_id}_sample_payload
from datosenorden.maintenance.{source_id}_prototype import render_{source_id}_summary_text


def test_{source_id}_scaffold_payload_is_marked_local() -> None:
    payload = load_{source_id}_sample_payload()

    assert payload["classification"] == "LOCAL_TEST_DATA"
    assert payload["official_status"] == "NOT_OFFICIAL_DATA"


def test_{source_id}_scaffold_summary_imports() -> None:
    assert "{source_id}_summary:" in render_{source_id}_summary_text({{"records": []}})
'''


def _docs_file(source_id: str, display_name: str, status: str) -> str:
    return f'''# {display_name}

Status: {status}

This is a local DatosEnOrden source scaffold. It uses `LOCAL_TEST_DATA` and `NOT_OFFICIAL_DATA` only.

## TODO

- Define concepts.
- Define relationships.
- Add local sample records.
- Implement loader persistence if needed.
- Add source-specific tests.
'''


def _normalize_source_id(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9_]+", "_", value.strip().lower().replace("-", "_"))
    normalized = re.sub(r"_+", "_", normalized).strip("_")
    if not normalized:
        raise ValueError("source_id cannot be empty")
    return normalized


if __name__ == "__main__":
    raise SystemExit(main())

