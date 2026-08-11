from __future__ import annotations

from typing import TypedDict


class SourceCoverageTemplateRow(TypedDict):
    source: str
    status: str
    contribution: str


SOURCE_COVERAGE_TEMPLATE: list[SourceCoverageTemplateRow] = [
    {"source": "ChileCompra", "status": "activo con datos", "contribution": "Compras publicas, proveedores, contratos y evidencia de adquisiciones."},
    {"source": "DIPRES", "status": "prototipo con datos", "contribution": "Presupuestos, anos fiscales y contexto de gasto publico."},
    {"source": "Lobby", "status": "prototipo con datos", "contribution": "Reuniones, contrapartes, materias declaradas y fechas."},
    {"source": "Transparencia Activa", "status": "prototipo con datos", "contribution": "Cargos, roles administrativos y periodos asociados."},
    {"source": "Contraloria", "status": "prototipo con datos", "contribution": "Informes y observaciones para trazabilidad documental."},
    {"source": "Diario Oficial", "status": "prototipo con datos", "contribution": "Publicaciones oficiales y actos administrativos publicados."},
    {"source": "Registro Empresas", "status": "prototipo con datos", "contribution": "Empresas, representantes y relaciones societarias locales."},
    {"source": "Declaraciones de Intereses", "status": "prototipo con datos", "contribution": "Declaraciones, intereses declarados y posibles entidades mencionadas."},
    {"source": "SERVEL", "status": "prototipo con datos", "contribution": "Autoridades electas y periodos electorales de muestra."},
    {"source": "Municipalidades", "status": "prototipo con datos", "contribution": "Contexto municipal y proyectos locales de muestra."},
    {"source": "Sanciones y Procedimientos", "status": "prototipo con datos", "contribution": "Procedimientos y resoluciones administrativas de prueba con trazabilidad local."},
]
