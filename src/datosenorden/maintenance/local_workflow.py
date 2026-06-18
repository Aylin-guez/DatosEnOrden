from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import subprocess
import sys

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from datosenorden.db.session import SessionLocal
from datosenorden.models import Claim, Evidence, RelationshipPublic, SourceRecord

PROJECT_ROOT = Path(__file__).resolve().parents[3]


@dataclass(frozen=True)
class LocalWorkflowCounts:
    source_record: int
    claim: int
    evidence: int
    relationship_public: int


def run_local_reset_migrate_seed_verify() -> LocalWorkflowCounts:
    _run_step([sys.executable, "-m", "alembic", "downgrade", "base"])
    _run_step([sys.executable, "-m", "alembic", "upgrade", "head"])
    _run_step([sys.executable, str(PROJECT_ROOT / "scripts" / "seed_traceability_flow.py")])
    return _read_counts(SessionLocal())


def _run_step(command: list[str]) -> None:
    subprocess.run(command, cwd=PROJECT_ROOT, check=True)


def _read_counts(session: Session) -> LocalWorkflowCounts:
    try:
        return LocalWorkflowCounts(
            source_record=_count(session, SourceRecord),
            claim=_count(session, Claim),
            evidence=_count(session, Evidence),
            relationship_public=_count(session, RelationshipPublic),
        )
    finally:
        session.close()


def _count(session: Session, model) -> int:  # type: ignore[no-untyped-def]
    return int(session.scalar(select(func.count()).select_from(model)) or 0)
