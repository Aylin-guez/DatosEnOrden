from __future__ import annotations

from dataclasses import fields, is_dataclass
from datetime import date, datetime
from types import MappingProxyType
from uuid import UUID


def to_json_safe(value: object) -> object:
    if value is None or isinstance(value, str | int | float | bool):
        return value
    if isinstance(value, UUID | date | datetime):
        return str(value)
    if is_dataclass(value) and not isinstance(value, type):
        return {
            field.name: to_json_safe(getattr(value, field.name, None))
            for field in fields(value)
        }
    if isinstance(value, MappingProxyType):
        return to_json_safe(dict(value))
    if hasattr(value, "model_dump"):
        try:
            return to_json_safe(value.model_dump())
        except Exception:  # noqa: BLE001
            return str(value)
    if isinstance(value, dict):
        return {str(to_json_safe(key)): to_json_safe(item) for key, item in value.items()}
    if isinstance(value, tuple | list | set | frozenset):
        return [to_json_safe(item) for item in value]
    if hasattr(value, "__dict__"):
        safe_fields = {
            key: item
            for key, item in vars(value).items()
            if not key.startswith("_") and not callable(item)
        }
        if safe_fields:
            return to_json_safe(safe_fields)
    return str(value)


def _json_dict(value: object) -> dict:
    safe = to_json_safe(value)
    return safe if isinstance(safe, dict) else {}


def _json_list(value: object) -> list:
    safe = to_json_safe(value)
    return safe if isinstance(safe, list) else []
