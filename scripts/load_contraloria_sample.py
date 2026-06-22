from argparse import ArgumentParser
from pathlib import Path
import sys
from typing import Sequence

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from datosenorden.db.session import SessionLocal
from datosenorden.maintenance.contraloria_prototype import CONTRALORIA_SAMPLE_PATH
from datosenorden.maintenance.contraloria_prototype import persist_contraloria_sample
from datosenorden.maintenance.contraloria_prototype import render_contraloria_import_result_text


def parse_args(argv: Sequence[str] | None = None):
    parser = ArgumentParser(description="Load the local Contraloria sample")
    parser.add_argument(
        "--input",
        type=Path,
        default=CONTRALORIA_SAMPLE_PATH,
        help="Path to the local Contraloria sample JSON file",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)

    try:
        with SessionLocal() as session:
            result = persist_contraloria_sample(session, args.input)
    except Exception as exc:  # noqa: BLE001
        print("No se pudo cargar el sample Contraloria.", file=sys.stderr)
        print(f"Detalle: {exc}", file=sys.stderr)
        return 1

    print(render_contraloria_import_result_text(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
