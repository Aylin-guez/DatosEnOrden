"""Adapter for Datos Abiertos Legislativos."""

from datosenorden.adapters.legislature.adapter import LegislativeAdapter
from datosenorden.adapters.legislature.client import LegislativeClient
from datosenorden.adapters.legislature.document_client import LegislativeDocumentClient
from datosenorden.adapters.legislature.document_resolver import LegislativeDocumentResolver
from datosenorden.adapters.legislature.foundation import (
    LEGISLATIVE_SOURCE_REGISTRY,
    AcquisitionManifest,
    OfficialLegislativeAcquisitionClient,
    OfficialResourceDescriptor,
)
from datosenorden.adapters.legislature.normalization import LegislativeMatter, LegislativeEvent, MatterChangeSnapshot

__all__ = [
    "LegislativeAdapter",
    "LegislativeClient",
    "LegislativeDocumentClient",
    "LegislativeDocumentResolver",
    "LEGISLATIVE_SOURCE_REGISTRY",
    "AcquisitionManifest",
    "OfficialLegislativeAcquisitionClient",
    "OfficialResourceDescriptor",
    "LegislativeMatter",
    "LegislativeEvent",
    "MatterChangeSnapshot",
]
