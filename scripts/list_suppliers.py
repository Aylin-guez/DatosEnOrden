from pathlib import Path
import sys
from typing import Sequence

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from datosenorden.db.session import SessionLocal
from datosenorden.maintenance.entity_explorer import list_suppliers
from datosenorden.maintenance.entity_explorer import render_suppliers_list_text


def main(argv: Sequence[str] | None = None) -> int:
    _ = argv

    try:
        with SessionLocal() as session:
            rows = list_suppliers(session)
    except Exception as exc:  # noqa: BLE001
        print("No se pudo listar proveedores.", file=sys.stderr)
        print(f"Detalle: {exc}", file=sys.stderr)
        return 1

    print(render_suppliers_list_text(rows))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
