"""Adapter for Datos Abiertos Legislativos."""

from datosenorden.adapters.legislature.adapter import LegislativeAdapter
from datosenorden.adapters.legislature.client import LegislativeClient
from datosenorden.adapters.legislature.document_client import LegislativeDocumentClient
from datosenorden.adapters.legislature.document_resolver import LegislativeDocumentResolver

__all__ = [
    "LegislativeAdapter",
    "LegislativeClient",
    "LegislativeDocumentClient",
    "LegislativeDocumentResolver",
]
