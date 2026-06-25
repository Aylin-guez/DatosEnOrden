from __future__ import annotations

from pathlib import Path
import sys
from typing import Sequence

from sqlalchemy import func, select

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from datosenorden.db.session import SessionLocal
from datosenorden.maintenance.source_plugins import list_prototype_sources
from datosenorden.models import Claim, Dataset, Entity, Evidence, RelationshipPublic
from validate_source_plugin import sample_file_exists
from validate_source_plugin import validate_plugin


def main(argv: Sequence[str] | None = None) -> int:
    _ = argv
    print("prototype_sources_summary:")
    try:
        with SessionLocal() as session:
            for plugin in list_prototype_sources():
                validation = validate_plugin(plugin)
                dataset_names = [item.strip() for item in str(plugin.technical_metadata.get("dataset_names", "")).split(",") if item.strip()]
                dataset_count = _count_loaded_datasets(session, dataset_names)
                print(f"- {plugin.id}")
                print(f"  name: {plugin.display_name}")
                print(f"  readiness: {'ok' if validation.valid else 'needs_attention'}")
                print(f"  sample_file_exists: {'yes' if sample_file_exists(plugin) else 'no'}")
                print(f"  loaded_datasets: {dataset_count}")
                print(f"  entities_total: {_count_rows(session, Entity)}")
                print(f"  relationships_total: {_count_rows(session, RelationshipPublic)}")
                print(f"  evidence_total: {_count_rows(session, Evidence)}")
                print(f"  claims_total: {_count_rows(session, Claim)}")
    except Exception as exc:  # noqa: BLE001
        print(f"prototype_sources_summary_failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    return 0


def _count_loaded_datasets(session, names: list[str]) -> int:  # noqa: ANN001
    if not names:
        return 0
    return int(session.scalar(select(func.count()).select_from(Dataset).where(Dataset.name.in_(names))) or 0)


def _count_rows(session, model) -> int:  # noqa: ANN001
    return int(session.scalar(select(func.count()).select_from(model)) or 0)


if __name__ == "__main__":
    raise SystemExit(main())

