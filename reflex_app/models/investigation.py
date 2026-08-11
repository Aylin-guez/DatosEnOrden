from __future__ import annotations

from typing import TypedDict


class InvestigationTopic(TypedDict):
    label: str
    example: str


INVESTIGATION_TOPICS: list[InvestigationTopic] = [
    {"label": "Organismos publicos", "example": "SERVICIO DE SALUD ARAUCO HOSPITAL DE ARAUCO"},
    {"label": "Empresas proveedoras", "example": "Consultora Publica SpA"},
    {"label": "Personas", "example": "Autoridades y representantes en registros locales"},
    {"label": "Autoridades", "example": "Cargos publicos y periodos declarados"},
    {"label": "Presupuestos", "example": "DIPRES budget 2026 Servicio de Salud Arauco"},
    {"label": "Contratos", "example": "Ordenes de compra y contratos ChileCompra"},
    {"label": "Reuniones de Lobby", "example": "Reuniones registradas con contraparte y materia"},
    {"label": "Informes de Contraloria", "example": "Informes y observaciones de muestra"},
    {"label": "Publicaciones del Diario Oficial", "example": "Publicaciones oficiales del caso demo"},
    {"label": "Declaraciones de intereses", "example": "Declaraciones locales de ejemplo"},
    {"label": "Sanciones y procedimientos", "example": "Procedimientos y resoluciones administrativas de prueba"},
]
