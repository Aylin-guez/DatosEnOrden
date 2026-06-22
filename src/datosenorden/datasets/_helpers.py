from __future__ import annotations

from dataclasses import asdict, is_dataclass
from datetime import date, datetime
from typing import Any


def jsonify(value: Any) -> Any:
    if is_dataclass(value) and not isinstance(value, type):
        return {key: jsonify(item) for key, item in asdict(value).items()}
    if isinstance(value, dict):
        return {str(key): jsonify(item) for key, item in value.items()}
    if isinstance(value, tuple | list):
        return [jsonify(item) for item in value]
    if isinstance(value, date | datetime):
        return value.isoformat()
    return value

