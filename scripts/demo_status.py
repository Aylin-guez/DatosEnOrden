from __future__ import annotations

from pathlib import Path
import sys
from typing import Sequence

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from datosenorden.db.session import SessionLocal
from datosenorden.maintenance.demo_pack import build_demo_status
from datosenorden.maintenance.demo_pack import render_demo_status_text


def main(argv: Sequence[str] | None = None) -> int:
    _ = argv

    try:
        with SessionLocal() as session:
            report = build_demo_status(session)
    except Exception as exc:  # noqa: BLE001
        print("DatosEnOrden demo status")
        print()
        print("Ready:")
        print("- none")
        print()
        print("Missing:")
        print("- database connected")
        print("Run:")
        print("  check DATABASE_URL and PostgreSQL, then rerun python scripts/demo_seed.py")
        print(f"Detalle: {exc}", file=sys.stderr)
        return 1

    print(render_demo_status_text(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
