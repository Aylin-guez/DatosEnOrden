from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from datosenorden.web.app_services import export_citizen_report_demo


def main() -> int:
    path = export_citizen_report_demo()
    print("citizen_report_export:")
    print(f"  path={path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
