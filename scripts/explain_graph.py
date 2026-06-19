from argparse import ArgumentParser
from pathlib import Path
import sys
from typing import Sequence

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from datosenorden.db.session import SessionLocal
from datosenorden.maintenance.entity_explorer import build_entity_graph
from datosenorden.maintenance.human_readable import explain_graph
from datosenorden.maintenance.human_readable import render_graph_explanation_text


def _build_parser() -> ArgumentParser:
    parser = ArgumentParser(description="Explain an entity graph in plain language")
    parser.add_argument("--entity-id", required=True, help="Entity UUID")
    parser.add_argument("--depth", type=int, default=3, help="Traversal depth (default: 3)")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)

    try:
        with SessionLocal() as session:
            graph = build_entity_graph(session, args.entity_id, depth=args.depth)
    except Exception as exc:  # noqa: BLE001
        print("No se pudo explicar el grafo.", file=sys.stderr)
        print(f"Detalle: {exc}", file=sys.stderr)
        return 1

    if graph is None:
        print(f"No se encontro entity_id={args.entity_id}", file=sys.stderr)
        return 1

    print(render_graph_explanation_text(explain_graph(graph)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
