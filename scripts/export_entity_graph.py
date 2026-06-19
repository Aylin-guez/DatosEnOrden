from argparse import ArgumentParser
from pathlib import Path
import sys
from typing import Sequence

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from datosenorden.db.session import SessionLocal
from datosenorden.maintenance.entity_explorer import build_entity_graph
from datosenorden.maintenance.entity_explorer import render_entity_graph_html

GRAPH_EXPORTS_DIR = Path("graph_exports")


def parse_args(argv: Sequence[str] | None = None):
    parser = ArgumentParser(description="Export a persisted entity graph as HTML")
    parser.add_argument("--entity-id", required=True, help="Entity UUID")
    parser.add_argument(
        "--depth",
        type=int,
        default=1,
        help="Traversal depth for the exported graph (default: 1)",
    )
    parser.add_argument(
        "--output",
        help="Output HTML path. Defaults to graph_exports/entity_<entity-id>.html",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    output_path = Path(args.output) if args.output else GRAPH_EXPORTS_DIR / f"entity_{args.entity_id}.html"

    try:
        with SessionLocal() as session:
            root = build_entity_graph(session, args.entity_id, depth=args.depth)
    except Exception as exc:  # noqa: BLE001
        print("No se pudo exportar el grafo de la entidad.", file=sys.stderr)
        print(f"Detalle: {exc}", file=sys.stderr)
        return 1

    if root is None:
        print(f"No se encontro entity_id={args.entity_id}", file=sys.stderr)
        return 1

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(render_entity_graph_html(root, args.depth), encoding="utf-8")
    print(f"entity_graph_exported: path={output_path.as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
