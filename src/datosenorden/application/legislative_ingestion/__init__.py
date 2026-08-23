"""Coordinated, explicit legislative ingestion gates for approved matters."""

from .service import BULLETIN_15975_25, LegislativeIngestionConflictError, ingest_bulletin_15975_25, preview_bulletin_15975_25
from .expedient import EXPEDIENT_ID, provision_reviewed_bulletin_15975_25, review_bulletin_15975_25_payload
from .golden_expedient import golden_v2_specification, provision_golden_v2

__all__ = ["BULLETIN_15975_25", "EXPEDIENT_ID", "LegislativeIngestionConflictError", "preview_bulletin_15975_25", "ingest_bulletin_15975_25", "review_bulletin_15975_25_payload", "provision_reviewed_bulletin_15975_25", "golden_v2_specification", "provision_golden_v2"]
