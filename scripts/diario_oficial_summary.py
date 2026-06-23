from pathlib import Path
import sys
from typing import Sequence

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from datosenorden.db.session import SessionLocal
from datosenorden.maintenance.diario_oficial_prototype import read_diario_oficial_summary
from datosenorden.maintenance.diario_oficial_prototype import render_diario_oficial_summary_text


def main(argv: Sequence[str] | None = None) -> int:
    _ = argv

    try:
        with SessionLocal() as session:
            summary = read_diario_oficial_summary(session)
    except Exception as exc:  # noqa: BLE001
        print("No se pudo resumir el sample Diario Oficial.", file=sys.stderr)
        print(f"Detalle: {exc}", file=sys.stderr)
        return 1

    print(render_diario_oficial_summary_text(summary))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
