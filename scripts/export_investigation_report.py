from __future__ import annotations

from argparse import ArgumentParser
from pathlib import Path
from typing import Sequence
import sys

from sqlalchemy import select

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from datosenorden.db.session import SessionLocal
from datosenorden.maintenance.entity_matching import match_entity_candidates
from datosenorden.maintenance.investigation_report import export_investigation_report
from datosenorden.models import Entity


def _build_parser() -> ArgumentParser:
    parser = ArgumentParser(description="Export a citizen-facing investigation report as HTML")
    parser.add_argument("entity_name", help="Entity name to resolve and export")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)

    try:
        entity_id, entity_name, entity_type = _resolve_entity(args.entity_name)
        output_path = export_investigation_report(entity_id)
    except Exception as exc:  # noqa: BLE001
        print("No se pudo exportar la investigacion.", file=sys.stderr)
        print(f"Detalle: {exc}", file=sys.stderr)
        return 1

    print(f"exported: {output_path}")
    print(f"entity: {entity_name} ({entity_type})")
    return 0


def _resolve_entity(entity_name: str) -> tuple[str, str, str]:
    with SessionLocal() as session:
        entity_types = session.scalars(select(Entity.entity_type).distinct().order_by(Entity.entity_type.asc())).all()
        candidates = []
        for entity_type in entity_types:
            candidates.extend(
                match_entity_candidates(session, entity_type=str(entity_type), name=entity_name, limit=1)
            )

    if not candidates:
        raise LookupError(f"No entity matched name={entity_name!r}")

    best = sorted(
        candidates,
        key=lambda item: (-item.score, item.candidate_name.lower(), item.candidate_entity_id),
    )[0]
    return best.candidate_entity_id, best.candidate_name, best.entity_type


if __name__ == "__main__":
    raise SystemExit(main())
