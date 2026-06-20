from argparse import ArgumentParser
from pathlib import Path
import sys
from typing import Sequence

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from datosenorden.db.session import SessionLocal
from datosenorden.maintenance.timeline_explorer import build_entity_timeline
from datosenorden.maintenance.timeline_explorer import render_entity_timeline_html

REPORTS_DIR = Path("reports")


def parse_args(argv: Sequence[str] | None = None):
    parser = ArgumentParser(description="Export an entity timeline as HTML")
    parser.add_argument("--entity-id", required=True, help="Entity UUID")
    parser.add_argument(
        "--output",
        help="Output HTML path. Defaults to reports/entity_timeline_<entity-id>.html",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    output_path = Path(args.output) if args.output else REPORTS_DIR / f"entity_timeline_{args.entity_id}.html"

    try:
        with SessionLocal() as session:
            timeline = build_entity_timeline(session, args.entity_id)
    except Exception as exc:  # noqa: BLE001
        print("No se pudo exportar la cronologia de la entidad.", file=sys.stderr)
        print(f"Detalle: {exc}", file=sys.stderr)
        return 1

    if timeline is None:
        print(f"No se encontro entity_id={args.entity_id}", file=sys.stderr)
        return 1

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(render_entity_timeline_html(timeline), encoding="utf-8")
    print(f"entity_timeline_exported: path={output_path.as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
