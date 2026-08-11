from __future__ import annotations

# Imports explícitos: el registry es el único lugar que registra páginas.
from reflex_app.app import not_found as not_found_page
from reflex_app.features.pulse import pages as pulse_pages
from reflex_app.features.sources import pages as sources_pages
from reflex_app.features.demo import pages as demo_pages
from reflex_app.features.document_reading import pages as document_reading_pages
from reflex_app.features.institutional import pages as institutional_pages
from reflex_app.features.search import pages as search_pages
from reflex_app.features.tracking import pages as tracking_pages
from reflex_app.features.reports import pages as reports_pages
from reflex_app.features.dashboard import pages as dashboard_pages
from reflex_app.features.public_record import pages as public_record_pages
from reflex_app.features.laboratory import pages as laboratory_pages

PAGE_MODULES = (
    not_found_page,
    pulse_pages,
    sources_pages,
    demo_pages,
    document_reading_pages,
    institutional_pages,
    search_pages,
    tracking_pages,
    reports_pages,
    dashboard_pages,
    public_record_pages,
    laboratory_pages,
)


def registered_page_modules() -> tuple[object, ...]:
    return PAGE_MODULES
