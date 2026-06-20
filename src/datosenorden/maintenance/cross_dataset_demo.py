from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from uuid import UUID

from sqlalchemy import distinct, func, select
from sqlalchemy.orm import Session

from datosenorden.maintenance.cross_dataset_explorer import _dataset_group
from datosenorden.maintenance.entity_matching import EntityMatchCandidate
from datosenorden.maintenance.entity_matching import match_entity_candidates
from datosenorden.maintenance.entity_matching import normalize_entity_name
from datosenorden.maintenance.lobby_prototype import (
    LOCAL_TEST_DATA,
    LOBBY_SAMPLE_DATASET_NAME,
    LOBBY_SAMPLE_PATH,
    NOT_OFFICIAL_DATA,
)
from datosenorden.models import Claim, Dataset, Entity, SourceRecord

CHILECOMPRA_DATASET = "chilecompra"
LOBBY_DATASET = "lobby"
LOBBY_ORGANIZATION_PREDICATE = "ORGANIZATION_HELD_LOBBY_MEETING"


@dataclass(frozen=True)
class DatasetOrganization:
    entity_id: str
    name: str
    normalized_name: str
    dataset: str


@dataclass(frozen=True)
class DiagnosticCandidateGroup:
    lobby_organization: DatasetOrganization
    candidates: tuple[EntityMatchCandidate, ...]


@dataclass(frozen=True)
class CrossDatasetMatchDiagnostic:
    chilecompra_organizations: tuple[DatasetOrganization, ...]
    lobby_organizations: tuple[DatasetOrganization, ...]
    shared_organization_ids: tuple[str, ...]
    candidate_matches: tuple[DiagnosticCandidateGroup, ...]
    reason: str


@dataclass(frozen=True)
class LobbySampleAlignmentResult:
    sample_path: str
    organization_id: str
    organization_name: str
    previous_organization_name: str
    changed: bool
    classification: str
    official_status: str


def debug_cross_dataset_matches(session: Session, *, candidate_limit: int = 3) -> CrossDatasetMatchDiagnostic:
    chilecompra_organizations = _organizations_for_dataset(session, CHILECOMPRA_DATASET)
    lobby_organizations = _organizations_for_dataset(session, LOBBY_DATASET)
    chilecompra_ids = {organization.entity_id for organization in chilecompra_organizations}
    lobby_ids = {organization.entity_id for organization in lobby_organizations}
    shared_ids = tuple(sorted(chilecompra_ids & lobby_ids))

    candidate_matches = tuple(
        DiagnosticCandidateGroup(
            lobby_organization=organization,
            candidates=_chilecompra_candidate_matches(
                session,
                organization.name,
                chilecompra_ids=chilecompra_ids,
                limit=candidate_limit,
            ),
        )
        for organization in lobby_organizations
    )
    return CrossDatasetMatchDiagnostic(
        chilecompra_organizations=chilecompra_organizations,
        lobby_organizations=lobby_organizations,
        shared_organization_ids=shared_ids,
        candidate_matches=candidate_matches,
        reason=_diagnostic_reason(chilecompra_organizations, lobby_organizations, shared_ids, candidate_matches),
    )


def align_lobby_sample_to_existing_org(
    session: Session,
    *,
    sample_path: Path | None = None,
) -> LobbySampleAlignmentResult:
    organization = _select_chilecompra_demo_organization(session)
    if organization is None:
        raise LookupError("No ChileCompra PUBLIC_ORGANIZATION was found for local demo alignment.")

    path = sample_path or LOBBY_SAMPLE_PATH
    payload = json.loads(path.read_text(encoding="utf-8"))
    _ensure_local_lobby_sample(payload)

    records = payload.get("records")
    if not isinstance(records, list) or not records:
        raise ValueError("Lobby sample must include at least one record")

    record = records[0]
    previous_name = str(record.get("organization_name", ""))
    changed = previous_name != organization.name
    record["organization_name"] = organization.name
    record["source_dataset_name"] = LOBBY_SAMPLE_DATASET_NAME
    record["notes"] = (
        f"{LOCAL_TEST_DATA} / {NOT_OFFICIAL_DATA} sample aligned to an existing "
        "ChileCompra organization for local cross-dataset demonstration. "
        "This is not official Lobby data and does not imply wrongdoing."
    )
    payload["classification"] = LOCAL_TEST_DATA
    payload["official_status"] = NOT_OFFICIAL_DATA
    payload["dataset_name"] = LOBBY_SAMPLE_DATASET_NAME
    payload["source_name"] = "DatosEnOrden Lobby Sample"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return LobbySampleAlignmentResult(
        sample_path=str(path),
        organization_id=str(organization.id),
        organization_name=organization.name,
        previous_organization_name=previous_name,
        changed=changed,
        classification=LOCAL_TEST_DATA,
        official_status=NOT_OFFICIAL_DATA,
    )


def render_cross_dataset_match_diagnostic_text(diagnostic: CrossDatasetMatchDiagnostic) -> str:
    lines = [
        "cross_dataset_match_diagnostic:",
        "",
        "chilecompra_organizations:",
    ]
    lines.extend(_render_organizations(diagnostic.chilecompra_organizations))
    lines.extend(["", "lobby_organizations:"])
    lines.extend(_render_organizations(diagnostic.lobby_organizations))
    lines.extend(["", "closest_candidate_matches:"])
    if not diagnostic.candidate_matches:
        lines.append("  (no lobby organizations available for matching)")
    for group in diagnostic.candidate_matches:
        lines.append(f"  lobby_organization={group.lobby_organization.name}")
        lines.append(f"  normalized_name={group.lobby_organization.normalized_name}")
        if not group.candidates:
            lines.append("    (no candidates found)")
            continue
        for index, candidate in enumerate(group.candidates, start=1):
            lines.extend(
                [
                    f"    candidate[{index}]:",
                    f"      candidate_entity_id={candidate.candidate_entity_id}",
                    f"      candidate_name={candidate.candidate_name}",
                    f"      normalized_name={normalize_entity_name(candidate.candidate_name) or 'None'}",
                    f"      score={candidate.score:.4f}",
                    f"      match_method={candidate.match_method}",
                    f"      explanation={candidate.explanation}",
                ]
            )
    lines.extend(["", "shared_organization_ids:"])
    if diagnostic.shared_organization_ids:
        lines.extend(f"  {entity_id}" for entity_id in diagnostic.shared_organization_ids)
    else:
        lines.append("  (none)")
    lines.extend(["", "reason:", diagnostic.reason])
    return "\n".join(lines)


def render_lobby_sample_alignment_text(result: LobbySampleAlignmentResult) -> str:
    return "\n".join(
        [
            "lobby_sample_alignment:",
            f"  sample_path={result.sample_path}",
            f"  organization_id={result.organization_id}",
            f"  organization_name={result.organization_name}",
            f"  previous_organization_name={result.previous_organization_name}",
            f"  changed={result.changed}",
            f"  classification={result.classification}",
            f"  official_status={result.official_status}",
            "  note=Only the local Lobby sample file was aligned; run scripts/load_lobby_sample.py to reload it.",
        ]
    )


def _organizations_for_dataset(session: Session, dataset_group: str) -> tuple[DatasetOrganization, ...]:
    rows = session.execute(
        select(distinct(Entity.id), Entity.name)
        .select_from(Claim)
        .join(Entity, Claim.subject_entity_id == Entity.id)
        .join(SourceRecord, Claim.source_record_id == SourceRecord.id)
        .join(Dataset, SourceRecord.dataset_id == Dataset.id)
        .where(Entity.entity_type == "PUBLIC_ORGANIZATION")
        .order_by(Entity.name.asc(), Entity.id.asc())
    ).all()
    organizations = []
    for entity_id, name in rows:
        datasets = _datasets_for_subject_entity(session, entity_id)
        if dataset_group not in datasets:
            continue
        organizations.append(
            DatasetOrganization(
                entity_id=str(entity_id),
                name=str(name),
                normalized_name=normalize_entity_name(name) or "",
                dataset=dataset_group,
            )
        )
    return tuple(organizations)


def _datasets_for_subject_entity(session: Session, entity_id: UUID) -> set[str]:
    rows = session.execute(
        select(distinct(Dataset.name))
        .select_from(Claim)
        .join(SourceRecord, Claim.source_record_id == SourceRecord.id)
        .join(Dataset, SourceRecord.dataset_id == Dataset.id)
        .where(Claim.subject_entity_id == entity_id)
    ).all()
    return {dataset for (name,) in rows if (dataset := _dataset_group(str(name))) is not None}


def _select_chilecompra_demo_organization(session: Session) -> Entity | None:
    return session.scalar(
        select(Entity)
        .join(Claim, Claim.subject_entity_id == Entity.id)
        .join(SourceRecord, Claim.source_record_id == SourceRecord.id)
        .join(Dataset, SourceRecord.dataset_id == Dataset.id)
        .where(Entity.entity_type == "PUBLIC_ORGANIZATION")
        .where(Dataset.name.like("chilecompra%"))
        .group_by(Entity.id)
        .order_by(func.count(Claim.id).desc(), Entity.name.asc(), Entity.id.asc())
        .limit(1)
    )


def _chilecompra_candidate_matches(
    session: Session,
    name: str,
    *,
    chilecompra_ids: set[str],
    limit: int,
) -> tuple[EntityMatchCandidate, ...]:
    candidates = match_entity_candidates(
        session,
        entity_type="PUBLIC_ORGANIZATION",
        name=name,
        limit=max(limit * 5, limit),
    )
    return tuple(candidate for candidate in candidates if candidate.candidate_entity_id in chilecompra_ids)[:limit]


def _ensure_local_lobby_sample(payload: dict) -> None:
    if payload.get("classification") != LOCAL_TEST_DATA:
        raise ValueError("Lobby sample alignment only supports LOCAL_TEST_DATA files")
    if payload.get("official_status") != NOT_OFFICIAL_DATA:
        raise ValueError("Lobby sample alignment only supports NOT_OFFICIAL_DATA files")


def _diagnostic_reason(
    chilecompra_organizations: tuple[DatasetOrganization, ...],
    lobby_organizations: tuple[DatasetOrganization, ...],
    shared_ids: tuple[str, ...],
    candidate_matches: tuple[DiagnosticCandidateGroup, ...],
) -> str:
    if shared_ids:
        return "At least one organization entity is already shared by ChileCompra and Lobby records."
    if not chilecompra_organizations:
        return "No ChileCompra PUBLIC_ORGANIZATION records were found in stored claims."
    if not lobby_organizations:
        return "No Lobby PUBLIC_ORGANIZATION records were found in stored claims. Load the local Lobby sample after alignment."
    if any(group.candidates for group in candidate_matches):
        return (
            "Lobby organization names have candidate ChileCompra matches, but the stored Lobby claims "
            "do not yet point to the same organization entity. Run the local alignment helper and reload the Lobby sample."
        )
    return (
        "ChileCompra and Lobby organizations are present, but no shared entity id or close normalized-name "
        "candidate was found."
    )


def _render_organizations(rows: tuple[DatasetOrganization, ...]) -> list[str]:
    if not rows:
        return ["  (none)"]
    lines: list[str] = []
    for row in rows:
        lines.extend(
            [
                f"  organization_id={row.entity_id}",
                f"  name={row.name}",
                f"  normalized_name={row.normalized_name}",
                f"  dataset={row.dataset}",
            ]
        )
    return lines
