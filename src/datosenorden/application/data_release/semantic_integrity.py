"""Fail-closed semantic text integrity checks for public data packages."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from datosenorden.application.canonical_entity_identity import (
    CanonicalNameAuthorityError,
    bootstrap_public_name_registry,
)


class PublicTextIntegrityError(ValueError):
    """Raised when a current public canonical field contains lossy text."""


_MOJIBAKE_MARKERS = (
    "\ufffd",
    "Ã¡",
    "Ã©",
    "Ã­",
    "Ã³",
    "Ãº",
    "Ã",
    "Ã‰",
    "Ã",
    "Ã“",
    "Ãš",
    "Ã±",
    "Ã‘",
    "Ã¼",
    "Ãœ",
    "Â¿",
    "Â¡",
    "â€",
    "ðŸ",
)
_CANONICAL_VERSION_FIELDS = ("title", "question", "summary")


def validate_public_text_integrity(
    rows: Mapping[str, Sequence[Mapping[str, Any]]],
) -> None:
    """Validate current public labels and authoritative ChileCompra identities.

    Historical superseded versions remain immutable provenance.  The public
    certification boundary is the current version selected by each REAL root.
    """
    roots = {
        str(row["expedient_id"]): int(row["current_version"])
        for row in rows.get("real_expedient", ())
    }
    versions = {
        (str(row["expedient_id"]), int(row["version"])): row
        for row in rows.get("real_expedient_version", ())
    }
    current_versions: dict[str, Mapping[str, Any]] = {}
    for expedient_id, version in roots.items():
        row = versions.get((expedient_id, version))
        if row is None:
            raise PublicTextIntegrityError(
                f"current public version is missing for {expedient_id}@{version}"
            )
        current_versions[expedient_id] = row
        for field in _CANONICAL_VERSION_FIELDS:
            _validate_canonical_text(
                row.get(field),
                location=f"real_expedient_version:{expedient_id}@{version}:{field}",
                allow_terminal_question=field == "question",
            )

    for row in rows.get("real_expedient_narrative", ()):
        expedient_id = str(row["expedient_id"])
        version = int(row["version"])
        if roots.get(expedient_id) != version:
            continue
        _validate_canonical_text(
            row.get("statement"),
            location=(
                "real_expedient_narrative:"
                f"{expedient_id}@{version}:{row.get('statement_id', '<unknown>')}"
            ),
            allow_terminal_question=False,
        )

    _validate_chilecompra_authoritative_names(rows, roots, current_versions)


def _validate_canonical_text(
    value: Any,
    *,
    location: str,
    allow_terminal_question: bool,
) -> None:
    if not isinstance(value, str) or not value.strip():
        raise PublicTextIntegrityError(f"empty canonical public text at {location}")
    if value.encode("utf-8").decode("utf-8") != value:
        raise PublicTextIntegrityError(f"UTF-8 round-trip mismatch at {location}")
    if any(marker in value for marker in _MOJIBAKE_MARKERS):
        raise PublicTextIntegrityError(f"known mojibake marker at {location}")
    question_positions = [index for index, character in enumerate(value) if character == "?"]
    allowed = [len(value) - 1] if allow_terminal_question and value.endswith("?") else []
    if question_positions != allowed:
        raise PublicTextIntegrityError(
            f"suspicious lossy question-mark substitution at {location}"
        )


def _validate_chilecompra_authoritative_names(
    rows: Mapping[str, Sequence[Mapping[str, Any]]],
    roots: Mapping[str, int],
    current_versions: Mapping[str, Mapping[str, Any]],
) -> None:
    entities = {str(row["id"]): row for row in rows.get("entity", ())}
    references: dict[tuple[str, int], list[Mapping[str, Any]]] = {}
    for row in rows.get("real_expedient_reference", ()):
        key = (str(row["expedient_id"]), int(row["version"]))
        references.setdefault(key, []).append(row)
    registry = bootstrap_public_name_registry()
    for expedient_id, version in roots.items():
        if not expedient_id.startswith("EXP-REAL-CHILECOMPRA-"):
            continue
        buyer_ids: list[str] = []
        for reference in references.get((expedient_id, version), ()):
            if reference.get("reference_type") != "entity":
                continue
            entity = entities.get(str(reference.get("reference_id")))
            external_id = str((entity or {}).get("external_id", ""))
            if external_id.startswith("chilecompra:buyer:"):
                buyer_ids.append(external_id)
        if len(buyer_ids) != 1:
            raise PublicTextIntegrityError(
                f"current ChileCompra expedient lacks one authoritative buyer at "
                f"{expedient_id}@{version}"
            )
        try:
            canonical_name = registry.get_canonical_public_name(buyer_ids[0])
        except CanonicalNameAuthorityError as exc:
            raise PublicTextIntegrityError(
                f"unverified current ChileCompra buyer at {expedient_id}@{version}"
            ) from exc
        row = current_versions[expedient_id]
        for field in ("title", "summary"):
            if canonical_name not in str(row[field]):
                raise PublicTextIntegrityError(
                    f"authoritative buyer-name mismatch at "
                    f"real_expedient_version:{expedient_id}@{version}:{field}"
                )
