from argparse import ArgumentParser
from pathlib import Path
import sys
from typing import Sequence

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from datosenorden.db.session import SessionLocal
from datosenorden.maintenance.cross_dataset_demo import debug_cross_dataset_matches
from datosenorden.maintenance.cross_dataset_demo import render_cross_dataset_match_diagnostic_text


def parse_args(argv: Sequence[str] | None = None):
    parser = ArgumentParser(description="Diagnose ChileCompra <-> Lobby organization matching")
    parser.add_argument("--candidate-limit", type=int, default=3, help="Closest candidates per Lobby organization")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)

    try:
        with SessionLocal() as session:
            diagnostic = debug_cross_dataset_matches(session, candidate_limit=args.candidate_limit)
    except Exception as exc:  # noqa: BLE001
        print("No se pudo diagnosticar la exploracion entre fuentes.", file=sys.stderr)
        print(f"Detalle: {exc}", file=sys.stderr)
        return 1

    print(render_cross_dataset_match_diagnostic_text(diagnostic))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
