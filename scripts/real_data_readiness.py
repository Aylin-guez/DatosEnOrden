from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from datosenorden.db.session import SessionLocal
from datosenorden.maintenance.dataset_registry import summarize_real_dataset_registry


def main() -> int:
    with SessionLocal() as session:
        report = summarize_real_dataset_registry(session)

    entries = list(report.get("entries", []))
    ready = [entry for entry in entries if entry.get("ready_for_real_data")]
    partial = [entry for entry in entries if str(entry.get("status", "")).startswith("prototype")]
    demo = [entry for entry in entries if entry.get("demo_available")]
    without_loader = [entry for entry in entries if not str(entry.get("loader_script", "")).strip()]

    print("real_data_readiness:")
    _print_group("fuentes listas", ready)
    _print_group("fuentes parciales", partial)
    _print_group("fuentes demo", demo)
    _print_group("fuentes sin loader", without_loader)
    return 0


def _print_group(label: str, rows: list[dict]) -> None:
    print(f"{label}: {len(rows)}")
    for row in rows:
        print(
            "  - "
            f"{row.get('id')}: {row.get('display_name')} | "
            f"status={row.get('status')} | "
            f"records={row.get('source_records', 0)} | "
            f"entities={row.get('entities', 0)} | "
            f"relationships={row.get('relationships', 0)} | "
            f"loader={row.get('loader_script') or 'none'}"
        )


if __name__ == "__main__":
    raise SystemExit(main())
