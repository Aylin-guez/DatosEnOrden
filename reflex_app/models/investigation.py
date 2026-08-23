from __future__ import annotations

from typing import NotRequired, TypedDict


class InvestigationTopic(TypedDict):
    label: str
    example: str
    collection_href: NotRequired[str]
    collection_key: NotRequired[str]


INVESTIGATION_TOPICS: list[InvestigationTopic] = [
    {"label": "Organismos públicos", "example": "Organismos con información incorporada", "collection_href": "/collections?category=organisms", "collection_key": "organisms"},
    {"label": "Empresas proveedoras", "example": "Proveedores con información incorporada", "collection_href": "/collections?category=companies", "collection_key": "companies"},
    {"label": "Personas", "example": "Autoridades y representantes en registros locales"},
    {"label": "Autoridades", "example": "Cargos publicos y periodos declarados"},
    {"label": "Presupuestos", "example": "DIPRES budget 2026 Servicio de Salud Arauco"},
    {"label": "Contratos", "example": "Órdenes de compra ChileCompra incorporadas", "collection_href": "/collections?category=contracts", "collection_key": "contracts"},
    {"label": "Reuniones de Lobby", "example": "Reuniones registradas con contraparte y materia"},
    {"label": "Informes de Contraloria", "example": "Informes y observaciones de muestra"},
    {"label": "Publicaciones del Diario Oficial", "example": "Publicaciones oficiales del caso demo"},
    {"label": "Declaraciones de intereses", "example": "Declaraciones locales de ejemplo"},
    {"label": "Sanciones y procedimientos", "example": "Procedimientos y resoluciones administrativas de prueba"},
]
