from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from datosenorden.adapters.legislature import LegislativeAdapter
from datosenorden.adapters.legislature.parser import normalize_bulletin_id
from datosenorden.db.session import SessionLocal
from datosenorden.etl.core.contracts import GraphBatch, SourceRecordPayload
from datosenorden.models.graph import Entity
from datosenorden.models.source_records import SourceRecord

DEFAULT_LEGISLATIVE_BULLETINS = ("8575-05",)
LEGISLATIVE_WATCH_SOURCE_ID = "datos-abiertos-legislativos"


class ChangeType(StrEnum):
    NEW = "new"
    UPDATED = "updated"
    IGNORED = "ignored"


@dataclass(frozen=True)
class WatchSource:
    id: str
    name: str
    url: str
    source_type: str = "official_legislative_source"
    operation: str = "getVotaciones_Boletin"


@dataclass(frozen=True)
class WatchRun:
    source: WatchSource
    started_at: datetime
    since: date | None = None
    limit: int | None = None
    status: str = "completed"
    note: str = "read_only_detection"


@dataclass(frozen=True)
class ChangeCandidate:
    source_id: str
    external_id: str
    title: str
    url: str
    detected_at: datetime
    change_type: ChangeType
    reason: str
    priority: int
    suggested_action: str


@dataclass(frozen=True)
class WatchResult:
    run: WatchRun
    candidates: tuple[ChangeCandidate, ...] = ()
    errors: tuple[str, ...] = ()

    @property
    def new_candidates(self) -> tuple[ChangeCandidate, ...]:
        return tuple(candidate for candidate in self.candidates if candidate.change_type == ChangeType.NEW)

    @property
    def updated_candidates(self) -> tuple[ChangeCandidate, ...]:
        return tuple(candidate for candidate in self.candidates if candidate.change_type == ChangeType.UPDATED)

    @property
    def ignored_candidates(self) -> tuple[ChangeCandidate, ...]:
        return tuple(candidate for candidate in self.candidates if candidate.change_type == ChangeType.IGNORED)


@dataclass(frozen=True)
class ExistingSourceRecordSnapshot:
    payload_hash_by_external_id: dict[str, str] = field(default_factory=dict)
    entity_external_ids: set[str] = field(default_factory=set)

    def has_source_record(self, external_id: str) -> bool:
        return external_id in self.payload_hash_by_external_id

    def payload_hash(self, external_id: str) -> str:
        return self.payload_hash_by_external_id.get(external_id, "")

    def has_entity(self, external_id: str) -> bool:
        return external_id in self.entity_external_ids


LEGISLATIVE_WATCH_SOURCE = WatchSource(
    id=LEGISLATIVE_WATCH_SOURCE_ID,
    name="Datos Abiertos Legislativos Congreso Nacional",
    url="https://opendata.camara.cl/",
)


def watch_legislative_source(
    *,
    since: date | None = None,
    limit: int | None = None,
    bulletins: Sequence[str] | None = None,
    adapter: LegislativeAdapter | None = None,
    session: Session | None = None,
) -> WatchResult:
    source = LEGISLATIVE_WATCH_SOURCE
    run = WatchRun(source=source, started_at=datetime.now(UTC), since=since, limit=limit)
    selected = _select_bulletins(bulletins or DEFAULT_LEGISLATIVE_BULLETINS)
    if not selected:
        return WatchResult(run=run)

    owns_session = session is None
    active_session = session or SessionLocal()
    try:
        snapshot = load_existing_snapshot(active_session)
        active_adapter = adapter or LegislativeAdapter()
        candidates: list[ChangeCandidate] = []
        errors: list[str] = []
        for bulletin in selected:
            try:
                batch = active_adapter.load_bill(bulletin)
            except Exception as exc:  # noqa: BLE001
                errors.append(f"{bulletin}: {type(exc).__name__}: {exc}")
                candidates.append(_error_candidate(source, bulletin, run.started_at, exc))
                continue
            candidates.extend(candidates_from_graph_batch(batch, source=source, snapshot=snapshot, detected_at=run.started_at, since=since))
        return WatchResult(run=run, candidates=tuple(_limit_candidates(candidates, limit)), errors=tuple(errors))
    finally:
        if owns_session:
            active_session.close()


def candidates_from_graph_batch(
    batch: GraphBatch,
    *,
    source: WatchSource = LEGISLATIVE_WATCH_SOURCE,
    snapshot: ExistingSourceRecordSnapshot | None = None,
    detected_at: datetime | None = None,
    since: date | None = None,
) -> tuple[ChangeCandidate, ...]:
    detected = detected_at or datetime.now(UTC)
    existing = snapshot or ExistingSourceRecordSnapshot()
    candidates: list[ChangeCandidate] = []
    bill_external_id = batch.entities[0].external_id if batch.entities else ""
    if bill_external_id and not existing.has_entity(bill_external_id):
        candidates.append(
            ChangeCandidate(
                source_id=source.id,
                external_id=bill_external_id,
                title=f"Boletin legislativo detectado {batch.dataset.version}",
                url=source.url,
                detected_at=detected,
                change_type=ChangeType.NEW,
                reason="El boletin no aparece cargado como entidad local.",
                priority=90,
                suggested_action="import_bill",
            )
        )

    for record in batch.source_records:
        if since and not _record_is_since(record, since):
            candidates.append(_candidate_for_record(record, source=source, detected_at=detected, change_type=ChangeType.IGNORED, reason=f"Registro anterior a {since.isoformat()}.", priority=10, suggested_action="ignore"))
            continue
        if not existing.has_source_record(record.external_id):
            candidates.append(_candidate_for_record(record, source=source, detected_at=detected, change_type=ChangeType.NEW, reason="Registro oficial no encontrado en source_record local.", priority=80, suggested_action="import_bill"))
            continue
        if existing.payload_hash(record.external_id) != record.payload_hash:
            candidates.append(_candidate_for_record(record, source=source, detected_at=detected, change_type=ChangeType.UPDATED, reason="Registro oficial existe localmente, pero el hash del payload cambio.", priority=70, suggested_action="update_topic"))
            continue
        candidates.append(_candidate_for_record(record, source=source, detected_at=detected, change_type=ChangeType.IGNORED, reason="Registro oficial ya existe localmente sin cambios detectados.", priority=0, suggested_action="ignore"))
    return tuple(candidates)


def load_existing_snapshot(session: Session) -> ExistingSourceRecordSnapshot:
    source_records = session.execute(
        select(SourceRecord.external_id, SourceRecord.payload_hash).where(
            SourceRecord.external_id.like("camara-%")
        )
    ).all()
    entities = session.execute(
        select(Entity.external_id).where(Entity.external_id.like("cl-congreso-boletin-%"))
    ).all()
    return ExistingSourceRecordSnapshot(
        payload_hash_by_external_id={str(external_id): str(payload_hash) for external_id, payload_hash in source_records},
        entity_external_ids={str(row[0]) for row in entities if row[0]},
    )


def summarize_watch_result(result: WatchResult) -> str:
    lines = ["source_watcher:"]
    lines.append(f"  source={result.run.source.name}")
    lines.append(f"  since={result.run.since.isoformat() if result.run.since else ''}")
    lines.append(f"  limit={result.run.limit if result.run.limit is not None else ''}")
    lines.append(f"  candidatos_nuevos={len(result.new_candidates)}")
    for candidate in result.new_candidates:
        lines.append(_candidate_line(candidate))
    lines.append(f"  candidatos_actualizados={len(result.updated_candidates)}")
    for candidate in result.updated_candidates:
        lines.append(_candidate_line(candidate))
    lines.append(f"  candidatos_ignorados={len(result.ignored_candidates)}")
    for candidate in result.ignored_candidates:
        lines.append(_candidate_line(candidate))
    lines.append("  acciones_sugeridas=")
    for action, count in _action_counts(result.candidates).items():
        lines.append(f"    - {action}: {count}")
    if result.errors:
        lines.append("  errores=")
        for error in result.errors:
            lines.append(f"    - {error}")
    return "\n".join(lines)


def _candidate_for_record(
    record: SourceRecordPayload,
    *,
    source: WatchSource,
    detected_at: datetime,
    change_type: ChangeType,
    reason: str,
    priority: int,
    suggested_action: str,
) -> ChangeCandidate:
    return ChangeCandidate(
        source_id=source.id,
        external_id=record.external_id,
        title=_record_title(record),
        url=_record_url(record),
        detected_at=detected_at,
        change_type=change_type,
        reason=reason,
        priority=priority,
        suggested_action=suggested_action,
    )


def _error_candidate(source: WatchSource, bulletin: str, detected_at: datetime, exc: Exception) -> ChangeCandidate:
    normalized = normalize_bulletin_id(bulletin)
    return ChangeCandidate(
        source_id=source.id,
        external_id=f"cl-congreso-boletin-{normalized}",
        title=f"Revision legislativa no disponible {normalized}",
        url=source.url,
        detected_at=detected_at,
        change_type=ChangeType.IGNORED,
        reason=f"La fuente no pudo revisarse en esta corrida: {type(exc).__name__}.",
        priority=0,
        suggested_action="ignore",
    )


def _record_title(record: SourceRecordPayload) -> str:
    payload = record.raw_payload or {}
    source_id = str(payload.get("source_id") or record.external_id)
    bulletin = str(payload.get("bulletin_id") or "")
    if record.record_type == "legislative_bill":
        return f"Boletin legislativo {bulletin or source_id}"
    if record.record_type == "legislative_vote":
        return f"Votacion legislativa {source_id}"
    return f"Registro legislativo {record.external_id}"


def _record_url(record: SourceRecordPayload) -> str:
    payload = record.raw_payload or {}
    source_id = str(payload.get("source_id") or record.external_id)
    vote_id = source_id.removeprefix("camara-votacion-")
    if record.record_type == "legislative_vote" and vote_id:
        return f"https://opendata.camara.cl/wscamaradiputados.asmx/getVotacion_Detalle?prmVotacionID={vote_id}"
    return "https://opendata.camara.cl/wscamaradiputados.asmx/getVotaciones_Boletin"


def _record_is_since(record: SourceRecordPayload, since: date) -> bool:
    payload = record.raw_payload or {}
    values: Iterable[Any] = (
        payload.get("date"),
        payload.get("session", {}).get("date") if isinstance(payload.get("session"), dict) else None,
        record.retrieved_at,
    )
    for value in values:
        parsed = _parse_date(value)
        if parsed is not None:
            return parsed >= since
    return True


def _parse_date(value: Any) -> date | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value).strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).date()
    except ValueError:
        try:
            return date.fromisoformat(text[:10])
        except ValueError:
            return None


def _action_counts(candidates: Sequence[ChangeCandidate]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for candidate in candidates:
        counts[candidate.suggested_action] = counts.get(candidate.suggested_action, 0) + 1
    return dict(sorted(counts.items()))


def _candidate_line(candidate: ChangeCandidate) -> str:
    return (
        f"    - {candidate.change_type.value}: {candidate.external_id} | "
        f"accion={candidate.suggested_action} | prioridad={candidate.priority} | {candidate.reason}"
    )


def _limit_candidates(candidates: Sequence[ChangeCandidate], limit: int | None) -> tuple[ChangeCandidate, ...]:
    if limit is None:
        return tuple(candidates)
    return tuple(candidates[: max(0, limit)])


def _select_bulletins(bulletins: Sequence[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(normalize_bulletin_id(item) for item in bulletins if str(item).strip()))