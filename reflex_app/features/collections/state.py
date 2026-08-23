from __future__ import annotations
import reflex as rx
from datosenorden.application.public_collections import public_collection
from datosenorden.db.session import SessionLocal
from reflex_app.helpers.routing import _router_query_value

class CollectionState(rx.State):
    title: str = ""
    description: str = ""
    items: list[dict] = []
    query: str = ""
    loaded: bool = False
    def load_collection(self):
        key = _router_query_value(self.router, "category")
        with SessionLocal() as session:
            view = public_collection(session, key)
        self.title = str(view.get("title", "Categoría"))
        self.description = str(view.get("description", ""))
        self.items = list(view.get("items", []))
        self.loaded = bool(view.get("found", False))
