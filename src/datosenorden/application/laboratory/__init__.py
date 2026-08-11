"""Public application boundary for the Laboratory feature."""

from .models import LABORATORY_EXPEDIENT_ID
from .service import get_expedient, load_expedient_catalog

__all__ = ("LABORATORY_EXPEDIENT_ID", "get_expedient", "load_expedient_catalog")
