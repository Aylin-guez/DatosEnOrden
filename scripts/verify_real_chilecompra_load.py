from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from sqlalchemy import func, select

from datosenorden.db.session import SessionLocal
from datosenorden.models import Claim, Dataset, Entity, Evidence, RelationshipPublic, SourceRecord
from datosenorden.web.app_services import get_investigation
from datosenorden.web.app_services import get_investigation_timeline
from datosenorden.web.app_services import search_workspace


CHILECOMPRA_DATASET_NAMES = ("chilecompra-ordenes-compra", "chilecompra-licitaciones")


def main() -> int:
    checks: list[tuple[str, bool, str]] = []
    with SessionLocal() as session:
        stats = _stats(session)
        candidate = _candidate_entity(session)

    checks.extend(
        [
            ("ChileCompra source records loaded", stats["source_records"] > 0, str(stats["source_records"])),
            ("buyers available", stats["buyers"] > 0, str(stats["buyers"])),
            ("suppliers available", stats["suppliers"] > 0, str(stats["suppliers"])),
            ("relationships available", stats["relationships"] > 0, str(stats["relationships"])),
            ("evidence available", stats["evidence"] > 0, str(stats["evidence"])),
        ]
    )
    checks.append(("candidate entity found", bool(candidate["id"]), candidate["name"]))

    if candidate["name"]:
        query_token = _query_token(candidate["name"])
        search = search_workspace(query_token)
        matches = search.get("matches", [])
        checks.append(("partial search works", len(matches) > 0, f"query={query_token} matches={len(matches)}"))
    if candidate["id"]:
        investigation = get_investigation(candidate["id"])
        metrics = investigation.get("compact_metrics", {})
        checks.append(("expediente opens", bool(investigation.get("found")) and int(metrics.get("evidence_count", 0) or 0) > 0, str(metrics)))
        timeline = get_investigation_timeline(candidate["id"])
        checks.append(("derived timeline available when dates exist", len(timeline.get("years", [])) > 0, str(len(timeline.get("years", [])))))

    print("verify_real_chilecompra_load:")
    for label, ok, detail in checks:
        print(f"  {'ok' if ok else 'FAIL'} - {label}: {detail}")
    print("counts:")
    for key, value in stats.items():
        print(f"  {key}={value}")
    if candidate["id"]:
        print(f"candidate_expediente: /investigation?id={candidate['id']}")
    return 1 if any(not ok for _, ok, _ in checks) else 0


def _stats(session) -> dict[str, int]:  # noqa: ANN001
    dataset_scope = select(Dataset.id).where(Dataset.name.in_(CHILECOMPRA_DATASET_NAMES)).subquery()
    source_record_ids = select(SourceRecord.id).where(SourceRecord.dataset_id.in_(select(dataset_scope.c.id))).subquery()
    claim_ids = select(Claim.id).where(Claim.source_record_id.in_(select(source_record_ids.c.id))).subquery()
    return {
        "source_records": int(session.scalar(select(func.count()).select_from(SourceRecord).where(SourceRecord.dataset_id.in_(select(dataset_scope.c.id)))) or 0),
        "buyers": int(session.scalar(select(func.count()).select_from(Entity).where(Entity.entity_type == "PUBLIC_ORGANIZATION", Entity.external_id.like("chilecompra:buyer:%"))) or 0),
        "suppliers": int(session.scalar(select(func.count()).select_from(Entity).where(Entity.entity_type == "COMPANY", Entity.external_id.like("chilecompra:supplier:%"))) or 0),
        "relationships": int(session.scalar(select(func.count()).select_from(RelationshipPublic).where(RelationshipPublic.claim_id.in_(select(claim_ids.c.id)))) or 0),
        "evidence": int(session.scalar(select(func.count()).select_from(Evidence).where(Evidence.source_record_id.in_(select(source_record_ids.c.id)))) or 0),
    }


def _candidate_entity(session) -> dict[str, str]:  # noqa: ANN001
    row = session.scalars(
        select(Entity)
        .where(Entity.entity_type == "PUBLIC_ORGANIZATION", Entity.external_id.like("chilecompra:buyer:%"))
        .order_by(Entity.name.asc(), Entity.id.asc())
        .limit(1)
    ).first()
    if row is None:
        row = session.scalars(
            select(Entity)
            .where(Entity.entity_type == "COMPANY", Entity.external_id.like("chilecompra:supplier:%"))
            .order_by(Entity.name.asc(), Entity.id.asc())
            .limit(1)
        ).first()
    return {"id": str(row.id), "name": row.name} if row is not None else {"id": "", "name": ""}


def _query_token(name: str) -> str:
    words = [word for word in name.split() if len(word) >= 4]
    return words[0] if words else name[:8]


if __name__ == "__main__":
    raise SystemExit(main())
