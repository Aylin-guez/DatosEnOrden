from __future__ import annotations

import reflex as rx
from reflex.page import DECORATED_PAGES

import reflex_app.reflex_app as entrypoint
from reflex_app.app.not_found import not_found
from reflex_app.app.styles import style
from reflex_app.constants.public import PUBLIC_OG_IMAGE_ALT, PUBLIC_SITE_AUTHOR, PUBLIC_SITE_NAME, PUBLIC_THEME_COLOR
from reflex_app.metadata.pages import PUBLIC_OG_IMAGE_URL, _public_url
from reflex_app.features.dashboard import pages as dashboard_pages
from reflex_app.features.dashboard.state import DashboardState
from reflex_app.features.demo import pages as demo_pages
from reflex_app.features.demo.state import DemoState
from reflex_app.features.document_reading import pages as document_reading_pages
from reflex_app.features.document_reading.state import DocumentReadingState
from reflex_app.features.institutional import pages as institutional_pages
from reflex_app.features.laboratory import pages as laboratory_pages
from reflex_app.features.laboratory.state import LaboratoryState
from reflex_app.features.pulse import pages as pulse_pages
from reflex_app.features.pulse.state import PulseState
from reflex_app.features.public_record import pages as public_record_pages
from reflex_app.features.public_record.state import PublicRecordState
from reflex_app.features.reports import pages as reports_pages
from reflex_app.features.reports.state import ReportsState
from reflex_app.features.search import pages as search_pages
from reflex_app.features.search.state import SearchState
from reflex_app.features.sources import pages as sources_pages
from reflex_app.features.sources.state import SourcesState
from reflex_app.features.tracking import pages as tracking_pages
from reflex_app.features.tracking.state import TrackingState


PAGE_BY_NAME = {
    "not_found": not_found,
    "home": pulse_pages.home,
    "ecosystem": sources_pages.ecosystem,
    "sources": sources_pages.sources,
    "demo": demo_pages.demo,
    "topic": document_reading_pages.topic,
    "knowledge": document_reading_pages.knowledge,
    "official_document": document_reading_pages.official_document,
    "library": document_reading_pages.library,
    "project": institutional_pages.project,
    "studio": institutional_pages.studio,
    "support": institutional_pages.support,
    "search": search_pages.search,
    "discover": search_pages.discover,
    "tracking": tracking_pages.tracking,
    "chronology": tracking_pages.chronology,
    "reports": reports_pages.reports,
    "dashboard": dashboard_pages.dashboard,
    "investigation": public_record_pages.investigation,
    "laboratory": laboratory_pages.laboratory,
    "laboratory_expedient": laboratory_pages.laboratory_expedient,
}
EXPECTED_ROUTE_FUNCTIONS = {
    "404": "not_found",
    "/": "home",
    "/ecosystem": "ecosystem",
    "/sources": "sources",
    "/demo": "demo",
    "/topic": "topic",
    "/knowledge": "knowledge",
    "/official-document": "official_document",
    "/library": "library",
    "/project": "project",
    "/studio": "studio",
    "/support": "support",
    "/search": "search",
    "/discover": "discover",
    "/tracking": "tracking",
    "/chronology": "chronology",
    "/reports": "reports",
    "/dashboard": "dashboard",
    "/investigation": "investigation",
    "/laboratory": "laboratory",
    "/laboratory/expedient": "laboratory_expedient",
}
EXPECTED_MOUNT_HANDLERS = {
    "/": PulseState.load_home,
    "/ecosystem": SourcesState.load_ecosystem,
    "/sources": SourcesState.load_ecosystem,
    "/demo": DemoState.load_demo,
    "/topic": DocumentReadingState.load_topic,
    "/knowledge": DocumentReadingState.load_knowledge,
    "/official-document": DocumentReadingState.load_knowledge,
    "/library": DocumentReadingState.load_knowledge,
    "/search": SearchState.load_search,
    "/discover": SearchState.load_discover,
    "/tracking": TrackingState.load_tracking,
    "/chronology": TrackingState.load_tracking,
    "/reports": ReportsState.load_reports,
    "/dashboard": DashboardState.load_dashboard,
}


EXPECTED_OG_DESCRIPTIONS = {
    "/project": "Por qué existe DatosEnOrden, cómo funciona y qué significa un MVP con evidencia verificable.",
}

EXPECTED_PAGE_METADATA = {
    "404": ("Pagina no encontrada - DatosEnOrden Ciudadano", "No encontramos esta ruta, pero puedes buscar informacion publica conectada.", "/404"),
    "/": ("DatosEnOrden Ciudadano - Informacion publica conectada", "Busca entidades, normas, proyectos, contratos, documentos y fuentes publicas con trazabilidad visible.", "/"),
    "/ecosystem": ("Fuentes - DatosEnOrden Ciudadano", "Catalogo honesto de fuentes conocidas, conectores, datos disponibles y cobertura publica.", "/sources"),
    "/sources": ("Fuentes - DatosEnOrden Ciudadano", "Catalogo honesto de fuentes conocidas, conectores, datos disponibles y cobertura publica.", "/sources"),
    "/demo": ("Recorrido guiado - DatosEnOrden", "Recorrido público de ejemplo para entender cómo DatosEnOrden conecta fuentes, expedientes y evidencia.", "/demo"),
    "/topic": ("Lectura documentada - Ley de Presupuestos 2013 - DatosEnOrden", "Lectura documentada del documento oficial principal con evidencia visible y navegación al PDF publicado.", "/topic"),
    "/knowledge": ("Conocimiento - DatosEnOrden", "Resumen estructurado de documentos oficiales con preguntas, claims y evidencia revisable.", "/knowledge"),
    "/official-document": ("Documento fuente - DatosEnOrden", "Visor del documento oficial con PDF publicado, fragmentos citados y contexto de evidencia.", "/official-document"),
    "/library": ("Más lecturas - DatosEnOrden", "Lecturas relacionadas para ampliar el contexto del documento principal y conectar con expediente, informe y cronología.", "/library"),
    "/project": ("Estado del proyecto - DatosEnOrden", "Estado público del proyecto DatosEnOrden, su propósito, alcance y límites.", "/project"),
    "/studio": ("DatosEnOrden Studio", "Entrada comercial para organizaciones que necesitan expedientes, fuentes y automatización documental verificable.", "/studio"),
    "/support": ("Apoyar DatosEnOrden", "Página pública de apoyo y colaboración para el lanzamiento de DatosEnOrden.", "/support"),
    "/search": ("Explorar - DatosEnOrden Ciudadano", "Busqueda compatible para explorar expedientes, entidades y documentos en DatosEnOrden.", "/search"),
    "/discover": ("Explorar - DatosEnOrden Ciudadano", "Entrada guiada compatible para explorar expedientes, entidades y documentos en DatosEnOrden.", "/search"),
    "/tracking": ("Cronología - DatosEnOrden", "Cronología local de documentos, propuestas, estados, evidencia, expedientes relacionados y cambios históricos.", "/tracking"),
    "/chronology": ("Cronología - DatosEnOrden", "Alias público de la cronología ciudadana de DatosEnOrden.", "/chronology"),
    "/reports": ("Informes ciudadanos - DatosEnOrden", "Informes ciudadanos con resumen, evidencia, secciones y exportaci?n local de muestra.", "/reports"),
    "/dashboard": ("Vista ciudadana - DatosEnOrden", "Vista ciudadana de presupuesto, compras, proveedores y reuniones para explorar datos locales de muestra.", "/dashboard"),
    "/investigation": ("Expediente - DatosEnOrden", "Expediente ciudadano para reunir entidades, relaciones, evidencia y trazabilidad en una sola lectura.", "/investigation"),
    "/laboratory": ("Laboratorio de Políticas Públicas - DatosEnOrden", "Lectura pública de problemas, hipótesis, evidencia, indicadores y fuentes.", "/laboratory"),
    "/laboratory/expedient": ("Expediente del Laboratorio - DatosEnOrden", "Ficha pública de un Expediente de políticas públicas.", "/laboratory/expedient"),
}


def _rendered_meta(metadata: list[object]) -> list[dict]:
    return [item.render() if hasattr(item, "render") else item for item in metadata]


def _meta_content(metadata: list[dict], key: str, value: str) -> bool:
    return any(row.get(key) == value for row in metadata)


def _registered_pages() -> dict[str, tuple[object, dict]]:
    return {kwargs["route"]: (page, kwargs) for page, kwargs in DECORATED_PAGES["reflex_app"]}


def _on_mount(page: object) -> object | None:
    chain = page().event_triggers.get("on_mount")
    return None if chain is None else chain.events[0].handler.fn


def test_entrypoint_creates_one_app_and_owns_no_pages_or_style() -> None:
    apps = [(name, value) for name, value in vars(entrypoint).items() if isinstance(value, rx.App)]

    assert apps == [("app", entrypoint.app)]
    assert entrypoint.app.style is style
    assert entrypoint.__all__ == ("app",)
    assert not hasattr(entrypoint, "home")


def test_registered_routes_keep_the_current_functions_and_owners() -> None:
    registered = _registered_pages()

    assert len(registered) == 21
    assert {route: page.__name__ for route, (page, _) in registered.items()} == EXPECTED_ROUTE_FUNCTIONS
    for route, name in EXPECTED_ROUTE_FUNCTIONS.items():
        assert registered[route][0] is PAGE_BY_NAME[name]

    expected_on_load = {
        "/search": SearchState.load_search.fn,
        "/discover": SearchState.load_discover.fn,
        "/tracking": TrackingState.load_tracking.fn,
        "/chronology": TrackingState.load_tracking.fn,
        "/reports": ReportsState.load_reports.fn,
        "/dashboard": DashboardState.load_dashboard.fn,
        "/investigation": PublicRecordState.load_investigation.fn,
        "/laboratory": LaboratoryState.load_catalog.fn,
        "/laboratory/expedient": LaboratoryState.load_expedient.fn,
    }
    assert {
        route: kwargs["on_load"].fn
        for route, (_, kwargs) in registered.items()
        if "on_load" in kwargs
    } == expected_on_load


def test_current_pages_keep_shell_lifecycle_and_metadata_contracts() -> None:
    registered = _registered_pages()
    assert set(EXPECTED_PAGE_METADATA) == set(registered)

    for route, page in PAGE_BY_NAME.items():
        assert "shell" in " ".join(page().render()["props"]), page.__name__

    for route, handler in EXPECTED_MOUNT_HANDLERS.items():
        assert _on_mount(registered[route][0]) is handler.fn

    for route in {"404", "/project", "/studio", "/support", "/investigation", "/laboratory", "/laboratory/expedient"}:
        assert _on_mount(registered[route][0]) is None

    for route, (title, description, canonical_path) in EXPECTED_PAGE_METADATA.items():
        _, kwargs = registered[route]
        assert kwargs["title"] == title
        assert kwargs["description"] == description
        assert kwargs["image"] == PUBLIC_OG_IMAGE_URL
        rendered_meta = _rendered_meta(kwargs["meta"])
        assert _meta_content(rendered_meta, "name", "keywords")
        assert {"name": "author", "content": PUBLIC_SITE_AUTHOR} in rendered_meta
        assert {"name": "theme-color", "content": PUBLIC_THEME_COLOR} in rendered_meta
        assert {"property": "og:type", "content": "website"} in rendered_meta
        assert {"property": "og:site_name", "content": PUBLIC_SITE_NAME} in rendered_meta
        assert {"property": "og:locale", "content": "es_CL"} in rendered_meta
        assert {"property": "og:url", "content": _public_url(canonical_path)} in rendered_meta
        assert {"property": "og:title", "content": title} in rendered_meta
        assert {"property": "og:description", "content": EXPECTED_OG_DESCRIPTIONS.get(route, description)} in rendered_meta
        assert {"property": "og:image", "content": PUBLIC_OG_IMAGE_URL} in rendered_meta
        assert {"property": "og:image:alt", "content": PUBLIC_OG_IMAGE_ALT} in rendered_meta
        assert {"name": "twitter:card", "content": "summary_large_image"} in rendered_meta
        assert {"name": "twitter:title", "content": title} in rendered_meta
        assert {"name": "twitter:description", "content": EXPECTED_OG_DESCRIPTIONS.get(route, description)} in rendered_meta
        assert {"name": "twitter:image", "content": PUBLIC_OG_IMAGE_URL} in rendered_meta
        canonical = next(row for row in rendered_meta if row.get("name") == '"link"')
        assert canonical["props"] == [f'href:"{_public_url(canonical_path)}"', 'rel:"canonical"']
