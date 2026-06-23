from argparse import ArgumentParser
from pathlib import Path
import sys
from typing import Sequence

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from datosenorden.db.session import SessionLocal
from datosenorden.maintenance.registro_empresas_prototype import REGISTRO_SAMPLE_PATH
from datosenorden.maintenance.registro_empresas_prototype import load_registro_empresas_sample
from datosenorden.maintenance.registro_empresas_prototype import render_registro_empresas_import_result_text


def parse_args(argv: Sequence[str] | None = None):
    parser = ArgumentParser(description="Load the local Registro Empresas sample")
    parser.add_argument(
        "--input",
        type=Path,
        default=REGISTRO_SAMPLE_PATH,
        help="Path to the local Registro Empresas sample JSON file",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)

    try:
        with SessionLocal() as session:
            result = load_registro_empresas_sample(session, args.input)
    except Exception as exc:  # noqa: BLE001
        print("No se pudo cargar el sample Registro Empresas.", file=sys.stderr)
        print(f"Detalle: {exc}", file=sys.stderr)
        return 1

    print(render_registro_empresas_import_result_text(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
