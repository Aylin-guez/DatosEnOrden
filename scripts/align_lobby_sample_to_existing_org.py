from argparse import ArgumentParser
from pathlib import Path
import sys
from typing import Sequence

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from datosenorden.db.session import SessionLocal
from datosenorden.maintenance.cross_dataset_demo import align_lobby_sample_to_existing_org
from datosenorden.maintenance.cross_dataset_demo import render_lobby_sample_alignment_text
from datosenorden.maintenance.lobby_prototype import LOBBY_SAMPLE_PATH


def parse_args(argv: Sequence[str] | None = None):
    parser = ArgumentParser(description="Align the local Lobby sample to an existing ChileCompra organization")
    parser.add_argument(
        "--sample-path",
        type=Path,
        default=LOBBY_SAMPLE_PATH,
        help="Path to the local Lobby sample JSON file",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)

    try:
        with SessionLocal() as session:
            result = align_lobby_sample_to_existing_org(session, sample_path=args.sample_path)
    except Exception as exc:  # noqa: BLE001
        print("No se pudo alinear el sample local de Lobby.", file=sys.stderr)
        print(f"Detalle: {exc}", file=sys.stderr)
        return 1

    print(render_lobby_sample_alignment_text(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
