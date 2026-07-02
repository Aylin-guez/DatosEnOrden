from __future__ import annotations

import hashlib
import json
import re
from datetime import UTC, date, datetime
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from xml.etree import ElementTree

from datosenorden.adapters.legislature.document_client import (
    LegislativeDocumentClient,
    canonical_url,
)
from datosenorden.adapters.legislature.document_models import (
    SENADO_SOURCE_NAME,
    LegislativeDocumentCandidate,
    LegislativeDocumentCatalog,
)
from datosenorden.adapters.legislature.parser import normalize_bulletin_id


DOCUMENT_TYPE_LABELS = {
    "mensaje_mocion": "Mensaje o mocion",
    "indicacion": "Indicacion",
    "indicaciones": "Indicaciones",
    "informe": "Informe",
    "informe_comision": "Informe de comision",
    "comparado": "Comparado",
    "oficio": "Oficio",
    "observacion": "Observacion",
    "observaciones": "Observaciones",
}
TIPODOC_TO_TYPE = {
    "mensaje_mocion": "mensaje_mocion",
    "info": "informe",
    "compa": "comparado",
    "ofic": "oficio",
    "indic": "indicacion",
    "observ": "observacion",
}
TYPE_TO_EXTENSION = {
    "application/msword": ".doc",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "application/pdf": ".pdf",
    "text/html": ".html",
    "text/xml": ".xml",
    "application/xml": ".xml",
}


class LegislativeDocumentResolver:
    """Resolve official documents associated with a legislative bulletin."""

    def __init__(self, client: LegislativeDocumentClient | None = None) -> None:
        self._client = client or LegislativeDocumentClient()

    def discover(self, bulletin_id: str) -> LegislativeDocumentCatalog:
        normalized = normalize_bulletin_id(bulletin_id)
        response = self._client.get_senate_project(_senate_query_id(normalized))
        root = ElementTree.fromstring(response.xml_text)
        returned_bulletin = _first_text(root, "boletin")
        if returned_bulletin is None:
            raise ValueError(f"Official Senate response did not include a bulletin for {normalized}")
        if normalize_bulletin_id(returned_bulletin) != normalized:
            raise ValueError(
                f"Official Senate response returned bulletin {returned_bulletin}, expected {normalized}"
            )
        documents = tuple(_dedupe_documents(_extract_documents(root)))
        return LegislativeDocumentCatalog(
            bulletin_id=normalized,
            source=SENADO_SOURCE_NAME,
            documents=documents,
            project_url=f"{response.url}?boletin={response.params['boletin']}",
            retrieved_at=response.retrieved_at,
            metadata={
                "title": _first_text(root, "titulo") or "",
                "status": _first_text(root, "estado") or "",
                "stage": _first_text(root, "etapa") or "",
                "law_number": _first_text(root, "leynro") or "",
            },
        )

    def download_selected(
        self,
        bulletin_id: str,
        document_type: str,
        incoming_dir: Path,
    ) -> tuple[Path, Path, LegislativeDocumentCandidate]:
        catalog = self.discover(bulletin_id)
        selected = _select_document(catalog.documents, document_type)
        downloaded = self._client.download_document(selected.url)
        content_hash = hashlib.sha256(downloaded.content).hexdigest()
        document_id = selected.document_id
        target_dir = incoming_dir / document_id
        target_dir.mkdir(parents=True, exist_ok=True)
        extension = _extension_for(downloaded.content_type, downloaded.filename)
        document_path = target_dir / f"document{extension}"
        metadata_path = target_dir / "metadata.json"
        document_path.write_bytes(downloaded.content)
        metadata = _official_metadata(
            catalog=catalog,
            selected=selected,
            source_url=downloaded.url,
            content_type=downloaded.content_type,
            size=downloaded.size,
            content_hash=content_hash,
            filename=document_path.name,
            retrieval_date=downloaded.retrieved_at.date(),
        )
        metadata_path.write_text(json.dumps(metadata, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
        return document_path, metadata_path, selected


def _senate_query_id(bulletin_id: str) -> str:
    return normalize_bulletin_id(bulletin_id).split("-", 1)[0]


def _extract_documents(root: ElementTree.Element) -> list[LegislativeDocumentCandidate]:
    documents: list[LegislativeDocumentCandidate] = []
    for node in root.iter():
        tag = _local_name(node.tag)
        text = _clean_text(node.text)
        if not text or "getDocto" not in text:
            continue
        url = canonical_url(text)
        parsed = urlparse(url)
        query = parse_qs(parsed.query)
        source_document_id = _last(query.get("iddocto")) or _hash_url(url)[:12]
        tipodoc = _last(query.get("tipodoc")) or _type_from_link_tag(tag)
        doc_type = _document_type(tag=tag, tipodoc=tipodoc)
        parent = _parent_for(root, node)
        publication_date = _publication_date(parent)
        title = _document_title(doc_type=doc_type, parent=parent, fallback=tag)
        document_id = f"senado-docto-{source_document_id}-{doc_type}"
        documents.append(
            LegislativeDocumentCandidate(
                document_id=document_id,
                type=doc_type,
                title=title,
                format=_format_for_url(url),
                url=url,
                publication_date=publication_date,
                source=SENADO_SOURCE_NAME,
                metadata={
                    "source_document_id": source_document_id,
                    "source_document_kind": tipodoc,
                    "source_xml_field": tag,
                },
            )
        )
    return documents


def _dedupe_documents(
    documents: list[LegislativeDocumentCandidate],
) -> list[LegislativeDocumentCandidate]:
    seen: set[tuple[str, str]] = set()
    deduped: list[LegislativeDocumentCandidate] = []
    for document in documents:
        key = (document.url, document.type)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(document)
    return deduped


def _select_document(
    documents: tuple[LegislativeDocumentCandidate, ...],
    document_type: str,
) -> LegislativeDocumentCandidate:
    normalized_type = _normalize_type(document_type)
    matches = [document for document in documents if document.type == normalized_type]
    if not matches:
        available = ", ".join(sorted({document.type for document in documents})) or "none"
        raise ValueError(f"No document of type {normalized_type}. Available types: {available}")
    return matches[0]


def _document_type(tag: str, tipodoc: str) -> str:
    if tipodoc in TIPODOC_TO_TYPE:
        mapped = TIPODOC_TO_TYPE[tipodoc]
        if mapped == "informe" and "COMISION" in tag.upper():
            return "informe_comision"
        return mapped
    return _normalize_type(_type_from_link_tag(tag))


def _type_from_link_tag(tag: str) -> str:
    name = tag.lower()
    if "mensaje" in name or "mocion" in name:
        return "mensaje_mocion"
    if "comparado" in name:
        return "comparado"
    if "oficio" in name:
        return "oficio"
    if "indicacion" in name:
        return "indicacion"
    if "observacion" in name:
        return "observacion"
    if "informe" in name:
        return "informe"
    return "documento"


def _normalize_type(value: str) -> str:
    normalized = value.strip().lower().replace("-", "_").replace(" ", "_")
    normalized = re.sub(r"[^a-z0-9_]", "", normalized)
    if normalized == "info":
        return "informe"
    if normalized == "compa":
        return "comparado"
    if normalized == "ofic":
        return "oficio"
    return normalized


def _document_title(doc_type: str, parent: ElementTree.Element | None, fallback: str) -> str:
    label = DOCUMENT_TYPE_LABELS.get(doc_type, doc_type.replace("_", " ").title())
    if parent is None:
        return label
    for field in ("TRAMITE", "DESCRIPCION", "COMPARADO", "TIPO"):
        value = _child_text(parent, field)
        if value:
            return f"{label}: {value}"
    return label if fallback.startswith("link_") else f"{label}: {fallback}"


def _publication_date(parent: ElementTree.Element | None) -> str | None:
    if parent is None:
        return None
    for field in ("FECHAINFORME", "FECHA", "FECHAINGRESO"):
        value = _child_text(parent, field)
        parsed = _parse_chilean_date(value)
        if parsed:
            return parsed
    return None


def _official_metadata(
    catalog: LegislativeDocumentCatalog,
    selected: LegislativeDocumentCandidate,
    source_url: str,
    content_type: str | None,
    size: int,
    content_hash: str,
    filename: str,
    retrieval_date: date,
) -> dict[str, object]:
    publication_date = selected.publication_date or retrieval_date.isoformat()
    title = selected.title
    project_title = catalog.metadata.get("title", "")
    if selected.type == "mensaje_mocion" and project_title:
        title = f"{DOCUMENT_TYPE_LABELS['mensaje_mocion']}: {project_title}"
    return {
        "id": selected.document_id,
        "title": title,
        "organization": selected.source,
        "source_url": source_url,
        "publication_date": publication_date,
        "retrieval_date": retrieval_date.isoformat(),
        "status": "incoming",
        "document_type": f"legislative_{selected.type}",
        "language": "es",
        "version": 1,
        "bill_id": f"cl-congreso-boletin-{catalog.bulletin_id}",
        "bulletin_id": catalog.bulletin_id,
        "project_url": catalog.project_url,
        "source_document_id": selected.metadata.get("source_document_id", ""),
        "source_document_kind": selected.metadata.get("source_document_kind", ""),
        "original_format": selected.format,
        "content_type": content_type or "",
        "content_size": size,
        "content_sha256": content_hash,
        "file_name": filename,
    }


def _extension_for(content_type: str | None, filename: str | None) -> str:
    if filename:
        suffix = Path(filename).suffix
        if suffix:
            return suffix.lower()
    if content_type:
        media_type = content_type.split(";", 1)[0].strip().lower()
        if media_type in TYPE_TO_EXTENSION:
            return TYPE_TO_EXTENSION[media_type]
    return ".bin"


def _format_for_url(url: str) -> str:
    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    tipodoc = _last(query.get("tipodoc"))
    return f"senado_getDocto:{tipodoc}" if tipodoc else "senado_getDocto"


def _first_text(root: ElementTree.Element, name: str) -> str | None:
    for node in root.iter():
        if _local_name(node.tag).lower() == name.lower():
            return _clean_text(node.text)
    return None


def _child_text(node: ElementTree.Element, name: str) -> str | None:
    for child in node:
        if _local_name(child.tag).lower() == name.lower():
            return _clean_text(child.text)
    return None


def _parent_for(root: ElementTree.Element, target: ElementTree.Element) -> ElementTree.Element | None:
    for parent in root.iter():
        for child in parent:
            if child is target:
                return parent
    return None


def _parse_chilean_date(value: str | None) -> str | None:
    if not value:
        return None
    for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, fmt).replace(tzinfo=UTC).date().isoformat()
        except ValueError:
            continue
    return None


def _clean_text(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = " ".join(value.strip().split())
    return cleaned or None


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _last(values: list[str] | None) -> str | None:
    if not values:
        return None
    value = values[-1].strip()
    return value or None


def _hash_url(url: str) -> str:
    return hashlib.sha256(url.encode("utf-8")).hexdigest()
