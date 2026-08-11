from __future__ import annotations


PUBLIC_RECORD_OWNERSHIP = {
    "state": "PUBLIC_PRODUCT_UI",
    "load_orchestration": "PUBLIC_PRODUCT_APPLICATION",
    "ports": "PUBLIC_CONTRACT",
    "graph_engine": "CORE_PRIVATE",
    "timeline_engine": "CORE_PRIVATE",
    "evidence_analysis": "CORE_PRIVATE",
}


def public_record_ownership() -> dict[str, str]:
    """Return the documented ownership map for Public Record boundaries."""

    return dict(PUBLIC_RECORD_OWNERSHIP)
