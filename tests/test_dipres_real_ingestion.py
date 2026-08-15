from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from datosenorden.adapters.dipres.ingestion import DEP_EXTERNAL_ID, DIPRES_DATASET_NAME, DIPRES_RECORD_TYPE, build_dep_real_batch
from datosenorden.adapters.dipres.models import AcquiredResource, ResourceDefinition
from datosenorden.adapters.dipres.parser import parse_budget_csv
from datosenorden.application.dipres.dep_real_ingestion import DipresRealIngestionConflictError, ingest_dep_second_quarter_2026
from datosenorden.application.provenance import PROVENANCE_MANIFEST
from datosenorden.etl.core.contracts import EntityRecord, EntityType


def _parsed(tmp_path: Path):
    path = tmp_path / "dep.csv"
    path.write_text("Partida;Capitulo;Programa;Subtitulo;Item;Asignacion;Denominacion;Presupuesto Inicial;Presupuesto Vigente;Ejecucion Acumulada a Segundo Trimestre\n09;17;01;21;;;GASTOS EN PERSONAL;10;9;4\n", encoding="utf-8")
    resource = ResourceDefinition("https://www.dipres.gob.cl/597/page", "https://www.dipres.gob.cl/597/dep.csv", "Segundo Trimestre 2026")
    return parse_budget_csv(AcquiredResource(resource, datetime.now(UTC), "d5ff03c5c950656751b057e344142b7eb6e29b7b6a1876fe415c380e560d82ba", path.stat().st_size, "text/csv", path, False))


def _organization() -> EntityRecord:
    return EntityRecord(EntityType.PUBLIC_ORGANIZATION, "DIRECCION DE EDUCACION PUBLICA", DEP_EXTERNAL_ID, normalized_key="direccion-de-educacion-publica")


def test_real_batch_is_single_certified_slice_with_direct_claims(tmp_path: Path) -> None:
    batch = build_dep_real_batch(_parsed(tmp_path), _organization())
    assert batch.dataset.name == DIPRES_DATASET_NAME
    assert batch.source_records[0].record_type == DIPRES_RECORD_TYPE
    assert len(batch.source_records) == 1
    assert len(batch.evidence) == 1
    assert len(batch.claims) == 4
    assert len(batch.public_relationships) == 1
    assert batch.public_relationships[0].metadata["causal_link"] is False
    assert batch.source_records[0].raw_payload["partida"] == "09"


def test_real_batch_rejects_any_non_certified_organization(tmp_path: Path) -> None:
    other = EntityRecord(EntityType.PUBLIC_ORGANIZATION, "Otra institución", "chilecompra:buyer:other")
    with pytest.raises(ValueError, match="certified ChileCompra organization"):
        build_dep_real_batch(_parsed(tmp_path), other)


def test_real_dipres_dataset_has_one_canonical_provenance_entry() -> None:
    entries = [item for item in PROVENANCE_MANIFEST if item.dataset_name == DIPRES_DATASET_NAME]
    assert len(entries) == 1
    assert entries[0].provenance_class.value == "REAL"
    assert entries[0].public_countable is True


def test_incompatible_resource_hash_fails_before_any_database_access(tmp_path: Path) -> None:
    path = tmp_path / "different.csv"
    path.write_text("Partida;Capitulo;Programa\n09;17;01\n", encoding="utf-8")

    class NoDatabaseAccess:
        def scalar(self, *_args, **_kwargs):  # noqa: ANN002, ANN003
            raise AssertionError("database access is forbidden for incompatible content")

    with pytest.raises(DipresRealIngestionConflictError, match="hash"):
        ingest_dep_second_quarter_2026(NoDatabaseAccess(), path)  # type: ignore[arg-type]
