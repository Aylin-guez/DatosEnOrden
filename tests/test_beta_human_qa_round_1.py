from __future__ import annotations

from pathlib import Path

from datosenorden.application.real_expedient.citizen_projection import (
    CitizenDocument,
    _document,
    _has_public_document_destination,
)
from datosenorden.web import app_services


ROOT = Path(__file__).resolve().parents[1]


def _source(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_public_return_controls_use_deterministic_routes_not_browser_history() -> None:
    expected = {
        "reflex_app/features/laboratory/components.py": 'return_navigation_link("← Volver", "/laboratory")',
        "reflex_app/features/document_reading/pages.py": 'return_navigation_link("← Volver", "/library")',
        "reflex_app/features/public_record/pages.py": 'return_navigation_link("← Volver", "/search")',
    }

    for relative, control in expected.items():
        source = _source(relative)
        assert control in source
        assert "window.history.back()" not in source

    search_state = _source("reflex_app/features/search/state.py")
    assert 'return rx.redirect("/search")' in search_state


def test_fragment_navigation_never_stringifies_reflex_state_rows() -> None:
    source = _source("reflex_app/features/document_reading/components.py")
    renderer = source[source.index("def topic_fragment_nav_item"):source.index("def document_fragment_panel")]

    assert "str(row" not in renderer
    assert "row.get(" not in renderer
    assert 'row["reference_label"]' in renderer
    assert 'rx.text("Fragmento"' in renderer
    assert "row_rx_state" not in renderer


def test_document_cta_requires_a_direct_public_destination() -> None:
    raw_chilecompra_detail = (
        "https://www.mercadopublico.cl/PurchaseOrder/Modules/PO/"
        "DetailsPurchaseOrder.aspx?qs=1002772-6758-SE26"
    )
    valid_chilecompra_detail = (
        "https://www.mercadopublico.cl/PurchaseOrder/Modules/PO/"
        "DetailsPurchaseOrder.aspx?qs=yOLfkjKmiIwBbfuEgBBQlw%3D%3D"
    )

    assert not _has_public_document_destination(raw_chilecompra_detail)
    assert _has_public_document_destination(valid_chilecompra_detail)
    assert _has_public_document_destination("https://www.bcn.cl/leychile/")
    assert not _has_public_document_destination("local://sample/document")

    projection = _document(
        CitizenDocument(
            "Ficha Mercado Público orden de compra 1002772-6758-SE26",
            "ChileCompra API Mercado Público",
            "Documento oficial referenciado",
            "Fuente incorporada",
            raw_chilecompra_detail,
        )
    )
    assert projection["can_open"] is False
    assert "dirección pública directa verificable" in str(projection["action_notice"])


def test_home_pulse_ctas_require_a_published_public_destination(monkeypatch) -> None:
    published = {
        "id": "current-topic-1",
        "title": "Lectura publicada",
        "summary": "Resumen",
        "status": "Analizado",
        "updated_at": "2026-09-07",
        "organization": "Documento oficial",
        "href": "/official-document",
        "primary_document": {"href": "/official-document"},
    }
    connector = {
        "id": "event-1",
        "title": "Evento de conector",
        "pulse_summary": "Contexto",
        "date": "2026-09-07",
        "source": "Conector",
    }
    monkeypatch.setattr(app_services, "_list_current_topics", lambda *, limit: [published][:limit])
    monkeypatch.setattr(app_services, "_loaded_connectors", lambda: [{"events": [connector], "display_name": "Conector"}])
    monkeypatch.setattr(app_services, "_load_source_population", lambda: {})

    rows = app_services.get_current_topics(limit=3)

    assert rows[0]["actionable"] is True
    assert rows[0]["href"] == "/official-document"
    assert rows[1]["actionable"] is False
    assert rows[1]["href"] == ""
    assert rows[1]["action_notice"]

    component = _source("reflex_app/features/pulse/components.py")
    assert 'row["actionable"]' in component
    assert 'rx.redirect(row["href"])' not in component
