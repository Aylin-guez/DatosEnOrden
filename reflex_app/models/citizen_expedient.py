from __future__ import annotations

from typing import TypedDict


class CitizenStatementRow(TypedDict):
    key: str
    section: str
    statement: str
    epistemic_class: str
    evidence: list[dict]
    support_text: str


class CitizenPublicSectionRow(TypedDict):
    title: str
    items: list[CitizenStatementRow]
