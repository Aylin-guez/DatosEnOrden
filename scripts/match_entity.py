from argparse import ArgumentParser
from pathlib import Path
import sys
from typing import Sequence

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from datosenorden.db.session import SessionLocal
from datosenorden.maintenance.entity_matching import match_entity_candidates
from datosenorden.maintenance.entity_matching import render_entity_match_candidates_text


def parse_args(argv: Sequence[str] | None = None):
    parser = ArgumentParser(description="Rank persisted entity matches for a new source entity")
    parser.add_argument("--type", dest="entity_type", required=True, help="Entity type, for example PUBLIC_ORGANIZATION")
    parser.add_argument("--name", required=True, help="Source entity name to match")
    parser.add_argument("--limit", type=int, default=10, help="Maximum number of ranked candidates (default: 10)")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)

    try:
        with SessionLocal() as session:
            candidates = match_entity_candidates(
                session,
                entity_type=args.entity_type,
                name=args.name,
                limit=args.limit,
            )
    except Exception as exc:  # noqa: BLE001
        print("No se pudo ejecutar el matcher de entidades.", file=sys.stderr)
        print(f"Detalle: {exc}", file=sys.stderr)
        return 1

    print(
        render_entity_match_candidates_text(
            entity_type=args.entity_type,
            name=args.name,
            candidates=candidates,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
