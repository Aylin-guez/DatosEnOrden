"""Explicit ingestion gate for one verified matter; no expedition coordination."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
from xml.etree import ElementTree

from sqlalchemy import select
from sqlalchemy.orm import Session

from datosenorden.adapters.legislature.foundation import AcquisitionMethod, IdentityConfidence, OfficialLegislativeAcquisitionClient, OfficialResourceDescriptor
from datosenorden.adapters.legislature.ingestion import build_observation_batch
from datosenorden.adapters.legislature.normalization import LegislativeEvent, LegislativeEventType, LegislativeMatter, LegislativeResourceType, LegislativeStatus, SourceObservation, matter_identity, normalize_bulletin_number, normalize_matter, snapshot_matter
from datosenorden.etl.loaders.graph_loader import GraphLoader
from datosenorden.models import SourceRecord


BULLETIN_15975_25 = "15975-25"
SENATE_PROJECT_URL = "https://tramitacion.senado.cl/wspublico/tramitacion.php?boletin=15975"
CAMARA_VOTES_URL = "https://opendata.camara.cl/wscamaradiputados.asmx/getVotaciones_Boletin?prmBoletin=15975-25"
SENATE_MIXED_COMMISSION_URL = "https://www.senado.cl/comunicaciones/noticias/proyecto-que-crea-subsistema-de-inteligencia-economica-paso-comision-mixta"


class LegislativeIngestionConflictError(RuntimeError):
    pass


@dataclass(frozen=True)
class LegislativePreview:
    matter: object
    snapshot_hash: str
    batches: tuple[object, ...]
    source_record_count: int
    claim_count: int
    evidence_count: int
    entity_count: int


@dataclass(frozen=True)
class LegislativeIngestionResult:
    created: bool
    reused: bool
    source_records: int
    claims: int
    evidences: int
    entities: int
    snapshot_hash: str


def preview_bulletin_15975_25(staging_dir: Path) -> LegislativePreview:
    """Acquire three known official resources and build, but do not write, the graph payload."""
    client = OfficialLegislativeAcquisitionClient(staging_dir=staging_dir)
    senate_project, camera_votes, senate_news = tuple(client.acquire(item) for item in _descriptors())
    title, stage = _senate_project_fields(senate_project.staging_path.read_text(encoding="utf-8", errors="replace"))
    _verify_camera_bulletin(camera_votes.staging_path.read_text(encoding="utf-8", errors="replace"))
    _verify_mixed_commission_news(senate_news.staging_path.read_text(encoding="utf-8", errors="replace"))
    matter = LegislativeMatter("CL", "BILL", BULLETIN_15975_25, matter_identity(BULLETIN_15975_25), title, "Senado")
    senate_observation = SourceObservation("senado", LegislativeResourceType.MATTER_SUMMARY, "bulletin:15975-25:project", senate_project.manifest, title, LegislativeStatus.IN_DISCUSSION, stage, IdentityConfidence.EXACT)
    camera_observation = SourceObservation("camara", LegislativeResourceType.VOTE, "bulletin:15975-25:votes", camera_votes.manifest, title, LegislativeStatus.UNKNOWN, None, IdentityConfidence.EXACT)
    news_observation = SourceObservation("senado", LegislativeResourceType.OFFICIAL_NEWS, "bulletin:15975-25:mixed-commission:2026-06-09", senate_news.manifest, title, LegislativeStatus.UNKNOWN, None, IdentityConfidence.STRONG)
    event = LegislativeEvent(LegislativeEventType.MIXED_COMMISSION, date(2026, 6, 9), "senado", news_observation.resource_identity, senate_news.manifest.retrieved_at, senate_news.manifest.official_url, IdentityConfidence.STRONG)
    normalized = normalize_matter(matter, (senate_observation, camera_observation), (event,))
    if normalized.source_conflict:
        raise LegislativeIngestionConflictError("official source observations conflict")
    batches = (build_observation_batch(normalized, senate_observation, ()), build_observation_batch(normalized, camera_observation, ()), build_observation_batch(normalized, news_observation, (event,)))
    return LegislativePreview(normalized, snapshot_matter(normalized, senate_news.manifest.retrieved_at).snapshot_hash, batches, sum(len(item.source_records) for item in batches), sum(len(item.claims) for item in batches), sum(len(item.evidence) for item in batches), len({item.external_id for batch in batches for item in batch.entities}))


def ingest_bulletin_15975_25(session: Session, preview: LegislativePreview) -> LegislativeIngestionResult:
    """Persist a preview exactly once; conflicting content always fails closed."""
    batches = tuple(preview.batches)
    existing = {row.external_id: row for row in session.scalars(select(SourceRecord).where(SourceRecord.record_type == "legislature:matter_observation")).all()}
    desired = {record.external_id: record for batch in batches for record in batch.source_records}
    if set(existing).intersection(desired) and not all(_same_observation(existing[key].raw_payload, value.raw_payload) for key, value in desired.items() if key in existing):
        raise LegislativeIngestionConflictError("official matter exists with changed or incompatible content")
    if all(key in existing for key in desired):
        return LegislativeIngestionResult(False, True, 0, 0, 0, 0, preview.snapshot_hash)
    if any(key in existing for key in desired):
        raise LegislativeIngestionConflictError("partial matter ingestion requires review")
    for batch in batches:
        GraphLoader(session).load(batch)
    return LegislativeIngestionResult(True, False, preview.source_record_count, preview.claim_count, preview.evidence_count, preview.entity_count, preview.snapshot_hash)


def _descriptors() -> tuple[OfficialResourceDescriptor, ...]:
    return (
        OfficialResourceDescriptor("senado", "bulletin:15975-25", "project_xml", SENATE_PROJECT_URL, AcquisitionMethod.STRUCTURED_ENDPOINT, ("text/xml", "application/xml"), IdentityConfidence.EXACT),
        OfficialResourceDescriptor("camara", "bulletin:15975-25", "vote_xml", CAMARA_VOTES_URL, AcquisitionMethod.STRUCTURED_ENDPOINT, ("text/xml", "application/xml"), IdentityConfidence.EXACT),
        OfficialResourceDescriptor("senado", "bulletin:15975-25", "official_news", SENATE_MIXED_COMMISSION_URL, AcquisitionMethod.DETERMINISTIC_DOCUMENT, ("text/html",), IdentityConfidence.STRONG),
    )


def _senate_project_fields(xml_text: str) -> tuple[str, str | None]:
    root = ElementTree.fromstring(xml_text)
    fields = {_tag(node.tag): " ".join((node.text or "").split()) for node in root.iter()}
    bulletin = normalize_bulletin_number(fields.get("boletin", ""))
    if bulletin != BULLETIN_15975_25:
        raise LegislativeIngestionConflictError("Senate resource returned a different bulletin")
    title = fields.get("titulo", "")
    if not title:
        raise LegislativeIngestionConflictError("Senate resource omitted the matter title")
    return title, fields.get("etapa") or fields.get("estado") or None


def _verify_camera_bulletin(xml_text: str) -> None:
    values = {normalize_bulletin_number((node.text or "").strip()) for node in ElementTree.fromstring(xml_text).iter() if _tag(node.tag).lower() == "boletin" and (node.text or "").strip()}
    if values and values != {BULLETIN_15975_25}:
        raise LegislativeIngestionConflictError("Camera resource contains another bulletin")


def _verify_mixed_commission_news(html_text: str) -> None:
    compact = " ".join(html_text.lower().split())
    if "15975-25" not in compact or "comisi" not in compact or "mixta" not in compact:
        raise LegislativeIngestionConflictError("Senate news does not verify the mixed-commission event")


def _tag(value: str) -> str:
    return value.rsplit("}", 1)[-1].lower()


def _same_observation(existing: object, desired: object) -> bool:
    """Ignore only acquisition timestamps; artifact hashes remain authoritative."""
    if not isinstance(existing, dict) or not isinstance(desired, dict):
        return False
    def stable(payload: dict) -> dict:  # type: ignore[type-arg]
        value = {**payload}
        observation = dict(value.get("observation") or {})
        manifest = dict(observation.get("manifest") or {})
        manifest.pop("retrieved_at", None)
        observation["manifest"] = manifest
        value["observation"] = observation
        return value
    return stable(existing) == stable(desired)
