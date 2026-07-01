from __future__ import annotations

from dataclasses import dataclass
from html import escape
from pathlib import Path
from typing import Any

from datosenorden.maintenance.platform_config import PlatformConfig
from datosenorden.maintenance.platform_config import get_default_platform_config
from datosenorden.maintenance.platform_config import output_template_ids
from datosenorden.maintenance.tracking import DEMO_ENTITY_NAME
from datosenorden.maintenance.tracking import DEMO_TRACKING_ITEM_ID
from datosenorden.maintenance.tracking import LOCAL_TEST_DATA
from datosenorden.maintenance.tracking import NOT_OFFICIAL_DATA


DEMO_CITIZEN_REPORT_ID = "citizen-report-arauco-hospital-demo"


@dataclass(frozen=True)
class CitizenReportSection:
    id: str
    title: str
    summary: str
    evidence_refs: tuple[str, ...] = ()


@dataclass(frozen=True)
class CitizenReport:
    id: str
    title: str
    subtitle: str
    subject: str
    summary: str
    current_status: str
    related_expediente_target: str
    related_tracking_item_id: str
    sources: tuple[str, ...]
    sections: tuple[CitizenReportSection, ...]
    evidence_refs: tuple[str, ...]
    classification: str = LOCAL_TEST_DATA
    official_status: str = NOT_OFFICIAL_DATA


def build_citizen_report_demo() -> CitizenReport:
    return CitizenReport(
        id=DEMO_CITIZEN_REPORT_ID,
        title="Reporte ciudadano demo: Servicio de Salud Arauco",
        subtitle="Lectura neutral de fuentes locales de prueba conectadas a un expediente y seguimiento documental.",
        subject=DEMO_ENTITY_NAME,
        summary=(
            "Reporte local de demostracion para explicar como DatosEnOrden convierte registros "
            "publicos y documentales en evidencia navegable. No representa datos oficiales y no "
            "afirma causalidad, irregularidad ni responsabilidad."
        ),
        current_status="demo_read_only",
        related_expediente_target=DEMO_ENTITY_NAME,
        related_tracking_item_id=DEMO_TRACKING_ITEM_ID,
        sources=(
            "ChileCompra",
            "DIPRES",
            "Contraloria",
            "Diario Oficial",
            "Transparencia Activa",
            "Lobby",
            "Registro Empresas",
        ),
        sections=(
            CitizenReportSection(
                id="overview",
                title="Que se observa en el demo",
                summary=(
                    "El caso une un organismo de salud, una propuesta de fortalecimiento, "
                    "presupuesto de muestra, compras publicas, proveedor, publicaciones y control documental."
                ),
                evidence_refs=("ev-propuesta", "ev-presupuesto"),
            ),
            CitizenReportSection(
                id="traceability",
                title="Trazabilidad documental",
                summary=(
                    "La lectura sigue una secuencia: propuesta, documento presupuestario, compra publica, "
                    "proveedor, publicacion o cargo, y control asociado."
                ),
                evidence_refs=("ev-compra", "ev-publicacion", "ev-control"),
            ),
            CitizenReportSection(
                id="citizen-use",
                title="Como usarlo en una revision ciudadana",
                summary=(
                    "Una persona puede abrir el expediente, revisar evidencia por fuente y volver al seguimiento "
                    "para ver como cambia la historia documental del caso."
                ),
                evidence_refs=("ev-transparencia-lobby",),
            ),
        ),
        evidence_refs=(
            "ev-propuesta",
            "ev-presupuesto",
            "ev-compra",
            "ev-proveedor",
            "ev-publicacion",
            "ev-control",
            "ev-transparencia-lobby",
        ),
    )


def list_citizen_reports() -> list[CitizenReport]:
    return [build_citizen_report_demo()]


def get_citizen_report(report_id: str) -> CitizenReport | None:
    report = build_citizen_report_demo()
    return report if report.id == report_id else None


def list_report_template_ids(config: PlatformConfig | None = None, audience_id: str | None = None) -> tuple[str, ...]:
    return output_template_ids(config or get_default_platform_config(), audience_id)


def export_citizen_report_demo(output_path: Path | str | None = None, report: CitizenReport | None = None) -> str:
    data = report or build_citizen_report_demo()
    path = Path(output_path) if output_path is not None else Path("reports") / "citizen_report_arauco.html"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_render_citizen_report_html(data), encoding="utf-8")
    return str(path)


def citizen_report_to_dict(report: CitizenReport) -> dict[str, Any]:
    return {
        "id": report.id,
        "title": report.title,
        "subtitle": report.subtitle,
        "subject": report.subject,
        "summary": report.summary,
        "current_status": report.current_status,
        "related_expediente_target": report.related_expediente_target,
        "related_tracking_item_id": report.related_tracking_item_id,
        "sources": list(report.sources),
        "sections": [section.__dict__ for section in report.sections],
        "evidence_refs": list(report.evidence_refs),
        "classification": report.classification,
        "official_status": report.official_status,
    }


def _render_citizen_report_html(report: CitizenReport) -> str:
    sources = ", ".join(escape(source) for source in report.sources)
    sections = "\n".join(
        f"<article><h3>{escape(section.title)}</h3><p>{escape(section.summary)}</p>"
        f"<small>Evidencia relacionada: {escape(', '.join(section.evidence_refs))}</small></article>"
        for section in report.sections
    )
    evidence = "\n".join(f"<li>{escape(ref)}</li>" for ref in report.evidence_refs)
    return f"""<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <title>{escape(report.title)} - DatosEnOrden</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 32px; line-height: 1.5; color: #18181b; }}
    header, section {{ max-width: 960px; margin: 0 auto 28px; }}
    article {{ border: 1px solid #d4d4d8; border-radius: 8px; padding: 14px; margin-bottom: 12px; }}
    .badge {{ display: inline-block; border: 1px solid #0f766e; color: #0f766e; padding: 4px 8px; border-radius: 999px; }}
  </style>
</head>
<body>
  <header>
    <p class="badge">{escape(report.classification)} / {escape(report.official_status)}</p>
    <h1>{escape(report.title)}</h1>
    <p>{escape(report.subtitle)}</p>
    <p><strong>Materia:</strong> {escape(report.subject)}</p>
    <p><strong>Estado:</strong> {escape(report.current_status)}</p>
  </header>
  <section>
    <h2>Resumen ciudadano</h2>
    <p>{escape(report.summary)}</p>
    <p><strong>Fuentes:</strong> {sources}</p>
  </section>
  <section>
    <h2>Lectura guiada</h2>
    {sections}
  </section>
  <section>
    <h2>Expediente y seguimiento relacionados</h2>
    <p>Expediente: {escape(report.related_expediente_target)}</p>
    <p>Seguimiento: {escape(report.related_tracking_item_id)}</p>
  </section>
  <section>
    <h2>Evidencia referenciada</h2>
    <ul>{evidence}</ul>
  </section>
  <section>
    <h2>Aclaracion</h2>
    <p>Este reporte usa datos locales de prueba, no oficiales. No afirma causalidad, irregularidad ni responsabilidad.</p>
  </section>
</body>
</html>
"""
