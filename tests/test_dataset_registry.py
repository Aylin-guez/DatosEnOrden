from __future__ import annotations

from datosenorden.maintenance.dataset_registry import DATASET_REGISTRY
from datosenorden.maintenance.dataset_registry import DatasetCountRow
from datosenorden.maintenance.dataset_registry import DatasetDetails
from datosenorden.maintenance.dataset_registry import DatasetSummary
from datosenorden.maintenance.dataset_registry import get_dataset_details
from datosenorden.maintenance.dataset_registry import list_datasets
from datosenorden.maintenance.dataset_registry import render_dataset_details_text
from datosenorden.maintenance.dataset_registry import render_dataset_list_text
from datosenorden.maintenance.dataset_registry import render_dataset_profile_html
from datosenorden.maintenance.dataset_registry import resolve_dataset
from datosenorden.maintenance.dataset_registry import get_real_dataset_entry
from datosenorden.maintenance.dataset_registry import list_real_dataset_registry
from datosenorden.maintenance.dataset_registry import summarize_real_dataset_registry


def test_resolve_dataset_matches_slug_alias_and_name() -> None:
    assert resolve_dataset("chilecompra") is not None
    assert resolve_dataset("ChileCompra") is not None
    assert resolve_dataset("mercado-publico") is not None
    assert resolve_dataset("dipres") is not None
    assert resolve_dataset("lobby-sample") is not None
    assert resolve_dataset("transparencia-activa") is not None
    assert resolve_dataset("contraloria") is not None
    assert resolve_dataset("municipalidades") is not None
    assert resolve_dataset("servel") is not None
    assert resolve_dataset("servel-sample") is not None
    assert resolve_dataset("elected-authorities") is not None
    assert resolve_dataset("unknown") is None


def test_list_datasets_discovers_registered_modules(monkeypatch) -> None:
    def _summarize_dataset(session, entry):  # noqa: ANN001
        return DatasetSummary(
            slug=entry.slug,
            name=entry.name,
            source_records=1 if entry.dataset_names else 0,
            entities=2 if entry.dataset_names else 0,
            claims=3 if entry.dataset_names else 0,
            evidence=4 if entry.dataset_names else 0,
            relationships=5 if entry.dataset_names else 0,
            health="active" if entry.dataset_names else "empty",
            planned=entry.planned,
        )

    monkeypatch.setattr("datosenorden.maintenance.dataset_registry._summarize_dataset", _summarize_dataset)

    rows = list_datasets(object())

    assert len(rows) == len(DATASET_REGISTRY)
    assert rows[0].name == "ChileCompra"
    assert rows[1].name == "Contraloria"
    assert rows[-1].name == "Transparencia Activa"
    assert any(row.slug == "servel" for row in rows)


def test_get_dataset_details_uses_wiring(monkeypatch) -> None:
    entry = resolve_dataset("chilecompra")
    assert entry is not None

    monkeypatch.setattr("datosenorden.maintenance.dataset_registry.resolve_dataset", lambda slug: entry)
    monkeypatch.setattr(
        "datosenorden.maintenance.dataset_registry._summarize_dataset",
        lambda session, resolved_entry: DatasetSummary(  # noqa: ARG005
            slug=resolved_entry.slug,
            name=resolved_entry.name,
            source_records=11,
            entities=7,
            claims=19,
            evidence=19,
            relationships=6,
            health="active",
            planned=False,
        ),
    )
    monkeypatch.setattr(
        "datosenorden.maintenance.dataset_registry._entity_type_counts",
        lambda session, entity_scope: (DatasetCountRow("PUBLIC_ORGANIZATION", 4),),  # noqa: ARG005
    )
    monkeypatch.setattr(
        "datosenorden.maintenance.dataset_registry._claim_type_counts",
        lambda session, resolved_entry: (DatasetCountRow("ISSUES_PURCHASE_ORDER", 12),),  # noqa: ARG005
    )
    monkeypatch.setattr(
        "datosenorden.maintenance.dataset_registry._relationship_type_counts",
        lambda session, resolved_entry: (DatasetCountRow("RECEIVES_CONTRACT", 6),),  # noqa: ARG005
    )
    monkeypatch.setattr(
        "datosenorden.maintenance.dataset_registry._source_record_status_counts",
        lambda session, resolved_entry: (DatasetCountRow("normalized", 11),),  # noqa: ARG005
    )

    details = get_dataset_details(object(), "chilecompra")

    assert details is not None
    assert details.name == "ChileCompra"
    assert details.health == "active"
    assert details.entities_by_type == (DatasetCountRow("PUBLIC_ORGANIZATION", 4),)
    assert details.claims_by_type == (DatasetCountRow("ISSUES_PURCHASE_ORDER", 12),)
    assert details.relationship_types == (DatasetCountRow("RECEIVES_CONTRACT", 6),)
    assert details.ingestion_stats[0] == DatasetCountRow("source_records", 11)


def test_transparencia_registry_entry_is_active_when_sample_loaded(monkeypatch) -> None:
    entry = resolve_dataset("transparencia")
    assert entry is not None
    assert entry.dataset_names == ("transparencia-activa-sample",)
    assert entry.planned is False

    monkeypatch.setattr(
        "datosenorden.maintenance.dataset_registry._count_source_records",
        lambda session, resolved_entry: 1,  # noqa: ARG005
    )
    monkeypatch.setattr(
        "datosenorden.maintenance.dataset_registry._count_entities",
        lambda session, resolved_entry: 3,  # noqa: ARG005
    )
    monkeypatch.setattr(
        "datosenorden.maintenance.dataset_registry._count_claims",
        lambda session, resolved_entry: 3,  # noqa: ARG005
    )
    monkeypatch.setattr(
        "datosenorden.maintenance.dataset_registry._count_evidence",
        lambda session, resolved_entry: 3,  # noqa: ARG005
    )
    monkeypatch.setattr(
        "datosenorden.maintenance.dataset_registry._count_relationships",
        lambda session, resolved_entry: 3,  # noqa: ARG005
    )

    rows = list_datasets(object())
    row = next(item for item in rows if item.slug == "transparencia")

    assert row.name == "Transparencia Activa"
    assert row.health == "active"
    assert row.source_records == 1
    assert row.entities == 3


def test_render_dataset_list_text_formats_rows() -> None:
    report = render_dataset_list_text(
        (
            DatasetSummary(
                slug="chilecompra",
                name="ChileCompra",
                source_records=11,
                entities=7,
                claims=19,
                evidence=19,
                relationships=6,
                health="active",
                planned=False,
            ),
            DatasetSummary(
                slug="dipres-prototype",
                name="DIPRES Prototype",
                source_records=1,
                entities=2,
                claims=3,
                evidence=3,
                relationships=1,
                health="active",
                planned=False,
            ),
        )
    )

    assert "dataset:" in report
    assert "name=ChileCompra" in report
    assert "source_records=11" in report
    assert "name=DIPRES Prototype" in report


def test_render_dataset_details_text_formats_sections() -> None:
    details = DatasetDetails(
        slug="chilecompra",
        name="ChileCompra",
        health="active",
        source_records=11,
        entities=7,
        claims=19,
        evidence=19,
        relationships=6,
        source_names=("ChileCompra API Mercado Publico",),
        dataset_names=("chilecompra-licitaciones", "chilecompra-ordenes-compra"),
        entities_by_type=(DatasetCountRow("PUBLIC_ORGANIZATION", 4),),
        claims_by_type=(DatasetCountRow("ISSUES_PURCHASE_ORDER", 12),),
        relationship_types=(DatasetCountRow("RECEIVES_CONTRACT", 6),),
        ingestion_stats=(DatasetCountRow("source_records", 11), DatasetCountRow("normalized", 11)),
        planned=False,
    )

    report = render_dataset_details_text(details)

    assert "dataset_details:" in report
    assert "slug=chilecompra" in report
    assert "health=active" in report
    assert "entities_by_type:" in report
    assert "PUBLIC_ORGANIZATION=4" in report
    assert "claims_by_type:" in report
    assert "ISSUES_PURCHASE_ORDER=12" in report
    assert "relationship_types:" in report
    assert "RECEIVES_CONTRACT=6" in report
    assert "ingestion_stats:" in report
    assert "normalized=11" in report


def test_render_dataset_profile_html_contains_key_sections() -> None:
    details = DatasetDetails(
        slug="chilecompra",
        name="ChileCompra",
        health="active",
        source_records=11,
        entities=7,
        claims=19,
        evidence=19,
        relationships=6,
        source_names=("ChileCompra API Mercado Publico",),
        dataset_names=("chilecompra-licitaciones", "chilecompra-ordenes-compra"),
        entities_by_type=(DatasetCountRow("PUBLIC_ORGANIZATION", 4),),
        claims_by_type=(DatasetCountRow("ISSUES_PURCHASE_ORDER", 12),),
        relationship_types=(DatasetCountRow("RECEIVES_CONTRACT", 6),),
        ingestion_stats=(DatasetCountRow("source_records", 11),),
        planned=False,
    )

    html = render_dataset_profile_html(details)

    assert "<title>Dataset profile: ChileCompra</title>" in html
    assert "ChileCompra" in html
    assert "source_records" in html
    assert "¿Qué significa esto?" in html
    assert "PUBLIC_ORGANIZATION" in html


def test_real_dataset_registry_declares_operational_fields() -> None:
    entries = list_real_dataset_registry()
    chilecompra = get_real_dataset_entry("chilecompra")

    assert chilecompra is not None
    assert chilecompra.loader_script == "scripts/load_chilecompra_file.py"
    assert chilecompra.expected_format
    assert chilecompra.supports_incremental is False
    assert "PUBLIC_ORGANIZATION" in chilecompra.entity_types
    assert all(entry.id and entry.display_name and entry.status for entry in entries)


def test_summarize_real_dataset_registry_is_json_safe_without_session() -> None:
    summary = summarize_real_dataset_registry()

    assert summary["totals"]["sources"] >= 1
    assert summary["totals"]["ready"] >= 1
    assert any(entry["id"] == "chilecompra" for entry in summary["entries"])
