from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from enum import StrEnum
import hashlib
import json
from pathlib import Path
from typing import Any

from datosenorden.studio.source_watcher import ChangeCandidate, ChangeType
from datosenorden.studio.topic_classifier import DEFAULT_TOPIC_CONFIG_PATH, TopicClassification

STATE_EVENTS_DIR = Path("data/state_events")


class StateEventType(StrEnum):
    NEW_BILL = "NEW_BILL"
    NEW_DOCUMENT = "NEW_DOCUMENT"
    NEW_VOTE = "NEW_VOTE"
    NEW_REPORT = "NEW_REPORT"
    NEW_DECREE = "NEW_DECREE"
    LAW_PUBLISHED = "LAW_PUBLISHED"
    COMMISSION_UPDATE = "COMMISSION_UPDATE"
    STATUS_CHANGED = "STATUS_CHANGED"
    DOCUMENT_UPDATED = "DOCUMENT_UPDATED"
    OTHER = "OTHER"


class StateEventImportance(StrEnum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


@dataclass(frozen=True)
class StateEvent:
    event_id: str
    topic_id: str
    category_id: str
    source_id: str
    source_url: str
    external_id: str
    title: str
    description: str
    detected_at: datetime
    importance: StateEventImportance
    event_type: StateEventType
    document_available: bool
    evidence_available: bool


@dataclass(frozen=True)
class StateEventSummary:
    total: int
    high: int
    medium: int
    low: int
    latest_detected_at: str


@dataclass(frozen=True)
class EventRule:
    event_type: StateEventType
    keywords: tuple[str, ...]
    external_id_prefixes: tuple[str, ...]
    suggested_actions: tuple[str, ...]
    change_types: tuple[str, ...]


@dataclass(frozen=True)
class ImportanceRule:
    importance: StateEventImportance
    event_types: tuple[StateEventType, ...]
    keywords: tuple[str, ...]
    suggested_actions: tuple[str, ...]


def build_state_event(
    candidate: ChangeCandidate,
    classification: TopicClassification,
    *,
    config_path: Path | str = DEFAULT_TOPIC_CONFIG_PATH,
) -> StateEvent:
    payload = _load_config(config_path)
    event_type = classify_state_event_type(candidate, payload)
    importance = classify_state_event_importance(candidate, event_type, payload)
    event_id = _event_id(candidate, classification, event_type)
    title = _event_title(event_type, classification.topic_id)
    description = _event_description(candidate, classification, event_type)
    return StateEvent(
        event_id=event_id,
        topic_id=classification.topic_id,
        category_id=classification.category_id,
        source_id=candidate.source_id,
        source_url=candidate.url,
        external_id=candidate.external_id,
        title=title,
        description=description,
        detected_at=candidate.detected_at,
        importance=importance,
        event_type=event_type,
        document_available=_document_available(candidate, event_type),
        evidence_available=_evidence_available(candidate),
    )


def build_state_events(
    pairs: list[tuple[ChangeCandidate, TopicClassification]] | tuple[tuple[ChangeCandidate, TopicClassification], ...],
    *,
    include_ignored: bool = False,
    config_path: Path | str = DEFAULT_TOPIC_CONFIG_PATH,
) -> tuple[StateEvent, ...]:
    events: list[StateEvent] = []
    for candidate, classification in pairs:
        if candidate.change_type == ChangeType.IGNORED and not include_ignored:
            continue
        events.append(build_state_event(candidate, classification, config_path=config_path))
    return tuple(events)


def classify_state_event_type(candidate: ChangeCandidate, config: dict[str, Any] | None = None) -> StateEventType:
    payload = config or _load_config(DEFAULT_TOPIC_CONFIG_PATH)
    rules = tuple(_event_rule(row) for row in payload.get("event_type_rules", [])) or _default_event_rules()
    rule = max(rules, key=lambda item: _score_event_rule(candidate, item))
    if _score_event_rule(candidate, rule) <= 0:
        if candidate.change_type == ChangeType.UPDATED:
            return StateEventType.DOCUMENT_UPDATED
        return StateEventType.OTHER
    return rule.event_type


def classify_state_event_importance(
    candidate: ChangeCandidate,
    event_type: StateEventType,
    config: dict[str, Any] | None = None,
) -> StateEventImportance:
    payload = config or _load_config(DEFAULT_TOPIC_CONFIG_PATH)
    rules = tuple(_importance_rule(row) for row in payload.get("importance_rules", [])) or _default_importance_rules()
    rule = max(rules, key=lambda item: _score_importance_rule(candidate, event_type, item))
    if _score_importance_rule(candidate, event_type, rule) <= 0:
        if event_type in {StateEventType.NEW_VOTE, StateEventType.LAW_PUBLISHED}:
            return StateEventImportance.HIGH
        if event_type in {StateEventType.NEW_BILL, StateEventType.NEW_DOCUMENT, StateEventType.NEW_REPORT}:
            return StateEventImportance.MEDIUM
        return StateEventImportance.LOW
    return rule.importance


def save_state_events(
    events: tuple[StateEvent, ...] | list[StateEvent],
    *,
    output_dir: Path | str = STATE_EVENTS_DIR,
    generated_at: datetime | None = None,
) -> Path:
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    timestamp = (generated_at or datetime.now(UTC)).strftime("%Y%m%dT%H%M%SZ")
    path = root / f"state_events_{timestamp}.json"
    payload = {
        "generated_at": (generated_at or datetime.now(UTC)).isoformat(),
        "events": [state_event_to_dict(event) for event in events],
        "summary": state_event_summary(events).__dict__,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def load_state_events(
    *,
    topic_id: str | None = None,
    root: Path | str = STATE_EVENTS_DIR,
    limit: int = 20,
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
        for event in payload.get("events", []):
            if topic_id and str(event.get("topic_id", "")) != topic_id:
                continue
            rows.append(dict(event))
    rows.sort(key=lambda item: str(item.get("detected_at", "")), reverse=True)
    return tuple(rows[:limit])


def state_event_summary(events: tuple[StateEvent, ...] | list[StateEvent]) -> StateEventSummary:
    rows = list(events)
    latest = max((event.detected_at.isoformat() for event in rows), default="")
    return StateEventSummary(
        total=len(rows),
        high=sum(1 for event in rows if event.importance == StateEventImportance.HIGH),
        medium=sum(1 for event in rows if event.importance == StateEventImportance.MEDIUM),
        low=sum(1 for event in rows if event.importance == StateEventImportance.LOW),
        latest_detected_at=latest,
    )


def state_event_to_dict(event: StateEvent) -> dict[str, Any]:
    payload = asdict(event)
    payload["detected_at"] = event.detected_at.isoformat()
    payload["importance"] = event.importance.value
    payload["event_type"] = event.event_type.value
    return payload


def state_event_from_dict(payload: dict[str, Any]) -> StateEvent:
    data = dict(payload)
    detected_at = data.get("detected_at")
    if isinstance(detected_at, str):
        data["detected_at"] = datetime.fromisoformat(detected_at.replace("Z", "+00:00"))
    data["importance"] = StateEventImportance(str(data.get("importance", StateEventImportance.LOW.value)))
    data["event_type"] = StateEventType(str(data.get("event_type", StateEventType.OTHER.value)))
    return StateEvent(**data)


def _load_config(path: Path | str) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _event_rule(row: dict[str, Any]) -> EventRule:
    return EventRule(
        event_type=StateEventType(str(row.get("event_type", StateEventType.OTHER.value))),
        keywords=_tuple_lower(row.get("keywords", [])),
        external_id_prefixes=tuple(str(item) for item in row.get("external_id_prefixes", [])),
        suggested_actions=tuple(str(item) for item in row.get("suggested_actions", [])),
        change_types=tuple(str(item) for item in row.get("change_types", [])),
    )


def _importance_rule(row: dict[str, Any]) -> ImportanceRule:
    return ImportanceRule(
        importance=StateEventImportance(str(row.get("importance", StateEventImportance.LOW.value))),
        event_types=tuple(StateEventType(str(item)) for item in row.get("event_types", [])),
        keywords=_tuple_lower(row.get("keywords", [])),
        suggested_actions=tuple(str(item) for item in row.get("suggested_actions", [])),
    )


def _score_event_rule(candidate: ChangeCandidate, rule: EventRule) -> int:
    haystack = _candidate_text(candidate)
    score = 0
    if candidate.suggested_action in rule.suggested_actions:
        score += 2
    if str(candidate.change_type.value) in rule.change_types:
        score += 2
    if any(candidate.external_id.startswith(prefix) for prefix in rule.external_id_prefixes):
        score += 4
    score += sum(2 for keyword in rule.keywords if keyword and keyword in haystack)
    return score


def _score_importance_rule(candidate: ChangeCandidate, event_type: StateEventType, rule: ImportanceRule) -> int:
    haystack = _candidate_text(candidate)
    score = 0
    if event_type in rule.event_types:
        score += 4
    if candidate.suggested_action in rule.suggested_actions:
        score += 2
    score += sum(2 for keyword in rule.keywords if keyword and keyword in haystack)
    return score


def _candidate_text(candidate: ChangeCandidate) -> str:
    return " ".join([candidate.external_id, candidate.title, candidate.reason, candidate.suggested_action]).lower()


def _event_id(candidate: ChangeCandidate, classification: TopicClassification, event_type: StateEventType) -> str:
    raw = "|".join(
        [
            classification.topic_id,
            candidate.source_id,
            candidate.external_id,
            event_type.value,
            candidate.detected_at.date().isoformat(),
        ]
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:20]


def _event_title(event_type: StateEventType, topic_id: str) -> str:
    labels = {
        StateEventType.NEW_BILL: "Nuevo proyecto detectado",
        StateEventType.NEW_DOCUMENT: "Nuevo documento oficial",
        StateEventType.NEW_VOTE: "Nueva votacion",
        StateEventType.NEW_REPORT: "Nuevo informe",
        StateEventType.NEW_DECREE: "Nuevo decreto",
        StateEventType.LAW_PUBLISHED: "Ley publicada",
        StateEventType.COMMISSION_UPDATE: "Actualizacion de comision",
        StateEventType.STATUS_CHANGED: "Cambio de estado",
        StateEventType.DOCUMENT_UPDATED: "Documento actualizado",
        StateEventType.OTHER: "Evento oficial detectado",
    }
    return f"{labels.get(event_type, 'Evento oficial detectado')} en {topic_id}"


def _event_description(candidate: ChangeCandidate, classification: TopicClassification, event_type: StateEventType) -> str:
    return (
        f"{candidate.title}. Evento {event_type.value} asociado a {classification.topic_id}. "
        f"Fuente: {candidate.source_id}. Accion sugerida: {candidate.suggested_action}."
    )


def _document_available(candidate: ChangeCandidate, event_type: StateEventType) -> bool:
    return bool(candidate.url) and event_type in {
        StateEventType.NEW_BILL,
        StateEventType.NEW_DOCUMENT,
        StateEventType.NEW_VOTE,
        StateEventType.NEW_REPORT,
        StateEventType.LAW_PUBLISHED,
        StateEventType.DOCUMENT_UPDATED,
    }


def _evidence_available(candidate: ChangeCandidate) -> bool:
    return bool(candidate.external_id and candidate.url)


def _default_event_rules() -> tuple[EventRule, ...]:
    return (
        EventRule(StateEventType.NEW_VOTE, ("votacion",), ("camara-votacion-",), ("import_bill", "update_topic"), ()),
        EventRule(StateEventType.NEW_BILL, ("boletin", "proyecto de ley"), ("cl-congreso-boletin-",), ("import_bill",), ()),
    )


def _default_importance_rules() -> tuple[ImportanceRule, ...]:
    return (
        ImportanceRule(StateEventImportance.HIGH, (StateEventType.NEW_VOTE, StateEventType.LAW_PUBLISHED), (), ()),
        ImportanceRule(StateEventImportance.MEDIUM, (StateEventType.NEW_BILL, StateEventType.NEW_DOCUMENT), (), ()),
    )


def _tuple_lower(values: Any) -> tuple[str, ...]:
    return tuple(str(item).lower() for item in values or [])