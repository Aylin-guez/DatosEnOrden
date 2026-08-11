from __future__ import annotations


def _clean(value: object, fallback: str = "Sin dato") -> str:
    text = "" if value is None else str(value).strip()
    return text or fallback


def _safe_public_values(obj: object) -> list[object]:
    if obj is None:
        return []
    if isinstance(obj, dict):
        return list(obj.values())
    try:
        fields = vars(obj)
    except Exception:  # noqa: BLE001
        return []
    return [
        value
        for name, value in fields.items()
        if not str(name).startswith("_") and isinstance(value, str | dict | list | tuple)
    ]
