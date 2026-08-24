from __future__ import annotations

from datetime import date
from datetime import UTC, datetime
from decimal import Decimal
import os
from pathlib import Path

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from datosenorden.application.canonical_entity_identity import bootstrap_public_name_registry
from datosenorden.application.chilecompra_expedient import (
    ChileCompraCanonicalIdentityResolver, ChileCompraValidatedContent,
    CorrectiveStatus, repair_chilecompra_expedient,
)
from datosenorden.application.data_release.contract import PackageCompatibilityError
from datosenorden.application.data_release.importer import TargetExpectation, import_package, verify_package
from datosenorden.application.data_release.exporter import export_production_data_package
from datosenorden.application.real_expedient.composition import extract_historical_enrichment
from datosenorden.application.real_expedient.eligibility import ProvenanceReferenceEligibility
from datosenorden.application.real_expedient.reader import ComposedPublicExpedientReader
from datosenorden.application.real_expedient.service import ExpedientConflictError, ExpedientProvisioningService
from datosenorden.infrastructure.real_expedient.repository import PostgresExpedientRepository
from datosenorden.models import SourceRecord


PACKAGE = Path("private/releases/data/deo-prod-data-0001-81dc47c722518efb.zip")
SHA256 = "4de868d6baa5de5be63a3ef2b858c50f5a5c311df8eadf80c6ffda17262cc3b0"
RELEASE = "0b805fa00dc2ab75a3f20e19f4a8e01f9352a04b"
ORDERS = {
    "1000813-247-CM26": "111870",
    "1002584-197-CM26": "1593363",
    "1002772-6758-SE26": "7383",
}


@pytest.fixture
def postgres_url() -> str:
    return os.environ["TEST_DATABASE_URL"]


def _content(session: Session, order_id: str):
    record = session.scalar(select(SourceRecord).where(SourceRecord.external_id == order_id))
    assert record is not None
    current = PostgresExpedientRepository(session).get_version(f"EXP-REAL-CHILECOMPRA-{order_id}", 1)
    assert current is not None
    payload = record.raw_payload
    items = payload["Items"]["Listado"]
    return ChileCompraValidatedContent(
        source_record_id=str(record.id), order_id=order_id,
        buyer_identity=f"chilecompra:buyer:{ORDERS[order_id]}",
        official_order_name=payload.get("Nombre"),
        official_item_products=tuple(item["Producto"] for item in items),
        source_id=current.specification.references.source_ids[0],
        claim_ids=current.specification.references.claim_ids,
        evidence_ids=current.specification.references.evidence_ids,
        entity_ids=current.specification.references.entity_ids,
        relationship_ids=current.specification.references.relationship_ids,
        supplier_observed_name=payload.get("Proveedor", {}).get("Nombre"),
        amount=Decimal(str(payload["Total"])), currency=payload.get("TipoMoneda"),
        order_date=date.fromisoformat(payload["Fechas"]["FechaAceptacion"][:10]),
    )


def test_corrective_versions_against_certified_baseline(postgres_url: str, tmp_path: Path) -> None:
    package = verify_package(PACKAGE, expected_sha256=SHA256)
    engine = create_engine(postgres_url)
    expectation = TargetExpectation(str(make_url(postgres_url).database), "isolated-test", RELEASE)
    assert import_package(engine, package, expectation=expectation).inserted == package.manifest["row_counts"]
    assert all(v == 0 for v in import_package(engine, package, expectation=expectation).inserted.values())
    resolver = ChileCompraCanonicalIdentityResolver(bootstrap_public_name_registry())
    with Session(engine) as session:
        repository = PostgresExpedientRepository(session)
        service = ExpedientProvisioningService(repository, ProvenanceReferenceEligibility(session))
        ids = {order: f"EXP-REAL-CHILECOMPRA-{order}" for order in ORDERS}
        assert [repository.get(ids[o]).specification.version for o in ORDERS] == [1, 2, 1]
        historical = {(ids[o], v): repository.get_version(ids[o], v) for o, v in (("1000813-247-CM26", 1), ("1002584-197-CM26", 1), ("1002584-197-CM26", 2), ("1002772-6758-SE26", 1))}
        legislative = repository.get("EXP-REAL-LEGISLATIVE-15975-25")
        assert legislative is not None
        dep_enrichment = extract_historical_enrichment(historical[(ids["1002584-197-CM26"], 1)], historical[(ids["1002584-197-CM26"], 2)])
        outcomes = [
            repair_chilecompra_expedient(_content(session, "1000813-247-CM26"), expected_current_version=1, service=service, identity_resolver=resolver),
            repair_chilecompra_expedient(_content(session, "1002584-197-CM26"), expected_current_version=2, service=service, identity_resolver=resolver, enrichment=dep_enrichment),
            repair_chilecompra_expedient(_content(session, "1002772-6758-SE26"), expected_current_version=1, service=service, identity_resolver=resolver),
        ]
        assert [item.status for item in outcomes] == [CorrectiveStatus.CREATED] * 3
        assert [repository.get(ids[o]).specification.version for o in ORDERS] == [2, 3, 2]
        for key, value in historical.items():
            restored = repository.get_version(*key)
            assert restored is not None
            assert restored.specification == value.specification
            assert restored.content_fingerprint == value.content_fingerprint
        dep_v3 = repository.get(ids["1002584-197-CM26"])
        assert set(dep_enrichment.references.source_ids) <= set(dep_v3.specification.references.source_ids)
        assert set(s.statement_id for s in dep_enrichment.statements) <= {s.statement_id for s in dep_v3.specification.statements}
        current_text = " ".join([repository.get(ids[o]).specification.title + " " + repository.get(ids[o]).specification.question for o in ORDERS])
        assert "Dirección de Educación Pública" in current_text and "¿Qué muestran los registros públicos" in current_text
        assert not any(marker in current_text for marker in ("Direcci?n", "Educaci?n", "P?blica", "Ã", "Â"))
        repeated = [
            repair_chilecompra_expedient(_content(session, "1000813-247-CM26"), expected_current_version=1, service=service, identity_resolver=resolver),
            repair_chilecompra_expedient(_content(session, "1002584-197-CM26"), expected_current_version=2, service=service, identity_resolver=resolver, enrichment=dep_enrichment),
            repair_chilecompra_expedient(_content(session, "1002772-6758-SE26"), expected_current_version=1, service=service, identity_resolver=resolver),
        ]
        assert [item.status for item in repeated] == [CorrectiveStatus.ALREADY_CORRECT] * 3
        with pytest.raises(ExpedientConflictError):
            repair_chilecompra_expedient(_content(session, "1000813-247-CM26"), expected_current_version=0, service=service, identity_resolver=resolver)
        reader = ComposedPublicExpedientReader(repository)
        assert [reader.get(ids[o])["version"] for o in ORDERS] == [2, 3, 2]
        assert reader.get("EXP-REAL-LEGISLATIVE-15975-25") is not None
        exported = export_production_data_package(
            session, output_dir=tmp_path, created_at=datetime(2026, 8, 19, tzinfo=UTC),
            compatible_code_releases=("c9e073c62d305083a30238045704f889835b7916",),
        )
        assert exported.logical_content_hash != "81dc47c722518efbc0f1a308288bc839ea6b57a88aa4f2710d5d55e4ff93b136"
        print(f"EXPORT={exported.package_id}|{exported.archive_sha256}|{exported.logical_content_hash}")
    engine.dispose()


def test_historical_exported_package_rejects_incompatible_code_release() -> None:
    from tests.postgres_isolation import EphemeralPostgres
    ephemeral = EphemeralPostgres.start(os.environ["TEST_DATABASE_URL"])
    try:
        ephemeral.migrate_to_head()
        engine = create_engine(ephemeral.test_url)
        package = verify_package(PACKAGE, expected_sha256=SHA256)
        expectation = TargetExpectation(
            str(make_url(ephemeral.test_url).database),
            "isolated-test",
            "intentionally-incompatible-release",
        )
        with pytest.raises(PackageCompatibilityError):
            import_package(engine, package, expectation=expectation)
        engine.dispose()
    finally:
        ephemeral.close()
