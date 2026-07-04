from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from datosenorden.etl.chilecompra.mappers import ChileCompraGraphMapper


REQUIRED_CODE_KEYS = ("Codigo", "CodigoExterno")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate a local ChileCompra JSON file without loading the database.")
    parser.add_argument("path", help="Local JSON file. Accepts an object with Listado or a direct list of records.")
    parser.add_argument("--limit", type=int, default=0, help="Validate only first N records after parsing. 0 means all.")
    args = parser.parse_args(argv)

    try:
        payload = read_chilecompra_payload(Path(args.path))
    except Exception as exc:  # noqa: BLE001
        print(f"validate_chilecompra_file: FAIL - {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1

    records = payload["Listado"]
    if args.limit > 0:
        records = records[: args.limit]

    report = validate_records(records)
    print_validation_report(Path(args.path), payload, records, report)
    return 0 if report["usable"] else 1


def read_chilecompra_payload(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if isinstance(payload, list):
        payload = {"Listado": payload, "Version": "", "FechaCreacion": ""}
    if not isinstance(payload, dict):
        raise ValueError("Expected JSON object or list.")
    records = payload.get("Listado", [])
    if isinstance(records, dict):
        records = [records]
    if not isinstance(records, list):
        raise ValueError("Expected field 'Listado' to be a list or object.")
    payload["Listado"] = [record for record in records if isinstance(record, dict)]
    return payload


def validate_records(records: list[dict[str, Any]]) -> dict[str, Any]:
    mapper = ChileCompraGraphMapper()
    missing_counter: Counter[str] = Counter()
    buyers: set[str] = set()
    suppliers: set[str] = set()
    usable_records = 0
    rejected_preview: list[str] = []

    for index, record in enumerate(records, start=1):
        code = _first_text(record, REQUIRED_CODE_KEYS)
        buyer_code, buyer_name = mapper._extract_buyer_identity(record)  # noqa: SLF001
        supplier_code, supplier_name = mapper._extract_supplier_identity(record)  # noqa: SLF001
        missing = []
        if not code:
            missing.append("Codigo/CodigoExterno")
        if not (buyer_code and buyer_name):
            missing.append("Comprador.{CodigoOrganismo/CodigoUnidadCompra + NombreOrganismo/NombreUnidadCompra}")
        if not (supplier_code and supplier_name):
            missing.append("Proveedor/Adjudicatario.{CodigoEmpresa/RutProveedor + NombreEmpresa/RazonSocial}")
        for item in missing:
            missing_counter[item] += 1
        if missing:
            rejected_preview.append(f"record={index} missing={'; '.join(missing)}")
        else:
            usable_records += 1
        if buyer_code or buyer_name:
            buyers.add(buyer_code or buyer_name or "")
        if supplier_code or supplier_name:
            suppliers.add(supplier_code or supplier_name or "")

    return {
        "records": len(records),
        "usable_records": usable_records,
        "buyers": len({item for item in buyers if item}),
        "suppliers": len({item for item in suppliers if item}),
        "missing": dict(missing_counter),
        "rejected_preview": rejected_preview[:5],
        "usable": bool(records) and usable_records > 0,
    }


def print_validation_report(path: Path, payload: dict[str, Any], records: list[dict[str, Any]], report: dict[str, Any]) -> None:
    print("validate_chilecompra_file:")
    print(f"  path={path}")
    print(f"  version={payload.get('Version', '')}")
    print(f"  fecha_creacion={payload.get('FechaCreacion', '')}")
    print(f"  records={report['records']}")
    print(f"  usable_records={report['usable_records']}")
    print(f"  buyers={report['buyers']}")
    print(f"  suppliers={report['suppliers']}")
    print(f"  status={'ok' if report['usable'] else 'invalid'}")
    if report["missing"]:
        print("  missing_fields:")
        for field, count in sorted(report["missing"].items()):
            print(f"    - {field}: {count}")
    if report["rejected_preview"]:
        print("  rejected_preview:")
        for item in report["rejected_preview"]:
            print(f"    - {item}")
    if records:
        first = records[0]
        safe_preview = {
            key: first.get(key)
            for key in ("Codigo", "CodigoExterno", "Nombre", "FechaEnvio", "FechaCreacion")
            if key in first
        }
        print(f"  safe_preview={json.dumps(safe_preview, ensure_ascii=False)}")


def _first_text(record: dict[str, Any], keys: tuple[str, ...]) -> str:
    for key in keys:
        value = record.get(key)
        text = str(value).strip() if value is not None else ""
        if text:
            return text
    return ""


if __name__ == "__main__":
    raise SystemExit(main())
