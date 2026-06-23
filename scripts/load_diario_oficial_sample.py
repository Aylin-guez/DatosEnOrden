from argparse import ArgumentParser
from pathlib import Path
import sys
from typing import Sequence

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from datosenorden.db.session import SessionLocal
from datosenorden.maintenance.diario_oficial_prototype import DIARIO_SAMPLE_PATH
from datosenorden.maintenance.diario_oficial_prototype import load_diario_oficial_sample
from datosenorden.maintenance.diario_oficial_prototype import render_diario_oficial_import_result_text


def parse_args(argv: Sequence[str] | None = None):
    parser = ArgumentParser(description="Load the local Diario Oficial publication sample")
    parser.add_argument(
        "--input",
        type=Path,
        default=DIARIO_SAMPLE_PATH,
        help="Path to the local Diario Oficial sample JSON file",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)

    try:
        with SessionLocal() as session:
            result = load_diario_oficial_sample(session, args.input)
    except Exception as exc:  # noqa: BLE001
        print("No se pudo cargar el sample Diario Oficial.", file=sys.stderr)
        print(f"Detalle: {exc}", file=sys.stderr)
        return 1

    print(render_diario_oficial_import_result_text(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
