from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from datosenorden.adapters.legislature import LegislativeAdapter
from datosenorden.adapters.legislature.parser import normalize_bulletin_id
from datosenorden.db.session import SessionLocal
from datosenorden.etl.core.contracts import GraphBatch
from datosenorden.etl.loaders.graph_loader import GraphLoader


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Load one official Congress bulletin into the DatosEnOrden graph.",
    )
    parser.add_argument("bulletin", nargs="?", help="Congress bulletin id, for example 8575-05.")
    parser.add_argument("--bill", dest="bill", help="Congress bulletin id, for example 8575-05.")
    parser.add_argument("--dry-run", action="store_true", help="Build and validate the graph without committing rows.")
    args = parser.parse_args(argv)

    try:
        bulletin_id = _resolve_bulletin_arg(args.bulletin, args.bill)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    try:
        batch = LegislativeAdapter().load_bill(bulletin_id)
    except Exception as exc:  # noqa: BLE001
        print(f"error: failed to build legislative graph batch: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1

    _print_batch_preview(batch, dry_run=args.dry_run)

    import_job_id = ""
    with SessionLocal() as session:
        try:
            import_job = GraphLoader(session).load(batch, dry_run=args.dry_run)
            if import_job is not None:
                import_job_id = str(import_job.id)
        except Exception as exc:  # noqa: BLE001
            print(f"error: failed to load legislative graph batch: {type(exc).__name__}: {exc}", file=sys.stderr)
            return 1

    print("load_legislative_bill:")
    print(f"  bulletin={bulletin_id}")
    print(f"  dry_run={args.dry_run}")
    print(f"  loaded={not args.dry_run}")
    print(f"  import_job_id={import_job_id}")
    return 0


def _resolve_bulletin_arg(positional: str | None, named: str | None) -> str:
    if positional and named and normalize_bulletin_id(positional) != normalize_bulletin_id(named):
        raise ValueError("provide the bulletin either positionally or with --bill, not both with different values")
    value = named or positional
    if not value:
        raise ValueError("bulletin id is required")
    return normalize_bulletin_id(value)


def _print_batch_preview(batch: GraphBatch, *, dry_run: bool) -> None:
    item_limit = 20
    print("legislative_bill_preview:")
    print(f"  source={batch.source.name}")
    print(f"  dataset={batch.dataset.name}")
    print(f"  dataset_version={batch.dataset.version}")
    print(f"  dry_run={dry_run}")
    print(f"  raw_records={batch.raw_count}")
    print(f"  rejected={batch.rejected_count}")
    print(f"  entidades_creadas={len(batch.entities)}")
    for entity in batch.entities[:item_limit]:
        print(f"    - {entity.entity_type.value}: {entity.external_id} | {entity.name}")
    print(f"  claims_creados={len(batch.claims)}")
    for claim in batch.claims[:item_limit]:
        print(f"    - {claim.predicate}: {claim.subject_entity.external_id}")
    if len(batch.claims) > item_limit:
        print(f"    - ... {len(batch.claims) - item_limit} mas")
    print(f"  source_records={len(batch.source_records)}")
    for record in batch.source_records[:item_limit]:
        print(f"    - {record.record_type}: {record.external_id}")
    if len(batch.source_records) > item_limit:
        print(f"    - ... {len(batch.source_records) - item_limit} mas")
    print(f"  documentos_encontrados={len(batch.evidence)}")
    for evidence in batch.evidence[:item_limit]:
        print(f"    - {evidence.title} | {evidence.url}")
    if len(batch.evidence) > item_limit:
        print(f"    - ... {len(batch.evidence) - item_limit} mas")
    if batch.errors:
        print("  errors:")
        for error in batch.errors:
            print(f"    - {error}")


if __name__ == "__main__":
    raise SystemExit(main())
