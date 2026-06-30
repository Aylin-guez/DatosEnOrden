# Source Operations Index

This index is the operational companion to `SOURCES.md`. It lists registered public source plugins, readiness status, local commands, and what each source contributes.

## Active

### ChileCompra

- Source id: `chilecompra`
- Contributes: procurement records, buyers, suppliers, purchase orders, contracts.
- Concepts: Organismo, Empresa, Contrato.
- Relationships: ISSUES_PURCHASE_ORDER, RECEIVES_CONTRACT, PUBLISHED_TENDER, AWARDS_CONTRACT.
- Loader: `python scripts/load_sample_purchase_orders.py`
- Summary: `python scripts/dataset_summary.py`
- Readiness: active local source with demo data.

## Prototype

### DIPRES

- Source id: `dipres`
- Contributes: budget allocation and execution sample records.
- Concepts: Presupuesto, Organismo.
- Relationships: BUDGET_ALLOCATED_TO, BUDGET_EXECUTED_BY.
- Loader: `python scripts/load_dipres_sample.py`
- Summary: `python scripts/budget_summary.py`
- Readiness: local prototype.

### Lobby

- Source id: `lobby`
- Contributes: registered meeting sample records.
- Concepts: Reunion, Persona, Organismo, Empresa.
- Relationships: ORGANIZATION_HELD_LOBBY_MEETING, COUNTERPARTY_PARTICIPATED_IN_LOBBY.
- Loader: `python scripts/load_lobby_sample.py`
- Summary: `python scripts/lobby_summary.py`
- Readiness: local prototype.

### Transparencia Activa

- Source id: `transparencia_activa`
- Contributes: public role sample records.
- Concepts: Persona, Cargo Publico, Organismo.
- Relationships: ORGANIZATION_HAS_PUBLIC_ROLE, ROLE_BELONGS_TO_ORGANIZATION, PERSON_HOLDS_PUBLIC_ROLE.
- Loader: `python scripts/load_transparencia_sample.py`
- Summary: `python scripts/transparencia_summary.py`
- Readiness: local prototype.

### Contraloria

- Source id: `contraloria`
- Contributes: control report sample records.
- Concepts: Organismo, Empresa, Informe de control.
- Relationships: CONTROL_REPORT_INVOLVES_ENTITY, OBSERVATION_TARGETS_ENTITY.
- Loader: `python scripts/load_contraloria_sample.py`
- Summary: `python scripts/contraloria_summary.py`
- Readiness: local prototype.

### Municipalidades

- Source id: `municipalidades`
- Contributes: municipal project and spending sample records.
- Concepts: Organismo, Presupuesto, Proyecto Publico.
- Relationships: MUNICIPALITY_RUNS_PROJECT, PROJECT_HAS_SPENDING_ITEM.
- Loader: `python scripts/load_municipalidades_sample.py`
- Summary: `python scripts/municipalidades_summary.py`
- Readiness: local prototype.

### SERVEL

- Source id: `servel`
- Contributes: elected authority sample records.
- Concepts: Persona, Cargo Publico, Organismo.
- Relationships: PERSON_HELD_ELECTED_OFFICE, OFFICE_BELONGS_TO_TERRITORY.
- Loader: `python scripts/load_servel_sample.py`
- Summary: `python scripts/servel_summary.py`
- Readiness: local prototype.

### Diario Oficial

- Source id: `diario_oficial`
- Contributes: official publication sample records.
- Concepts: Persona, Organismo, Cargo Publico, Decreto, Nombramiento, Renuncia.
- Relationships: PERSON_APPOINTED_TO_PUBLIC_OFFICE, PERSON_RESIGNED_FROM_PUBLIC_OFFICE, DECREE_APPLIES_TO_ORGANIZATION.
- Loader: `python scripts/load_diario_oficial_sample.py`
- Summary: `python scripts/diario_oficial_summary.py`
- Readiness: local prototype.

### Registro Empresas

- Source id: `registro_empresas`
- Contributes: company registry sample records.
- Concepts: Empresa, Persona, Representante, Socio.
- Relationships: PERSON_REPRESENTS_COMPANY, PERSON_OWNS_COMPANY, COMPANY_REGISTERED_ON, COMPANY_MODIFIED_ON.
- Loader: `python scripts/load_registro_empresas_sample.py`
- Summary: `python scripts/registro_empresas_summary.py`
- Readiness: local prototype.

### Declaraciones de Intereses

- Source id: `declaraciones_intereses`
- Contributes: local declaration sample records connecting people, roles, organizations, and companies.
- Concepts: Persona, Cargo Publico, Organizacion, Empresa, Declaracion, Patrimonio / interes declarado.
- Relationships: PERSON_HAS_DECLARATION, DECLARATION_REFERENCES_COMPANY, DECLARATION_REFERENCES_ORGANIZATION, PERSON_HOLDS_PUBLIC_ROLE.
- Loader: `python scripts/load_declaraciones_intereses_sample.py`
- Summary: `python scripts/declaraciones_intereses_summary.py`
- Readiness: local prototype.

### Sanciones y Procedimientos

- Source id: `sanciones_procedimientos`
- Contributes: administrative procedure and resolution sample records.
- Concepts: Organismo, Empresa, Persona, Procedimiento administrativo, Resolucion administrativa.
- Relationships: PROCEDURE_INVOLVES_ORGANIZATION, PROCEDURE_INVOLVES_COMPANY, PROCEDURE_INVOLVES_PERSON, PROCEDURE_HAS_RESOLUTION.
- Loader: `python scripts/load_sanciones_procedimientos_sample.py`
- Summary: `python scripts/sanciones_procedimientos_summary.py`
- Readiness: local prototype.

## Planned

No planned-only source is required for the current demo pack.
