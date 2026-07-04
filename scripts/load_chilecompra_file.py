from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from datosenorden.db.session import SessionLocal
from datosenorden.etl.chilecompra.client import ApiResponse
from datosenorden.etl.chilecompra.mappers import ChileCompraGraphMapper
from datosenorden.etl.chilecompra.normalizers import ChileCompraNormalizer
from datosenorden.etl.core.pipeline import DatasetAdapter
from datosenorden.etl.core.pipeline import DatasetLoadRequest
from datosenorden.etl.core.pipeline import load_dataset
from validate_chilecompra_file import read_chilecompra_payload
from validate_chilecompra_file import validate_records


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
        payload = _read_payload(
            request.input_path,
            limit=int((request.metadata or {}).get("limit", 0) or 0),
            source_label=str((request.metadata or {}).get("source_label", "")),
            data_classification=str((request.metadata or {}).get("data_classification", "TEST_DATA")),
        )
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
    parser.add_argument("--limit", type=int, default=0, help="Load only first N records. 0 means all records.")
    parser.add_argument("--source-label", default="", help="Human label for the local file/source.")
    data_mode = parser.add_mutually_exclusive_group()
    data_mode.add_argument("--official-data", action="store_true", help="Mark payload metadata as operator-provided official data.")
    data_mode.add_argument("--test-data", action="store_true", help="Mark payload metadata as local test/sample data.")
    args = parser.parse_args(argv)

    payload_path = Path(args.path)
    data_classification = "OFFICIAL_DATA_OPERATOR_PROVIDED" if args.official_data else "LOCAL_TEST_DATA"
    request = DatasetLoadRequest(
        dataset_id="chilecompra",
        input_path=payload_path,
        dry_run=args.dry_run,
        metadata={
            "query_date": args.query_date,
            "limit": args.limit,
            "source_label": args.source_label,
            "data_classification": data_classification,
        },
    )
    adapter = ChileCompraFileAdapter()
    validation_errors = adapter.validate(request)
    if validation_errors:
        for error in validation_errors:
            print(f"error: {error}", file=sys.stderr)
        return 1

    payload = _read_payload(
        payload_path,
        limit=args.limit,
        source_label=args.source_label,
        data_classification=data_classification,
    )
    validation_report = validate_records(payload["Listado"])
    print("load_chilecompra_file_preview:")
    print(f"  records={validation_report['records']}")
    print(f"  usable_records={validation_report['usable_records']}")
    print(f"  buyers={validation_report['buyers']}")
    print(f"  suppliers={validation_report['suppliers']}")
    print(f"  data_classification={data_classification}")
    print(f"  source_label={args.source_label or payload_path.name}")
    if not validation_report["usable"]:
        print("error: no usable ChileCompra records found", file=sys.stderr)
        return 1

    with SessionLocal() as session:
        result = load_dataset(session, adapter, request)

    print("load_chilecompra_file:")
    print(f"  source={payload_path}")
    print(f"  dry_run={args.dry_run}")
    print(f"  limit={args.limit}")
    print(f"  source_label={args.source_label or payload_path.name}")
    print(f"  data_classification={data_classification}")
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


def _read_payload(payload_path: Path, *, limit: int = 0, source_label: str = "", data_classification: str = "LOCAL_TEST_DATA") -> dict:
    payload = read_chilecompra_payload(payload_path)
    if limit > 0:
        payload["Listado"] = payload["Listado"][:limit]
    payload.setdefault("Version", data_classification)
    payload.setdefault("FechaCreacion", "")
    payload["_datosenorden_notice"] = (
        "OFFICIAL_DATA_OPERATOR_PROVIDED. Verify original source and attribution before public use."
        if data_classification == "OFFICIAL_DATA_OPERATOR_PROVIDED"
        else "LOCAL_TEST_DATA / NOT_OFFICIAL_DATA unless the operator verifies the source."
    )
    payload["_datosenorden_source_label"] = source_label or payload_path.name
    payload["_datosenorden_data_classification"] = data_classification
    payload["_datosenorden_loader"] = "scripts/load_chilecompra_file.py"
    return payload


if __name__ == "__main__":
    raise SystemExit(main())
