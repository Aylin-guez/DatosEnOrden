from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import verify_mvp_demo


def test_verify_mvp_demo_passes_with_nonzero_service_data(monkeypatch, capsys) -> None:
    monkeypatch.setattr(verify_mvp_demo, "_check_database", lambda: ("database reachable", True, "ok"))
    monkeypatch.setattr(verify_mvp_demo, "_check_reflex_import", lambda: ("Reflex import smoke test", True, "ok"))
    monkeypatch.setattr(
        verify_mvp_demo,
        "load_complete_demo_case_payload",
        lambda: {"main_entity": {"name": verify_mvp_demo.MAIN_ENTITY}},
    )
    monkeypatch.setattr(
        verify_mvp_demo,
        "resolve_investigation_target",
        lambda value: {
            "found": True,
            "entity_id": "11111111-1111-1111-1111-111111111111",
            "entity_name": verify_mvp_demo.MAIN_ENTITY,
            "matched_by": "exact_name",
            "warning": "",
        },
    )
    monkeypatch.setattr(
        verify_mvp_demo,
        "resolve_canonical_expediente_target",
        lambda value: {
            "found": True,
            "canonical_entity_id": "11111111-1111-1111-1111-111111111111",
            "canonical_entity_name": verify_mvp_demo.MAIN_ENTITY,
            "is_record": False,
        },
    )
    monkeypatch.setattr(
        verify_mvp_demo,
        "get_investigation",
        lambda entity_id: {
            "found": True,
            "resolution": {"entity_id": entity_id},
            "compact_metrics": {
                "datasets_involved": 7,
                "evidence_count": 33,
                "relationship_count": 34,
            },
        },
    )
    monkeypatch.setattr(
        verify_mvp_demo,
        "get_entity_comparison",
        lambda entity_id: {"coverage_summary": "Across these sources there are 37 claims, 34 relationships, and 33 evidence items."},
    )
    monkeypatch.setattr(
        verify_mvp_demo,
        "get_source_trace",
        lambda entity_id: {"sources": [{"dataset": "ChileCompra"}, {"dataset": "DIPRES"}, {"dataset": "Lobby"}]},
    )
    monkeypatch.setattr(
        verify_mvp_demo,
        "get_investigation_timeline",
        lambda entity_id: {"years": [{"categories": [{"items": [1, 2, 3]}, {"items": [4, 5]}]}]},
    )
    monkeypatch.setattr(verify_mvp_demo, "get_investigation_story", lambda entity_id: {"summary": "Neutral summary."})
    monkeypatch.setattr(
        verify_mvp_demo,
        "search_workspace",
        lambda query: {"matches": [{"entity_id": "11111111-1111-1111-1111-111111111111", "canonical_entity_id": "11111111-1111-1111-1111-111111111111"}]},
    )
    monkeypatch.setattr(
        verify_mvp_demo,
        "get_guided_discovery_options",
        lambda category: [{"entity_id": "budget-1" if category == "budgets" else "option-1"}],
    )
    monkeypatch.setattr(
        verify_mvp_demo,
        "get_record_context",
        lambda value: {"canonical_entity_id": "11111111-1111-1111-1111-111111111111", "is_record": True},
    )

    exit_code = verify_mvp_demo.main()

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "mvp_demo_verification:" in captured.out
    assert "ok - investigation service" in captured.out


def test_verify_mvp_demo_fails_when_main_entity_is_missing(monkeypatch) -> None:
    monkeypatch.setattr(verify_mvp_demo, "_check_database", lambda: ("database reachable", True, "ok"))
    monkeypatch.setattr(verify_mvp_demo, "_check_reflex_import", lambda: ("Reflex import smoke test", True, "ok"))
    monkeypatch.setattr(
        verify_mvp_demo,
        "load_complete_demo_case_payload",
        lambda: {"main_entity": {"name": verify_mvp_demo.MAIN_ENTITY}},
    )
    monkeypatch.setattr(
        verify_mvp_demo,
        "resolve_investigation_target",
        lambda value: {"found": False, "entity_id": "", "warning": "missing"},
    )
    monkeypatch.setattr(verify_mvp_demo, "resolve_canonical_expediente_target", lambda value: {"found": False, "canonical_entity_id": ""})
    monkeypatch.setattr(verify_mvp_demo, "get_investigation", lambda entity_id: {"found": False, "compact_metrics": {}})
    monkeypatch.setattr(verify_mvp_demo, "get_entity_comparison", lambda entity_id: {"coverage_summary": ""})
    monkeypatch.setattr(verify_mvp_demo, "get_source_trace", lambda entity_id: {"sources": []})
    monkeypatch.setattr(verify_mvp_demo, "get_investigation_timeline", lambda entity_id: {"years": []})
    monkeypatch.setattr(verify_mvp_demo, "get_investigation_story", lambda entity_id: {"summary": ""})
    monkeypatch.setattr(verify_mvp_demo, "search_workspace", lambda query: {"matches": []})
    monkeypatch.setattr(verify_mvp_demo, "get_guided_discovery_options", lambda category: [])
    monkeypatch.setattr(verify_mvp_demo, "get_record_context", lambda value: {})

    exit_code = verify_mvp_demo.main()

    assert exit_code == 1
