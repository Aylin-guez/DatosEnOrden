from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
import json
from tempfile import TemporaryDirectory
from typing import Any

from datosenorden.core.config import PROJECT_ROOT
from datosenorden.etl.chilecompra.client import ApiResponse
from datosenorden.etl.chilecompra.mappers import ChileCompraGraphMapper
from datosenorden.etl.chilecompra.normalizers import ChileCompraNormalizer
from datosenorden.etl.loaders.graph_loader import GraphLoader
from datosenorden.maintenance.contraloria_prototype import build_contraloria_sample_batch
from datosenorden.maintenance.diario_oficial_prototype import build_diario_oficial_sample_batch
from datosenorden.maintenance.dipres_prototype import build_dipres_sample_batch
from datosenorden.maintenance.lobby_prototype import build_lobby_sample_batch
from datosenorden.maintenance.registro_empresas_prototype import build_registro_empresas_sample_batch
from datosenorden.maintenance.transparencia_activa_prototype import build_transparencia_sample_batch


LOCAL_TEST_DATA = "LOCAL_TEST_DATA"
NOT_OFFICIAL_DATA = "NOT_OFFICIAL_DATA"
COMPLETE_DEMO_CASE_PATH = PROJECT_ROOT / "data" / "demo_cases" / "servicio_salud_arauco_complete.json"
COMPLETE_DEMO_CASE_SECTION_ORDER = (
    "dipres",
    "registro_empresas",
    "chilecompra",
    "diario_oficial",
    "transparencia",
    "lobby",
    "contraloria",
)


@dataclass(frozen=True)
class CompleteDemoCaseSummary:
    main_entity: str
    datasets: tuple[str, ...]
    created_entities: tuple[str, ...]
    reused_entities: tuple[str, ...]
    relationships_created: int
    evidence_count: int
    timeline_start: date | None
    timeline_end: date | None
    connected_suppliers: tuple[str, ...]
    connected_people: tuple[str, ...]
    connected_official_publications: tuple[str, ...]


@dataclass(frozen=True)
class CompleteDemoCaseLoadResult:
    summary: CompleteDemoCaseSummary
    source_records: int
    claims: int
    evidence: int
    entities: int
    relationships: int


def load_complete_demo_case_payload(input_path: Path | None = None) -> dict[str, Any]:
    path = input_path or COMPLETE_DEMO_CASE_PATH
    payload = json.loads(path.read_text(encoding="utf-8"))
    _validate_complete_demo_case_payload(payload)
    return payload


def build_complete_demo_case_summary(payload: dict[str, Any]) -> CompleteDemoCaseSummary:
    main_entity = str(payload["main_entity"]["name"]).strip()
    datasets = tuple(_dataset_label(section_name) for section_name in COMPLETE_DEMO_CASE_SECTION_ORDER if payload["datasets"].get(section_name))
    entity_occurrences: dict[str, set[str]] = defaultdict(set)
    connected_suppliers: set[str] = set()
    connected_people: set[str] = set()
    connected_publications: set[str] = set()
    timeline_dates: list[date] = []
    evidence_count = 0
    relationships_created = 0

    for section_name in COMPLETE_DEMO_CASE_SECTION_ORDER:
        section = payload["datasets"].get(section_name)
        if not section:
            continue
        records = section.get("records") or []
        for record in records:
            _register_main_entity(entity_occurrences, main_entity, section_name, record)
            if section_name == "dipres":
                _register_dipres_entities(entity_occurrences, section_name, record)
                evidence_count += 3
                relationships_created += 1
                budget_date = _iso_date_to_date(record.get("fiscal_year"), year_only=True)
                if budget_date is not None:
                    timeline_dates.append(budget_date)
                continue
            if section_name == "registro_empresas":
                company_name = str(record.get("company_name", "")).strip()
                representative = str(record.get("representative_name", "")).strip()
                owners = [str(owner.get("name", "")).strip() for owner in record.get("owners", []) if str(owner.get("name", "")).strip()]
                if company_name:
                    _register_entity(entity_occurrences, company_name, section_name)
                    connected_suppliers.add(company_name)
                if representative:
                    _register_entity(entity_occurrences, representative, section_name)
                    connected_people.add(representative)
                for owner_name in owners:
                    _register_entity(entity_occurrences, owner_name, section_name)
                    connected_people.add(owner_name)
                evidence_count += 4
                relationships_created += 2 + (2 * len(owners or ([representative] if representative else [])))
                timeline_dates.extend(
                    _date_values(
                        record.get("publication_date"),
                        record.get("company_constitution_date"),
                        record.get("company_modified_date"),
                    )
                )
                continue
            if section_name == "chilecompra":
                contract_label = str(record.get("Nombre") or f"Orden de compra {record.get('Codigo', '')}").strip()
                supplier_name = _chilecompra_supplier_name(record)
                if contract_label:
                    _register_entity(entity_occurrences, contract_label, section_name)
                if supplier_name:
                    _register_entity(entity_occurrences, supplier_name, section_name)
                    connected_suppliers.add(supplier_name)
                evidence_count += 1
                relationships_created += 2
                timeline_dates.extend(_date_values(record.get("FechaEnvio"), record.get("FechaCreacion"), record.get("FechaPublicacion")))
                continue
            if section_name == "diario_oficial":
                publication_label = str(record.get("publication_number") or record.get("publication_title") or record.get("external_id")).strip()
                person_name = str(record.get("person_name", "")).strip()
                office_name = str(record.get("office_name", "")).strip()
                if publication_label:
                    _register_entity(entity_occurrences, publication_label, section_name)
                    connected_publications.add(publication_label)
                if person_name:
                    _register_entity(entity_occurrences, person_name, section_name)
                    connected_people.add(person_name)
                if office_name:
                    _register_entity(entity_occurrences, office_name, section_name)
                evidence_count += 4
                relationships_created += 4
                timeline_dates.extend(_date_values(record.get("publication_date")))
                continue
            if section_name == "transparencia":
                role_label = str(record.get("role_title", "")).strip()
                person_name = str(record.get("person_name", "")).strip()
                if role_label:
                    _register_entity(entity_occurrences, role_label, section_name)
                if person_name:
                    _register_entity(entity_occurrences, person_name, section_name)
                    connected_people.add(person_name)
                evidence_count += 3
                relationships_created += 3
                timeline_dates.extend(_date_values(record.get("period")))
                continue
            if section_name == "lobby":
                meeting_label = _lobby_meeting_label(record)
                counterpart = str(record.get("counterparty_name", "")).strip()
                if meeting_label:
                    _register_entity(entity_occurrences, meeting_label, section_name)
                if counterpart:
                    _register_entity(entity_occurrences, counterpart, section_name)
                    connected_people.add(counterpart)
                evidence_count += 3
                relationships_created += 2
                timeline_dates.extend(_date_values(record.get("meeting_date")))
                continue
            if section_name == "contraloria":
                report_label = str(record.get("report_title") or record.get("report_number") or record.get("external_id")).strip()
                observation_label = str(record.get("observation_text", "")).strip()
                if report_label:
                    _register_entity(entity_occurrences, report_label, section_name)
                if observation_label:
                    _register_entity(entity_occurrences, observation_label, section_name)
                evidence_count += 2
                relationships_created += 2
                timeline_dates.extend(_date_values(record.get("report_date"), record.get("observation_date")))
                continue

    created_entities = tuple(
        sorted(label for label, sections in entity_occurrences.items() if len(sections) == 1)
    )
    reused_entities = tuple(
        sorted(label for label, sections in entity_occurrences.items() if len(sections) > 1)
    )
    timeline_start, timeline_end = _timeline_range(timeline_dates)
    return CompleteDemoCaseSummary(
        main_entity=main_entity,
        datasets=datasets,
        created_entities=created_entities,
        reused_entities=reused_entities,
        relationships_created=relationships_created,
        evidence_count=evidence_count,
        timeline_start=timeline_start,
        timeline_end=timeline_end,
        connected_suppliers=tuple(sorted(connected_suppliers)),
        connected_people=tuple(sorted(connected_people)),
        connected_official_publications=tuple(sorted(connected_publications)),
    )


def persist_complete_demo_case(session, payload: dict[str, Any] | None = None) -> CompleteDemoCaseLoadResult:  # noqa: ANN001
    case = payload or load_complete_demo_case_payload()
    batches = build_complete_demo_case_batches(session, case)
    for _section_name, batch in batches:
        GraphLoader(session).load(batch, dry_run=False)

    summary = build_complete_demo_case_summary(case)
    source_records = sum(len(batch.source_records) for _section_name, batch in batches)
    claims = sum(len(batch.claims) for _section_name, batch in batches)
    evidence = sum(len(batch.evidence) for _section_name, batch in batches)
    entities = len(
        {
            (entity.entity_type.value, entity.external_id)
            for _section_name, batch in batches
            for entity in batch.entities
        }
    )
    relationships = sum(len(batch.public_relationships) for _section_name, batch in batches)
    return CompleteDemoCaseLoadResult(
        summary=summary,
        source_records=source_records,
        claims=claims,
        evidence=evidence,
        entities=entities,
        relationships=relationships,
    )


def build_complete_demo_case_batches(session, payload: dict[str, Any]) -> tuple[tuple[str, Any], ...]:  # noqa: ANN001
    datasets = payload["datasets"]
    batches: list[tuple[str, Any]] = []
    batches.append(("dipres", build_dipres_sample_batch(session, datasets["dipres"])))
    batches.append(("registro_empresas", build_registro_empresas_sample_batch(session, datasets["registro_empresas"])))
    batches.append(("chilecompra", _build_chilecompra_demo_batch(session, datasets["chilecompra"])))
    batches.append(("diario_oficial", build_diario_oficial_sample_batch(session, datasets["diario_oficial"])))
    batches.append(("transparencia", build_transparencia_sample_batch(session, datasets["transparencia"])))
    batches.append(("lobby", build_lobby_sample_batch(session, datasets["lobby"])))
    batches.append(("contraloria", build_contraloria_sample_batch(session, datasets["contraloria"])))
    return tuple(batches)


def render_complete_demo_case_summary_text(summary: CompleteDemoCaseSummary) -> str:
    lines = [
        "complete_demo_case_summary:",
        f"  main_entity={summary.main_entity}",
        "  datasets:",
    ]
    lines.extend(f"    - {dataset}" for dataset in summary.datasets)
    lines.extend(
        [
            "  entities:",
            f"    created={len(summary.created_entities)}",
            f"    reused={len(summary.reused_entities)}",
            "  relationships_created:",
            f"    {summary.relationships_created}",
            "  evidence_count:",
            f"    {summary.evidence_count}",
            "  timeline_range:",
            f"    {summary.timeline_start.isoformat() if summary.timeline_start else 'None'} -> {summary.timeline_end.isoformat() if summary.timeline_end else 'None'}",
            "  connected_suppliers:",
        ]
    )
    lines.extend(f"    - {item}" for item in summary.connected_suppliers or ("None",))
    lines.append("  connected_people:")
    lines.extend(f"    - {item}" for item in summary.connected_people or ("None",))
    lines.append("  connected_official_publications:")
    lines.extend(f"    - {item}" for item in summary.connected_official_publications or ("None",))
    lines.append("  created_entities:")
    lines.extend(f"    - {item}" for item in summary.created_entities or ("None",))
    lines.append("  reused_entities:")
    lines.extend(f"    - {item}" for item in summary.reused_entities or ("None",))
    return "\n".join(lines)


def render_complete_demo_case_load_text(result: CompleteDemoCaseLoadResult) -> str:
    lines = [
        "complete_demo_case_loaded:",
        f"  main_entity={result.summary.main_entity}",
        f"  datasets={len(result.summary.datasets)}",
        f"  source_records={result.source_records}",
        f"  claims={result.claims}",
        f"  evidence={result.evidence}",
        f"  entities={result.entities}",
        f"  relationships={result.relationships}",
    ]
    lines.extend(render_complete_demo_case_summary_text(result.summary).splitlines())
    return "\n".join(lines)


def _build_chilecompra_demo_batch(session, section: dict[str, Any]):  # noqa: ANN001
    _ = session
    records = section.get("records") or []
    api_payload = {
        "Version": section.get("api_version", "local-demo"),
        "FechaCreacion": section.get("created_at", "2026-05-01"),
        "Listado": records,
    }
    response = ApiResponse(
        url=str(section.get("source_url", "local://demo-case/chilecompra")),
        params={str(key): str(value) for key, value in (section.get("request_params") or {}).items()},
        payload=api_payload,
    )
    normalized = ChileCompraNormalizer().normalize(response)
    return ChileCompraGraphMapper().map_purchase_orders(normalized)


def _validate_complete_demo_case_payload(payload: dict[str, Any]) -> None:
    if payload.get("classification") != LOCAL_TEST_DATA:
        raise ValueError("Complete demo case must be marked LOCAL_TEST_DATA")
    if payload.get("official_status") != NOT_OFFICIAL_DATA:
        raise ValueError("Complete demo case must be marked NOT_OFFICIAL_DATA")
    datasets = payload.get("datasets")
    if not isinstance(datasets, dict):
        raise ValueError("Complete demo case must include a datasets object")
    missing = [section for section in COMPLETE_DEMO_CASE_SECTION_ORDER if section not in datasets]
    if missing:
        raise ValueError(f"Complete demo case is missing sections: {', '.join(missing)}")


def _register_main_entity(occurrences: dict[str, set[str]], main_entity: str, section_name: str, record: dict[str, Any]) -> None:
    if section_name == "dipres":
        service_name = str(record.get("service_name", "")).strip()
        if service_name:
            _register_entity(occurrences, service_name, section_name)
        return
    if section_name == "chilecompra":
        buyer_name = _chilecompra_buyer_name(record)
        if buyer_name:
            _register_entity(occurrences, buyer_name, section_name)
        return
    if section_name in {"diario_oficial", "transparencia", "lobby", "contraloria"}:
        organization_name = str(record.get("organization_name", "")).strip()
        if organization_name:
            _register_entity(occurrences, organization_name, section_name)
        return
    if section_name == "registro_empresas":
        return
    _register_entity(occurrences, main_entity, section_name)


def _register_dipres_entities(occurrences: dict[str, set[str]], section_name: str, record: dict[str, Any]) -> None:
    service_name = str(record.get("service_name", "")).strip()
    fiscal_year = str(record.get("fiscal_year", "")).strip()
    program_name = str(record.get("program_name") or record.get("program") or record.get("description") or "").strip()
    budget_label = f"DIPRES budget {fiscal_year} - {service_name}"
    if program_name:
        budget_label = f"{budget_label} / {program_name}"
    _register_entity(occurrences, budget_label, section_name)


def _register_entity(occurrences: dict[str, set[str]], label: str, section_name: str) -> None:
    cleaned = label.strip()
    if cleaned:
        occurrences[cleaned].add(section_name)


def _dataset_label(section_name: str) -> str:
    labels = {
        "dipres": "DIPRES",
        "registro_empresas": "Registro Empresas",
        "chilecompra": "ChileCompra",
        "diario_oficial": "Diario Oficial",
        "transparencia": "Transparencia Activa",
        "lobby": "Lobby",
        "contraloria": "Contraloria",
    }
    return labels.get(section_name, section_name)


def _chilecompra_buyer_name(record: dict[str, Any]) -> str:
    buyer = record.get("Comprador") or record.get("CompradorOrganismo") or record.get("DatosComprador") or record.get("OrganismoComprador")
    if isinstance(buyer, dict):
        for key in ("NombreOrganismo", "NombreUnidadCompra", "NombreComprador", "RazonSocial"):
            value = str(buyer.get(key, "")).strip()
            if value:
                return value
    for key in ("NombreOrganismo", "NombreUnidadCompra", "NombreComprador", "RazonSocial"):
        value = str(record.get(key, "")).strip()
        if value:
            return value
    return ""


def _chilecompra_supplier_name(record: dict[str, Any]) -> str:
    supplier = record.get("Adjudicatario") or record.get("DatosProveedor") or record.get("Empresa") or record.get("Proveedor") or record.get("ProveedorAdjudicado")
    if isinstance(supplier, dict):
        for key in ("NombreEmpresa", "NombreProveedor", "RazonSocial"):
            value = str(supplier.get(key, "")).strip()
            if value:
                return value
    for key in ("NombreEmpresa", "NombreProveedor", "RazonSocial"):
        value = str(record.get(key, "")).strip()
        if value:
            return value
    return ""


def _lobby_meeting_label(record: dict[str, Any]) -> str:
    meeting_date = str(record.get("meeting_date", "")).strip()
    organization_name = str(record.get("organization_name", "")).strip()
    counterparty_name = str(record.get("counterparty_name", "")).strip()
    return f"Lobby meeting {meeting_date} - {organization_name} / {counterparty_name}".strip()


def _date_values(*values: Any) -> list[date]:
    parsed: list[date] = []
    for value in values:
        parsed_date = _value_to_date(value)
        if parsed_date is not None:
            parsed.append(parsed_date)
    return parsed


def _value_to_date(value: Any) -> date | None:
    if value is None:
        return None
    if isinstance(value, date):
        return value
    if isinstance(value, int):
        return date(int(value), 1, 1)
    text = str(value).strip()
    if not text:
        return None
    if len(text) == 7 and text[4] == "-":
        text = f"{text}-01"
    try:
        return date.fromisoformat(text)
    except ValueError:
        return None


def _iso_date_to_date(value: Any, *, year_only: bool = False) -> date | None:
    if year_only:
        try:
            year = int(value)
        except (TypeError, ValueError):
            return None
        return date(year, 1, 1)
    return _value_to_date(value)


def _timeline_range(values: list[date]) -> tuple[date | None, date | None]:
    if not values:
        return None, None
    return min(values), max(values)
