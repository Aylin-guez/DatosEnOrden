from __future__ import annotations

import reflex as rx

from datosenorden.application.real_expedient.public_facade import (
    get_public_expedient,
    list_public_expedient_catalog,
)
from datosenorden.application.public_deployment.sanitization import public_error
from reflex_app.helpers.routing import _router_query_value


REQUIRED_SECTIONS = ("summary", "problem", "evidence", "claims", "hypotheses", "indicators", "sources", "relationships")


class LaboratoryState(rx.State):
    catalog_rows: list[dict] = []
    requested_expedient_id: str = ""
    expedient_id: str = ""
    expedient_title: str = ""
    expedient_summary: str = ""
    expedient_status: str = ""
    expedient_provenance_class: str = ""
    expedient_scope: str = ""
    expedient_territory: str = ""
    expedient_period: str = ""
    expedient_updated_at: str = ""
    problem_title: str = ""
    problem_description: str = ""
    problem_scope: str = ""
    problem_affected_population: str = ""
    problem_territory: str = ""
    problem_period: str = ""
    problem_status: str = ""
    sections: list[dict] = []
    hypotheses: list[dict] = []
    evidence_items: list[dict] = []
    claims: list[dict] = []
    indicators: list[dict] = []
    sources: list[dict] = []
    relationships: list[dict] = []
    open_questions_summary: str = ""
    participation_status: str = "LOCKED"
    active_section: str = "summary"
    visited_sections: list[str] = []
    reading_progress: int = 0
    reading_complete: bool = False
    load_status: str = "idle"
    error_message: str = ""
    public_error_code: str = ""

    def load_catalog(self) -> None:
        self.load_status = "loading"
        self.error_message = ""
        try:
            self.catalog_rows = list_public_expedient_catalog()
            self.load_status = "loaded" if self.catalog_rows else "empty"
        except Exception:  # noqa: BLE001
            self.catalog_rows = []
            self.load_status = "error"
            self.public_error_code, self.error_message = public_error()

    def load_expedient(self) -> None:
        self.load_status = "loading"
        self.error_message = ""
        requested = _router_query_value(self.router, "id") or "EXP-001"
        self.requested_expedient_id = requested
        try:
            payload = get_public_expedient(requested)
            if not payload:
                self._clear_expedient()
                self.load_status = "not_found"
                return
            if payload.get("provenance_class") == "REAL":
                self._load_real_expedient(payload)
                self.load_status = "loaded"
                return
            self.expedient_id = str(payload["id"])
            self.expedient_title = str(payload["title"])
            self.expedient_summary = str(payload["summary"])
            self.expedient_status = str(payload["status"])
            self.expedient_scope = str(payload["scope"])
            self.expedient_territory = str(payload["territory"])
            self.expedient_period = str(payload["period"])
            self.expedient_updated_at = str(payload["updated_at"])
            problem = payload["problem"]
            self.problem_title = str(problem["title"])
            self.problem_description = str(problem["description"])
            self.problem_scope = str(problem["scope"])
            self.problem_affected_population = str(problem["affected_population"])
            self.problem_territory = str(problem["territory"])
            self.problem_period = str(problem["period"])
            self.problem_status = str(problem["status"])
            self.sections = payload["sections"]
            self.hypotheses = payload["hypotheses"]
            self.evidence_items = payload["evidence_items"]
            self.claims = payload["claims"]
            self.indicators = payload["indicators"]
            self.sources = payload["sources"]
            self.relationships = payload["relationships"]
            self.open_questions_summary = str(payload["open_questions_summary"])
            self.participation_status = str(payload["participation_status"])
            self.active_section = "summary"
            self.visited_sections = ["summary"]
            self._recalculate_progress()
            self.load_status = "loaded"
        except Exception:  # noqa: BLE001
            self._clear_expedient()
            self.load_status = "error"
            self.public_error_code, self.error_message = public_error()

    def set_active_section(self, section_id: str) -> None:
        section = str(section_id or "").strip()
        allowed = {row["id"] for row in self.sections}
        if section not in allowed:
            return
        self.active_section = section
        if section in REQUIRED_SECTIONS and section not in self.visited_sections:
            self.visited_sections = [*self.visited_sections, section]
        self._recalculate_progress()

    def _recalculate_progress(self) -> None:
        visited = set(self.visited_sections)
        completed = len(visited.intersection(REQUIRED_SECTIONS))
        self.reading_progress = int((completed / len(REQUIRED_SECTIONS)) * 100)
        self.reading_complete = completed == len(REQUIRED_SECTIONS)

    def _load_real_expedient(self, payload: dict[str, object]) -> None:
        references = payload.get("references", {})
        statements = payload.get("statements", [])
        self.expedient_id = str(payload["id"])
        self.expedient_title = str(payload["title"])
        self.expedient_summary = str(payload["summary"])
        self.expedient_status = str(payload["status"])
        self.expedient_provenance_class = "REAL"
        self.expedient_scope = "Referencias públicas verificadas"
        self.expedient_territory = "Chile"
        self.expedient_period = str(payload.get("updated_at", ""))[:10]
        self.expedient_updated_at = str(payload.get("updated_at", ""))
        self.problem_title = str(payload["question"])
        self.problem_description = str(payload["summary"])
        self.problem_scope = "Lectura de una orden de compra ya registrada."
        self.problem_affected_population = "No determinada por este expediente."
        self.problem_territory = "Chile"
        self.problem_period = self.expedient_period
        self.problem_status = "DOCUMENTED"
        self.sections = [
            {"id": section, "title": title, "summary": "Contenido disponible según referencias verificadas.", "status": "READY"}
            for section, title in (
                ("summary", "Resumen"),
                ("problem", "Pregunta pública"),
                ("evidence", "Evidencia"),
                ("claims", "Afirmaciones"),
                ("hypotheses", "Preguntas abiertas"),
                ("indicators", "Indicadores"),
                ("sources", "Fuentes"),
                ("relationships", "Relaciones"),
                ("participation", "Participación"),
            )
        ]
        evidence_ids = _reference_ids(references, "evidences")
        source_ids = _reference_ids(references, "sources")
        relationship_ids = _reference_ids(references, "relationships")
        self.evidence_items = [
            {
                "id": value,
                "title": "Evidencia oficial referenciada",
                "type": "OFFICIAL_REFERENCE",
                "source": "Fuente pública registrada",
                "fragment_reference": value,
                "status": "VERIFIED",
                "limitations": "La ficha oficial se consulta mediante la navegación de referencias.",
            }
            for value in evidence_ids
        ]
        self.claims = [
            {
                "id": str(row.get("id", "")),
                "text": str(row.get("text", "")),
                "type": str(row.get("epistemic_class", "UNKNOWN")),
                "status": "SUPPORTED",
                "certainty": str(row.get("epistemic_class", "UNKNOWN")),
            }
            for row in statements
            if isinstance(row, dict)
        ]
        self.hypotheses = []
        self.indicators = []
        self.sources = [
            {
                "id": value,
                "name": "Fuente pública referenciada",
                "type": "PUBLIC_SOURCE",
                "issuer": "Registrado en el expediente",
                "status": "VERIFIED",
                "warning": "La fuente conserva su identificación pública sin copiar payloads.",
            }
            for value in source_ids
        ]
        self.relationships = [
            {
                "id": value,
                "source_entity": "Entidad referenciada",
                "relation_type": "RELACIÓN DOCUMENTADA",
                "target_entity": "Entidad referenciada",
                "status": "VERIFIED",
                "context": "La relación se resuelve desde la referencia pública del expediente.",
            }
            for value in relationship_ids
        ]
        self.open_questions_summary = (
            "Este expediente no determina causalidad, regularidad ni responsabilidad; "
            "solo organiza las referencias seleccionadas."
        )
        self.participation_status = "LOCKED"
        self.active_section = "summary"
        self.visited_sections = ["summary"]
        self._recalculate_progress()

    def _clear_expedient(self) -> None:
        self.expedient_id = ""
        self.expedient_provenance_class = ""
        self.expedient_title = ""
        self.expedient_summary = ""
        self.sections = []
        self.hypotheses = []
        self.evidence_items = []
        self.claims = []
        self.indicators = []
        self.sources = []
        self.relationships = []
        self.visited_sections = []
        self.reading_progress = 0
        self.reading_complete = False


def _reference_ids(references: object, key: str) -> list[str]:
    if not isinstance(references, dict):
        return []
    values = references.get(key, [])
    return [str(value) for value in values] if isinstance(values, list) else []
