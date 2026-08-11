from __future__ import annotations

import reflex as rx

from datosenorden.application.public_deployment.sanitization import public_error

from datosenorden.web.app_services import get_data_ecosystem, get_real_data_readiness
from reflex_app.serialization.json_safe import _json_dict, _json_list


class SourcesState(rx.State):
    ecosystem_sources: list[dict] = []
    ecosystem_active_sources: list[dict] = []
    ecosystem_prototype_sources: list[dict] = []
    ecosystem_planned_sources: list[dict] = []
    ecosystem_concepts: list[dict] = []
    ecosystem_roadmap: list[dict] = []
    ecosystem_active_count: int = 0
    ecosystem_prototype_count: int = 0
    ecosystem_planned_count: int = 0
    ecosystem_concept_count: int = 0
    real_data_sources: list[dict] = []
    real_data_ready_count: int = 0
    real_data_partial_count: int = 0
    real_data_demo_count: int = 0
    real_data_without_loader_count: int = 0
    sources_error: str = ""
    sources_error_code: str = ""

    def load_ecosystem(self) -> None:
        self.sources_error = ""
        try:
            ecosystem = get_data_ecosystem()
            sources = [
                {
                    **dict(row),
                    "presentation_status": _presentation_status(row),
                    "catalog_status": "CATALOGUED",
                    "connector_status_label": _connector_status_label(row),
                    "data_status_label": _data_status_label(row),
                    "coverage_status_label": _coverage_status_label(row),
                    "concepts_text": " | ".join(str(item) for item in row.get("concepts", [])),
                    "relationships_text": " | ".join(str(item) for item in row.get("relationships", [])),
                    "connects_with_text": " | ".join(str(item) for item in row.get("connects_with", [])),
                    "entities_text": " | ".join(str(item) for item in row.get("entities", [])),
                    "population_records": int(row.get("population_records", 0) or 0),
                    "population_summary": str(row.get("population_summary", "")),
                    "population_status_label": str(row.get("population_status_label", "")),
                    "population_label": (
                        f"poblacion minima: {row.get('population_status_label', '')} ({int(row.get('population_records', 0) or 0)} registro). {row.get('population_summary', '')}"
                        if int(row.get("population_records", 0) or 0)
                        else ""
                    ),
                    "connector_label": (
                        f"connector: {row.get('connector_status', '')} | entidades {int(row.get('connector_entities', 0) or 0)} | relaciones {int(row.get('connector_relationships', 0) or 0)} | eventos {int(row.get('connector_events', 0) or 0)}"
                        if str(row.get("connector_status", ""))
                        else ""
                    ),
                    "state_graph_contribution_label": (
                        f"Aporta conexiones al StateGraph: {int(row.get('connector_relationships', 0) or 0)} relaciones documentadas."
                        if int(row.get("connector_relationships", 0) or 0)
                        else ""
                    ),
                }
                for row in ecosystem.get("sources", [])
            ]
            self.ecosystem_sources = sources
            self.ecosystem_active_sources = [row for row in sources if row.get("status") == "active"]
            self.ecosystem_prototype_sources = [row for row in sources if row.get("status") == "prototype"]
            self.ecosystem_planned_sources = [row for row in sources if row.get("status") == "planned"]
            self.ecosystem_concepts = [
                {
                    **dict(row),
                    "datasets_text": " | ".join(str(item) for item in row.get("datasets", [])),
                }
                for row in ecosystem.get("concepts", [])
            ]
            self.ecosystem_roadmap = [
                {
                    **dict(row),
                    "sources_text": " | ".join(str(item) for item in row.get("sources", [])),
                    "note_text": "Diario Oficial ya figura como prototipo local." if row.get("status") == "prototype" else "",
                }
                for row in ecosystem.get("roadmap", [])
            ]
            self.ecosystem_active_count = len(self.ecosystem_active_sources)
            self.ecosystem_prototype_count = len(self.ecosystem_prototype_sources)
            self.ecosystem_planned_count = len(self.ecosystem_planned_sources)
            self.ecosystem_concept_count = len(self.ecosystem_concepts)
            readiness = _json_dict(get_real_data_readiness())
            self.real_data_sources = [
                {
                    **dict(row),
                    "entity_types_text": " | ".join(str(item) for item in row.get("entity_types", [])),
                    "last_loaded_text": str(row.get("last_loaded", "from_database")),
                    "official_url_text": str(row.get("official_url", "")) or "Pendiente",
                }
                for row in _json_list(readiness.get("entries", []))
            ]
            totals = _json_dict(readiness.get("totals", {}))
            self.real_data_ready_count = int(totals.get("ready", 0) or 0)
            self.real_data_partial_count = int(totals.get("partial", 0) or 0)
            self.real_data_demo_count = int(totals.get("demo", 0) or 0)
            self.real_data_without_loader_count = int(totals.get("without_loader", 0) or 0)
        except Exception as exc:  # noqa: BLE001
            self.sources_error_code, self.sources_error = public_error()


def _presentation_status(row: dict) -> str:
    status = str(row.get("status", "")).lower()
    connector = str(row.get("connector_status", "")).lower()
    population = int(row.get("population_records", 0) or 0)
    relationships = int(row.get("connector_relationships", 0) or 0)
    if status == "planned":
        return "CONNECTOR_PLANNED"
    if status == "prototype":
        return "CONNECTOR_PROTOTYPE"
    if status == "active" and (population or relationships or connector == "active"):
        return "DATA_AVAILABLE" if population or relationships else "CONNECTOR_ACTIVE"
    if status == "active":
        return "CATALOGUED"
    return "CATALOGUED"


def _connector_status_label(row: dict) -> str:
    status = _presentation_status(row)
    if status == "CONNECTOR_PLANNED":
        return "Conector planificado; no implica datos disponibles."
    if status == "CONNECTOR_PROTOTYPE":
        return "Conector prototipo; requiere validacion antes de uso publico pleno."
    if status in {"CONNECTOR_ACTIVE", "DATA_AVAILABLE"}:
        return "Conector con capacidad local representada en esta publicacion."
    return "Fuente catalogada; conector no confirmado."


def _data_status_label(row: dict) -> str:
    population = int(row.get("population_records", 0) or 0)
    relationships = int(row.get("connector_relationships", 0) or 0)
    if population or relationships:
        return f"Datos disponibles localmente: {population} registros base y {relationships} relaciones."
    return "Datos disponibles: no confirmados en esta publicacion."


def _coverage_status_label(row: dict) -> str:
    coverage = str(row.get("coverage", "")).strip() or "sin detalle"
    if int(row.get("population_records", 0) or 0) or int(row.get("connector_relationships", 0) or 0):
        return f"Cobertura informada: {coverage}. Puede ser parcial."
    return f"Cobertura informada: {coverage}. No equivale a cobertura suficiente."
