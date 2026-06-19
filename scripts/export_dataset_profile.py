from argparse import ArgumentParser
from pathlib import Path
import sys
from typing import Sequence

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from datosenorden.db.session import SessionLocal
from datosenorden.maintenance.dataset_registry import get_dataset_details
from datosenorden.maintenance.dataset_registry import render_dataset_profile_html

DEFAULT_OUTPUT_DIR = Path("reports")


def _build_parser() -> ArgumentParser:
    parser = ArgumentParser(description="Export a dataset profile HTML report")
    parser.add_argument("--dataset", required=True, help="Dataset slug, alias, or name")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)

    try:
        with SessionLocal() as session:
            details = get_dataset_details(session, args.dataset)
        if details is None:
            print(f"Dataset no encontrado: {args.dataset}", file=sys.stderr)
            return 1

        output_path = DEFAULT_OUTPUT_DIR / f"dataset_{details.slug}.html"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(render_dataset_profile_html(details), encoding="utf-8")
    except Exception as exc:  # noqa: BLE001
        print("No se pudo exportar el perfil del dataset.", file=sys.stderr)
        print(f"Detalle: {exc}", file=sys.stderr)
        return 1

    print(f"dataset_profile_exported: path={output_path.as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
