from __future__ import annotations

from types import SimpleNamespace


def _projection() -> dict[str, object]:
    return {
        "title": "Tramitación del proyecto de Inteligencia Económica",
        "type": "Expediente legislativo",
        "question": "¿Qué cambió durante la tramitación del proyecto de Inteligencia Económica y qué sabemos sobre la discusión del secreto bancario?",
        "summary": "El proyecto propuso un Sistema de Inteligencia Económica; cuatro divergencias entre Senado y Cámara llevaron a Comisión Mixta. El corpus incorporado no acredita todavía el resultado final de la regla bancaria ni su vigencia.",
        "status": "PUBLISHED",
        "facts": [{"statement": "D3 corresponde a la Ley N° 18.046.", "evidence": []}],
        "what_is_missing": [{"statement": "No se acreditó el resultado de Comisión Mixta.", "evidence": []}],
        "what_we_cannot_conclude": [{"statement": "No puede afirmarse que el Senado haya rechazado la regla de acceso bancario.", "evidence": []}],
        "sections": {
            "bank_secrecy": [{"statement": "Texto de Cámara sobre secreto bancario.", "evidence": []}],
            "mixed_commission": [{"statement": "D4 trata de clasificadoras de riesgo y auditoría externa.", "evidence": []}],
        },
        "chronology": [{"date": "2026-06-09", "event_type": "SUBSTANTIVE", "text": "El Senado rechaza cuatro modificaciones."}],
        "actors": ["Senado", "Cámara de Diputadas y Diputados", "UAF"],
        "documents": [{"title": "Oficio 36701", "institution": "Senado de la República", "type": "Oficio", "stage": "Tercer trámite", "official_url": "", "date": "2026-06-09"}],
        "sources": ["Senado de la República"],
        "questions": [{"question": "¿El Senado rechazó que la UAF accediera sin autorización judicial?", "answer": "No puede afirmarse con la evidencia incorporada."}],
        "knowledge_cutoff": {"substantive_through": "2026-06-09", "latest_administrative_record": "2026-08-05", "explanation": "Esto indica hasta dónde llega la evidencia incorporada y verificada en este expediente. No significa que no existan actuaciones posteriores."},
    }


def test_citizen_projection_is_mapped_to_reflex_state_with_human_labels() -> None:
    from reflex_app.features.laboratory.state import LaboratoryState

    state = SimpleNamespace()
    LaboratoryState._load_real_expedient(state, _projection())

    assert state.citizen_expedient is True
    assert state.citizen_type == "Expediente legislativo"
    assert state.citizen_question.startswith("¿Qué cambió")
    assert state.citizen_cutoff_substantive == "9 de junio de 2026"
    assert state.citizen_chronology[0]["kind_label"] == "Cambio sustantivo"
    assert state.citizen_actors == ["Senado", "Cámara de Diputadas y Diputados", "UAF"]
    assert "D3 corresponde" in state.citizen_facts[0]["statement"]
    assert "D4 trata" in state.citizen_divergences[0]["statement"]


def test_citizen_renderer_is_generic_and_omits_unprojected_sections() -> None:
    from reflex_app.features.laboratory import components

    source = open(components.__file__, encoding="utf-8").read()
    body = source[source.index("def citizen_expedient_view"):]
    assert "EXP-REAL-LEGISLATIVE-15975-25" not in body
    assert "EXP-REAL-LEGISLATIVE-15975-25" not in body
    assert "No está acreditado con las fuentes incorporadas." in body
    assert "No puede afirmarse con la evidencia incorporada" in body
    assert "rx.cond(LaboratoryState.citizen_documents" in body
    assert "0 documentos" not in body and "Sin datos" not in body
