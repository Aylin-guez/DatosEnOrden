from pathlib import Path
import sys
from typing import Sequence

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from datosenorden.db.session import SessionLocal
from datosenorden.maintenance.declaraciones_intereses_prototype import read_declaraciones_intereses_summary
from datosenorden.maintenance.declaraciones_intereses_prototype import render_declaraciones_intereses_summary_text


def main(argv: Sequence[str] | None = None) -> int:
    _ = argv

    try:
        with SessionLocal() as session:
            summary = read_declaraciones_intereses_summary(session)
    except Exception as exc:  # noqa: BLE001
        print("No se pudo resumir el sample Declaraciones de Intereses.", file=sys.stderr)
        print(f"Detalle: {exc}", file=sys.stderr)
        return 1

    print(render_declaraciones_intereses_summary_text(summary))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

