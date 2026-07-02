from __future__ import annotations

import argparse
from pathlib import Path
import sys

from sqlalchemy import func, select

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from datosenorden.adapters.legislature.parser import canonical_bill_id, normalize_bulletin_id
from datosenorden.db.session import SessionLocal
from datosenorden.models import Claim, Dataset, Entity, Evidence, SourceRecord


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify one imported Congress bulletin in the graph database.")
    parser.add_argument("bulletin", nargs="?", help="Congress bulletin id, for example 8575-05.")
    parser.add_argument("--bill", dest="bill", help="Congress bulletin id, for example 8575-05.")
    args = parser.parse_args(argv)

    try:
        bulletin_id = _resolve_bulletin_arg(args.bulletin, args.bill)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    external_id = canonical_bill_id(bulletin_id)
    with SessionLocal() as session:
        entity = session.scalar(
            select(Entity).where(
                Entity.entity_type == "PUBLIC_PROJECT",
                Entity.external_id == external_id,
            )
        )
        dataset = session.scalar(
            select(Dataset).where(
                Dataset.name == "congreso-votaciones-boletin",
                Dataset.version == bulletin_id,
            )
        )
        entity_count = session.scalar(
            select(func.count()).select_from(Entity).where(Entity.external_id == external_id)
        )
        claim_count = 0
        evidence_count = 0
        source_record_count = 0
        document_count = 0
        if entity is not None:
            claim_count = session.scalar(
                select(func.count()).select_from(Claim).where(Claim.subject_entity_id == entity.id)
            ) or 0
        if dataset is not None:
            source_record_count = session.scalar(
                select(func.count()).select_from(SourceRecord).where(SourceRecord.dataset_id == dataset.id)
            ) or 0
            evidence_count = session.scalar(
                select(func.count()).select_from(Evidence).where(Evidence.dataset_id == dataset.id)
            ) or 0
            document_count = evidence_count

    exists = entity is not None and dataset is not None
    resolved = entity is not None and entity.external_id == external_id

    print("verify_legislative_bill:")
    print(f"  bulletin={bulletin_id}")
    print(f"  expected_external_id={external_id}")
    print(f"  exists={exists}")
    print(f"  external_id_resolved={resolved}")
    print(f"  entidades={entity_count or 0}")
    print(f"  claims={claim_count}")
    print(f"  evidencias={evidence_count}")
    print(f"  source_records={source_record_count}")
    print(f"  documentos={document_count}")
    return 0 if exists and resolved else 1


def _resolve_bulletin_arg(positional: str | None, named: str | None) -> str:
    if positional and named and normalize_bulletin_id(positional) != normalize_bulletin_id(named):
        raise ValueError("provide the bulletin either positionally or with --bill, not both with different values")
    value = named or positional
    if not value:
        raise ValueError("bulletin id is required")
    return normalize_bulletin_id(value)


if __name__ == "__main__":
    raise SystemExit(main())
