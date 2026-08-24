from __future__ import annotations

import reflex as rx

from datosenorden.application.real_expedient.public_facade import (
    get_citizen_expedient,
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
    citizen_expedient: bool = False
    citizen_question: str = ""
    citizen_type: str = ""
    citizen_facts: list[dict] = []
    citizen_bank_stages: list[dict] = []
    citizen_divergences: list[dict] = []
    citizen_unknowns: list[dict] = []
    citizen_limitations: list[dict] = []
    citizen_chronology: list[dict] = []
    citizen_actors: list[str] = []
    citizen_documents: list[dict] = []
    citizen_sources: list[str] = []
    citizen_questions: list[dict] = []
    citizen_topics: list[str] = []
    citizen_missing_knowledge: list[str] = []
    citizen_cutoff_substantive: str = ""
    citizen_cutoff_administrative: str = ""
    citizen_cutoff_explanation: str = ""

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
                citizen_payload = get_citizen_expedient(requested)
                if not citizen_payload:
                    self._clear_expedient()
                    self.load_status = "not_found"
                    return
                self._load_real_expedient(citizen_payload)
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
        """Map the citizen projection into UI-only, human-readable state."""
        if "facts" not in payload:
            LaboratoryState._load_legacy_real_expedient(self, payload)
            return
        self.citizen_expedient = True
        self.expedient_id = ""
        self.expedient_title = str(payload.get("title", ""))
        self.expedient_summary = str(payload.get("summary", ""))
        self.expedient_status = str(payload.get("status", ""))
        self.expedient_provenance_class = "REAL"
        self.citizen_question = str(payload.get("question", ""))
        self.citizen_type = str(payload.get("type", "Expediente"))
        sections = payload.get("sections", {})
        sections = sections if isinstance(sections, dict) else {}
        self.citizen_facts = _citizen_statement_rows(payload.get("facts", []))
        self.citizen_bank_stages = _citizen_statement_rows(sections.get("bank_secrecy", []))
        self.citizen_divergences = _citizen_statement_rows(sections.get("mixed_commission", []))
        self.citizen_unknowns = _citizen_statement_rows(payload.get("what_is_missing", []))
        self.citizen_limitations = _citizen_statement_rows(payload.get("what_we_cannot_conclude", []))
        labels = {"PROCEDURAL": "Procedimiento", "SUBSTANTIVE": "Cambio sustantivo", "ADMINISTRATIVE": "Actuación administrativa"}
        self.citizen_chronology = [
            {**row, "date": _citizen_date(str(row.get("date", ""))), "kind_label": labels.get(str(row.get("event_type", "")), "Actuación")}
            for row in payload.get("chronology", []) if isinstance(row, dict)
        ]
        self.citizen_actors = [str(item) for item in payload.get("actors", [])]
        self.citizen_documents = list(payload.get("documents", []))
        self.citizen_sources = [str(item) for item in payload.get("sources", [])]
        self.citizen_questions = list(payload.get("questions", []))
        self.citizen_topics = [str(item) for item in payload.get("topics", [])]
        self.citizen_missing_knowledge = [str(item) for item in payload.get("missing_knowledge", [])]
        cutoff = payload.get("knowledge_cutoff", {})
        cutoff = cutoff if isinstance(cutoff, dict) else {}
        self.citizen_cutoff_substantive = _citizen_date(str(cutoff.get("substantive_through", "")))
        self.citizen_cutoff_administrative = _citizen_date(str(cutoff.get("latest_administrative_record", "")))
        self.citizen_cutoff_explanation = str(cutoff.get("explanation", ""))

    def _load_legacy_real_expedient(self, payload: dict[str, object]) -> None:
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
        self.citizen_expedient = False
        self.citizen_question = ""
        self.citizen_type = ""
        self.citizen_facts = []
        self.citizen_bank_stages = []
        self.citizen_divergences = []
        self.citizen_unknowns = []
        self.citizen_limitations = []
        self.citizen_chronology = []
        self.citizen_actors = []
        self.citizen_documents = []
        self.citizen_sources = []
        self.citizen_questions = []
        self.citizen_topics = []
        self.citizen_missing_knowledge = []
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


def _citizen_date(value: str) -> str:
    """Present ISO dates as Spanish citizen-facing copy without changing data."""
    months = ("", "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre")
    try:
        year, month, day = (int(part) for part in value[:10].split("-"))
        return f"{day} de {months[month]} de {year}"
    except (ValueError, IndexError):
        return value


def _citizen_statement_rows(items: object) -> list[dict]:
    if not isinstance(items, list):
        return []
    rows: list[dict] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        evidence = item.get("evidence", [])
        support = []
        if isinstance(evidence, list):
            for source in evidence:
                if isinstance(source, dict) and source.get("title"):
                    support.append(" · ".join(str(source.get(key, "")) for key in ("title", "source", "document_date") if source.get(key)))
        rows.append({**item, "support_text": " | ".join(support)})
    return rows
