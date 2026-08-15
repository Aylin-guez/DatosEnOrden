"""CSV parsing and normalized field names for acquired InfoLobby catalogues."""

from __future__ import annotations

import csv
import re
import unicodedata

from .acquisition import InfoLobbyAcquisitionError
from .models import AcquisitionMetadata, NormalizedCatalog


def parse_catalog(metadata: AcquisitionMetadata) -> NormalizedCatalog:
    try:
        raw = metadata.staging_path.read_bytes()
    except OSError as exc:
        raise InfoLobbyAcquisitionError("staged InfoLobby catalog is unavailable") from exc
    text = _decode(raw)
    delimiter = _detect_delimiter(text)
    reader = csv.DictReader(text.splitlines(), delimiter=delimiter)
    if not reader.fieldnames:
        raise InfoLobbyAcquisitionError("InfoLobby CSV has no header")
    columns = tuple(_normalise_column(value) for value in reader.fieldnames)
    if len(columns) != len(set(columns)) or any(not value for value in columns):
        raise InfoLobbyAcquisitionError("InfoLobby CSV has ambiguous columns")
    rows: list[dict[str, str]] = []
    for row in reader:
        if None in row:
            raise InfoLobbyAcquisitionError("InfoLobby CSV row has more values than its header")
        if not any((value or "").strip() for value in row.values()):
            continue
        try:
            rows.append({column: (value or "").strip() for column, value in zip(columns, row.values(), strict=True)})
        except ValueError as exc:
            raise InfoLobbyAcquisitionError("InfoLobby CSV row is incompatible with its header") from exc
    return NormalizedCatalog(metadata, columns, tuple(rows), delimiter)


def _decode(raw: bytes) -> str:
    try:
        return raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        return raw.decode("latin-1")


def _detect_delimiter(text: str) -> str:
    first_line = text.splitlines()[0] if text.splitlines() else ""
    return max((",", ";", "\t"), key=first_line.count)


def _normalise_column(value: str) -> str:
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"_+", "_", re.sub(r"[^a-z0-9]+", "_", value.casefold())).strip("_")
