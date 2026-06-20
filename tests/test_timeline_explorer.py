from __future__ import annotations

from datetime import date
from types import SimpleNamespace
from uuid import UUID

import datosenorden.maintenance.timeline_explorer as timeline_explorer
from datosenorden.maintenance.timeline_explorer import TimelineClaimRow
from datosenorden.maintenance.timeline_explorer import TimelineEvent
from datosenorden.maintenance.timeline_explorer import build_entity_timeline
from datosenorden.maintenance.timeline_explorer import render_entity_timeline_html
from datosenorden.maintenance.timeline_explorer import render_entity_timeline_text
from datosenorden.maintenance.timeline_explorer import timeline_caution_text
from datosenorden.maintenance.timeline_explorer import timeline_explanation_text


ENTITY_ID = UUID("11111111-1111-1111-1111-111111111111")


class _FakeSession:
    def __init__(self, entity):
        self._entity = entity

    def get(self, model, identity):  # noqa: ANN001
        _ = model
        if identity == ENTITY_ID:
            return self._entity
        return None


def _entity():
    return SimpleNamespace(
        id=ENTITY_ID,
        entity_type="PUBLIC_ORGANIZATION",
        name="DIVISION LOGISTICA DEL EJERCITO",
        external_id="buyer-1",
    )


def _claim(claim_id: str, predicate: str, source_record_id: str, valid_from: date | None = None):
    return SimpleNamespace(
        id=UUID(claim_id),
        predicate=predicate,
        valid_from=valid_from,
        source_record_id=UUID(source_record_id),
        source_record=SimpleNamespace(raw_payload={}),
    )


def _row(
    claim,
    dataset_name: str,
    *,
    evidence_count: int = 1,
    relationship_count: int = 1,
    evidence_dates=(),  # noqa: ANN001
):
    return TimelineClaimRow(
        claim=claim,
        dataset_name=dataset_name,
        evidence_dates=tuple(evidence_dates),
        relationship_dates=(),
        evidence_count=evidence_count,
        relationship_count=relationship_count,
    )


def test_timeline_orders_events_ascending(monkeypatch) -> None:
    rows = (
        _row(
            _claim(
                "22222222-2222-2222-2222-222222222222",
                "ISSUES_PURCHASE_ORDER",
                "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
                date(2026, 5, 4),
            ),
            "chilecompra-ordenes-compra",
        ),
        _row(
            _claim(
                "33333333-3333-3333-3333-333333333333",
                "HAS_APPROVED_BUDGET",
                "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
                date(2026, 1, 1),
            ),
            "dipres-budget-sample",
        ),
    )
    monkeypatch.setattr(timeline_explorer, "_load_timeline_claim_rows", lambda session, entity_id: rows)

    timeline = build_entity_timeline(_FakeSession(_entity()), str(ENTITY_ID))

    assert timeline is not None
    assert [event.event_date for event in timeline.events] == [date(2026, 1, 1), date(2026, 5, 4)]
    assert [event.dataset for event in timeline.events] == ["DIPRES", "CHILECOMPRA"]


def test_timeline_merges_multi_dataset_events(monkeypatch) -> None:
    rows = (
        _row(
            _claim(
                "22222222-2222-2222-2222-222222222222",
                "ISSUES_PURCHASE_ORDER",
                "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
                date(2026, 4, 12),
            ),
            "chilecompra-ordenes-compra",
            evidence_count=2,
        ),
        _row(
            _claim(
                "33333333-3333-3333-3333-333333333333",
                "ORGANIZATION_HELD_LOBBY_MEETING",
                "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
                date(2026, 3, 15),
            ),
            "lobby-meeting-sample",
        ),
        _row(
            _claim(
                "44444444-4444-4444-4444-444444444444",
                "ORGANIZATION_HAS_PUBLIC_ROLE",
                "cccccccc-cccc-cccc-cccc-cccccccccccc",
                date(2026, 2, 1),
            ),
            "transparencia-activa-sample",
        ),
    )
    monkeypatch.setattr(timeline_explorer, "_load_timeline_claim_rows", lambda session, entity_id: rows)

    timeline = build_entity_timeline(_FakeSession(_entity()), str(ENTITY_ID))

    assert timeline is not None
    assert [event.dataset for event in timeline.events] == ["TRANSPARENCIA", "LOBBY", "CHILECOMPRA"]
    assert [event.title for event in timeline.events] == ["Role period", "Lobby meeting", "Purchase order"]
    assert timeline.events[-1].evidence_count == 2


def test_render_entity_timeline_text_matches_cli_contract() -> None:
    timeline = SimpleNamespace(
        entity=SimpleNamespace(
            id=str(ENTITY_ID),
            entity_type="PUBLIC_ORGANIZATION",
            name="DIVISION LOGISTICA DEL EJERCITO",
            external_id="buyer-1",
        ),
        events=(
            TimelineEvent(
                event_date=date(2026, 1, 1),
                dataset="DIPRES",
                dataset_name="dipres-budget-sample",
                title="Budget assigned",
                explanation="Registro presupuestario asociado a la entidad.",
                claim_id="22222222-2222-2222-2222-222222222222",
                predicate="HAS_APPROVED_BUDGET",
                source_record_id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
                evidence_count=1,
                relationship_count=0,
            ),
        ),
        explanation=timeline_explanation_text(),
        caution=timeline_caution_text(),
    )

    report = render_entity_timeline_text(timeline)

    assert "entity_timeline:" in report
    assert "DIVISION LOGISTICA DEL EJERCITO" in report
    assert "2026-01-01" in report
    assert "[DIPRES]" in report
    assert "Budget assigned" in report
    assert "evidence_count=1" in report
    assert "relationship_count=0" in report


def test_render_entity_timeline_html_groups_by_year_and_counts() -> None:
    timeline = SimpleNamespace(
        entity=SimpleNamespace(
            id=str(ENTITY_ID),
            entity_type="PUBLIC_ORGANIZATION",
            name="DIVISION LOGISTICA DEL EJERCITO",
            external_id="buyer-1",
        ),
        events=(
            TimelineEvent(
                event_date=date(2025, 12, 1),
                dataset="TRANSPARENCIA",
                dataset_name="transparencia-activa-sample",
                title="Role period",
                explanation="Registro administrativo de cargo o periodo asociado a la entidad.",
                claim_id="22222222-2222-2222-2222-222222222222",
                predicate="ORGANIZATION_HAS_PUBLIC_ROLE",
                source_record_id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
                evidence_count=3,
                relationship_count=2,
            ),
            TimelineEvent(
                event_date=date(2026, 1, 1),
                dataset="DIPRES",
                dataset_name="dipres-budget-sample",
                title="Budget assigned",
                explanation="Registro presupuestario asociado a la entidad.",
                claim_id="33333333-3333-3333-3333-333333333333",
                predicate="HAS_APPROVED_BUDGET",
                source_record_id="bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
                evidence_count=1,
                relationship_count=0,
            ),
        ),
        explanation=timeline_explanation_text(),
        caution=timeline_caution_text(),
    )

    html = render_entity_timeline_html(timeline)

    assert "<!doctype html>" in html
    assert 'class="timeline"' in html
    assert ">2025<" in html
    assert ">2026<" in html
    assert "TRANSPARENCIA" in html
    assert "DIPRES" in html
    assert "evidence 3" in html
    assert "relationships 2" in html
    assert "El orden temporal no implica relacion causal." in html


def test_timeline_human_explanation_is_neutral() -> None:
    assert "eventos publicos" in timeline_explanation_text()
    assert "distintas fuentes" in timeline_explanation_text()
    assert timeline_caution_text() == "El orden temporal no implica relacion causal."
