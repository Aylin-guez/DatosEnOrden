from argparse import ArgumentParser
from pathlib import Path
import sys
from typing import Sequence

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from datosenorden.db.session import SessionLocal
from datosenorden.maintenance.dataset_registry import get_dataset_details
from datosenorden.maintenance.human_readable import explain_dataset
from datosenorden.maintenance.human_readable import render_dataset_explanation_text


def _build_parser() -> ArgumentParser:
    parser = ArgumentParser(description="Explain a dataset in plain language")
    parser.add_argument("--dataset", required=True, help="Dataset slug, alias, or name")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)

    try:
        with SessionLocal() as session:
            details = get_dataset_details(session, args.dataset)
    except Exception as exc:  # noqa: BLE001
        print("No se pudo explicar el dataset.", file=sys.stderr)
        print(f"Detalle: {exc}", file=sys.stderr)
        return 1

    if details is None:
        print(f"Dataset no encontrado: {args.dataset}", file=sys.stderr)
        return 1

    print(render_dataset_explanation_text(explain_dataset(details)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
