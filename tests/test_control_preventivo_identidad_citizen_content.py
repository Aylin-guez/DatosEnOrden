from datetime import UTC, datetime

from datosenorden.application.provenance.models import ProvenanceClass
from datosenorden.application.provenance.service import PROVENANCE_MANIFEST
from datosenorden.application.real_expedient.citizen_projection import (
    citizen_expedient_projection,
)
from datosenorden.application.real_expedient.control_preventivo_identidad import (
    EXPEDIENT_ID,
    QUESTION,
    TITLE,
    control_preventivo_identidad_citizen_context,
    provision_control_preventivo_identidad,
)
from datosenorden.application.real_expedient.models import (
    EpistemicClass,
    ExpedientReferences,
    ExpedientSpecification,
    ExpedientStatus,
    NarrativeStatement,
    StoredExpedient,
)
from datosenorden.application.search.service import run_workspace_search
from datosenorden.db.session import SessionLocal


def _projection() -> dict[str, object]:
    stored = StoredExpedient(
        ExpedientSpecification(
            EXPEDIENT_ID,
            TITLE,
            QUESTION,
            "Resumen.",
            ProvenanceClass.REAL,
            ExpedientStatus.PUBLISHED,
            1,
            ExpedientReferences(("claim",), ("evidence",)),
            (
                NarrativeStatement(
                    "preventive",
                    "comparison",
                    "Regla preventiva.",
                    EpistemicClass.FACT,
                    ("claim",),
                    ("evidence",),
                ),
                NarrativeStatement(
                    "investigative",
                    "comparison",
                    "Regla investigativa.",
                    EpistemicClass.FACT,
                    ("claim",),
                    ("evidence",),
                ),
            ),
        ),
        "control-identidad-v1",
        datetime(2026, 8, 26, tzinfo=UTC),
        datetime(2026, 8, 26, tzinfo=UTC),
    )
    return citizen_expedient_projection(stored, control_preventivo_identidad_citizen_context())


def test_control_preventivo_context_separates_current_rule_from_limits() -> None:
    context = control_preventivo_identidad_citizen_context()
    answers = {item.question: item.answer for item in context.answers}

    assert EXPEDIENT_ID == "EXP-REAL-CONTROL-PREVENTIVO-IDENTIDAD"
    assert TITLE == "Control preventivo de identidad"
    assert len(context.answers) == 18
    assert "no exige un indicio individual previo" in answers["¿Me pueden controlar sin sospechar que cometí un delito?"]
    assert "No se encontró" in answers["¿Pueden revisar mi teléfono?"]
    assert "prohibición absoluta" in answers["¿Pueden obligarme a desbloquear un teléfono o celular?"]
    assert "No." in answers["¿El Tribunal Constitucional declaró constitucional todo el control preventivo?"]


def test_control_preventivo_context_preserves_epistemic_boundaries() -> None:
    answers = {item.question: item.answer for item in control_preventivo_identidad_citizen_context().answers}

    assert "procedimiento distinto" in answers["¿Qué diferencia hay con el control investigativo?"]
    assert "no equivale" in answers["¿Pueden revisar mi teléfono?"]
    assert "si no pueden verificar identidad" in answers["¿Pueden llevarme a una comisaría si no pueden identificarme?"]
    assert "mayores de 18" in answers["¿Qué pasa si soy menor de edad?"]


def test_control_preventivo_projection_exposes_a_generic_comparison_section() -> None:
    projection = _projection()

    assert projection["title"] == TITLE
    assert projection["version"] == 1
    assert projection["official_title"] == "Ley N° 20.931, artículos 12 y 12 bis"
    assert projection["public_sections"] == [
        {
            "title": "Control preventivo vs. control investigativo",
            "items": projection["sections"]["comparison"],
        }
    ]
    assert all(item.official_url and item.official_url.startswith("https://") for item in control_preventivo_identidad_citizen_context().evidence)


def test_control_preventivo_real_corpus_has_exact_public_provenance_and_is_idempotent() -> None:
    assert any(
        item.source_name == "LeyChile"
        and item.dataset_name == "control-preventivo-identidad"
        and item.dataset_version == "1092269@2026-08-12"
        and item.provenance_class is ProvenanceClass.REAL
        and item.public_countable
        for item in PROVENANCE_MANIFEST
    )
    with SessionLocal() as session:
        first = provision_control_preventivo_identidad(session)
        session.commit()
        second = provision_control_preventivo_identidad(session)
        session.commit()

    assert first.created is True
    assert second.created is False
    assert second.expedient.specification.version == 1


def test_control_preventivo_citizen_searches_resolve_to_the_direct_route() -> None:
    with SessionLocal() as session:
        provision_control_preventivo_identidad(session)
        session.commit()

    target = "/laboratory/expedient?id=EXP-REAL-CONTROL-PREVENTIVO-IDENTIDAD"
    terms = (
        "control de identidad",
        "me pueden pedir carnet",
        "revisar mochila",
        "revisar teléfono",
        "desbloquear celular",
        "control investigativo",
        "Ley 20.931",
        "artículo 12",
    )
    for term in terms:
        assert any(row["action_href"] == target for row in run_workspace_search(term))
