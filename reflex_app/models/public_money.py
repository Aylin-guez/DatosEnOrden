from __future__ import annotations

from typing import TypedDict


class PublicMoneyObservationRow(TypedDict):
    metric_label: str
    display_amount: str
    as_of_date: str
    authority: str
    universe: str
    note: str


class PublicMoneyInstrumentRow(TypedDict):
    identifier: str
    title: str
    purpose: str
    observations: list[PublicMoneyObservationRow]


class PublicMoneySnapshotRow(TypedDict):
    title: str
    as_of_date: str
    cutoff_label: str
    authority: str
    universe: str
    note: str
    observations: list[PublicMoneyObservationRow]


class PublicMoneyActionRow(TypedDict):
    title: str
    note: str
    observations: list[PublicMoneyObservationRow]


class PublicMoneyProceedingRow(TypedDict):
    title: str
    text: str
    kind: str
