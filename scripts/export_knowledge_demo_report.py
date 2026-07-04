from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from datosenorden.maintenance.knowledge_engine import export_knowledge_demo_report


def main() -> int:
    report_path = export_knowledge_demo_report()
    print("knowledge_demo_report:")
    print(f"  path={report_path}")
    print(f"  exists={Path(report_path).exists()}")
    return 0 if Path(report_path).exists() else 1


if __name__ == "__main__":
    raise SystemExit(main())
