from __future__ import annotations

from pathlib import Path

from datosenorden.application.document_reading.context import document_pdf_href
from reflex_app.features.document_reading.state import (
    PUBLISHED_DOCUMENT_PDF_ASSET_PATH,
    PUBLISHED_DOCUMENT_PDF_PUBLIC_HREF,
)


def test_published_document_pdf_uses_the_served_asset_contract() -> None:
    """The new-tab URL must be the real public asset, never an application search route."""
    href = document_pdf_href(PUBLISHED_DOCUMENT_PDF_PUBLIC_HREF, 19)

    assert PUBLISHED_DOCUMENT_PDF_ASSET_PATH == Path("assets/official_documents/senado-docto-9000-mensaje_mocion/document.pdf")
    assert PUBLISHED_DOCUMENT_PDF_ASSET_PATH.exists()
    assert href == "/official_documents/senado-docto-9000-mensaje_mocion/document.pdf#page=19"
    assert "/search" not in href
    assert "/official-document" not in href
