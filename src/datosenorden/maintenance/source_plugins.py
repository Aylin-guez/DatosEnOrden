from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class SourceStatus(StrEnum):
    ACTIVE = "active"
    PROTOTYPE = "prototype"
    PLANNED = "planned"


@dataclass(frozen=True)
class SourceCoverage:
    level: str
    description: str


@dataclass(frozen=True)
class SourceConcept:
    name: str
    description: str
    entity_types: tuple[str, ...] = ()


@dataclass(frozen=True)
class SourceRelationshipDefinition:
    predicate: str
    subject: str
    object: str
    description: str


@dataclass(frozen=True)
class SourceCommand:
    kind: str
    command: str
    description: str


@dataclass(frozen=True)
class PublicSourcePlugin:
    id: str
    display_name: str
    status: SourceStatus
    description: str
    category: str
    coverage: SourceCoverage
    concepts: tuple[SourceConcept, ...]
    relationships: tuple[SourceRelationshipDefinition, ...]
    compatible_source_ids: tuple[str, ...]
    commands: tuple[SourceCommand, ...]
    evidence_types: tuple[str, ...]
    timeline_contribution: str
    search_hints: tuple[str, ...]
    discovery_hints: tuple[str, ...]
    technical_metadata: dict[str, str]
    aliases: tuple[str, ...] = ()


def get_source_plugins() -> tuple[PublicSourcePlugin, ...]:
    return _SOURCE_PLUGINS


def get_source_plugin(source_id: str) -> PublicSourcePlugin | None:
    cleaned = source_id.strip().lower().replace("-", "_")
    for plugin in _SOURCE_PLUGINS:
        identifiers = {plugin.id.lower(), plugin.display_name.lower(), *(alias.lower() for alias in plugin.aliases)}
        if cleaned in {item.replace("-", "_").replace(" ", "_") for item in identifiers}:
            return plugin
    return None


def list_active_sources() -> tuple[PublicSourcePlugin, ...]:
    return tuple(plugin for plugin in _SOURCE_PLUGINS if plugin.status == SourceStatus.ACTIVE)


def list_prototype_sources() -> tuple[PublicSourcePlugin, ...]:
    return tuple(plugin for plugin in _SOURCE_PLUGINS if plugin.status == SourceStatus.PROTOTYPE)


def list_planned_sources() -> tuple[PublicSourcePlugin, ...]:
    return tuple(plugin for plugin in _SOURCE_PLUGINS if plugin.status == SourceStatus.PLANNED)


def get_sources_by_concept(concept: str) -> tuple[PublicSourcePlugin, ...]:
    normalized = concept.strip().lower()
    return tuple(
        plugin
        for plugin in _SOURCE_PLUGINS
        if any(item.name.lower() == normalized for item in plugin.concepts)
    )


def get_sources_connected_to(source_id: str) -> tuple[PublicSourcePlugin, ...]:
    plugin = get_source_plugin(source_id)
    if plugin is None:
        return ()
    return tuple(
        connected
        for connected_id in plugin.compatible_source_ids
        if (connected := get_source_plugin(connected_id)) is not None
    )


def get_source_commands(source_id: str) -> tuple[SourceCommand, ...]:
    plugin = get_source_plugin(source_id)
    return plugin.commands if plugin is not None else ()


def plugin_status_value(plugin: PublicSourcePlugin) -> str:
    return str(plugin.status.value)


def plugin_concept_names(plugin: PublicSourcePlugin) -> tuple[str, ...]:
    return tuple(concept.name for concept in plugin.concepts)


def plugin_relationship_predicates(plugin: PublicSourcePlugin) -> tuple[str, ...]:
    return tuple(relationship.predicate for relationship in plugin.relationships)


def _concept(name: str, description: str, *entity_types: str) -> SourceConcept:
    return SourceConcept(name=name, description=description, entity_types=tuple(entity_types))


def _relationship(predicate: str, subject: str, object_: str, description: str) -> SourceRelationshipDefinition:
    return SourceRelationshipDefinition(predicate=predicate, subject=subject, object=object_, description=description)


def _command(kind: str, command: str, description: str) -> SourceCommand:
    return SourceCommand(kind=kind, command=command, description=description)


def _coverage(level: str, description: str) -> SourceCoverage:
    return SourceCoverage(level=level, description=description)


_SOURCE_PLUGINS: tuple[PublicSourcePlugin, ...] = (
    PublicSourcePlugin(
        id="chilecompra",
        display_name="ChileCompra",
        status=SourceStatus.ACTIVE,
        description="Public procurement records and related evidence.",
        category="procurement",
        coverage=_coverage("covered", "Local loader and demo data are available."),
        concepts=(
            _concept("Organismo", "Public buyer organization.", "PUBLIC_ORGANIZATION"),
            _concept("Empresa", "Supplier company.", "COMPANY"),
            _concept("Contrato", "Purchase order or contract.", "CONTRACT"),
        ),
        relationships=(
            _relationship("ISSUES_PURCHASE_ORDER", "Organismo", "Contrato", "Organization issues a purchase order."),
            _relationship("RECEIVES_CONTRACT", "Empresa", "Contrato", "Supplier receives a public contract."),
            _relationship("PUBLISHED_TENDER", "Organismo", "Contrato", "Organization publishes a tender."),
            _relationship("AWARDS_CONTRACT", "Organismo", "Contrato", "Organization awards a contract."),
        ),
        compatible_source_ids=("dipres", "lobby", "contraloria", "municipalidades", "registro_empresas"),
        commands=(
            _command("loader", "python scripts/load_sample_purchase_orders.py", "Load local procurement sample records."),
            _command("summary", "python scripts/dataset_summary.py", "Show dataset summary counts."),
        ),
        evidence_types=("purchase_order_url", "source_record", "local_sample_payload"),
        timeline_contribution="Purchase order and contract dates.",
        search_hints=("proveedor", "compra publica", "orden de compra", "contrato"),
        discovery_hints=("who_sells_to_this_body", "which_suppliers_appear", "procurement"),
        technical_metadata={"dataset_names": "chilecompra-purchase-orders", "module": "etl.chilecompra"},
        aliases=("ChileCompra", "Mercado Publico"),
    ),
    PublicSourcePlugin(
        id="dipres",
        display_name="DIPRES",
        status=SourceStatus.PROTOTYPE,
        description="Budget allocation and execution records.",
        category="budget",
        coverage=_coverage("partial", "Local prototype and complete demo records are available."),
        concepts=(
            _concept("Presupuesto", "Budget allocation or execution record.", "BUDGET"),
            _concept("Organismo", "Public organization linked to budget records.", "PUBLIC_ORGANIZATION"),
        ),
        relationships=(
            _relationship("BUDGET_ALLOCATED_TO", "Presupuesto", "Organismo", "Budget assigned to an organization."),
            _relationship("BUDGET_EXECUTED_BY", "Presupuesto", "Organismo", "Budget executed by an organization."),
        ),
        compatible_source_ids=("chilecompra", "municipalidades"),
        commands=(
            _command("loader", "python scripts/load_dipres_sample.py", "Load local DIPRES sample."),
            _command("summary", "python scripts/budget_summary.py", "Show budget summary."),
        ),
        evidence_types=("budget_record", "local_sample_payload"),
        timeline_contribution="Fiscal year and budget period events.",
        search_hints=("presupuesto", "dipres", "gasto publico"),
        discovery_hints=("budgets", "procurement"),
        technical_metadata={"dataset_names": "dipres-budget-sample", "module": "maintenance.dipres_prototype"},
        aliases=("DIPRES", "dipres-prototype"),
    ),
    PublicSourcePlugin(
        id="lobby",
        display_name="Lobby",
        status=SourceStatus.PROTOTYPE,
        description="Registered lobby meetings and related evidence.",
        category="lobby",
        coverage=_coverage("partial", "Local prototype and demo records are available."),
        concepts=(
            _concept("Reunion", "Registered meeting.", "LOBBY_MEETING"),
            _concept("Persona", "Meeting participant.", "PERSON"),
            _concept("Organismo", "Public organization linked to a meeting.", "PUBLIC_ORGANIZATION"),
            _concept("Empresa", "Company participant.", "COMPANY"),
        ),
        relationships=(
            _relationship("ORGANIZATION_HELD_LOBBY_MEETING", "Organismo", "Reunion", "Organization has a registered meeting."),
            _relationship("COUNTERPARTY_PARTICIPATED_IN_LOBBY", "Persona/Empresa", "Reunion", "Counterparty participates in a meeting."),
        ),
        compatible_source_ids=("transparencia_activa", "servel", "chilecompra"),
        commands=(
            _command("loader", "python scripts/load_lobby_sample.py", "Load local Lobby sample."),
            _command("summary", "python scripts/lobby_summary.py", "Show Lobby summary."),
        ),
        evidence_types=("meeting_record", "source_url", "local_sample_payload"),
        timeline_contribution="Meeting dates.",
        search_hints=("lobby", "reunion", "contraparte"),
        discovery_hints=("which_meetings_were_recorded", "meetings"),
        technical_metadata={"dataset_names": "lobby-meeting-sample", "module": "maintenance.lobby_prototype"},
        aliases=("Lobby", "lobby-meeting-sample"),
    ),
    PublicSourcePlugin(
        id="transparencia_activa",
        display_name="Transparencia Activa",
        status=SourceStatus.PROTOTYPE,
        description="Administrative transparency records published by organizations.",
        category="transparency",
        coverage=_coverage("partial", "Local prototype records are available."),
        concepts=(
            _concept("Persona", "Person in an administrative role.", "PERSON"),
            _concept("Cargo Publico", "Public role or office.", "ROLE"),
            _concept("Organismo", "Organization publishing role information.", "PUBLIC_ORGANIZATION"),
        ),
        relationships=(
            _relationship("ORGANIZATION_HAS_PUBLIC_ROLE", "Organismo", "Cargo Publico", "Organization has a public role."),
            _relationship("ROLE_BELONGS_TO_ORGANIZATION", "Cargo Publico", "Organismo", "Role belongs to organization."),
            _relationship("PERSON_HOLDS_PUBLIC_ROLE", "Persona", "Cargo Publico", "Person holds a public role."),
        ),
        compatible_source_ids=("lobby", "servel", "declaraciones_intereses", "diario_oficial"),
        commands=(
            _command("loader", "python scripts/load_transparencia_sample.py", "Load local Transparencia Activa sample."),
            _command("summary", "python scripts/transparencia_summary.py", "Show transparency summary."),
        ),
        evidence_types=("role_record", "period_record", "local_sample_payload"),
        timeline_contribution="Role periods and appointment records.",
        search_hints=("transparencia", "cargo publico", "funcionario"),
        discovery_hints=("which_authorities_appear", "public_offices"),
        technical_metadata={"dataset_names": "transparencia-activa-sample", "module": "maintenance.transparencia_activa_prototype"},
        aliases=("Transparencia Activa", "transparencia-activa", "transparencia"),
    ),
    PublicSourcePlugin(
        id="contraloria",
        display_name="Contraloria",
        status=SourceStatus.PROTOTYPE,
        description="Control reports and observations from the local prototype data.",
        category="audits",
        coverage=_coverage("partial", "Local prototype records are available."),
        concepts=(
            _concept("Organismo", "Organization referenced by a control report.", "PUBLIC_ORGANIZATION"),
            _concept("Empresa", "Company referenced by a report or observation.", "COMPANY"),
            _concept("Informe de control", "Control report.", "CONTROL_REPORT"),
        ),
        relationships=(
            _relationship("CONTROL_REPORT_INVOLVES_ENTITY", "Informe de control", "Entidad", "Report references an entity."),
            _relationship("OBSERVATION_TARGETS_ENTITY", "Observacion", "Entidad", "Observation references an entity."),
        ),
        compatible_source_ids=("chilecompra", "municipalidades", "sanciones_procedimientos", "diario_oficial"),
        commands=(
            _command("loader", "python scripts/load_contraloria_sample.py", "Load local Contraloria sample."),
            _command("summary", "python scripts/contraloria_summary.py", "Show Contraloria summary."),
        ),
        evidence_types=("control_report", "observation_record", "local_sample_payload"),
        timeline_contribution="Report and observation dates.",
        search_hints=("contraloria", "informe de control", "observacion"),
        discovery_hints=("audits", "public_organizations"),
        technical_metadata={"dataset_names": "contraloria-sample", "module": "maintenance.contraloria_prototype"},
        aliases=("Contraloria", "Contraloría"),
    ),
    PublicSourcePlugin(
        id="municipalidades",
        display_name="Municipalidades",
        status=SourceStatus.PROTOTYPE,
        description="Municipal project and spending records from the local prototype data.",
        category="municipal",
        coverage=_coverage("partial", "Local prototype records are available."),
        concepts=(
            _concept("Organismo", "Municipality or local public entity.", "MUNICIPALITY"),
            _concept("Presupuesto", "Budget or spending record.", "BUDGET"),
            _concept("Proyecto Publico", "Public project.", "PUBLIC_PROJECT"),
        ),
        relationships=(
            _relationship("MUNICIPALITY_RUNS_PROJECT", "Organismo", "Proyecto Publico", "Municipality runs a project."),
            _relationship("PROJECT_HAS_SPENDING_ITEM", "Proyecto Publico", "Presupuesto", "Project has spending item."),
        ),
        compatible_source_ids=("dipres", "chilecompra", "contraloria"),
        commands=(
            _command("loader", "python scripts/load_municipalidades_sample.py", "Load local Municipalidades sample."),
            _command("summary", "python scripts/municipalidades_summary.py", "Show municipal summary."),
        ),
        evidence_types=("project_record", "spending_record", "local_sample_payload"),
        timeline_contribution="Project and spending period events.",
        search_hints=("municipalidad", "proyecto", "gasto municipal"),
        discovery_hints=("budgets", "public_organizations"),
        technical_metadata={"dataset_names": "municipalidades-sample", "module": "maintenance.municipalidades_prototype"},
        aliases=("Municipalidades", "municipalidades-sample"),
    ),
    PublicSourcePlugin(
        id="servel",
        display_name="SERVEL",
        status=SourceStatus.PROTOTYPE,
        description="Local sample of elected authority records.",
        category="authorities",
        coverage=_coverage("partial", "Local prototype records are available."),
        concepts=(
            _concept("Persona", "Elected authority.", "PERSON"),
            _concept("Cargo Publico", "Public elected office.", "ROLE"),
            _concept("Organismo", "Territory or public entity represented.", "PUBLIC_ORGANIZATION"),
        ),
        relationships=(
            _relationship("PERSON_HELD_ELECTED_OFFICE", "Persona", "Cargo Publico", "Person held elected office."),
            _relationship("OFFICE_BELONGS_TO_TERRITORY", "Cargo Publico", "Organismo", "Office belongs to a territory."),
        ),
        compatible_source_ids=("transparencia_activa", "lobby", "declaraciones_intereses"),
        commands=(
            _command("loader", "python scripts/load_servel_sample.py", "Load local SERVEL sample."),
            _command("summary", "python scripts/servel_summary.py", "Show SERVEL summary."),
        ),
        evidence_types=("authority_record", "period_record", "local_sample_payload"),
        timeline_contribution="Election periods and office terms.",
        search_hints=("servel", "autoridad", "periodo electoral"),
        discovery_hints=("which_authorities_appear", "public_offices"),
        technical_metadata={"dataset_names": "servel-authorities-sample", "module": "maintenance.servel_prototype"},
        aliases=("SERVEL", "servel-authorities-sample"),
    ),
    PublicSourcePlugin(
        id="diario_oficial",
        display_name="Diario Oficial",
        status=SourceStatus.PROTOTYPE,
        description="Local prototype of official publication records.",
        category="official_publications",
        coverage=_coverage("partial", "Local prototype records are available."),
        concepts=(
            _concept("Persona", "Person named in an official publication.", "PERSON"),
            _concept("Organismo", "Organization referenced by an official publication.", "PUBLIC_ORGANIZATION"),
            _concept("Cargo Publico", "Public office or role.", "ROLE"),
            _concept("Decreto", "Administrative decree.", "PUBLICATION"),
            _concept("Nombramiento", "Appointment record.", "PUBLICATION"),
            _concept("Renuncia", "Resignation record.", "PUBLICATION"),
        ),
        relationships=(
            _relationship("PERSON_APPOINTED_TO_PUBLIC_OFFICE", "Persona", "Cargo Publico", "Person appointed to public office."),
            _relationship("PERSON_RESIGNED_FROM_PUBLIC_OFFICE", "Persona", "Cargo Publico", "Person resigned from public office."),
            _relationship("DECREE_APPLIES_TO_ORGANIZATION", "Decreto", "Organismo", "Decree applies to organization."),
            _relationship("OFFICIAL_PUBLICATION_REFERENCES_ENTITY", "Publicacion", "Entidad", "Publication references entity."),
            _relationship("PUBLIC_OFFICE_BELONGS_TO_ORGANIZATION", "Cargo Publico", "Organismo", "Office belongs to organization."),
        ),
        compatible_source_ids=("transparencia_activa", "servel", "contraloria", "municipalidades"),
        commands=(
            _command("loader", "python scripts/load_diario_oficial_sample.py", "Load local Diario Oficial sample."),
            _command("summary", "python scripts/diario_oficial_summary.py", "Show Diario Oficial summary."),
        ),
        evidence_types=("official_publication", "decree_record", "local_sample_payload"),
        timeline_contribution="Publication, appointment, and resignation dates.",
        search_hints=("diario oficial", "decreto", "nombramiento", "renuncia"),
        discovery_hints=("which_official_publications_exist", "which_authorities_appear", "public_offices"),
        technical_metadata={"dataset_names": "diario-oficial-sample", "module": "maintenance.diario_oficial_prototype"},
        aliases=("Diario Oficial", "diario-oficial"),
    ),
    PublicSourcePlugin(
        id="registro_empresas",
        display_name="Registro Empresas",
        status=SourceStatus.PROTOTYPE,
        description="Local prototype of company registry records.",
        category="company_registry",
        coverage=_coverage("partial", "Local prototype and complete demo records are available."),
        concepts=(
            _concept("Empresa", "Registered company.", "COMPANY"),
            _concept("Persona", "Representative or owner.", "PERSON"),
            _concept("Representante", "Company representative.", "PERSON"),
            _concept("Socio", "Company owner or partner.", "PERSON"),
        ),
        relationships=(
            _relationship("PERSON_REPRESENTS_COMPANY", "Persona", "Empresa", "Person represents company."),
            _relationship("PERSON_OWNS_COMPANY", "Persona", "Empresa", "Person owns or participates in company."),
            _relationship("COMPANY_REGISTERED_ON", "Empresa", "Fecha", "Company registration event."),
            _relationship("COMPANY_MODIFIED_ON", "Empresa", "Fecha", "Company modification event."),
        ),
        compatible_source_ids=("chilecompra", "diario_oficial", "lobby"),
        commands=(
            _command("loader", "python scripts/load_registro_empresas_sample.py", "Load local company registry sample."),
            _command("summary", "python scripts/registro_empresas_summary.py", "Show company registry summary."),
        ),
        evidence_types=("company_record", "representative_record", "ownership_record", "local_sample_payload"),
        timeline_contribution="Company registration and modification dates.",
        search_hints=("empresa", "representante", "socio", "registro empresas"),
        discovery_hints=("which_related_companies_exist", "which_suppliers_appear", "suppliers"),
        technical_metadata={"dataset_names": "registro-empresas-sample", "module": "maintenance.registro_empresas_prototype"},
        aliases=("Registro Empresas", "registro-empresas", "registro_empresas"),
    ),
    PublicSourcePlugin(
        id="declaraciones_intereses",
        display_name="Declaraciones de Intereses",
        status=SourceStatus.PROTOTYPE,
        description="Local prototype for public declarations of interests and patrimony records.",
        category="integrity",
        coverage=_coverage("partial", "Local prototype records are available."),
        concepts=(
            _concept("Persona", "Declarant person.", "PERSON"),
            _concept("Cargo Publico", "Public role associated with declaration.", "ROLE"),
            _concept("Organizacion", "Organization referenced by a declaration.", "PUBLIC_ORGANIZATION"),
            _concept("Empresa", "Company referenced by a declaration.", "COMPANY"),
            _concept("Declaracion", "Declaration source record.", "SOURCE_RECORD"),
            _concept("Patrimonio / interes declarado", "Declared patrimony or interest item.", "SOURCE_RECORD"),
        ),
        relationships=(
            _relationship("PERSON_HAS_DECLARATION", "Persona", "Declaracion", "Person has a declaration record."),
            _relationship("DECLARATION_REFERENCES_COMPANY", "Declaracion", "Empresa", "Declaration references a company."),
            _relationship("DECLARATION_REFERENCES_ORGANIZATION", "Declaracion", "Organizacion", "Declaration references an organization."),
            _relationship("PERSON_HOLDS_PUBLIC_ROLE", "Persona", "Cargo Publico", "Person holds a public role."),
        ),
        compatible_source_ids=("servel", "transparencia_activa", "lobby", "registro_empresas", "diario_oficial"),
        commands=(
            _command("loader", "python scripts/load_declaraciones_intereses_sample.py", "Load local declarations sample."),
            _command("summary", "python scripts/declaraciones_intereses_summary.py", "Show declarations sample summary."),
        ),
        evidence_types=("declaration_record", "local_sample_payload"),
        timeline_contribution="Declaration dates and public role periods when available.",
        search_hints=("declaracion de intereses", "patrimonio", "interes declarado"),
        discovery_hints=("which_authorities_appear", "public_offices", "which_related_companies_exist"),
        technical_metadata={"dataset_names": "declaraciones-intereses-sample", "module": "maintenance.declaraciones_intereses_prototype"},
        aliases=("Declaraciones de intereses", "declaraciones-intereses"),
    ),
    PublicSourcePlugin(
        id="sanciones_procedimientos",
        display_name="Sanciones y procedimientos",
        status=SourceStatus.PLANNED,
        description="Fuente planificada para resoluciones, sanciones y procedimientos administrativos.",
        category="oversight",
        coverage=_coverage("future", "Planned source; no local loader yet."),
        concepts=(
            _concept("Organismo", "Public organization.", "PUBLIC_ORGANIZATION"),
            _concept("Empresa", "Company named in a procedure.", "COMPANY"),
            _concept("Persona", "Person named in a procedure.", "PERSON"),
        ),
        relationships=(
            _relationship("ENTITY_HAS_ADMINISTRATIVE_RECORD", "Entidad", "Registro", "Entity has an administrative record."),
            _relationship("PROCEDURE_INVOLVES_ENTITY", "Procedimiento", "Entidad", "Procedure involves an entity."),
        ),
        compatible_source_ids=("contraloria", "chilecompra"),
        commands=(),
        evidence_types=("procedure_record", "resolution_record"),
        timeline_contribution="Future procedure and resolution dates.",
        search_hints=("sancion", "procedimiento", "resolucion"),
        discovery_hints=("audits", "public_organizations"),
        technical_metadata={"planned": "true"},
        aliases=("Sanciones y procedimientos", "sanciones-procedimientos"),
    ),
)
