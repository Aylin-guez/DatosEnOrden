from datetime import UTC, datetime

import pytest

from datosenorden.application.provenance.models import ProvenanceClass
from datosenorden.application.real_expedient.composition import (
    ExpedientCompositionError,
    compose_versioned_enrichment,
    extract_historical_enrichment,
)
from datosenorden.application.real_expedient.models import (
    EpistemicClass, ExpedientReferences, ExpedientSpecification, ExpedientStatus,
    NarrativeStatement, StoredExpedient,
)


def _stored(version, title, refs, statements=()):
    return StoredExpedient(
        ExpedientSpecification("EXP-REAL-CHILECOMPRA-1002584-197-CM26", title, "¿Qué muestran los registros públicos?", "Resumen", ProvenanceClass.REAL, ExpedientStatus.PUBLISHED, version, refs, statements),
        f"fp-{version}", datetime.now(UTC), datetime.now(UTC),
    )


def test_extract_and_compose_preserves_only_certified_enrichment():
    base = _stored(1, "corrupt base", ExpedientReferences(("c-base",), ("e-base",), source_ids=("s-base",)))
    dipres = NarrativeStatement("dipres-budget", "budget", "DIPRES factual", EpistemicClass.FACT, ("c-dipres",), ("e-dipres",))
    v2 = _stored(2, "corrupt v2", ExpedientReferences(("c-base", "c-dipres"), ("e-base", "e-dipres"), source_ids=("s-base", "s-dipres")), (dipres,))
    enrichment = extract_historical_enrichment(base, v2)
    clean = _stored(1, "Dirección de Educación Pública", ExpedientReferences(("c-base-clean",), ("e-base-clean",), source_ids=("s-base-clean",))).specification
    v3 = compose_versioned_enrichment(clean, enrichment, version=3)
    assert v3.title == "Dirección de Educación Pública"
    assert v3.references.claim_ids == ("c-base-clean", "c-dipres")
    assert v3.statements == (dipres,)
    assert v2.specification.title == "corrupt v2"


def test_rejects_cross_boundary_supports_and_reference_duplication():
    base = _stored(1, "base", ExpedientReferences(("c",), ("e",)))
    invalid = NarrativeStatement("new", "x", "fact", EpistemicClass.FACT, ("c",), ("e",))
    v2 = _stored(2, "v2", ExpedientReferences(("c",), ("e",)), (invalid,))
    with pytest.raises(ExpedientCompositionError):
        extract_historical_enrichment(base, v2)
