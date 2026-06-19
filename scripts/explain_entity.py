from argparse import ArgumentParser
from pathlib import Path
import sys
from typing import Sequence

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from datosenorden.db.session import SessionLocal
from datosenorden.maintenance.human_readable import explain_entity
from datosenorden.maintenance.human_readable import render_entity_explanation_text


def _build_parser() -> ArgumentParser:
    parser = ArgumentParser(description="Explain an entity in plain language")
    parser.add_argument("--entity-id", required=True, help="Entity UUID")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)

    try:
        with SessionLocal() as session:
            explanation = explain_entity(session, args.entity_id)
    except Exception as exc:  # noqa: BLE001
        print("No se pudo explicar la entidad.", file=sys.stderr)
        print(f"Detalle: {exc}", file=sys.stderr)
        return 1

    if explanation is None:
        print(f"No se encontro entity_id={args.entity_id}", file=sys.stderr)
        return 1

    print(render_entity_explanation_text(explanation))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
