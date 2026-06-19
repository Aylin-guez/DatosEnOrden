from argparse import ArgumentParser
from pathlib import Path
import sys
from typing import Sequence

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from datosenorden.db.session import SessionLocal
from datosenorden.maintenance.entity_explorer import list_entities
from datosenorden.maintenance.entity_explorer import render_entities_list_text


def parse_args(argv: Sequence[str] | None = None):
    parser = ArgumentParser(description="List persisted entities")
    parser.add_argument("--limit", type=int, default=50, help="Maximum rows to list (default: 50)")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)

    try:
        with SessionLocal() as session:
            rows = list_entities(session, limit=args.limit)
    except Exception as exc:  # noqa: BLE001
        print("No se pudo listar entidades.", file=sys.stderr)
        print(f"Detalle: {exc}", file=sys.stderr)
        return 1

    print(render_entities_list_text(rows))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
