"""Contracts for acquiring official InfoLobby CSV catalogues."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import Mapping

from datosenorden.application.provenance import ProvenanceClass


class CatalogKey(StrEnum):
    ACTIVOS = "activos"
    PASIVOS = "pasivos"
    AUDIENCIAS = "audiencias"
    DATOS_AUDIENCIA = "datos_audiencia"
    ASISTENCIAS_ACTIVOS = "asistencias_activos"
    ASISTENCIAS_PASIVOS = "asistencias_pasivos"
    REPRESENTACIONES = "representaciones"


@dataclass(frozen=True)
class CatalogDefinition:
    key: CatalogKey
    url: str
    description: str


CATALOGS: Mapping[CatalogKey, CatalogDefinition] = {
    CatalogKey.ACTIVOS: CatalogDefinition(CatalogKey.ACTIVOS, "https://datosinfolobby.cplt.cl/catalogos/activos.csv", "Sujetos activos"),
    CatalogKey.PASIVOS: CatalogDefinition(CatalogKey.PASIVOS, "https://datosinfolobby.cplt.cl/catalogos/pasivos.csv", "Sujetos pasivos"),
    CatalogKey.AUDIENCIAS: CatalogDefinition(CatalogKey.AUDIENCIAS, "https://datosinfolobby.cplt.cl/catalogos/audiencias.csv", "Audiencias"),
    CatalogKey.DATOS_AUDIENCIA: CatalogDefinition(CatalogKey.DATOS_AUDIENCIA, "https://datosinfolobby.cplt.cl/catalogos/datosAudiencia.csv", "Detalle de audiencias"),
    CatalogKey.ASISTENCIAS_ACTIVOS: CatalogDefinition(CatalogKey.ASISTENCIAS_ACTIVOS, "https://datosinfolobby.cplt.cl/catalogos/asistenciasActivos.csv", "Asistencia de activos"),
    CatalogKey.ASISTENCIAS_PASIVOS: CatalogDefinition(CatalogKey.ASISTENCIAS_PASIVOS, "https://datosinfolobby.cplt.cl/catalogos/asistenciasPasivos.csv", "Asistencia de pasivos"),
    CatalogKey.REPRESENTACIONES: CatalogDefinition(CatalogKey.REPRESENTACIONES, "https://datosinfolobby.cplt.cl/catalogos/representaciones.csv", "Representados"),
}


@dataclass(frozen=True)
class AcquisitionMetadata:
    catalog: CatalogDefinition
    acquired_at: datetime
    sha256: str
    byte_count: int
    content_type: str | None
    staging_path: Path
    reused_staged_file: bool
    provenance_candidate: ProvenanceClass = ProvenanceClass.REAL
    public_countable: bool = False


@dataclass(frozen=True)
class NormalizedCatalog:
    metadata: AcquisitionMetadata
    columns: tuple[str, ...]
    rows: tuple[dict[str, str], ...]
    delimiter: str
