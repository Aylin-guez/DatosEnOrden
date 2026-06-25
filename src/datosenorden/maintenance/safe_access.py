from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import Any


def _field(obj: object, key: str, fallback: object = None) -> object:
    if obj is None:
        return fallback
    if isinstance(obj, dict):
        return obj.get(key, fallback)
    if hasattr(obj, key):
        return getattr(obj, key, fallback)
    if is_dataclass(obj) and not isinstance(obj, type):
        return asdict(obj).get(key, fallback)
    for method_name in ("model_dump", "dict"):
        method = getattr(obj, method_name, None)
        if callable(method):
            try:
                dumped = method()
            except TypeError:
                continue
            if isinstance(dumped, dict):
                return dumped.get(key, fallback)
    return fallback


def _as_text(value: object, fallback: str = "") -> str:
    if value is None:
        return fallback
    text = str(value).strip()
    return text or fallback


def _as_list(value: object) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple | set):
        return list(value)
    return [value]
