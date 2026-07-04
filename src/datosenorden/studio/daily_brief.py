from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
import json
from pathlib import Path
from typing import Any

from datosenorden.studio.state_events import StateEventImportance, load_state_events

DAILY_BRIEFS_DIR = Path("data/daily_briefs")


@dataclass(frozen=True)
class DailyEntry:
    event_id: str
    topic: str
    category: str
    title: str
    summary: str
    importance: str
    detected_at: str
    source: str
    link_to_topic: str
    link_to_source: str


@dataclass(frozen=True)
class DailySection:
    title: str
    entries: tuple[DailyEntry, ...]


@dataclass(frozen=True)
class DailyBrief:
    generated_at: datetime
    title: str
    sections: tuple[DailySection, ...]


def build_daily_brief(
    events: tuple[dict[str, Any], ...] | list[dict[str, Any]] | None = None,
    *,
    now: datetime | None = None,
    max_age_days: int = 1,
    limit: int = 10,
) -> DailyBrief:
    generated_at = now or datetime.now(UTC)
    rows = list(events) if events is not None else list(load_state_events(limit=100))
    recent = [_normal_event(row) for row in rows if _is_recent(row, generated_at, max_age_days)]
    recent.sort(key=lambda row: (_importance_rank(str(row.get("importance", "LOW"))), str(row.get("detected_at", ""))), reverse=True)
    entries = tuple(_daily_entry(row) for row in recent[:limit])
    return DailyBrief(
        generated_at=generated_at,
        title="Daily Brief desde eventos oficiales",
        sections=(DailySection(title="Eventos importantes recientes", entries=entries),),
    )


def save_daily_brief(
    brief: DailyBrief,
    *,
    output_dir: Path | str = DAILY_BRIEFS_DIR,
) -> Path:
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    path = root / f"daily_brief_{brief.generated_at.strftime('%Y%m%dT%H%M%SZ')}.json"
    path.write_text(json.dumps(daily_brief_to_dict(brief), ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def load_latest_daily_brief(*, root: Path | str = DAILY_BRIEFS_DIR) -> dict[str, Any]:
    directory = Path(root)
    if not directory.exists():
        return {}
    files = sorted(directory.glob("daily_brief_*.json"), reverse=True)
    for path in files:
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            continue
    return {}


def daily_brief_to_dict(brief: DailyBrief) -> dict[str, Any]:
    payload = asdict(brief)
    payload["generated_at"] = brief.generated_at.isoformat()
    return payload


def daily_entries_from_latest(*, root: Path | str = DAILY_BRIEFS_DIR, limit: int = 5) -> tuple[dict[str, Any], ...]:
    brief = load_latest_daily_brief(root=root)
    rows: list[dict[str, Any]] = []
    for section in brief.get("sections", []):
        for entry in section.get("entries", []):
            rows.append(dict(entry))
            if len(rows) >= limit:
                return tuple(rows)
    return tuple(rows)


def _daily_entry(event: dict[str, Any]) -> DailyEntry:
    topic_id = str(event.get("topic_id", ""))
    return DailyEntry(
        event_id=str(event.get("event_id", "")),
        topic=_topic_label(topic_id),
        category=str(event.get("category_id", "")),
        title=str(event.get("title", "Evento oficial detectado")),
        summary=str(event.get("description", "")),
        importance=str(event.get("importance", StateEventImportance.LOW.value)),
        detected_at=str(event.get("detected_at", "")),
        source=str(event.get("source_id", "")),
        link_to_topic="/topic",
        link_to_source=str(event.get("source_url", "")),
    )


def _normal_event(row: dict[str, Any]) -> dict[str, Any]:
    return dict(row)


def _is_recent(row: dict[str, Any], now: datetime, max_age_days: int) -> bool:
    detected = _parse_datetime(str(row.get("detected_at", "")))
    if detected is None:
        return True
    if detected.tzinfo is None:
        detected = detected.replace(tzinfo=UTC)
    return detected >= now - timedelta(days=max_age_days)


def _parse_datetime(value: str) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _importance_rank(value: str) -> int:
    ranks = {"HIGH": 3, "MEDIUM": 2, "LOW": 1}
    return ranks.get(value, 0)


def _topic_label(topic_id: str) -> str:
    labels = {
        "presupuesto-publico": "Presupuesto Publico",
        "actividad-legislativa": "Actividad Legislativa",
    }
    return labels.get(topic_id, topic_id.replace("-", " ").title())