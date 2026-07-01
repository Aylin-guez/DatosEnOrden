from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum
from html import escape
from pathlib import Path
from typing import Any


LOCAL_TEST_DATA = "LOCAL_TEST_DATA"
NOT_OFFICIAL_DATA = "NOT_OFFICIAL_DATA"
INTERNAL_ENGINE_NAME = "DatosEnOrden seguimiento engine"
PUBLIC_FEATURE_NAME = "Seguimiento"
DEMO_TRACKING_ITEM_ID = "tracking-arauco-hospital-strengthening"
DEMO_ENTITY_NAME = "SERVICIO DE SALUD ARAUCO HOSPITAL DE ARAUCO"


class TrackingStatus(StrEnum):
    PROPOSED = "proposed"
    PUBLISHED = "published"
    IN_DISCUSSION = "in_discussion"
    APPROVED = "approved"
    REJECTED = "rejected"
    IMPLEMENTED = "implemented"
    PARTIALLY_IMPLEMENTED = "partially_implemented"
    UPDATED = "updated"
    ARCHIVED = "archived"
    UNKNOWN = "unknown"


OPEN_TRACKING_STATUSES = {
    TrackingStatus.PROPOSED,
    TrackingStatus.PUBLISHED,
    TrackingStatus.IN_DISCUSSION,
    TrackingStatus.APPROVED,
    TrackingStatus.UPDATED,
    TrackingStatus.UNKNOWN,
}
DONE_TRACKING_STATUSES = {
    TrackingStatus.IMPLEMENTED,
    TrackingStatus.PARTIALLY_IMPLEMENTED,
    TrackingStatus.REJECTED,
    TrackingStatus.ARCHIVED,
}


@dataclass(frozen=True)
class OfficialDocumentRef:
    id: str
    title: str
    source: str
    document_type: str
    published_at: str
    official_url: str
    summary: str
    hash_sha256: str = ""
    classification: str = LOCAL_TEST_DATA
    official_status: str = NOT_OFFICIAL_DATA


@dataclass(frozen=True)
class EvidenceAnchor:
    id: str
    source: str
    label: str
    url: str
    excerpt: str
    document_id: str = ""
    classification: str = LOCAL_TEST_DATA
    official_status: str = NOT_OFFICIAL_DATA


@dataclass(frozen=True)
class TrackingEvent:
    id: str
    date: str
    status: TrackingStatus
    title: str
    description: str
    source: str
    evidence_ids: tuple[str, ...] = ()
    document_ids: tuple[str, ...] = ()
    related_entity_names: tuple[str, ...] = ()


@dataclass(frozen=True)
class TrackingHistoryEntry:
    id: str
    date: str
    actor: str
    field: str
    previous_value: str
    new_value: str
    event_id: str
    note: str = ""


@dataclass(frozen=True)
class TrackingDocumentCoverage:
    expected_document_ids: tuple[str, ...]
    linked_document_ids: tuple[str, ...]
    missing_document_ids: tuple[str, ...]
    coverage_percent: int


@dataclass(frozen=True)
class TrackingProgress:
    total_events: int
    completed_events: int
    open_events: int
    documented_events: int
    progress_percent: int
    document_coverage_percent: int
    current_status: TrackingStatus


@dataclass(frozen=True)
class TrackingAlert:
    id: str
    severity: str
    title: str
    detail: str
    event_id: str = ""
    document_id: str = ""
    days_open: int = 0


@dataclass(frozen=True)
class FollowTarget:
    id: str
    label: str
    target_type: str
    target_value: str
    enabled: bool = False
    note: str = "Proximamente: suscripcion local a cambios, sin envio de emails en esta fase."


@dataclass(frozen=True)
class TrackableItem:
    id: str
    title: str
    item_type: str
    current_status: TrackingStatus
    summary: str
    responsible_entity: str
    related_expediente_target: str
    related_sources: tuple[str, ...]
    classification: str = LOCAL_TEST_DATA
    official_status: str = NOT_OFFICIAL_DATA


@dataclass(frozen=True)
class TrackingTimeline:
    item: TrackableItem
    events: tuple[TrackingEvent, ...]
    documents: tuple[OfficialDocumentRef, ...]
    evidence: tuple[EvidenceAnchor, ...]
    follow_targets: tuple[FollowTarget, ...]


def build_tracking_demo() -> TrackingTimeline:
    item = TrackableItem(
        id=DEMO_TRACKING_ITEM_ID,
        title="Programa / propuesta de fortalecimiento hospitalario Arauco",
        item_type="public_program_proposal",
        current_status=TrackingStatus.PARTIALLY_IMPLEMENTED,
        summary=(
            "Caso local de demostracion para seguir la historia de una propuesta publica: "
            "desde una propuesta inicial hasta documentos, presupuesto, compras, proveedores, "
            "publicaciones y controles asociados. No representa datos oficiales."
        ),
        responsible_entity=DEMO_ENTITY_NAME,
        related_expediente_target=DEMO_ENTITY_NAME,
        related_sources=(
            "DIPRES",
            "ChileCompra",
            "Diario Oficial",
            "Contraloria",
            "Transparencia Activa",
            "Lobby",
            "Registro Empresas",
            "Sanciones y Procedimientos",
            "Declaraciones de Intereses",
        ),
    )
    documents = (
        OfficialDocumentRef(
            id="doc-propuesta-arauco-2026",
            title="Propuesta local de fortalecimiento hospitalario Arauco 2026",
            source="Documento local de demo",
            document_type="proposal",
            published_at="2026-01-15",
            official_url="local://tracking/araucodemo/propuesta-2026",
            summary="Metadata local de una propuesta ficticia usada para mostrar seguimiento documental.",
            hash_sha256="demo-sha256-propuesta-arauco-2026",
        ),
        OfficialDocumentRef(
            id="doc-dipres-arauco-2026",
            title="Ficha presupuestaria local DIPRES para fortalecimiento hospitalario",
            source="DIPRES",
            document_type="budget_record",
            published_at="2026-02-02",
            official_url="local://tracking/araucodemo/dipres-2026",
            summary="Referencia liviana a presupuesto de muestra, sin almacenar PDF pesado.",
            hash_sha256="demo-sha256-dipres-arauco-2026",
        ),
        OfficialDocumentRef(
            id="doc-diario-arauco-2026",
            title="Publicacion local de acto administrativo asociado",
            source="Diario Oficial",
            document_type="official_publication",
            published_at="2026-03-24",
            official_url="local://tracking/araucodemo/diario-oficial-12801",
            summary="Publicacion de demostracion conectada con cargo y acto administrativo.",
        ),
        OfficialDocumentRef(
            id="doc-control-arauco-2026",
            title="Informe local de control y seguimiento documental",
            source="Contraloria",
            document_type="control_report",
            published_at="2026-05-21",
            official_url="local://tracking/araucodemo/control-2026",
            summary="Informe de muestra para explicar revision de evidencia y trazabilidad.",
        ),
    )
    evidence = (
        EvidenceAnchor(
            id="ev-propuesta",
            source="Documento local de demo",
            label="Propuesta marcada como LOCAL_TEST_DATA",
            url="local://tracking/araucodemo/propuesta-2026#metadata",
            excerpt="La propuesta describe objetivos, etapas y fuentes esperadas para el seguimiento.",
            document_id="doc-propuesta-arauco-2026",
        ),
        EvidenceAnchor(
            id="ev-presupuesto",
            source="DIPRES",
            label="Registro presupuestario de muestra",
            url="local://tracking/araucodemo/dipres-2026#budget",
            excerpt="Referencia a asignacion presupuestaria local usada para el caso demo.",
            document_id="doc-dipres-arauco-2026",
        ),
        EvidenceAnchor(
            id="ev-compra",
            source="ChileCompra",
            label="Compra publica de muestra",
            url="local://tracking/araucodemo/chilecompra-oc-2026",
            excerpt="Orden de compra ficticia relacionada con insumos o servicios del programa.",
        ),
        EvidenceAnchor(
            id="ev-proveedor",
            source="Registro Empresas",
            label="Proveedor relacionado en registro local",
            url="local://tracking/araucodemo/registro-empresas",
            excerpt="Metadata local del proveedor usado para mostrar conexion con expediente.",
        ),
        EvidenceAnchor(
            id="ev-publicacion",
            source="Diario Oficial",
            label="Publicacion/cargo asociado de muestra",
            url="local://tracking/araucodemo/diario-oficial-12801#publication",
            excerpt="Publicacion local usada para enlazar acto administrativo y cargo.",
            document_id="doc-diario-arauco-2026",
        ),
        EvidenceAnchor(
            id="ev-control",
            source="Contraloria",
            label="Control documental de muestra",
            url="local://tracking/araucodemo/control-2026#report",
            excerpt="Registro local para mostrar control y seguimiento sin inferir irregularidades.",
            document_id="doc-control-arauco-2026",
        ),
        EvidenceAnchor(
            id="ev-transparencia-lobby",
            source="Transparencia Activa / Lobby",
            label="Roles y reuniones relacionadas",
            url="local://tracking/araucodemo/transparencia-lobby",
            excerpt="Cruce descriptivo de roles y reuniones en datos locales de prueba.",
        ),
    )
    events = (
        TrackingEvent(
            id="evt-proposed",
            date="2026-01-15",
            status=TrackingStatus.PROPOSED,
            title="Propuesta registrada",
            description="Se crea una propuesta local de fortalecimiento hospitalario para seguimiento publico.",
            source="Documento local de demo",
            evidence_ids=("ev-propuesta",),
            document_ids=("doc-propuesta-arauco-2026",),
            related_entity_names=(DEMO_ENTITY_NAME,),
        ),
        TrackingEvent(
            id="evt-published",
            date="2026-02-02",
            status=TrackingStatus.PUBLISHED,
            title="Documento presupuestario asociado",
            description="Se enlaza una referencia DIPRES de muestra como documento asociado a la propuesta.",
            source="DIPRES",
            evidence_ids=("ev-presupuesto",),
            document_ids=("doc-dipres-arauco-2026",),
            related_entity_names=(DEMO_ENTITY_NAME,),
        ),
        TrackingEvent(
            id="evt-budget-approved",
            date="2026-02-20",
            status=TrackingStatus.APPROVED,
            title="Presupuesto de muestra aprobado",
            description="El seguimiento registra un hito presupuestario local para continuar la trazabilidad.",
            source="DIPRES",
            evidence_ids=("ev-presupuesto",),
            document_ids=("doc-dipres-arauco-2026",),
            related_entity_names=(DEMO_ENTITY_NAME,),
        ),
        TrackingEvent(
            id="evt-procurement",
            date="2026-03-10",
            status=TrackingStatus.IN_DISCUSSION,
            title="Compra publica relacionada",
            description="Se conecta una compra publica local con el programa y su expediente relacionado.",
            source="ChileCompra",
            evidence_ids=("ev-compra", "ev-proveedor"),
            related_entity_names=(DEMO_ENTITY_NAME, "CONSULTORA PUBLICA SPA"),
        ),
        TrackingEvent(
            id="evt-official-publication",
            date="2026-03-24",
            status=TrackingStatus.UPDATED,
            title="Publicacion y cargo asociados",
            description="Se agrega una publicacion local y un cargo asociado para explicar cambios documentales.",
            source="Diario Oficial / Transparencia Activa",
            evidence_ids=("ev-publicacion", "ev-transparencia-lobby"),
            document_ids=("doc-diario-arauco-2026",),
            related_entity_names=(DEMO_ENTITY_NAME, "SOFIA RAMOS"),
        ),
        TrackingEvent(
            id="evt-lobby",
            date="2026-05-15",
            status=TrackingStatus.UPDATED,
            title="Reunion registrada en datos locales",
            description="El seguimiento enlaza una reunion de muestra como contexto documental.",
            source="Lobby",
            evidence_ids=("ev-transparencia-lobby",),
            related_entity_names=(DEMO_ENTITY_NAME, "SOFIA RAMOS"),
        ),
        TrackingEvent(
            id="evt-control",
            date="2026-05-21",
            status=TrackingStatus.PARTIALLY_IMPLEMENTED,
            title="Control y seguimiento documental",
            description="Se registra un control local de muestra para revisar evidencia y trazabilidad.",
            source="Contraloria / Sanciones y Procedimientos",
            evidence_ids=("ev-control",),
            document_ids=("doc-control-arauco-2026",),
            related_entity_names=(DEMO_ENTITY_NAME,),
        ),
    )
    follow_targets = (
        FollowTarget(
            id="follow-tracking-item",
            label="Seguir cambios de esta propuesta",
            target_type="tracking_item",
            target_value=DEMO_TRACKING_ITEM_ID,
        ),
        FollowTarget(
            id="follow-expediente",
            label="Seguir expediente relacionado",
            target_type="expediente",
            target_value=DEMO_ENTITY_NAME,
        ),
    )
    return TrackingTimeline(item=item, events=events, documents=documents, evidence=evidence, follow_targets=follow_targets)


def list_tracking_items() -> list[TrackableItem]:
    return [build_tracking_demo().item]


def get_tracking_item(item_id: str) -> TrackingTimeline | None:
    timeline = build_tracking_demo()
    return timeline if item_id == timeline.item.id else None


def get_tracking_timeline(item_id: str) -> TrackingTimeline | None:
    return get_tracking_item(item_id)


def render_tracking_demo_summary(timeline: TrackingTimeline | None = None) -> str:
    data = timeline or build_tracking_demo()
    lines = [
        "tracking_demo_summary:",
        f"  id={data.item.id}",
        f"  title={data.item.title}",
        f"  status={data.item.current_status.value}",
        f"  classification={data.item.classification}",
        f"  official_status={data.item.official_status}",
        f"  events={len(data.events)}",
        f"  documents={len(data.documents)}",
        f"  evidence={len(data.evidence)}",
        f"  related_expediente={data.item.related_expediente_target}",
        "  sources:",
    ]
    lines.extend(f"    - {source}" for source in data.item.related_sources)
    return "\n".join(lines)


def export_tracking_demo_report(output_path: Path | str | None = None, timeline: TrackingTimeline | None = None) -> str:
    data = timeline or build_tracking_demo()
    path = Path(output_path) if output_path is not None else Path("reports") / "tracking_demo_arauco.html"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_render_tracking_html(data), encoding="utf-8")
    return str(path)


def _render_tracking_html(timeline: TrackingTimeline) -> str:
    item = timeline.item
    event_items = "\n".join(
        f"<li><strong>{escape(event.date)} - {escape(event.title)}</strong>"
        f"<br><span>{escape(event.status.value)}</span>"
        f"<p>{escape(event.description)}</p>"
        f"<small>Fuente: {escape(event.source)}</small></li>"
        for event in timeline.events
    )
    document_items = "\n".join(
        f"<li><strong>{escape(doc.title)}</strong>"
        f"<br><span>{escape(doc.source)} | {escape(doc.document_type)} | {escape(doc.published_at)}</span>"
        f"<p>{escape(doc.summary)}</p>"
        f"<code>{escape(doc.official_url)}</code></li>"
        for doc in timeline.documents
    )
    evidence_items = "\n".join(
        f"<li><strong>{escape(anchor.label)}</strong>"
        f"<br><span>{escape(anchor.source)}</span>"
        f"<p>{escape(anchor.excerpt)}</p>"
        f"<code>{escape(anchor.url)}</code></li>"
        for anchor in timeline.evidence
    )
    sources = ", ".join(escape(source) for source in item.related_sources)
    return f"""<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <title>{escape(item.title)} - DatosEnOrden</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 32px; line-height: 1.45; color: #18181b; }}
    header, section {{ max-width: 960px; margin: 0 auto 28px; }}
    .badge {{ display: inline-block; border: 1px solid #0f766e; color: #0f766e; padding: 4px 8px; border-radius: 999px; }}
    li {{ margin-bottom: 16px; }}
    code {{ background: #f4f4f5; padding: 2px 4px; }}
  </style>
</head>
<body>
  <header>
    <p class="badge">{escape(item.classification)} / {escape(item.official_status)}</p>
    <h1>{escape(item.title)}</h1>
    <p>{escape(item.summary)}</p>
    <p><strong>Estado actual:</strong> {escape(item.current_status.value)}</p>
    <p><strong>Expediente relacionado:</strong> {escape(item.related_expediente_target)}</p>
  </header>
  <section>
    <h2>Que se esta siguiendo</h2>
    <p>DatosEnOrden no solo busca entidades: permite seguir la historia publica de documentos, propuestas y expedientes conectados por evidencia.</p>
    <p><strong>Fuentes consultadas:</strong> {sources}</p>
  </section>
  <section>
    <h2>Timeline</h2>
    <ol>{event_items}</ol>
  </section>
  <section>
    <h2>Documentos oficiales asociados</h2>
    <ul>{document_items}</ul>
  </section>
  <section>
    <h2>Evidencia asociada</h2>
    <ul>{evidence_items}</ul>
  </section>
  <section>
    <h2>Aclaracion</h2>
    <p>Este reporte usa datos locales de prueba, no oficiales. No afirma causalidad, irregularidad ni responsabilidad.</p>
  </section>
</body>
</html>
"""


def build_tracking_history(timeline: TrackingTimeline, actor: str = INTERNAL_ENGINE_NAME) -> tuple[TrackingHistoryEntry, ...]:
    previous_status = TrackingStatus.UNKNOWN.value
    entries: list[TrackingHistoryEntry] = []
    for event in sorted(timeline.events, key=lambda item: item.date):
        new_status = event.status.value
        if new_status != previous_status:
            entries.append(
                TrackingHistoryEntry(
                    id=f"hist-{event.id}-status",
                    date=event.date,
                    actor=actor,
                    field="status",
                    previous_value=previous_status,
                    new_value=new_status,
                    event_id=event.id,
                    note=event.title,
                )
            )
            previous_status = new_status
        if event.document_ids:
            entries.append(
                TrackingHistoryEntry(
                    id=f"hist-{event.id}-documents",
                    date=event.date,
                    actor=actor,
                    field="documents",
                    previous_value="",
                    new_value=", ".join(event.document_ids),
                    event_id=event.id,
                    note="Documentos asociados al hito.",
                )
            )
    return tuple(entries)


def calculate_document_coverage(timeline: TrackingTimeline) -> TrackingDocumentCoverage:
    expected_ids = tuple(document.id for document in timeline.documents)
    linked_ids = tuple(
        sorted({document_id for event in timeline.events for document_id in event.document_ids})
    )
    missing_ids = tuple(document_id for document_id in expected_ids if document_id not in linked_ids)
    coverage = _percent(len(expected_ids) - len(missing_ids), len(expected_ids))
    return TrackingDocumentCoverage(
        expected_document_ids=expected_ids,
        linked_document_ids=linked_ids,
        missing_document_ids=missing_ids,
        coverage_percent=coverage,
    )


def calculate_tracking_progress(timeline: TrackingTimeline) -> TrackingProgress:
    coverage = calculate_document_coverage(timeline)
    completed_events = sum(1 for event in timeline.events if event.status in DONE_TRACKING_STATUSES)
    open_events = sum(1 for event in timeline.events if event.status in OPEN_TRACKING_STATUSES)
    documented_events = sum(1 for event in timeline.events if event.document_ids or event.evidence_ids)
    progress = _percent(completed_events, len(timeline.events))
    return TrackingProgress(
        total_events=len(timeline.events),
        completed_events=completed_events,
        open_events=open_events,
        documented_events=documented_events,
        progress_percent=progress,
        document_coverage_percent=coverage.coverage_percent,
        current_status=timeline.item.current_status,
    )


def build_tracking_alerts(
    timeline: TrackingTimeline,
    *,
    today: date | None = None,
    stale_days: int = 45,
) -> tuple[TrackingAlert, ...]:
    reference_date = today or date.today()
    alerts: list[TrackingAlert] = []
    for event in timeline.events:
        if not event.evidence_ids and not event.document_ids:
            alerts.append(
                TrackingAlert(
                    id=f"alert-{event.id}-without-support",
                    severity="medium",
                    title="Hito sin respaldo asociado",
                    detail="El hito no tiene documentos ni anclas de evidencia enlazadas.",
                    event_id=event.id,
                )
            )
        event_date = _parse_date(event.date)
        if event.status in OPEN_TRACKING_STATUSES and event_date is not None:
            days_open = (reference_date - event_date).days
            if days_open > stale_days:
                alerts.append(
                    TrackingAlert(
                        id=f"alert-{event.id}-stale",
                        severity="low",
                        title="Hito abierto sin actualizacion reciente",
                        detail=f"El hito lleva {days_open} dias desde su fecha registrada.",
                        event_id=event.id,
                        days_open=days_open,
                    )
                )
    for missing_id in calculate_document_coverage(timeline).missing_document_ids:
        alerts.append(
            TrackingAlert(
                id=f"alert-{missing_id}-not-linked",
                severity="medium",
                title="Documento sin hito enlazado",
                detail="El documento esta registrado, pero no aparece enlazado desde el timeline.",
                document_id=missing_id,
            )
        )
    return tuple(alerts)


def build_tracking_overview(timeline: TrackingTimeline, *, today: date | None = None) -> dict[str, Any]:
    progress = calculate_tracking_progress(timeline)
    coverage = calculate_document_coverage(timeline)
    alerts = build_tracking_alerts(timeline, today=today)
    return {
        "item_id": timeline.item.id,
        "current_status": timeline.item.current_status.value,
        "progress": progress.__dict__ | {"current_status": progress.current_status.value},
        "document_coverage": coverage.__dict__,
        "alerts": [alert.__dict__ for alert in alerts],
        "history": [entry.__dict__ for entry in build_tracking_history(timeline)],
    }


def _percent(part: int, total: int) -> int:
    if total <= 0:
        return 0
    return round((part / total) * 100)


def _parse_date(value: str) -> date | None:
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


def tracking_to_dict(timeline: TrackingTimeline) -> dict[str, Any]:
    return {
        "item": _item_to_dict(timeline.item),
        "events": [_event_to_dict(event) for event in timeline.events],
        "documents": [document.__dict__ for document in timeline.documents],
        "evidence": [anchor.__dict__ for anchor in timeline.evidence],
        "follow_targets": [target.__dict__ for target in timeline.follow_targets],
        "overview": build_tracking_overview(timeline),
    }


def _item_to_dict(item: TrackableItem) -> dict[str, Any]:
    return {**item.__dict__, "current_status": item.current_status.value}


def _event_to_dict(event: TrackingEvent) -> dict[str, Any]:
    return {**event.__dict__, "status": event.status.value}
