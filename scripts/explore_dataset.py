from pathlib import Path
import sys
from typing import Sequence

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from datosenorden.db.session import SessionLocal
from datosenorden.maintenance.dataset_exploration import explore_dataset
from datosenorden.maintenance.dataset_exploration import render_dataset_exploration_text


def main(argv: Sequence[str] | None = None) -> int:
    _ = argv

    try:
        with SessionLocal() as session:
            exploration = explore_dataset(session)
    except Exception as exc:  # noqa: BLE001
        print("No se pudo explorar el dataset.", file=sys.stderr)
        print(f"Detalle: {exc}", file=sys.stderr)
        return 1

    print(render_dataset_exploration_text(exploration))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
