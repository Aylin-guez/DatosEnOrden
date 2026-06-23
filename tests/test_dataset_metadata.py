from __future__ import annotations

from datosenorden.maintenance.dataset_metadata import dataset_category
from datosenorden.maintenance.dataset_metadata import dataset_citizen_summary
from datosenorden.maintenance.dataset_metadata import dataset_metadata_for_name
from datosenorden.maintenance.dataset_metadata import source_contribution_bullets


def test_dataset_metadata_exposes_citizen_facing_fields() -> None:
    metadata = dataset_metadata_for_name("SERVEL")

    assert metadata is not None
    assert metadata.name == "SERVEL"
    assert metadata.category == "authorities"
    assert "authorities" not in metadata.description.lower() or metadata.category == "authorities"
    assert metadata.citizen_summary
    assert source_contribution_bullets("SERVEL")[0].startswith("- ")
    assert dataset_category("SERVEL") == "authorities"
    assert "elected authority" in dataset_citizen_summary("SERVEL").lower()


def test_dataset_metadata_includes_diario_oficial_prototype() -> None:
    metadata = dataset_metadata_for_name("Diario Oficial")

    assert metadata is not None
    assert metadata.name == "Diario Oficial"
    assert metadata.status == "prototype"
    assert metadata.category == "official_publications"
    assert "appointments" in dataset_citizen_summary("Diario Oficial").lower()
    assert source_contribution_bullets("Diario Oficial")[0].startswith("- ")


def test_dataset_metadata_includes_registro_empresas_prototype() -> None:
    metadata = dataset_metadata_for_name("Registro Empresas")

    assert metadata is not None
    assert metadata.name == "Registro Empresas"
    assert metadata.status == "prototype"
    assert metadata.category == "company_registry"
    assert "company registry" in dataset_citizen_summary("Registro Empresas").lower()
    assert source_contribution_bullets("Registro Empresas")[0].startswith("- ")
