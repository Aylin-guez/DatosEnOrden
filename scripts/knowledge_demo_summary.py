from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from datosenorden.maintenance.knowledge_engine import render_knowledge_demo_summary


def main() -> int:
    print(render_knowledge_demo_summary())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
