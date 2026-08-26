"""Generic, non-persistent citizen projection for public-money evidence.

Amounts are observations, never a linear accounting state machine. This
contract intentionally does not calculate balances, differences or recoveries.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Mapping


class MoneyMetric(StrEnum):
    BUDGETED = "BUDGETED"
    COMMITTED = "COMMITTED"
    AGREED = "AGREED"
    TRANSFERRED = "TRANSFERRED"
    PAID = "PAID"
    EXECUTED = "EXECUTED"
    RENDERED = "RENDERED"
    UNRENDERED = "UNRENDERED"
    APPROVED = "APPROVED"
    OBSERVED = "OBSERVED"
    REJECTED = "REJECTED"
    INVESTIGATED_AMOUNT = "INVESTIGATED_AMOUNT"
    ACCREDITED_LOSS = "ACCREDITED_LOSS"
    RESTITUTION_ORDERED = "RESTITUTION_ORDERED"
    RECOVERED = "RECOVERED"


class MoneyEpistemicStatus(StrEnum):
    VERIFIED = "VERIFIED"
    UNKNOWN = "UNKNOWN"
    NOT_COMPARABLE = "NOT_COMPARABLE"


@dataclass(frozen=True)
class PublicMoneyObservation:
    metric: MoneyMetric
    amount: int | None
    currency: str
    universe: str
    authority: str
    as_of_date: str | None = None
    period: str | None = None
    epistemic_status: MoneyEpistemicStatus = MoneyEpistemicStatus.VERIFIED
    evidence_ids: tuple[str, ...] = ()
    note: str | None = None


@dataclass(frozen=True)
class PublicMoneyInstrument:
    identifier: str
    title: str
    purpose: str | None
    observations: tuple[PublicMoneyObservation, ...]
    evidence_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class PublicMoneySnapshot:
    title: str
    as_of_date: str
    universe: str
    authority: str
    observations: tuple[PublicMoneyObservation, ...]
    evidence_ids: tuple[str, ...] = ()
    note: str | None = None


@dataclass(frozen=True)
class PublicMoneyAction:
    title: str
    observations: tuple[PublicMoneyObservation, ...]
    evidence_ids: tuple[str, ...] = ()
    note: str | None = None


@dataclass(frozen=True)
class PublicMoneyProceeding:
    title: str
    text: str
    kind: str
    evidence_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class PublicMoneySummary:
    title: str
    universe: PublicMoneyObservation
    instruments: tuple[PublicMoneyInstrument, ...] = ()
    snapshots: tuple[PublicMoneySnapshot, ...] = ()
    subsequent_actions: tuple[PublicMoneyAction, ...] = ()
    oversight: tuple[PublicMoneyProceeding, ...] = ()
    proceedings: tuple[PublicMoneyProceeding, ...] = ()
    limitations: tuple[str, ...] = ()


def public_money_projection(summary: PublicMoneySummary, evidence: Mapping[str, Mapping[str, object]]) -> dict[str, object]:
    """Serialize a generic summary while preserving each observation's support."""
    return {
        "title": summary.title,
        "universe": _observation(summary.universe, evidence),
        "instruments": [_instrument(item, evidence) for item in summary.instruments],
        "snapshots": [_snapshot(item, evidence) for item in summary.snapshots],
        "subsequent_actions": [_action(item, evidence) for item in summary.subsequent_actions],
        "oversight": [_proceeding(item, evidence) for item in summary.oversight],
        "proceedings": [_proceeding(item, evidence) for item in summary.proceedings],
        "limitations": list(summary.limitations),
        "comparability_notice": "Estas cifras describen estados y momentos distintos; no deben sumarse entre sí.",
    }


def _instrument(item: PublicMoneyInstrument, evidence: Mapping[str, Mapping[str, object]]) -> dict[str, object]:
    return {"identifier": item.identifier, "title": item.title, "purpose": item.purpose or "", "observations": [_observation(value, evidence) for value in item.observations], "evidence": _evidence(item.evidence_ids, evidence)}


def _snapshot(item: PublicMoneySnapshot, evidence: Mapping[str, Mapping[str, object]]) -> dict[str, object]:
    return {"title": item.title, "as_of_date": item.as_of_date, "universe": item.universe, "authority": item.authority, "observations": [_observation(value, evidence) for value in item.observations], "evidence": _evidence(item.evidence_ids, evidence), "note": item.note or ""}


def _action(item: PublicMoneyAction, evidence: Mapping[str, Mapping[str, object]]) -> dict[str, object]:
    return {"title": item.title, "observations": [_observation(value, evidence) for value in item.observations], "evidence": _evidence(item.evidence_ids, evidence), "note": item.note or ""}


def _proceeding(item: PublicMoneyProceeding, evidence: Mapping[str, Mapping[str, object]]) -> dict[str, object]:
    return {"title": item.title, "text": item.text, "kind": item.kind, "evidence": _evidence(item.evidence_ids, evidence)}


def _observation(item: PublicMoneyObservation, evidence: Mapping[str, Mapping[str, object]]) -> dict[str, object]:
    return {"metric": item.metric.value, "metric_label": _metric_label(item.metric), "amount": item.amount, "display_amount": _display_amount(item), "currency": item.currency, "universe": item.universe, "authority": item.authority, "as_of_date": item.as_of_date or "", "period": item.period or "", "epistemic_status": item.epistemic_status.value, "note": item.note or "", "evidence": _evidence(item.evidence_ids, evidence)}


def _display_amount(item: PublicMoneyObservation) -> str:
    if item.epistemic_status is MoneyEpistemicStatus.UNKNOWN or item.amount is None:
        return "No acreditada en el corpus disponible."
    return f"${item.amount:,}".replace(",", ".")


def _metric_label(metric: MoneyMetric) -> str:
    return {
        MoneyMetric.BUDGETED: "Presupuestado",
        MoneyMetric.COMMITTED: "Comprometido",
        MoneyMetric.AGREED: "Convenido",
        MoneyMetric.TRANSFERRED: "Transferido",
        MoneyMetric.PAID: "Pagado",
        MoneyMetric.EXECUTED: "Ejecutado",
        MoneyMetric.RENDERED: "Rendido",
        MoneyMetric.UNRENDERED: "Por rendir",
        MoneyMetric.APPROVED: "Aprobado",
        MoneyMetric.OBSERVED: "Observado",
        MoneyMetric.REJECTED: "Rechazado",
        MoneyMetric.INVESTIGATED_AMOUNT: "Monto investigado",
        MoneyMetric.ACCREDITED_LOSS: "Perjuicio acreditado",
        MoneyMetric.RESTITUTION_ORDERED: "Restitución ordenada",
        MoneyMetric.RECOVERED: "Recuperado",
    }[metric]


def _evidence(ids: tuple[str, ...], evidence: Mapping[str, Mapping[str, object]]) -> list[dict[str, object]]:
    return [dict(evidence[item]) for item in ids if item in evidence]
