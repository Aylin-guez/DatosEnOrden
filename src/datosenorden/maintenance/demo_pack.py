from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from datosenorden.core.config import PROJECT_ROOT
from datosenorden.etl.local_seed import persist_local_traceability_seed
from datosenorden.maintenance.cross_dataset_demo import align_lobby_sample_to_existing_org
from datosenorden.maintenance.cross_dataset_explorer import list_cross_dataset_organizations
from datosenorden.maintenance.dipres_prototype import persist_dipres_sample
from datosenorden.maintenance.entity_explorer import EntityProfile
from datosenorden.maintenance.entity_explorer import get_entity_profile
from datosenorden.maintenance.entity_matching import match_entity_candidates
from datosenorden.maintenance.lobby_prototype import persist_lobby_sample
from datosenorden.maintenance.timeline_explorer import build_entity_timeline
from datosenorden.maintenance.transparencia_activa_prototype import persist_transparencia_sample
from datosenorden.models import Entity, Evidence, RelationshipPublic
from datosenorden.maintenance.dataset_registry import list_datasets

DEMO_ENTITY_NAME = "DIVISION LOGISTICA DEL EJERCITO"
DEMO_REQUIRED_DATASETS = (
    ("chilecompra", "ChileCompra", ("python scripts/load_sample_purchase_orders.py --limit 100",)),
    ("dipres-prototype", "DIPRES sample", ("python scripts/load_dipres_sample.py",)),
    (
        "lobby",
        "Lobby sample",
        (
            "python scripts/align_lobby_sample_to_existing_org.py",
            "python scripts/load_lobby_sample.py",
        ),
    ),
    (
        "transparencia",
        "Transparencia Activa sample",
        ("python scripts/load_transparencia_sample.py",),
    ),
)


@dataclass(frozen=True)
class DemoDatasetStatus:
    slug: str
    label: str
    loaded: bool
    health: str


@dataclass(frozen=True)
class DemoRepair:
    label: str
    commands: tuple[str, ...]


@dataclass(frozen=True)
class DemoSeedResult:
    datasets: tuple[DemoDatasetStatus, ...]
    entities: int
    relationships: int
    evidence: int
    cross_dataset_organizations: int
    timeline_ready_entities: int


@dataclass(frozen=True)
class DemoStatusReport:
    database_connected: bool
    required_datasets_loaded: bool
    dataset_statuses: tuple[DemoDatasetStatus, ...]
    cross_dataset_organization: str | None
    timeline_entity: str | None
    streamlit_app_available: bool
    repairs: tuple[DemoRepair, ...]


def seed_demo_data(session: Session) -> None:
    persist_local_traceability_seed(session)
    persist_dipres_sample(session)
    _align_lobby_sample_if_possible(session)
    persist_lobby_sample(session)
    persist_transparencia_sample(session)


def build_demo_seed_result(session: Session) -> DemoSeedResult:
    dataset_statuses = _required_dataset_statuses(session)
    cross_dataset_rows = list_cross_dataset_organizations(session)
    demo_profile = resolve_demo_entity_profile(session)
    timeline_ready_entities = 0
    if demo_profile is not None:
        timeline = build_entity_timeline(session, demo_profile.entity.id)
        if timeline is not None and timeline.events:
            timeline_ready_entities = 1

    return DemoSeedResult(
        datasets=dataset_statuses,
        entities=_count_rows(session, Entity),
        relationships=_count_rows(session, RelationshipPublic),
        evidence=_count_rows(session, Evidence),
        cross_dataset_organizations=len(cross_dataset_rows),
        timeline_ready_entities=timeline_ready_entities,
    )


def render_demo_seed_text(result: DemoSeedResult) -> str:
    lines = ["demo_seed_complete:", "datasets:"]
    for dataset in result.datasets:
        lines.append(f"  {dataset.slug}: {dataset.health}")
    lines.extend(
        [
            f"entities={result.entities}",
            f"relationships={result.relationships}",
            f"evidence={result.evidence}",
            f"cross_dataset_organizations={result.cross_dataset_organizations}",
            f"timeline_ready_entities={result.timeline_ready_entities}",
        ]
    )
    return "\n".join(lines)


def build_demo_status(session: Session, *, streamlit_app_path: Path | None = None) -> DemoStatusReport:
    dataset_statuses = _required_dataset_statuses(session)
    required_datasets_loaded = all(dataset.loaded for dataset in dataset_statuses)
    cross_dataset_organization = _demo_cross_dataset_organization(session)
    demo_profile = resolve_demo_entity_profile(session)
    streamlit_app_available = _streamlit_app_available(streamlit_app_path)
    timeline_entity = None
    if demo_profile is not None:
        timeline = build_entity_timeline(session, demo_profile.entity.id)
        if timeline is not None and timeline.events:
            timeline_entity = demo_profile.entity.name

    repairs: list[DemoRepair] = []
    for dataset in dataset_statuses:
        if dataset.loaded:
            continue
        commands = _repair_commands_for_dataset(dataset.slug)
        if commands:
            repairs.append(DemoRepair(label=f"{dataset.label}.", commands=commands))

    if cross_dataset_organization is None:
        repairs.append(
            DemoRepair(
                label="Cross-dataset organization.",
                commands=(
                    "python scripts/align_lobby_sample_to_existing_org.py",
                    "python scripts/load_lobby_sample.py",
                ),
            )
        )

    if timeline_entity is None:
        repairs.append(
            DemoRepair(
                label="Timeline available.",
                commands=("python scripts/demo_seed.py",),
            )
        )

    if not streamlit_app_available:
        repairs.append(
            DemoRepair(
                label="Streamlit app available.",
                commands=("streamlit run streamlit_app.py",),
            )
        )

    return DemoStatusReport(
        database_connected=True,
        required_datasets_loaded=required_datasets_loaded,
        dataset_statuses=dataset_statuses,
        cross_dataset_organization=cross_dataset_organization,
        timeline_entity=timeline_entity,
        streamlit_app_available=streamlit_app_available,
        repairs=tuple(repairs),
    )


def render_demo_status_text(report: DemoStatusReport) -> str:
    lines = ["DatosEnOrden demo status", ""]
    ready = []
    if report.database_connected:
        ready.append("database connected")
    if report.required_datasets_loaded:
        ready.append("required datasets loaded")
    if report.cross_dataset_organization is not None:
        ready.append("cross-dataset organization found")
    if report.timeline_entity is not None:
        ready.append("timeline available")
    if report.streamlit_app_available:
        ready.append("Streamlit app available")

    lines.append("Ready:")
    if ready:
        lines.extend(f"- {item}" for item in ready)
    else:
        lines.append("- none")

    if report.repairs:
        lines.extend(["", "Missing:"])
        for repair in report.repairs:
            lines.append(f"- {repair.label}")
            if repair.commands:
                lines.append("Run:")
                lines.extend(f"  {command}" for command in repair.commands)

    return "\n".join(lines)


def resolve_demo_entity_profile(session: Session, *, entity_name: str = DEMO_ENTITY_NAME) -> EntityProfile | None:
    candidates = match_entity_candidates(session, entity_type="PUBLIC_ORGANIZATION", name=entity_name, limit=1)
    if not candidates:
        return None
    try:
        entity_id = UUID(candidates[0].candidate_entity_id)
    except ValueError:
        return None
    entity = session.get(Entity, entity_id)
    if entity is None:
        return None
    return get_entity_profile(session, str(entity.id))


def demo_mode_enabled() -> bool:
    import os

    value = os.getenv("DEMO_MODE", "")
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _required_dataset_statuses(session: Session) -> tuple[DemoDatasetStatus, ...]:
    summaries = {row.slug: row for row in list_datasets(session)}
    statuses: list[DemoDatasetStatus] = []
    for slug, label, _commands in DEMO_REQUIRED_DATASETS:
        summary = summaries.get(slug)
        if summary is None:
            statuses.append(DemoDatasetStatus(slug=slug, label=label, loaded=False, health="missing"))
            continue
        loaded = summary.health != "empty" and not summary.planned
        statuses.append(DemoDatasetStatus(slug=slug, label=label, loaded=loaded, health=summary.health))
    return tuple(statuses)


def _repair_commands_for_dataset(slug: str) -> tuple[str, ...]:
    for item_slug, _label, commands in DEMO_REQUIRED_DATASETS:
        if item_slug == slug:
            return commands
    return ()


def _demo_cross_dataset_organization(session: Session) -> str | None:
    summary = next(iter(list_cross_dataset_organizations(session)), None)
    return summary.organization_name if summary is not None else None


def _align_lobby_sample_if_possible(session: Session) -> None:
    try:
        align_lobby_sample_to_existing_org(session)
    except LookupError:
        return


def _streamlit_app_available(app_path: Path | None) -> bool:
    path = app_path or PROJECT_ROOT / "streamlit_app.py"
    return path.exists()


def _count_rows(session: Session, model) -> int:  # type: ignore[no-untyped-def]
    return int(session.scalar(select(func.count()).select_from(model)) or 0)
