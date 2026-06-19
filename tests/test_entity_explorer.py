from __future__ import annotations

from datetime import datetime, timezone

from datosenorden.maintenance.entity_explorer import EntityClaimSummary
from datosenorden.maintenance.entity_explorer import EntityEvidenceSummary
from datosenorden.maintenance.entity_explorer import EntityNavigationLink
from datosenorden.maintenance.entity_explorer import EntityNeighborSummary
from datosenorden.maintenance.entity_explorer import EntityProfile
from datosenorden.maintenance.entity_explorer import EntityRelationshipSummary
from datosenorden.maintenance.entity_explorer import EntityRelationshipCount
from datosenorden.maintenance.entity_explorer import EntitySearchResult
from datosenorden.maintenance.entity_explorer import EntitySummary
from datosenorden.maintenance.entity_explorer import render_buyer_search
from datosenorden.maintenance.entity_explorer import render_entity_details
from datosenorden.maintenance.entity_explorer import render_entity_profile_html
from datosenorden.maintenance.entity_explorer import render_supplier_search


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
    evidence = EntityEvidenceSummary(
        id="55555555-5555-5555-5555-555555555555",
        title="Ficha Mercado Publico orden de compra 2097-241-SE14",
        url="https://www.mercadopublico.cl/PurchaseOrder/Modules/PO/DetailsPurchaseOrder.aspx?qs=2097-241-SE14",
        published_at=None,
        claim_id=claim.id,
    )
    neighbor = EntityNeighborSummary(
        relationship_id=relationship.id,
        relationship_type=relationship.relationship_type,
        direction="outgoing",
        neighbor=contract,
        source_entity=supplier,
        target_entity=contract,
        profile_link=EntityNavigationLink(label="entity_profile", href="profiles/22222222-2222-2222-2222-222222222222.html"),
        graph_link=EntityNavigationLink(label="entity_graph", href="graph_exports/entity_22222222-2222-2222-2222-222222222222.html"),
    )
    return EntityProfile(
        generated_at=datetime(2026, 6, 18, 12, 30, tzinfo=timezone.utc),
        entity=supplier,
        claims=(claim,),
        relationships=(relationship,),
        evidences=(evidence,),
        related_entities=(contract,),
        direct_neighbors=(neighbor,),
        relationship_counts=(EntityRelationshipCount(relationship_type="RECEIVES_CONTRACT", count=1),),
        navigation_links=(
            EntityNavigationLink(label="profile_html", href="profiles/11111111-1111-1111-1111-111111111111.html"),
            EntityNavigationLink(label="graph_html", href="graph_exports/entity_11111111-1111-1111-1111-111111111111.html"),
        ),
    )


def test_render_supplier_search_lists_matches() -> None:
    result = EntitySearchResult(
        id="11111111-1111-1111-1111-111111111111",
        entity_type="COMPANY",
        name="SKY AIRLINE S.A.",
        external_id="chilecompra:supplier:76123456-7",
        purchase_orders=4,
        claims=8,
        relationships=8,
    )

    report = render_supplier_search("SKY", (result,))

    assert "supplier search: SKY" in report
    assert "supplier:" in report
    assert "name=SKY AIRLINE S.A." in report
    assert "external_id=chilecompra:supplier:76123456-7" in report
    assert "purchase_orders=4" in report
    assert "claims=8" in report
    assert "relationships=8" in report


def test_render_buyer_search_lists_matches() -> None:
    result = EntitySearchResult(
        id="66666666-6666-6666-6666-666666666666",
        entity_type="PUBLIC_ORGANIZATION",
        name="DIVISION LOGISTICA DEL EJERCITO",
        external_id="chilecompra:buyer:1234",
        purchase_orders=4,
        claims=8,
        relationships=8,
    )

    report = render_buyer_search("EJERCITO", (result,))

    assert "buyer search: EJERCITO" in report
    assert "buyer:" in report
    assert "name=DIVISION LOGISTICA DEL EJERCITO" in report
    assert "external_id=chilecompra:buyer:1234" in report
    assert "purchase_orders=4" in report
    assert "claims=8" in report
    assert "relationships=8" in report


def test_render_entity_details_includes_claims_relationships_evidence_and_related_entities() -> None:
    report = render_entity_details(_sample_profile())

    assert "entity:" in report
    assert "type=COMPANY" in report
    assert "name=SKY AIRLINE S.A." in report
    assert "claims:" in report
    assert "predicate=RECEIVES_CONTRACT" in report
    assert "evidence_count=1" in report
    assert "relationship_count=1" in report
    assert "relationship_counts:" in report
    assert "RECEIVES_CONTRACT=1" in report
    assert "direct_neighbors:" in report
    assert "profile_link=profiles/22222222-2222-2222-2222-222222222222.html" in report
    assert "navigation_links:" in report
    assert "relationships:" in report
    assert "related_entity=CONTRACT | Pasajes aereos" in report
    assert "evidence:" in report
    assert "https://www.mercadopublico.cl/PurchaseOrder" in report
    assert "related_entities:" in report


def test_render_entity_profile_html_contains_navigable_profile() -> None:
    html = render_entity_profile_html(_sample_profile())

    assert "<!doctype html>" in html
    assert "SKY AIRLINE S.A." in html
    assert "claims" in html
    assert "relationships" in html
    assert "evidence links" in html
    assert "Direct neighbors" in html
    assert "Relationship counts" in html
    assert "Related entities" in html
    assert "Pasajes aereos" in html
    assert "Source: DatosEnOrden local dataset" in html
    assert "Generated at 2026-06-18T12:30:00+00:00" in html
    assert "ticket" not in html.lower()
    assert "DATABASE_URL" not in html
