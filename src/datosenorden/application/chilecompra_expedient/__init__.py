"""Deterministic, provenance-first candidates for REAL ChileCompra expedients."""

from .generator import build_chilecompra_expedient_candidate
from .models import ChileCompraExpedientInput, ChileCompraExpedientInputError
from .adapters import ChileCompraCanonicalIdentityResolver, ChileCompraValidatedContent, PublicSubject, build_chilecompra_input, resolve_public_subject
from .corrective import CorrectiveResult, CorrectiveStatus, repair_chilecompra_expedient

__all__ = [
    "ChileCompraExpedientInput",
    "ChileCompraExpedientInputError",
    "build_chilecompra_expedient_candidate",
    "ChileCompraCanonicalIdentityResolver",
    "ChileCompraValidatedContent",
    "PublicSubject",
    "build_chilecompra_input",
    "resolve_public_subject",
    "CorrectiveResult",
    "CorrectiveStatus",
    "repair_chilecompra_expedient",
]
