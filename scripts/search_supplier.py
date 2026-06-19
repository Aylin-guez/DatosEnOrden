from argparse import ArgumentParser
from pathlib import Path
import sys
from typing import Sequence

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from datosenorden.db.session import SessionLocal
from datosenorden.maintenance.entity_explorer import render_supplier_search
from datosenorden.maintenance.entity_explorer import search_suppliers


def parse_args(argv: Sequence[str] | None = None):
    parser = ArgumentParser(description="Search persisted supplier entities")
    parser.add_argument("query", help="Case-insensitive supplier name search")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)

    try:
        with SessionLocal() as session:
            results = search_suppliers(session, args.query)
    except Exception as exc:  # noqa: BLE001
        print("No se pudo buscar proveedores.", file=sys.stderr)
        print(f"Detalle: {exc}", file=sys.stderr)
        return 1

    print(render_supplier_search(args.query, results))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
