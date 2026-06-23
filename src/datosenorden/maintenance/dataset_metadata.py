from __future__ import annotations

from dataclasses import dataclass

from datosenorden.datasets import dataset_definition_for_name
from datosenorden.datasets import dataset_label_for_name
from datosenorden.datasets import dataset_catalog


@dataclass(frozen=True)
class DatasetMetadata:
    slug: str
    name: str
    description: str
    contributes: tuple[str, ...]
    category: str
    citizen_summary: str
    status: str
    coverage: str
    concepts: tuple[str, ...]
    relationships: tuple[str, ...]
    connects_with: tuple[str, ...]
    entities: tuple[str, ...]


_DATASET_METADATA: dict[str, DatasetMetadata] = {
    "ChileCompra": DatasetMetadata(
        slug="chilecompra",
        name="ChileCompra",
        description="Public procurement records and related evidence.",
        contributes=(
            "Procurement records",
            "Suppliers",
            "Purchase orders",
        ),
        category="procurement",
        citizen_summary="Shows public purchasing activity and supplier relationships.",
        status="active",
        coverage="covered",
        concepts=("Organismo", "Empresa", "Contrato"),
        relationships=("ISSUES_PURCHASE_ORDER", "RECEIVES_CONTRACT", "PUBLISHED_TENDER", "AWARDS_CONTRACT"),
        connects_with=("DIPRES", "Lobby", "Contraloria", "Municipalidades"),
        entities=("Organismo", "Empresa", "Contrato"),
    ),
    "DIPRES": DatasetMetadata(
        slug="dipres",
        name="DIPRES",
        description="Budget allocation and execution records.",
        contributes=(
            "Budget allocation",
            "Budget execution",
            "Program spending",
        ),
        category="budget",
        citizen_summary="Shows budget assignments and how public funds are executed.",
        status="prototype",
        coverage="partial",
        concepts=("Presupuesto", "Organismo"),
        relationships=("BUDGET_ALLOCATED_TO", "BUDGET_EXECUTED_BY"),
        connects_with=("ChileCompra", "Municipalidades"),
        entities=("Presupuesto", "Organismo"),
    ),
    "Lobby": DatasetMetadata(
        slug="lobby",
        name="Lobby",
        description="Registered lobby meetings and related evidence.",
        contributes=(
            "Meetings",
            "Public officials",
            "Meeting subjects",
        ),
        category="lobby",
        citizen_summary="Shows registered meetings and the public counterparts involved.",
        status="prototype",
        coverage="partial",
        concepts=("Reunion", "Persona", "Organismo", "Empresa"),
        relationships=("ORGANIZATION_HELD_LOBBY_MEETING", "COUNTERPARTY_PARTICIPATED_IN_LOBBY"),
        connects_with=("Transparencia Activa", "SERVEL", "ChileCompra"),
        entities=("Reunion", "Persona", "Organismo", "Empresa"),
    ),
    "Transparencia Activa": DatasetMetadata(
        slug="transparencia-activa",
        name="Transparencia Activa",
        description="Administrative transparency records published by organizations.",
        contributes=(
            "Personnel",
            "Public information",
            "Administrative records",
        ),
        category="transparency",
        citizen_summary="Shows published administrative information and personnel records.",
        status="prototype",
        coverage="partial",
        concepts=("Persona", "Cargo Publico", "Organismo"),
        relationships=("ORGANIZATION_HAS_PUBLIC_ROLE", "ROLE_BELONGS_TO_ORGANIZATION"),
        connects_with=("Lobby", "SERVEL", "Declaraciones de intereses"),
        entities=("Persona", "Cargo Publico", "Organismo"),
    ),
    "SERVEL": DatasetMetadata(
        slug="servel",
        name="SERVEL",
        description="Local sample of elected authority records.",
        contributes=(
            "Public authorities",
            "Office records",
            "Territories",
            "Electoral periods",
        ),
        category="authorities",
        citizen_summary="Shows elected authority records, offices, territories, and periods.",
        status="prototype",
        coverage="partial",
        concepts=("Persona", "Cargo Publico", "Organismo"),
        relationships=("PERSON_HELD_ELECTED_OFFICE", "OFFICE_BELONGS_TO_TERRITORY"),
        connects_with=("Transparencia Activa", "Lobby", "Declaraciones de intereses"),
        entities=("Persona", "Cargo Publico", "Organismo"),
    ),
    "Diario Oficial": DatasetMetadata(
        slug="diario-oficial",
        name="Diario Oficial",
        description="Local prototype of official publication records.",
        contributes=(
            "Official publication records",
            "Appointments and resignations",
            "Administrative acts",
        ),
        category="official_publications",
        citizen_summary="Shows official publication records for appointments, resignations, decrees, and administrative acts from the local prototype data.",
        status="prototype",
        coverage="partial",
        concepts=("Persona", "Organismo", "Cargo Publico", "Decreto", "Nombramiento", "Renuncia"),
        relationships=(
            "PERSON_APPOINTED_TO_PUBLIC_OFFICE",
            "PERSON_RESIGNED_FROM_PUBLIC_OFFICE",
            "DECREE_APPLIES_TO_ORGANIZATION",
            "OFFICIAL_PUBLICATION_REFERENCES_ENTITY",
            "PUBLIC_OFFICE_BELONGS_TO_ORGANIZATION",
        ),
        connects_with=("Transparencia Activa", "SERVEL", "Contraloria", "Municipalidades"),
        entities=("Persona", "Organismo", "Cargo Publico"),
    ),
    "Registro Empresas": DatasetMetadata(
        slug="registro_empresas",
        name="Registro Empresas",
        description="Local prototype of company registry records.",
        contributes=(
            "Company records",
            "Representatives",
            "Owners",
            "Registration and modification events",
        ),
        category="company_registry",
        citizen_summary="Shows company registry records, representatives, owners, and registration or modification events from the local prototype data.",
        status="prototype",
        coverage="partial",
        concepts=("Empresa", "Persona", "Representante", "Socio"),
        relationships=(
            "PERSON_REPRESENTS_COMPANY",
            "PERSON_OWNS_COMPANY",
            "COMPANY_REGISTERED_ON",
            "COMPANY_MODIFIED_ON",
        ),
        connects_with=("ChileCompra", "Diario Oficial", "Lobby"),
        entities=("Empresa", "Persona"),
    ),
    "Contraloria": DatasetMetadata(
        slug="contraloria",
        name="Contraloria",
        description="Control reports and observations from the local prototype data.",
        contributes=(
            "Audit records",
            "Observations",
            "Control follow-up",
        ),
        category="audits",
        citizen_summary="Shows audit-style reports and observations from the local prototype data.",
        status="prototype",
        coverage="partial",
        concepts=("Organismo", "Empresa", "Informe de control"),
        relationships=("CONTROL_REPORT_INVOLVES_ENTITY", "OBSERVATION_TARGETS_ENTITY"),
        connects_with=("ChileCompra", "Municipalidades", "Sanciones y procedimientos"),
        entities=("Organismo", "Empresa", "Informe de control"),
    ),
    "Municipalidades": DatasetMetadata(
        slug="municipalidades",
        name="Municipalidades",
        description="Municipal project and spending records from the local prototype data.",
        contributes=(
            "Municipal records",
            "Projects",
            "Spending items",
        ),
        category="municipal",
        citizen_summary="Shows municipal records, projects, and spending items from the local prototype data.",
        status="prototype",
        coverage="partial",
        concepts=("Organismo", "Presupuesto", "Proyecto Publico"),
        relationships=("MUNICIPALITY_RUNS_PROJECT", "PROJECT_HAS_SPENDING_ITEM"),
        connects_with=("DIPRES", "ChileCompra", "Contraloria"),
        entities=("Organismo", "Presupuesto", "Proyecto Publico"),
    ),
}


def dataset_metadata_for_name(name: str) -> DatasetMetadata | None:
    definition = dataset_definition_for_name(name)
    if definition is None:
        label = dataset_label_for_name(name)
        return _DATASET_METADATA.get(label)
    metadata = _DATASET_METADATA.get(definition.dataset_name)
    if metadata is not None:
        return metadata
    label = dataset_label_for_name(name)
    return _DATASET_METADATA.get(label)


def dataset_metadata_catalog() -> tuple[DatasetMetadata, ...]:
    rows: list[DatasetMetadata] = []
    for definition in dataset_catalog():
        metadata = _DATASET_METADATA.get(definition.dataset_name)
        if metadata is not None:
            rows.append(metadata)
    return tuple(rows)


def source_contribution_bullets(name: str) -> tuple[str, ...]:
    metadata = dataset_metadata_for_name(name)
    if metadata is None:
        return ("Public records associated with this entity.",)
    return tuple(f"- {item}" for item in metadata.contributes)


def dataset_category(name: str) -> str:
    metadata = dataset_metadata_for_name(name)
    return metadata.category if metadata is not None else "general"


def dataset_citizen_summary(name: str) -> str:
    metadata = dataset_metadata_for_name(name)
    if metadata is not None:
        return metadata.citizen_summary
    return "Shows public records associated with this entity."

