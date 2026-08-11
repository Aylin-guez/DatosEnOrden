"""Pure model namespace for DEO Ciudadano."""

from reflex_app.models.document import PDFHighlightTarget
from reflex_app.models.investigation import INVESTIGATION_TOPICS, InvestigationTopic
from reflex_app.models.source import SOURCE_COVERAGE_TEMPLATE, SourceCoverageTemplateRow

__all__ = [
    "INVESTIGATION_TOPICS",
    "PDFHighlightTarget",
    "SOURCE_COVERAGE_TEMPLATE",
    "InvestigationTopic",
    "SourceCoverageTemplateRow",
]
