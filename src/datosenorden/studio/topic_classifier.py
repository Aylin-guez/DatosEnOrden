from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

from datosenorden.studio.source_watcher import ChangeCandidate

DEFAULT_TOPIC_CONFIG_PATH = Path("config/topics/topics.json")


@dataclass(frozen=True)
class TopicClassification:
    category_id: str
    topic_id: str
    confidence: float
    reason: str


@dataclass(frozen=True)
class TopicRule:
    topic_id: str
    category_id: str
    title: str
    keywords: tuple[str, ...]
    source_ids: tuple[str, ...]
    external_ids: tuple[str, ...]
    external_id_prefixes: tuple[str, ...]
    suggested_actions: tuple[str, ...]
    document_types: tuple[str, ...]


@dataclass(frozen=True)
class TopicClassifierConfig:
    default_topic_id: str
    categories: dict[str, tuple[str, ...]]
    rules: tuple[TopicRule, ...]

    def default_rule(self) -> TopicRule:
        return next((rule for rule in self.rules if rule.topic_id == self.default_topic_id), self.rules[0])


def load_topic_classifier_config(path: Path | str = DEFAULT_TOPIC_CONFIG_PATH) -> TopicClassifierConfig:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    categories = {
        str(row["id"]): tuple(str(item).lower() for item in row.get("keywords", []))
        for row in payload.get("categories", [])
    }
    rules = tuple(_topic_rule(row) for row in payload.get("topics", []))
    if not rules:
        raise ValueError("topic classifier config must define at least one topic")
    default_topic_id = str(payload.get("default_topic_id") or rules[0].topic_id)
    return TopicClassifierConfig(default_topic_id=default_topic_id, categories=categories, rules=rules)


def classify_candidate(
    candidate: ChangeCandidate,
    config: TopicClassifierConfig | None = None,
) -> TopicClassification:
    active_config = config or load_topic_classifier_config()
    rule = max(
        active_config.rules,
        key=lambda item: _score_rule(candidate, item, active_config.categories),
    )
    score = _score_rule(candidate, rule, active_config.categories)
    if score <= 0:
        fallback = active_config.default_rule()
        return TopicClassification(
            category_id=fallback.category_id,
            topic_id=fallback.topic_id,
            confidence=0.25,
            reason=f"Fallback configurado: {fallback.topic_id}.",
        )
    confidence = min(0.99, 0.35 + (score * 0.12))
    return TopicClassification(
        category_id=rule.category_id,
        topic_id=rule.topic_id,
        confidence=round(confidence, 2),
        reason=_classification_reason(candidate, rule, score),
    )


def classify_candidates(
    candidates: tuple[ChangeCandidate, ...] | list[ChangeCandidate],
    config: TopicClassifierConfig | None = None,
) -> tuple[TopicClassification, ...]:
    active_config = config or load_topic_classifier_config()
    return tuple(classify_candidate(candidate, active_config) for candidate in candidates)


def _topic_rule(row: dict[str, Any]) -> TopicRule:
    return TopicRule(
        topic_id=str(row["id"]),
        category_id=str(row["category_id"]),
        title=str(row.get("title", row["id"])),
        keywords=_tuple_lower(row.get("keywords", [])),
        source_ids=tuple(str(item) for item in row.get("source_ids", [])),
        external_ids=tuple(str(item) for item in row.get("external_ids", [])),
        external_id_prefixes=tuple(str(item) for item in row.get("external_id_prefixes", [])),
        suggested_actions=tuple(str(item) for item in row.get("suggested_actions", [])),
        document_types=_tuple_lower(row.get("document_types", [])),
    )


def _score_rule(candidate: ChangeCandidate, rule: TopicRule, category_keywords: dict[str, tuple[str, ...]]) -> int:
    haystack = " ".join(
        [
            candidate.external_id,
            candidate.title,
            candidate.reason,
            candidate.suggested_action,
        ]
    ).lower()
    score = 0
    if candidate.source_id in rule.source_ids:
        score += 3
    if candidate.suggested_action in rule.suggested_actions:
        score += 2
    if candidate.external_id in rule.external_ids:
        score += 8
    if any(candidate.external_id.startswith(prefix) for prefix in rule.external_id_prefixes):
        score += 3
    score += sum(2 for keyword in rule.keywords if keyword and keyword in haystack)
    score += sum(1 for keyword in category_keywords.get(rule.category_id, ()) if keyword and keyword in haystack)
    score += sum(1 for doc_type in rule.document_types if doc_type and doc_type in haystack)
    return score


def _classification_reason(candidate: ChangeCandidate, rule: TopicRule, score: int) -> str:
    matches: list[str] = []
    if candidate.source_id in rule.source_ids:
        matches.append(f"source_id={candidate.source_id}")
    if candidate.suggested_action in rule.suggested_actions:
        matches.append(f"suggested_action={candidate.suggested_action}")
    exact_external_id = next((item for item in rule.external_ids if candidate.external_id == item), "")
    if exact_external_id:
        matches.append(f"external_id={exact_external_id}")
    prefix = next((item for item in rule.external_id_prefixes if candidate.external_id.startswith(item)), "")
    if prefix:
        matches.append(f"external_id_prefix={prefix}")
    keyword = next((item for item in rule.keywords if item and item in candidate.title.lower()), "")
    if keyword:
        matches.append(f"keyword={keyword}")
    details = ", ".join(matches) or f"score={score}"
    return f"Asignado a {rule.topic_id} por reglas: {details}."


def _tuple_lower(values: Any) -> tuple[str, ...]:
    return tuple(str(item).lower() for item in values or [])