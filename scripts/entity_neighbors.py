from argparse import ArgumentParser
from pathlib import Path
import sys
from typing import Sequence

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from datosenorden.db.session import SessionLocal
from datosenorden.maintenance.entity_explorer import get_entity_profile
from datosenorden.maintenance.entity_explorer import render_entity_neighbors_text


def parse_args(argv: Sequence[str] | None = None):
    parser = ArgumentParser(description="Inspect direct neighbors for a persisted entity")
    parser.add_argument("--entity-id", required=True, help="Entity UUID")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)

    try:
        with SessionLocal() as session:
            profile = get_entity_profile(session, args.entity_id)
    except Exception as exc:  # noqa: BLE001
        print("No se pudo leer los vecinos de la entidad.", file=sys.stderr)
        print(f"Detalle: {exc}", file=sys.stderr)
        return 1

    if profile is None:
        print(f"No se encontro entity_id={args.entity_id}", file=sys.stderr)
        return 1

    print(render_entity_neighbors_text(profile.entity, profile.direct_neighbors))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
