"""Read-only summaries and deterministic candidate matching for InfoLobby CSVs."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import re
from typing import Iterable

from .models import NormalizedCatalog


@dataclass(frozen=True)
class CatalogDryRun:
    catalog: str
    rows: int
    columns: tuple[str, ...]
    date_range: tuple[str, str] | None
    identifier_columns: tuple[str, ...]
    join_columns: tuple[str, ...]
    institution_count: int


@dataclass(frozen=True)
class EntityMatch:
    infolobby_value: str
    chilecompra_entity_id: str
    classification: str
    basis: str


def summarize_catalogs(catalogs: Iterable[NormalizedCatalog]) -> tuple[CatalogDryRun, ...]:
    return tuple(_summary(catalog) for catalog in catalogs)


def deterministic_matches(
    catalogs: Iterable[NormalizedCatalog],
    entities: Iterable[tuple[str, str, str, str | None]],
) -> tuple[EntityMatch, ...]:
    """Match only exact identifiers or exact institutional values from official fields."""
    entity_values = tuple(
        (
            entity_id,
            entity_type,
            name.casefold().strip(),
            (external_id or "").casefold().strip(),
            _rut_token(external_id or ""),
        )
        for entity_id, entity_type, name, external_id in entities
    )
    matches: set[EntityMatch] = set()
    for catalog in catalogs:
        for row in catalog.rows:
            for column, value in row.items():
                normalized = value.casefold().strip()
                if not normalized:
                    continue
                for entity_id, entity_type, name, external_id, rut_token in entity_values:
                    if external_id and normalized == external_id:
                        matches.add(EntityMatch(value, entity_id, "EXACT_ID_MATCH", f"{catalog.metadata.catalog.key.value}.{column}"))
                    elif _identifier_column(column) and rut_token and _rut_token(value) == rut_token:
                        matches.add(EntityMatch(value, entity_id, "EXACT_ID_MATCH", f"{catalog.metadata.catalog.key.value}.{column}"))
                    elif entity_type == "PUBLIC_ORGANIZATION" and _institution_column(column) and normalized == name:
                        matches.add(EntityMatch(value, entity_id, "STRONG_INSTITUTION_MATCH", f"{catalog.metadata.catalog.key.value}.{column}"))
    return tuple(sorted(matches, key=lambda item: (item.classification, item.chilecompra_entity_id, item.infolobby_value)))


def _summary(catalog: NormalizedCatalog) -> CatalogDryRun:
    columns = catalog.columns
    date_values = sorted(
        parsed
        for row in catalog.rows
        for column, value in row.items()
        if "fecha" in column
        for parsed in [_as_iso_date(value)]
        if parsed
    )
    joins = tuple(column for column in columns if any(token in column for token in ("audiencia", "activo", "pasivo", "asistencia", "represent", "id_")))
    identifiers = tuple(column for column in columns if _identifier_column(column))
    institutions = {
        value.casefold().strip()
        for row in catalog.rows
        for column, value in row.items()
        if _institution_column(column) and value.strip()
    }
    return CatalogDryRun(catalog.metadata.catalog.key.value, len(catalog.rows), columns, (date_values[0], date_values[-1]) if date_values else None, identifiers, joins, len(institutions))


def _as_iso_date(value: str) -> str | None:
    for pattern in ("%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(value.strip(), pattern).date().isoformat()
        except ValueError:
            continue
    return None


def _institution_column(column: str) -> bool:
    return any(token in column for token in ("institucion", "organismo", "servicio"))


def _identifier_column(column: str) -> bool:
    return any(token in column for token in ("rut", "identificador", "codigo", "id_"))


def _rut_token(value: str) -> str | None:
    normalized = re.sub(r"[^0-9kK]", "", value)
    return normalized.casefold() if re.fullmatch(r"\d{7,8}[0-9k]", normalized) else None
