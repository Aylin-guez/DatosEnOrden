"""Read-only, targeted acquisition of official DIPRES budget resources."""

from .acquisition import DipresTargetedClient
from .ingestion import build_dep_real_batch
from .models import DipresIdentity, IdentityClassification, ResourceDefinition, classify_identity
from .parser import parse_budget_csv

__all__ = ["DipresIdentity", "DipresTargetedClient", "IdentityClassification", "ResourceDefinition", "build_dep_real_batch", "classify_identity", "parse_budget_csv"]
