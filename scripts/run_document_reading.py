from __future__ import annotations

from dataclasses import dataclass
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from datosenorden.maintenance.knowledge_engine import (  # noqa: E402
    DocumentSection,
    OfficialDocument,
    build_knowledge_digest,
    knowledge_digest_to_dict,
)
from datosenorden.studio.document_reading_pipeline import (  # noqa: E402
    document_experience_to_dict,
    generate_document_experience,
)
from datosenorden.studio.publication_engine import (  # noqa: E402
    PublicationArtifact,
    PublicationPlan,
    PublicationResult,
    document_view_payload,
    publication_result_to_dict,
    publish_document_view,
    publish_library,
    publish_report,
    publish_search,
)

DEFAULT_DOCUMENT_ID = "senado-docto-9000-mensaje_mocion"
PROCESSING_ROOT = ROOT / "data" / "official_documents" / "processing"
PUBLISHED_ROOT = ROOT / "data" / "official_documents" / "published"


@dataclass(frozen=True)
class ReadingResult:
    document: dict[str, Any]
    fragments: tuple[dict[str, Any], ...]
    references: tuple[dict[str, Any], ...]
    limitations: tuple[str, ...]


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    document_id = args[0] if args else DEFAULT_DOCUMENT_ID
    output = run_document_reading(document_id)
    print("document_reading: OK")
    print(f"  document_id={output['document_id']}")
    print(f"  published_dir={output['published_dir']}")
    print(f"  fragments={output['fragments']}")
    print(f"  questions={output['questions']}")
    print(f"  references={output['references']}")
    print("  outputs=reading.json knowledge.json publication.json")
    return 0


def run_document_reading(document_id: str = DEFAULT_DOCUMENT_ID) -> dict[str, object]:
    processing_dir = PROCESSING_ROOT / document_id
    document_json = _load_json(processing_dir / "document.json")
    fragments_payload = _load_json(processing_dir / "fragments.json")
    metadata = _load_json(processing_dir / "metadata.json")
    extracted_text = (processing_dir / "extracted.txt").read_text(encoding="utf-8")
    fragments = _validated_fragments(fragments_payload)
    official_document = _official_document_from_processed(
        document_json=document_json,
        fragments=fragments,
        metadata=metadata,
        extracted_text=extracted_text,
    )

    reading_result = _build_reading_result(official_document, fragments, metadata)
    experience = generate_document_experience(official_document)
    experience_payload = document_experience_to_dict(experience)
    digest = build_knowledge_digest(official_document)
    knowledge_payload = knowledge_digest_to_dict(digest)
    knowledge_payload["limitations"] = list(reading_result.limitations)
    knowledge_payload["source_processing"] = {
        "document_json": "document.json",
        "fragments_json": "fragments.json",
        "metadata_json": "metadata.json",
        "extracted_text": "extracted.txt",
    }

    publication = _publish_real_document(official_document.id, experience_payload)
    publication_payload = publication_result_to_dict(publication)
    publication_payload["document_view"] = document_view_payload(publication)
    publication_payload["citizen_summary"] = experience_payload.get("citizen_summary", "")
    publication_payload["references"] = experience_payload.get("references", [])
    publication_payload["evidence"] = experience_payload.get("evidence", [])
    publication_payload["document_coverage"] = experience_payload.get("document_coverage", {})
    publication_payload["limitations"] = list(reading_result.limitations)

    published_dir = PUBLISHED_ROOT / document_id
    published_dir.mkdir(parents=True, exist_ok=True)
    (published_dir / "reading.json").write_text(_json(_reading_to_dict(reading_result)), encoding="utf-8")
    (published_dir / "knowledge.json").write_text(_json(knowledge_payload), encoding="utf-8")
    (published_dir / "publication.json").write_text(_json(publication_payload), encoding="utf-8")
    return {
        "document_id": document_id,
        "published_dir": str(published_dir),
        "fragments": len(reading_result.fragments),
        "questions": len(knowledge_payload.get("citizen_questions", [])),
        "references": len(publication_payload.get("references", [])),
    }


def _official_document_from_processed(
    document_json: dict[str, Any],
    fragments: tuple[dict[str, Any], ...],
    metadata: dict[str, Any],
    extracted_text: str,
) -> OfficialDocument:
    document_id = str(document_json["document_id"])
    sections = tuple(
        DocumentSection(
            id=str(fragment["fragment_id"]),
            title=_section_title(fragment),
            text=str(fragment["text"]),
            order=int(fragment["order"]),
            page=_page_number(fragment),
            fragment_id=str(fragment["fragment_id"]),
        )
        for fragment in fragments
    )
    return OfficialDocument(
        id=document_id,
        title=str(document_json.get("title", metadata.get("title", document_id))),
        source=str(document_json.get("source", metadata.get("organization", ""))),
        document_type=str(metadata.get("document_type", document_json.get("mime_type", ""))),
        published_at=str(metadata.get("publication_date", "")),
        official_url=str(metadata.get("source_url", "")),
        summary=_summary_from_text(extracted_text),
        related_expediente_target=str(metadata.get("bill_id", metadata.get("bulletin_id", ""))),
        related_tracking_item_id=str(metadata.get("bulletin_id", "")),
        related_citizen_report_id=str(metadata.get("source_document_id", "")),
        public_source=str(metadata.get("project_url", metadata.get("source_url", ""))),
        sections=sections,
        hash_sha256=str(metadata.get("content_sha256", "")),
        classification="OFFICIAL_DOCUMENT",
        official_status="REAL_OFFICIAL_SOURCE",
    )


def _build_reading_result(
    document: OfficialDocument,
    fragments: tuple[dict[str, Any], ...],
    metadata: dict[str, Any],
) -> ReadingResult:
    useful_fragments = tuple(
        {
            "fragment_id": str(fragment["fragment_id"]),
            "order": int(fragment["order"]),
            "text": str(fragment["text"]),
            "page": fragment.get("page"),
            "heading": fragment.get("heading"),
            "character_count": int(fragment.get("character_count", len(str(fragment["text"])))),
            "source_document_id": document.id,
        }
        for fragment in sorted(fragments, key=lambda item: int(item["order"]))
        if str(fragment.get("text", "")).strip()
    )
    references = tuple(
        {
            "id": f"reading-reference-{fragment['fragment_id']}",
            "document_id": document.id,
            "fragment_id": fragment["fragment_id"],
            "order": fragment["order"],
            "page": fragment["page"],
            "source_url": document.official_url,
            "excerpt": _excerpt(str(fragment["text"])),
        }
        for fragment in useful_fragments
    )
    limitations = (
        "El documento procesado no contiene paginas identificables; las paginas se preservan como null en reading.json y se normalizan solo para compatibilidad del Knowledge Engine existente.",
        "La lectura usa reglas existentes y no usa IA; no interpreta intenciones ni evalua el contenido.",
        "La seleccion de puntos, preguntas y afirmaciones es automatica; puede omitir materias relevantes del documento.",
        "La lectura no incorpora antecedentes externos, historia legislativa ni comparacion con otras fuentes.",
        f"Fuente oficial: {metadata.get('source_url', '')}",
    )
    return ReadingResult(
        document={
            "id": document.id,
            "title": document.title,
            "source": document.source,
            "document_type": document.document_type,
            "official_url": document.official_url,
            "published_at": document.published_at,
            "hash_sha256": document.hash_sha256,
        },
        fragments=useful_fragments,
        references=references,
        limitations=limitations,
    )


def _publish_real_document(document_id: str, experience: dict[str, Any]) -> PublicationResult:
    plan = PublicationPlan(document_id=document_id)
    artifacts = tuple(
        artifact
        for artifact in (
            publish_library(plan, experience),
            publish_report(plan, experience),
            publish_search(plan, experience),
            publish_document_view(plan, experience),
            PublicationArtifact(
                surface="evidence",
                should_publish=True,
                document_id=document_id,
                payload={
                    "references": experience.get("references", []),
                    "evidence": experience.get("evidence", []),
                },
            ),
        )
        if artifact.should_publish
    )
    return PublicationResult(plan=plan, artifacts=artifacts)


def _validated_fragments(payload: dict[str, Any]) -> tuple[dict[str, Any], ...]:
    rows = payload.get("fragments", [])
    if not isinstance(rows, list) or not rows:
        raise ValueError("fragments.json must contain a non-empty fragments list")
    required = {"fragment_id", "order", "text", "page", "heading", "character_count"}
    for row in rows:
        if not isinstance(row, dict) or not required <= set(row):
            raise ValueError("Each fragment must include fragment_id, order, text, page, heading and character_count")
    return tuple(sorted(rows, key=lambda item: int(item["order"])))


def _reading_to_dict(result: ReadingResult) -> dict[str, Any]:
    return {
        "document": result.document,
        "fragments": list(result.fragments),
        "references": list(result.references),
        "limitations": list(result.limitations),
        "generated_at": datetime.now(UTC).isoformat(),
    }


def _section_title(fragment: dict[str, Any]) -> str:
    heading = str(fragment.get("heading") or "").strip()
    if heading:
        return heading
    return f"Fragmento {int(fragment['order']):02d}"


def _page_number(fragment: dict[str, Any]) -> int:
    page = fragment.get("page")
    if page is None:
        return int(fragment["order"])
    return int(page)


def _summary_from_text(text: str) -> str:
    paragraphs = [paragraph.strip() for paragraph in text.split("\n\n") if paragraph.strip()]
    return _excerpt(paragraphs[0] if paragraphs else text, limit=280)


def _excerpt(text: str, limit: int = 240) -> str:
    cleaned = " ".join(text.split())
    return cleaned if len(cleaned) <= limit else cleaned[: limit - 1].rstrip() + "..."


def _load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return data


def _json(data: object) -> str:
    return json.dumps(data, ensure_ascii=True, indent=2) + "\n"


if __name__ == "__main__":
    raise SystemExit(main())
