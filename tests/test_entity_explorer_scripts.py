from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
import sys

from datosenorden.maintenance.entity_explorer import EntityClaimSummary
from datosenorden.maintenance.entity_explorer import EntityEvidenceSummary
from datosenorden.maintenance.entity_explorer import EntityNavigationLink
from datosenorden.maintenance.entity_explorer import EntityNeighborSummary
from datosenorden.maintenance.entity_explorer import EntityProfile
from datosenorden.maintenance.entity_explorer import EntityRelationshipSummary
from datosenorden.maintenance.entity_explorer import EntityRelationshipCount
from datosenorden.maintenance.entity_explorer import EntitySearchResult
from datosenorden.maintenance.entity_explorer import EntitySummary

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import entity_details
import export_entity_profile
import search_buyer
import search_supplier


def _session_manager(session):
    @contextmanager
    def _manager():
        yield session

    return _manager()


def _sample_profile() -> EntityProfile:
    supplier = EntitySummary(
        id="11111111-1111-1111-1111-111111111111",
        entity_type="COMPANY",
        name="SKY AIRLINE S.A.",
        external_id="chilecompra:supplier:76123456-7",
    )
    contract = EntitySummary(
        id="22222222-2222-2222-2222-222222222222",
        entity_type="CONTRACT",
        name="Pasajes aereos",
        external_id="chilecompra:purchase_order:2097-241-SE14",
    )
    claim = EntityClaimSummary(
        id="33333333-3333-3333-3333-333333333333",
        predicate="RECEIVES_CONTRACT",
        status="validated",
        subject_entity=supplier,
        object_entity=contract,
        valid_from=None,
        evidence_count=1,
        relationship_count=1,
    )
    relationship = EntityRelationshipSummary(
        id="44444444-4444-4444-4444-444444444444",
        relationship_type="RECEIVES_CONTRACT",
        status="published",
        source_entity=supplier,
        target_entity=contract,
        related_entity=contract,
        claim_id=claim.id,
    )
    return EntityProfile(
        generated_at=datetime(2026, 6, 18, 12, 30, tzinfo=timezone.utc),
        entity=supplier,
        claims=(claim,),
        relationships=(relationship,),
        evidences=(
            EntityEvidenceSummary(
                id="55555555-5555-5555-5555-555555555555",
                title="Ficha Mercado Publico orden de compra",
                url="https://www.mercadopublico.cl/PurchaseOrder/Modules/PO/DetailsPurchaseOrder.aspx?qs=2097-241-SE14",
                published_at=None,
                claim_id=claim.id,
            ),
        ),
        related_entities=(contract,),
        direct_neighbors=(
            EntityNeighborSummary(
                relationship_id=relationship.id,
                relationship_type=relationship.relationship_type,
                direction="outgoing",
                neighbor=contract,
                source_entity=supplier,
                target_entity=contract,
                profile_link=EntityNavigationLink(
                    label="entity_profile",
                    href="profiles/22222222-2222-2222-2222-222222222222.html",
                ),
                graph_link=EntityNavigationLink(
                    label="entity_graph",
                    href="graph_exports/entity_22222222-2222-2222-2222-222222222222.html",
                ),
            ),
        ),
        relationship_counts=(
            EntityRelationshipCount(relationship_type="RECEIVES_CONTRACT", count=1),
        ),
        navigation_links=(
            EntityNavigationLink(
                label="profile_html",
                href="profiles/11111111-1111-1111-1111-111111111111.html",
            ),
            EntityNavigationLink(
                label="graph_html",
                href="graph_exports/entity_11111111-1111-1111-1111-111111111111.html",
            ),
        ),
    )


def test_search_supplier_script_prints_results(monkeypatch, capsys) -> None:
    result = EntitySearchResult(
        id="11111111-1111-1111-1111-111111111111",
        entity_type="COMPANY",
        name="SKY AIRLINE S.A.",
        external_id="chilecompra:supplier:76123456-7",
        purchase_orders=4,
        claims=8,
        relationships=8,
    )
    monkeypatch.setattr(search_supplier, "SessionLocal", lambda: _session_manager(object()))
    monkeypatch.setattr(search_supplier, "search_suppliers", lambda session, query: (result,))

    exit_code = search_supplier.main(["SKY"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "supplier search: SKY" in captured.out
    assert "name=SKY AIRLINE S.A." in captured.out
    assert "purchase_orders=4" in captured.out
    assert captured.err == ""


def test_search_buyer_script_prints_results(monkeypatch, capsys) -> None:
    result = EntitySearchResult(
        id="66666666-6666-6666-6666-666666666666",
        entity_type="PUBLIC_ORGANIZATION",
        name="DIVISION LOGISTICA DEL EJERCITO",
        external_id="chilecompra:buyer:1234",
        purchase_orders=4,
        claims=8,
        relationships=8,
    )
    monkeypatch.setattr(search_buyer, "SessionLocal", lambda: _session_manager(object()))
    monkeypatch.setattr(search_buyer, "search_buyers", lambda session, query: (result,))

    exit_code = search_buyer.main(["EJERCITO"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "buyer search: EJERCITO" in captured.out
    assert "name=DIVISION LOGISTICA DEL EJERCITO" in captured.out
    assert "relationships=8" in captured.out
    assert captured.err == ""


def test_entity_details_script_prints_profile(monkeypatch, capsys) -> None:
    monkeypatch.setattr(entity_details, "SessionLocal", lambda: _session_manager(object()))
    monkeypatch.setattr(entity_details, "get_entity_profile", lambda session, entity_id: _sample_profile())

    exit_code = entity_details.main(["--entity-id", "11111111-1111-1111-1111-111111111111"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "entity:" in captured.out
    assert "name=SKY AIRLINE S.A." in captured.out
    assert "relationships:" in captured.out
    assert "evidence:" in captured.out
    assert captured.err == ""


def test_entity_details_script_reports_missing_entity(monkeypatch, capsys) -> None:
    monkeypatch.setattr(entity_details, "SessionLocal", lambda: _session_manager(object()))
    monkeypatch.setattr(entity_details, "get_entity_profile", lambda session, entity_id: None)

    exit_code = entity_details.main(["--entity-id", "missing"])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "No se encontro entity_id=missing" in captured.err


def test_export_entity_profile_script_writes_html(monkeypatch, tmp_path, capsys) -> None:
    profiles_dir = tmp_path / "profiles"
    monkeypatch.setattr(export_entity_profile, "PROFILES_DIR", profiles_dir)
    monkeypatch.setattr(export_entity_profile, "SessionLocal", lambda: _session_manager(object()))
    monkeypatch.setattr(export_entity_profile, "get_entity_profile", lambda session, entity_id: _sample_profile())

    entity_id = "11111111-1111-1111-1111-111111111111"
    exit_code = export_entity_profile.main(["--entity-id", entity_id])

    captured = capsys.readouterr()
    output_path = profiles_dir / f"{entity_id}.html"
    assert exit_code == 0
    assert f"entity_profile_exported: path={output_path.as_posix()}" in captured.out
    html = output_path.read_text(encoding="utf-8")
    assert "SKY AIRLINE S.A." in html
    assert "Related entities" in html
    assert "Source: DatosEnOrden local dataset" in html
    assert captured.err == ""
