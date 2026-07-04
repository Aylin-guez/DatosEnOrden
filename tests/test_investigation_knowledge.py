from __future__ import annotations

from datosenorden.maintenance.investigation_knowledge import build_investigation_knowledge
from datosenorden.maintenance.investigation_knowledge import investigation_knowledge_to_dict


def test_build_investigation_knowledge_generates_non_empty_summary() -> None:
    knowledge = build_investigation_knowledge(_payload())

    assert "Entidad Demo" in knowledge.citizen_summary
    assert "2 fuentes" in knowledge.citizen_summary
    assert "evidencia" in knowledge.citizen_summary


def test_build_investigation_knowledge_includes_neutral_warning() -> None:
    knowledge = build_investigation_knowledge(_payload())

    assert "No afirma causalidad" in knowledge.neutrality_notice
    assert "irregularidad" in knowledge.neutrality_notice
    assert "responsabilidad" in knowledge.neutrality_notice
    assert "No afirma causalidad" in knowledge.citizen_summary


def test_key_points_include_evidence_or_sources() -> None:
    knowledge = build_investigation_knowledge(_payload())

    assert 3 <= len(knowledge.key_points) <= 6
    assert all(point.evidence_ids or point.source_ids for point in knowledge.key_points)
    assert any("ev-1" in point.evidence_ids for point in knowledge.key_points)
    assert any("Fuente A" in point.source_ids for point in knowledge.key_points)


def test_suggested_questions_are_generated() -> None:
    knowledge = build_investigation_knowledge(_payload())

    assert any("fuente respalda" in question for question in knowledge.suggested_questions)
    assert any("tiempo" in question for question in knowledge.suggested_questions)
    assert any("entidades aparecen conectadas" in question for question in knowledge.suggested_questions)


def test_minimal_investigation_payload_works() -> None:
    knowledge = build_investigation_knowledge({"entity": {"name": "Entidad minima"}})
    payload = investigation_knowledge_to_dict(knowledge)

    assert payload["citizen_summary"]
    assert payload["key_points"]
    assert payload["limitations"]


def test_knowledge_does_not_invent_findings_or_accusations() -> None:
    knowledge = build_investigation_knowledge(_payload())
    text = " ".join(
        [
            knowledge.citizen_summary,
            knowledge.neutrality_notice,
            *[point.text for point in knowledge.key_points],
        ]
    ).lower()

    forbidden = ["culpable", "delito", "fraude", "corrupcion", "corrupción", "ilegal"]
    assert not any(word in text for word in forbidden)


def _payload() -> dict:
    return {
        "entity": {"name": "Entidad Demo"},
        "dataset_badges": ["Fuente A", "Fuente B"],
        "compact_metrics": {
            "datasets_involved": 2,
            "evidence_count": 3,
            "relationship_count": 2,
            "connected_entities": 1,
        },
        "evidence": [
            {
                "dataset": "Fuente A",
                "links": [
                    {"evidence_id": "ev-1", "title": "Documento 1"},
                    {"evidence_id": "ev-2", "title": "Documento 2"},
                ],
            }
        ],
        "connections": {
            "relationship_cards": [
                {"relationship_id": "rel-1", "name": "Entidad relacionada"},
            ]
        },
        "timeline": [
            {"event_id": "evt-1", "title": "Evento registrado"},
        ],
        "contracts_compras": [{"id": "op-1"}],
    }
