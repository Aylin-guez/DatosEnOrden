from __future__ import annotations

from typing import Any

SAFE_FIELD_NAMES = (
    "Codigo",
    "CodigoExterno",
    "Nombre",
    "CodigoOrganismo",
    "NombreOrganismo",
    "CodigoUnidadCompra",
    "NombreUnidadCompra",
    "CodigoProveedor",
    "NombreProveedor",
    "CodigoEmpresa",
    "Proveedor",
    "Comprador",
    "FechaEnvio",
    "FechaCreacion",
)


def summarize_payload_shape(payload: dict[str, Any]) -> str:
    lines = ["payload_shape:"]
    lines.append(f"  top_level_keys={sorted(payload.keys())}")

    records = payload.get("Listado")
    if isinstance(records, list):
        lines.append(f"  listado_count={len(records)}")
        if records and isinstance(records[0], dict):
            lines.append(f"  first_record_keys={sorted(records[0].keys())}")
            lines.extend(_summarize_record(records[0], prefix="  "))
    elif isinstance(records, dict):
        lines.append("  listado_type=dict")
        lines.append(f"  listado_keys={sorted(records.keys())}")
        lines.extend(_summarize_record(records, prefix="  "))
    else:
        lines.append(f"  listado_type={type(records).__name__}")

    return "\n".join(lines)


def summarize_normalized_record(record: dict[str, Any]) -> str:
    lines = ["normalized_record_shape:"]
    lines.append(f"  keys={sorted(record.keys())}")
    lines.extend(_summarize_record(record, prefix="  "))
    return "\n".join(lines)


def _summarize_record(record: dict[str, Any], prefix: str) -> list[str]:
    lines: list[str] = []
    present = [name for name in SAFE_FIELD_NAMES if name in record and record.get(name) not in (None, "")]
    missing = [name for name in SAFE_FIELD_NAMES if name not in record or record.get(name) in (None, "")]
    lines.append(f"{prefix}present_fields={present}")
    lines.append(f"{prefix}missing_fields={missing}")

    for key in ("Comprador", "Proveedor", "Detalle", "Detalles", "Productos", "Items"):
        value = record.get(key)
        if isinstance(value, dict):
            lines.append(f"{prefix}{key}_keys={sorted(value.keys())}")
        elif isinstance(value, list) and value and isinstance(value[0], dict):
            lines.append(f"{prefix}{key}_count={len(value)}")
            lines.append(f"{prefix}{key}_first_keys={sorted(value[0].keys())}")
    return lines
