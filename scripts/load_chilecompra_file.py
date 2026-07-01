from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from datosenorden.db.session import SessionLocal
from datosenorden.etl.chilecompra.client import ApiResponse
from datosenorden.etl.chilecompra.mappers import ChileCompraGraphMapper
from datosenorden.etl.chilecompra.normalizers import ChileCompraNormalizer
from datosenorden.etl.loaders.graph_loader import GraphLoader


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Load a local ChileCompra JSON export into the current graph schema.")
    parser.add_argument("path", help="Local JSON file with a ChileCompra-like payload or a list of purchase order records.")
    parser.add_argument("--dry-run", action="store_true", help="Map and validate without committing rows.")
    parser.add_argument("--query-date", default="", help="Optional YYYY-MM-DD date used as dataset version.")
    args = parser.parse_args(argv)

    payload_path = Path(args.path)
    payload = json.loads(payload_path.read_text(encoding="utf-8"))
    if isinstance(payload, list):
        payload = {"Listado": payload, "Version": "LOCAL_TEST_DATA", "FechaCreacion": ""}
    if not isinstance(payload, dict):
        raise SystemExit("Expected a JSON object or list of purchase order records.")
    payload.setdefault("Listado", [])
    payload.setdefault("_datosenorden_notice", "LOCAL_TEST_DATA / NOT_OFFICIAL_DATA unless the operator verifies the source.")

    query_date = date.fromisoformat(args.query_date) if args.query_date else None
    response = ApiResponse(url=f"local://chilecompra-file/{payload_path.name}", params={"source": str(payload_path)}, payload=payload)
    normalized = ChileCompraNormalizer().normalize(response, query_date=query_date)
    batch = ChileCompraGraphMapper().map_purchase_orders(normalized)

    with SessionLocal() as session:
        job = GraphLoader(session).load(batch, dry_run=args.dry_run)

    print("load_chilecompra_file:")
    print(f"  source={payload_path}")
    print(f"  dry_run={args.dry_run}")
    print(f"  records={batch.raw_count}")
    print(f"  rejected={batch.rejected_count}")
    print(f"  entities={len(batch.entities)}")
    print(f"  claims={len(batch.claims)}")
    print(f"  evidence={len(batch.evidence)}")
    print(f"  relationships={len(batch.public_relationships)}")
    print(f"  import_job_id={getattr(job, 'id', '') if job is not None else ''}")
    if batch.errors:
        print("  errors:")
        for error in batch.errors:
            print(f"    - {error}")
    return 1 if batch.errors and not batch.claims else 0


if __name__ == "__main__":
    raise SystemExit(main())
