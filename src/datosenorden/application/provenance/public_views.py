"""Public view-models derived from the provenance authority."""

from __future__ import annotations

from typing import Any

from .service import build_provenance_snapshot, build_public_metric_projection


def build_public_dataset_summary(
    session: object,
    datasets: list[dict[str, Any]],
) -> dict[str, Any]:
    snapshot = build_provenance_snapshot(session)
    public_metrics = build_public_metric_projection(session)
    metrics_by_label = {str(row["source_label"]): row for row in snapshot.source_metrics}
    public_datasets = [
        {
            **row,
            "source_records": int(
                metrics_by_label.get(str(row["name"]), {}).get("available_real_records", 0)
            ),
            "entities": int(metrics_by_label.get(str(row["name"]), {}).get("real_entities", 0)),
            "claims": int(metrics_by_label.get(str(row["name"]), {}).get("real_claims", 0)),
            "evidence": int(metrics_by_label.get(str(row["name"]), {}).get("real_evidence", 0)),
            "relationships": int(
                metrics_by_label.get(str(row["name"]), {}).get("real_relationships", 0)
            ),
            "health": (
                "active"
                if int(
                    metrics_by_label.get(str(row["name"]), {}).get(
                        "available_real_records", 0
                    )
                )
                else "empty"
            ),
        }
        for row in datasets
    ]
    active_datasets = sum(
        1 for row in snapshot.source_metrics if int(row["available_real_records"]) > 0
    )
    return {
        "datasets": public_datasets,
        "totals": {
            "datasets": active_datasets,
            "active_datasets": active_datasets,
            "source_records": public_metrics["source_records"],
            "entities": public_metrics["entities"],
            "claims": public_metrics["claims"],
            "evidence": public_metrics["evidences"],
            "relationships": public_metrics["relationships"],
            "documents": public_metrics["documents"],
            "expedients": public_metrics["expedients"],
        },
    }


def enrich_public_ecosystem(
    session: object,
    ecosystem: dict[str, Any],
) -> dict[str, Any]:
    source_metrics = build_provenance_snapshot(session).source_metrics
    by_label = {str(row["source_label"]): row for row in source_metrics}
    for source in ecosystem.get("sources", []):
        metrics = by_label.get(str(source.get("name", "")), {})
        source["real_records"] = int(metrics.get("real_records", 0))
        source["real_available_records"] = int(metrics.get("available_real_records", 0))
        source["real_rejected_records"] = int(metrics.get("rejected_real_records", 0))
        source["real_relationships"] = int(metrics.get("real_relationships", 0))
        source["provenance_status"] = str(metrics.get("provenance_class", "UNKNOWN"))
    return ecosystem
