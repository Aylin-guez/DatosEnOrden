from pathlib import Path
import sys
from typing import Sequence

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from datosenorden.db.session import SessionLocal
from datosenorden.maintenance.dipres_prototype import read_budget_summary
from datosenorden.maintenance.dipres_prototype import render_budget_summary_text


def main(argv: Sequence[str] | None = None) -> int:
    _ = argv

    try:
        with SessionLocal() as session:
            rows = read_budget_summary(session)
    except Exception as exc:  # noqa: BLE001
        print("No se pudo resumir el presupuesto DIPRES.", file=sys.stderr)
        print(f"Detalle: {exc}", file=sys.stderr)
        return 1

    print(render_budget_summary_text(rows))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
