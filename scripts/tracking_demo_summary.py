from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from datosenorden.maintenance.tracking import build_tracking_demo
from datosenorden.maintenance.tracking import render_tracking_demo_summary


def main() -> int:
    print(render_tracking_demo_summary(build_tracking_demo()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
