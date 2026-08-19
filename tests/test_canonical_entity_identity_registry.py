import pytest

from datosenorden.application.canonical_entity_identity import CanonicalNameAuthorityError, bootstrap_public_name_registry


def test_registry_resolves_only_explicit_source_backed_identities() -> None:
    registry = bootstrap_public_name_registry()
    assert registry.get_canonical_public_name("chilecompra:buyer:1593363") == "Dirección de Educación Pública"
    assert registry.get_canonical_public_name("chilecompra:buyer:111870") == "División Logística del Ejército"
    assert registry.get_canonical_public_name("chilecompra:buyer:7383") == "Hospital Clínico Dr. Félix Bulnes Cerda"


def test_missing_identity_fails_closed_without_alias_normalization() -> None:
    with pytest.raises(CanonicalNameAuthorityError, match="CANONICAL_IDENTITY_REVIEW_REQUIRED"):
        bootstrap_public_name_registry().get_canonical_public_name("DIRECCION DE EDUCACION PUBLICA")
