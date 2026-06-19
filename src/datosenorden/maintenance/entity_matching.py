from __future__ import annotations

from dataclasses import dataclass
import re
import unicodedata

from sqlalchemy import select
from sqlalchemy.orm import Session

from datosenorden.models import Entity

_STOPWORDS = {"DE", "DEL", "LA", "EL", "LOS", "LAS"}


@dataclass(frozen=True)
class EntityMatchCandidate:
    candidate_entity_id: str
    candidate_name: str
    entity_type: str
    score: float
    match_method: str
    explanation: str


def normalize_entity_name(value: object | None) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    uppercase = text.upper()
    decomposed = unicodedata.normalize("NFKD", uppercase)
    ascii_text = "".join(char for char in decomposed if not unicodedata.combining(char))
    tokens = re.findall(r"[A-Z0-9]+", ascii_text)
    filtered = [token for token in tokens if token not in _STOPWORDS]
    if not filtered:
        return None
    return " ".join(filtered)


def match_entity_candidates(
    session: Session,
    *,
    entity_type: str,
    name: str,
    limit: int = 10,
) -> tuple[EntityMatchCandidate, ...]:
    if limit < 1:
        raise ValueError("limit must be greater than zero")

    normalized_query = normalize_entity_name(name)
    if normalized_query is None:
        return ()

    candidates = session.scalars(
        select(Entity)
        .where(Entity.entity_type == entity_type.upper())
        .order_by(Entity.name.asc(), Entity.id.asc())
    ).all()

    results: list[EntityMatchCandidate] = []
    for candidate in candidates:
        normalized_candidate = normalize_entity_name(candidate.name)
        if normalized_candidate is None:
            continue
        score, match_method, explanation = _score_candidate(normalized_query, normalized_candidate)
        if score is None:
            continue
        results.append(
            EntityMatchCandidate(
                candidate_entity_id=str(candidate.id),
                candidate_name=candidate.name,
                entity_type=candidate.entity_type,
                score=score,
                match_method=match_method,
                explanation=explanation,
            )
        )

    results.sort(key=lambda item: (-item.score, item.candidate_name.lower(), item.candidate_entity_id))
    return tuple(results[:limit])


def render_entity_match_candidates_text(
    *,
    entity_type: str,
    name: str,
    candidates: tuple[EntityMatchCandidate, ...],
) -> str:
    lines = [
        "entity_match_candidates:",
        f"query_type={entity_type}",
        f"query_name={name}",
    ]
    if not candidates:
        lines.append("  (no candidates found)")
        return "\n".join(lines)

    for index, candidate in enumerate(candidates, start=1):
        lines.extend(
            [
                f"candidate[{index}]:",
                f"  candidate_entity_id={candidate.candidate_entity_id}",
                f"  candidate_name={candidate.candidate_name}",
                f"  entity_type={candidate.entity_type}",
                f"  score={candidate.score:.4f}",
                f"  match_method={candidate.match_method}",
                f"  explanation={candidate.explanation}",
            ]
        )
    return "\n".join(lines)


def _score_candidate(
    normalized_query: str,
    normalized_candidate: str,
) -> tuple[float | None, str, str]:
    if normalized_query == normalized_candidate:
        return (
            1.0,
            "exact_normalized_match",
            "Normalized names are identical after accent, punctuation, and stopword removal.",
        )

    if normalized_query in normalized_candidate or normalized_candidate in normalized_query:
        return (
            0.95,
            "contains_normalized_match",
            "One normalized name contains the other after accent, punctuation, and stopword removal.",
        )

    query_tokens = set(normalized_query.split())
    candidate_tokens = set(normalized_candidate.split())
    shared_tokens = sorted(query_tokens & candidate_tokens)
    if not shared_tokens:
        return None, "no_match", "No shared tokens after normalization."

    union = query_tokens | candidate_tokens
    score = len(shared_tokens) / len(union) if union else 0.0
    if score < 0.4:
        return None, "no_match", "Token overlap is below the match threshold."

    return (
        round(score, 4),
        "token_overlap",
        "Shared normalized tokens: " + ", ".join(shared_tokens),
    )
