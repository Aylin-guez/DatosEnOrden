from argparse import ArgumentParser
from pathlib import Path
import sys
from typing import Sequence

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from datosenorden.db.session import SessionLocal
from datosenorden.maintenance.trace_graph_export import render_trace_graph_html
from datosenorden.maintenance.traceability_inspector import inspect_traceability_chain
from datosenorden.maintenance.traceability_inspector import summarize_traceability_chain


def parse_args(argv: Sequence[str] | None = None):
    parser = ArgumentParser(description="Export a persisted ChileCompra trace graph to HTML")
    parser.add_argument("--external-id", required=True, help="Purchase order external id")
    parser.add_argument(
        "--output",
        help="Output HTML path. Defaults to graph_exports/<external-id>.html",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    output_path = Path(args.output) if args.output else Path("graph_exports") / f"{args.external_id}.html"

    try:
        with SessionLocal() as session:
            traces = inspect_traceability_chain(session, args.external_id)
    except Exception as exc:  # noqa: BLE001
        print("No se pudo exportar el grafo persistido.", file=sys.stderr)
        print(f"Detalle: {exc}", file=sys.stderr)
        return 1

    if not traces:
        print(
            f"No se encontro source_record persistido para external_id={args.external_id}",
            file=sys.stderr,
        )
        return 1

    html = render_trace_graph_html(summarize_traceability_chain(traces), args.external_id)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")
    print(f"graph_export: wrote {output_path.as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
