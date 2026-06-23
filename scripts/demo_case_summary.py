from argparse import ArgumentParser
from pathlib import Path
import sys
from typing import Sequence

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from datosenorden.maintenance.complete_demo_case import COMPLETE_DEMO_CASE_PATH
from datosenorden.maintenance.complete_demo_case import build_complete_demo_case_summary
from datosenorden.maintenance.complete_demo_case import load_complete_demo_case_payload
from datosenorden.maintenance.complete_demo_case import render_complete_demo_case_summary_text


def parse_args(argv: Sequence[str] | None = None):
    parser = ArgumentParser(description="Summarize the complete SERVICIO DE SALUD ARAUCO demo case")
    parser.add_argument(
        "--input",
        type=Path,
        default=COMPLETE_DEMO_CASE_PATH,
        help="Path to the complete demo case JSON file",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)

    try:
        payload = load_complete_demo_case_payload(args.input)
        summary = build_complete_demo_case_summary(payload)
    except Exception as exc:  # noqa: BLE001
        print("No se pudo resumir el caso demo completo.", file=sys.stderr)
        print(f"Detalle: {exc}", file=sys.stderr)
        return 1

    print(render_complete_demo_case_summary_text(summary))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
