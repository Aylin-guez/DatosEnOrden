"""Adapter for Datos Abiertos Legislativos."""

from datosenorden.adapters.legislature.adapter import LegislativeAdapter
from datosenorden.adapters.legislature.client import LegislativeClient

__all__ = ["LegislativeAdapter", "LegislativeClient"]
