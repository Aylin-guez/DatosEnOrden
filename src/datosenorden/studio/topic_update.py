from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
import json
from pathlib import Path
from typing import Any

from datosenorden.studio.source_watcher import ChangeCandidate, ChangeType
from datosenorden.studio.topic_classifier import TopicClassification
from datosenorden.studio.state_events import build_state_event, state_event_to_dict

TOPIC_UPDATES_DIR = Path("data/topic_updates")


@dataclass(frozen=True)
class TopicUpdate:
    topic_id: str
    title: str
    source_id: str
    external_id: str
    detected_at: datetime
    summary: str
    suggested_action: str
    timeline_event: dict[str, Any]
    status: str
    category_id: str
    confidence: float
    classification_reason: str
    source_url: str
    state_event: dict[str, Any] = field(default_factory=dict)


def build_topic_update(candidate: ChangeCandidate, classification: TopicClassification) -> TopicUpdate:
    status = _status_for_candidate(candidate)
    title = _title_for_update(candidate, classification)
    summary = _summary_for_update(candidate, classification)
    state_event = build_state_event(candidate, classification)
    timeline_event = {
        "date": candidate.detected_at.date().isoformat(),
        "source": candidate.source_id,
        "title": title,
        "description": summary,
        "status": status,
        "suggested_action": candidate.suggested_action,
        "external_id": candidate.external_id,
        "url": candidate.url,
        "origin": "state_event",
        "event_id": state_event.event_id,
        "event_type": state_event.event_type.value,
        "importance": state_event.importance.value,
        "document_available": state_event.document_available,
        "evidence_available": state_event.evidence_available,
    }
    return TopicUpdate(
        topic_id=classification.topic_id,
        title=title,
        source_id=candidate.source_id,
        external_id=candidate.external_id,
        detected_at=candidate.detected_at,
        summary=summary,
        suggested_action=candidate.suggested_action,
        timeline_event=timeline_event,
        status=status,
        category_id=classification.category_id,
        confidence=classification.confidence,
        classification_reason=classification.reason,
        source_url=candidate.url,
        state_event=state_event_to_dict(state_event),
    )


def build_topic_updates(
    pairs: list[tuple[ChangeCandidate, TopicClassification]] | tuple[tuple[ChangeCandidate, TopicClassification], ...],
    *,
    include_ignored: bool = False,
) -> tuple[TopicUpdate, ...]:
    updates: list[TopicUpdate] = []
    for candidate, classification in pairs:
        if candidate.change_type == ChangeType.IGNORED and not include_ignored:
            continue
        updates.append(build_topic_update(candidate, classification))
    return tuple(updates)


def save_topic_updates(
    updates: tuple[TopicUpdate, ...] | list[TopicUpdate],
    *,
    output_dir: Path | str = TOPIC_UPDATES_DIR,
    generated_at: datetime | None = None,
) -> Path:
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    timestamp = (generated_at or datetime.now(UTC)).strftime("%Y%m%dT%H%M%SZ")
    path = root / f"topic_updates_{timestamp}.json"
    payload = {
        "generated_at": (generated_at or datetime.now(UTC)).isoformat(),
        "updates": [topic_update_to_dict(update) for update in updates],
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def load_topic_updates(
    *,
    topic_id: str | None = None,
    root: Path | str = TOPIC_UPDATES_DIR,
    limit: int = 10,
) -> tuple[dict[str, Any], ...]:
    directory = Path(root)
    if not directory.exists():
        return ()
    rows: list[dict[str, Any]] = []
    for path in sorted(directory.glob("*.json"), reverse=True):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            continue
        for update in payload.get("updates", []):
            if topic_id and str(update.get("topic_id", "")) != topic_id:
                continue
            rows.append(dict(update))
            if len(rows) >= limit:
                return tuple(rows)
    return tuple(rows)


def topic_update_to_dict(update: TopicUpdate) -> dict[str, Any]:
    payload = asdict(update)
    payload["detected_at"] = update.detected_at.isoformat()
    return payload


def topic_update_from_dict(payload: dict[str, Any]) -> TopicUpdate:
    data = dict(payload)
    detected_at = data.get("detected_at")
    if isinstance(detected_at, str):
        data["detected_at"] = datetime.fromisoformat(detected_at.replace("Z", "+00:00"))
    return TopicUpdate(**data)


def _status_for_candidate(candidate: ChangeCandidate) -> str:
    if candidate.change_type == ChangeType.NEW:
        return "detected"
    if candidate.change_type == ChangeType.UPDATED:
        return "updated"
    return "ignored"


def _title_for_update(candidate: ChangeCandidate, classification: TopicClassification) -> str:
    if candidate.change_type == ChangeType.UPDATED:
        return f"Actualizacion detectada en {classification.topic_id}"
    return f"Novedad detectada en {classification.topic_id}"


def _summary_for_update(candidate: ChangeCandidate, classification: TopicClassification) -> str:
    return (
        f"{candidate.title}. Fuente: {candidate.source_id}. "
        f"Accion sugerida: {candidate.suggested_action}. "
        f"Clasificacion: {classification.reason}"
    )