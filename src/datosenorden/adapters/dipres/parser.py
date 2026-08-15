"""Minimal read-only CSV parser for an acquired DIPRES resource."""

from __future__ import annotations

import csv
import re
import unicodedata

from .acquisition import DipresAcquisitionError
from .models import AcquiredResource, BudgetRow, ParsedBudgetCsv


def parse_budget_csv(acquisition: AcquiredResource) -> ParsedBudgetCsv:
    try:
        raw = acquisition.staging_path.read_bytes()
    except OSError as exc:
        raise DipresAcquisitionError("staged DIPRES resource is unavailable") from exc
    text = _decode(raw)
    delimiter = _delimiter(text)
    reader = csv.DictReader(text.splitlines(), delimiter=delimiter)
    if not reader.fieldnames:
        raise DipresAcquisitionError("DIPRES CSV has no header")
    columns = tuple(_column(value) for value in reader.fieldnames)
    if any(not column for column in columns) or len(columns) != len(set(columns)):
        raise DipresAcquisitionError("DIPRES CSV has ambiguous columns")
    rows: list[BudgetRow] = []
    for row in reader:
        if None in row:
            raise DipresAcquisitionError("DIPRES CSV row has more values than its header")
        if any((value or "").strip() for value in row.values()):
            rows.append(BudgetRow({key: (value or "").strip() for key, value in zip(columns, row.values(), strict=True)}))
    return ParsedBudgetCsv(acquisition, columns, tuple(rows), delimiter)


def _decode(raw: bytes) -> str:
    for encoding in ("utf-8-sig", "latin-1"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise DipresAcquisitionError("DIPRES CSV encoding is unsupported")


def _delimiter(text: str) -> str:
    first_line = text.splitlines()[0] if text.splitlines() else ""
    return max((",", ";", "\t"), key=first_line.count)


def _column(value: str) -> str:
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"_+", "_", re.sub(r"[^a-z0-9]+", "_", value.casefold())).strip("_")
