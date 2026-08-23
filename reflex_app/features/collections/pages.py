from __future__ import annotations
import reflex as rx
from reflex_app.constants.routes import PAGE_SEARCH
from reflex_app.features.collections.state import CollectionState
from reflex_app.layouts.shell import shell
from reflex_app.metadata.pages import PUBLIC_OG_IMAGE_URL, _page_meta

@rx.page(
    route="/collections",
    title="Colección - DatosEnOrden Ciudadano",
    image=PUBLIC_OG_IMAGE_URL,
    meta=_page_meta(
        "/collections",
        "colecciones, información pública, fuentes, expedientes",
        "Colección - DatosEnOrden Ciudadano",
        "Colecciones de información pública y expedientes conectados.",
    ),
    on_load=CollectionState.load_collection,
)
def collections() -> rx.Component:
    return shell(rx.vstack(
        rx.box(rx.text(CollectionState.title, class_name="title"), rx.text(CollectionState.description, class_name="subtitle"), rx.text(CollectionState.items.length(), " resultados reales", class_name="source-fact"), class_name="hero"),
        rx.cond(CollectionState.items, rx.grid(rx.foreach(CollectionState.items, lambda row: rx.box(rx.text(row["object_type"], class_name="badge badge-teal"), rx.text(row["title"], class_name="card-title"), rx.text(row["context"], class_name="muted small"), rx.text(row["sources_text"], class_name="source-fact"), rx.button("Abrir", on_click=rx.redirect(row["target"]), class_name="button button-secondary"), class_name="card")), columns="3", spacing="3", class_name="responsive-grid"), rx.text("Esta categoría aún no tiene información pública incorporada.", class_name="muted")), spacing="4", align="stretch"), active_page=PAGE_SEARCH)
