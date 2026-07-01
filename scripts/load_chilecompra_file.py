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
from datosenorden.etl.core.pipeline import DatasetAdapter
from datosenorden.etl.core.pipeline import DatasetLoadRequest
from datosenorden.etl.core.pipeline import load_dataset


class ChileCompraFileAdapter(DatasetAdapter):
    dataset_id = "chilecompra"

    def validate(self, request: DatasetLoadRequest) -> tuple[str, ...]:
        if request.input_path is None:
            return ("input_path is required",)
        if not request.input_path.exists():
            return (f"file not found: {request.input_path}",)
        if request.input_path.suffix.lower() != ".json":
            return ("expected a .json file",)
        return ()

    def normalize(self, request: DatasetLoadRequest):  # noqa: ANN201
        assert request.input_path is not None
        payload = _read_payload(request.input_path)
        query_date_value = str((request.metadata or {}).get("query_date", ""))
        query_date = date.fromisoformat(query_date_value) if query_date_value else None
        response = ApiResponse(
            url=f"local://chilecompra-file/{request.input_path.name}",
            params={"source": str(request.input_path)},
            payload=payload,
        )
        return ChileCompraNormalizer().normalize(response, query_date=query_date)

    def build_relationships(self, normalized):  # noqa: ANN201
        return ChileCompraGraphMapper().map_purchase_orders(normalized)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Load a local ChileCompra JSON export into the current graph schema.")
    parser.add_argument("path", help="Local JSON file with a ChileCompra-like payload or a list of purchase order records.")
    parser.add_argument("--dry-run", action="store_true", help="Map and validate without committing rows.")
    parser.add_argument("--query-date", default="", help="Optional YYYY-MM-DD date used as dataset version.")
    args = parser.parse_args(argv)

    payload_path = Path(args.path)
    request = DatasetLoadRequest(
        dataset_id="chilecompra",
        input_path=payload_path,
        dry_run=args.dry_run,
        metadata={"query_date": args.query_date} if args.query_date else {},
    )
    adapter = ChileCompraFileAdapter()
    validation_errors = adapter.validate(request)
    if validation_errors:
        for error in validation_errors:
            print(f"error: {error}", file=sys.stderr)
        return 1

    with SessionLocal() as session:
        result = load_dataset(session, adapter, request)

    print("load_chilecompra_file:")
    print(f"  source={payload_path}")
    print(f"  dry_run={args.dry_run}")
    print(f"  records={result.raw_count}")
    print(f"  rejected={result.rejected_count}")
    print(f"  entities={result.entities}")
    print(f"  claims={result.claims}")
    print(f"  evidence={result.evidence}")
    print(f"  relationships={result.relationships}")
    print("  import_job_id=")
    if result.errors:
        print("  errors:")
        for error in result.errors:
            print(f"    - {error}")
    return 1 if result.errors and not result.claims else 0


def _read_payload(payload_path: Path) -> dict:
    payload = json.loads(payload_path.read_text(encoding="utf-8"))
    if isinstance(payload, list):
        payload = {"Listado": payload, "Version": "LOCAL_TEST_DATA", "FechaCreacion": ""}
    if not isinstance(payload, dict):
        raise SystemExit("Expected a JSON object or list of purchase order records.")
    payload.setdefault("Listado", [])
    payload.setdefault("_datosenorden_notice", "LOCAL_TEST_DATA / NOT_OFFICIAL_DATA unless the operator verifies the source.")
    return payload


if __name__ == "__main__":
    raise SystemExit(main())
