from argparse import ArgumentParser
from pathlib import Path
import sys
from typing import Sequence

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from datosenorden.db.session import SessionLocal
from datosenorden.maintenance.entity_explorer import build_entity_graph
from datosenorden.maintenance.entity_explorer import render_entity_graph_text


def parse_args(argv: Sequence[str] | None = None):
    parser = ArgumentParser(description="Traverse a persisted entity graph")
    parser.add_argument("--entity-id", required=True, help="Entity UUID")
    parser.add_argument("--depth", type=int, default=1, help="Traversal depth (default: 1)")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)

    try:
        with SessionLocal() as session:
            root = build_entity_graph(session, args.entity_id, depth=args.depth)
    except Exception as exc:  # noqa: BLE001
        print("No se pudo recorrer el grafo de la entidad.", file=sys.stderr)
        print(f"Detalle: {exc}", file=sys.stderr)
        return 1

    if root is None:
        print(f"No se encontro entity_id={args.entity_id}", file=sys.stderr)
        return 1

    print(render_entity_graph_text(root, args.depth))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
