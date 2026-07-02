from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path

from datosenorden.adapters.legislature.document_models import (
    LegislativeDownloadedDocument,
    LegislativeProjectXmlResponse,
)
from datosenorden.adapters.legislature.document_resolver import LegislativeDocumentResolver


SAMPLE_PROJECT_XML = """<proyectos><proyecto>
  <descripcion>
    <boletin>8575-05</boletin>
    <titulo>Ley de Presupuestos del sector publico para el ano 2013.</titulo>
    <estado>Publicado</estado>
    <etapa>Tramitacion terminada</etapa>
    <link_mensaje_mocion>http://www.senado.cl/appsenado/index.php?mo=tramitacion&amp;ac=getDocto&amp;iddocto=9000&amp;tipodoc=mensaje_mocion</link_mensaje_mocion>
  </descripcion>
  <informes>
    <informe>
      <FECHAINFORME>10/10/2012</FECHAINFORME>
      <TRAMITE>Informe de comision</TRAMITE>
      <LINK_INFORME>http://www.senado.cl/appsenado/index.php?mo=tramitacion&amp;ac=getDocto&amp;iddocto=15431&amp;tipodoc=info</LINK_INFORME>
    </informe>
  </informes>
  <comparados>
    <comparado>
      <COMPARADO>Comparado de prueba</COMPARADO>
      <LINK_COMPARADO>http://www.senado.cl/appsenado/index.php?mo=tramitacion&amp;ac=getDocto&amp;iddocto=1107&amp;tipodoc=compa</LINK_COMPARADO>
    </comparado>
  </comparados>
  <oficios>
    <oficio>
      <FECHA>02/10/2012</FECHA>
      <DESCRIPCION>Remite proyecto</DESCRIPCION>
      <LINK_OFICIO>http://www.senado.cl/appsenado/index.php?mo=tramitacion&amp;ac=getDocto&amp;iddocto=17543&amp;tipodoc=ofic</LINK_OFICIO>
    </oficio>
  </oficios>
</proyecto></proyectos>"""


class FakeDocumentClient:
    def __init__(self) -> None:
        self.project_queries: list[str] = []
        self.downloaded_urls: list[str] = []

    def get_senate_project(self, bulletin_query_id: str) -> LegislativeProjectXmlResponse:
        self.project_queries.append(bulletin_query_id)
        return LegislativeProjectXmlResponse(
            url="https://tramitacion.senado.cl/wspublico/tramitacion.php",
            params={"boletin": bulletin_query_id},
            xml_text=SAMPLE_PROJECT_XML,
            retrieved_at=datetime(2026, 7, 2, 12, 0, tzinfo=UTC),
        )

    def download_document(self, url: str) -> LegislativeDownloadedDocument:
        self.downloaded_urls.append(url)
        return LegislativeDownloadedDocument(
            url=url,
            content=b"official document",
            content_type="application/msword",
            filename="archivo.doc",
            size=len(b"official document"),
            retrieved_at=datetime(2026, 7, 2, 12, 5, tzinfo=UTC),
        )


def test_document_resolver_discovers_senate_documents() -> None:
    client = FakeDocumentClient()
    catalog = LegislativeDocumentResolver(client=client).discover("8575-05")  # type: ignore[arg-type]

    assert client.project_queries == ["8575"]
    assert catalog.bulletin_id == "8575-05"
    assert len(catalog.documents) == 4
    assert {document.type for document in catalog.documents} == {
        "mensaje_mocion",
        "informe",
        "comparado",
        "oficio",
    }
    assert catalog.documents[0].document_id == "senado-docto-9000-mensaje_mocion"
    assert "getDocto" in catalog.documents[0].url


def test_document_resolver_downloads_selected_document_and_metadata(tmp_path: Path) -> None:
    client = FakeDocumentClient()
    document_path, metadata_path, selected = LegislativeDocumentResolver(
        client=client  # type: ignore[arg-type]
    ).download_selected("8575-05", "mensaje_mocion", tmp_path)

    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    assert selected.type == "mensaje_mocion"
    assert document_path.name == "document.doc"
    assert document_path.read_bytes() == b"official document"
    assert metadata["id"] == "senado-docto-9000-mensaje_mocion"
    assert metadata["bill_id"] == "cl-congreso-boletin-8575-05"
    assert metadata["document_type"] == "legislative_mensaje_mocion"
    assert metadata["content_type"] == "application/msword"
    assert metadata["retrieval_date"] == "2026-07-02"
