"""Reusable, persistence-free normalization for verified legislative resources."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, date, datetime
from enum import StrEnum
import re

from datosenorden.etl.core.hash import stable_json_hash

from .foundation import AcquisitionManifest, IdentityConfidence, LegislativeStatus


class LegislativeResourceType(StrEnum):
    MATTER_SUMMARY = "MATTER_SUMMARY"
    TRAMITATION_PAGE = "TRAMITATION_PAGE"
    LEGISLATIVE_DOCUMENT = "LEGISLATIVE_DOCUMENT"
    COMMISSION_REPORT = "COMMISSION_REPORT"
    VOTE = "VOTE"
    INDICATION = "INDICATION"
    LAW_TEXT = "LAW_TEXT"
    OFFICIAL_NEWS = "OFFICIAL_NEWS"
    OTHER_OFFICIAL_RESOURCE = "OTHER_OFFICIAL_RESOURCE"


class LegislativeEventType(StrEnum):
    INTRODUCED = "INTRODUCED"
    REFERRED_TO_COMMISSION = "REFERRED_TO_COMMISSION"
    CHAMBER_APPROVED = "CHAMBER_APPROVED"
    CHAMBER_REJECTED = "CHAMBER_REJECTED"
    SENT_TO_OTHER_CHAMBER = "SENT_TO_OTHER_CHAMBER"
    MIXED_COMMISSION = "MIXED_COMMISSION"
    CONGRESS_APPROVED = "CONGRESS_APPROVED"
    PROMULGATED = "PROMULGATED"
    PUBLISHED = "PUBLISHED"
    OTHER_VERIFIED_EVENT = "OTHER_VERIFIED_EVENT"


@dataclass(frozen=True)
class LegislativeMatter:
    jurisdiction: str
    matter_type: str
    bulletin_number: str
    canonical_identifier: str
    title: str
    origin_chamber: str | None


@dataclass(frozen=True)
class SourceObservation:
    source_id: str
    resource_type: LegislativeResourceType
    resource_identity: str
    manifest: AcquisitionManifest
    title: str
    matter_status: LegislativeStatus
    current_stage: str | None
    confidence: IdentityConfidence


@dataclass(frozen=True)
class LegislativeEvent:
    event_type: LegislativeEventType
    event_date: date | None
    source_id: str
    source_resource_id: str
    retrieved_at: datetime
    evidence_url: str
    confidence: IdentityConfidence


@dataclass(frozen=True)
class NormalizedLegislativeMatter:
    matter: LegislativeMatter
    observations: tuple[SourceObservation, ...]
    events: tuple[LegislativeEvent, ...]
    matter_status: LegislativeStatus
    current_stage: str | None
    last_verified_event: LegislativeEvent | None
    source_conflict: bool


@dataclass(frozen=True)
class MatterChangeSnapshot:
    canonical_identifier: str
    snapshot_hash: str
    retrieved_at: datetime
    matter_status: LegislativeStatus
    event_keys: tuple[str, ...]


@dataclass(frozen=True)
class MatterSnapshotChange:
    state: str
    significance: str | None
    review_required: bool


def normalize_bulletin_number(value: str) -> str:
    compact = re.sub(r"[\s_]+", "-", value.strip())
    if compact.count("-") != 1:
        raise ValueError("bulletin number must contain one deterministic hyphen")
    number, category = compact.split("-", 1)
    if not (number.isdigit() and category.isdigit() and number and category):
        raise ValueError("bulletin number must be numeric on both sides")
    return f"{int(number)}-{int(category):02d}"


def matter_identity(bulletin_number: str) -> str:
    return f"cl-congreso-boletin-{normalize_bulletin_number(bulletin_number)}"


def normalize_matter(
    matter: LegislativeMatter,
    observations: tuple[SourceObservation, ...],
    events: tuple[LegislativeEvent, ...],
) -> NormalizedLegislativeMatter:
    bulletin = normalize_bulletin_number(matter.bulletin_number)
    if matter.canonical_identifier != matter_identity(bulletin):
        raise ValueError("legislative matter canonical identity does not match bulletin")
    if not observations or any(item.confidence not in {IdentityConfidence.EXACT, IdentityConfidence.STRONG} for item in observations):
        raise ValueError("matter needs verified official observations")
    titles = {" ".join(item.title.lower().split()) for item in observations if item.title}
    source_conflict = len(titles) > 1
    statuses = {item.matter_status for item in observations if item.matter_status is not LegislativeStatus.UNKNOWN}
    if len(statuses) > 1:
        source_conflict = True
    status = next(iter(statuses)) if len(statuses) == 1 else LegislativeStatus.UNKNOWN
    stages = {item.current_stage for item in observations if item.current_stage}
    stage = next(iter(stages)) if len(stages) == 1 else None
    ordered_events = tuple(sorted(events, key=lambda item: (item.event_date or date.min, item.source_id, item.source_resource_id)))
    last_event = ordered_events[-1] if ordered_events else None
    return NormalizedLegislativeMatter(matter, observations, ordered_events, status, stage, last_event, source_conflict)


def snapshot_matter(matter: NormalizedLegislativeMatter, retrieved_at: datetime | None = None) -> MatterChangeSnapshot:
    event_keys = tuple(_event_key(event) for event in matter.events)
    payload = {
        "matter": asdict(matter.matter),
        "observations": [
            {"source": item.source_id, "resource": item.resource_identity, "sha256": item.manifest.sha256, "status": item.matter_status.value, "stage": item.current_stage}
            for item in sorted(matter.observations, key=lambda value: (value.source_id, value.resource_identity))
        ],
        "events": event_keys,
        "status": matter.matter_status.value,
        "stage": matter.current_stage,
        "conflict": matter.source_conflict,
    }
    return MatterChangeSnapshot(matter.matter.canonical_identifier, stable_json_hash(payload), retrieved_at or datetime.now(UTC), matter.matter_status, event_keys)


def compare_snapshots(previous: MatterChangeSnapshot | None, current: MatterChangeSnapshot, *, unavailable: bool = False) -> MatterSnapshotChange:
    if unavailable:
        return MatterSnapshotChange("UNAVAILABLE", None, True)
    if previous is None:
        return MatterSnapshotChange("BASELINE", "MEANINGFUL_CHANGE", True)
    if previous.snapshot_hash == current.snapshot_hash:
        return MatterSnapshotChange("UNCHANGED", None, False)
    major_statuses = {LegislativeStatus.APPROVED_BY_CONGRESS, LegislativeStatus.PROMULGATED, LegislativeStatus.PUBLISHED, LegislativeStatus.IN_FORCE, LegislativeStatus.REJECTED}
    if current.matter_status in major_statuses and current.matter_status != previous.matter_status:
        return MatterSnapshotChange("CHANGED", "MAJOR_CHANGE", True)
    if set(current.event_keys) - set(previous.event_keys):
        return MatterSnapshotChange("CHANGED", "MEANINGFUL_CHANGE", True)
    return MatterSnapshotChange("CHANGED", "MINOR_CHANGE", True)


def _event_key(event: LegislativeEvent) -> str:
    return "|".join((event.event_type.value, event.event_date.isoformat() if event.event_date else "", event.source_id, event.source_resource_id))
