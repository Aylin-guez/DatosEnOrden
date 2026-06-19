from pathlib import Path
import sys
from typing import Sequence

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from datosenorden.db.session import SessionLocal
from datosenorden.maintenance.dataset_metrics import read_dataset_summary
from datosenorden.maintenance.dataset_metrics import render_dataset_summary


def main(argv: Sequence[str] | None = None) -> int:
    _ = argv

    try:
        with SessionLocal() as session:
            summary = read_dataset_summary(session)
    except Exception as exc:  # noqa: BLE001
        print("No se pudo leer el resumen del dataset.", file=sys.stderr)
        print(f"Detalle: {exc}", file=sys.stderr)
        return 1

    print(render_dataset_summary(summary))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
