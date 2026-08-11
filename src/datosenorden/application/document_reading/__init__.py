from __future__ import annotations

from datosenorden.application.document_reading.ports import (
    DocumentReadingPort,
    EvidenceCandidatePort,
)
from datosenorden.application.document_reading.service import (
    DEMO_INVESTIGATION_TARGET,
    TOPIC_BUDGET_2013_TITLE,
    TOPIC_BUDGET_2013_TARGET,
    build_knowledge_payload,
    build_topic_payload,
    knowledge_error_payload,
    select_document_payload,
)

__all__ = (
    "DEMO_INVESTIGATION_TARGET",
    "DocumentReadingPort",
    "EvidenceCandidatePort",
    "TOPIC_BUDGET_2013_TITLE",
    "TOPIC_BUDGET_2013_TARGET",
    "build_knowledge_payload",
    "build_topic_payload",
    "knowledge_error_payload",
    "select_document_payload",
)
