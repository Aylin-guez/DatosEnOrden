from __future__ import annotations

from pathlib import Path
import subprocess
import sys
from typing import Sequence

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from datosenorden.core.config import PROJECT_ROOT
from datosenorden.db.session import SessionLocal
from datosenorden.maintenance.demo_pack import build_demo_seed_result
from datosenorden.maintenance.demo_pack import render_demo_seed_text
from datosenorden.maintenance.demo_pack import seed_demo_data


def _run_alembic_upgrade() -> None:
    subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=PROJECT_ROOT,
        check=True,
    )


def main(argv: Sequence[str] | None = None) -> int:
    _ = argv

    try:
        _run_alembic_upgrade()
        with SessionLocal() as session:
            seed_demo_data(session)
            result = build_demo_seed_result(session)
    except Exception as exc:  # noqa: BLE001
        print("No se pudo completar el pack de demo.", file=sys.stderr)
        print(f"Detalle: {exc}", file=sys.stderr)
        return 1

    print(render_demo_seed_text(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
