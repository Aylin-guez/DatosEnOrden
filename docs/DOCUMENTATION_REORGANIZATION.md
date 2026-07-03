# Propuesta de reorganizacion documental

Este documento propone una reorganizacion logica de `docs/` sin mover archivos todavia.

El objetivo es que la documentacion siga siendo navegable cuando DEO tenga mas fuentes, mas temas, mas eventos y mas documentos.

## Estructura propuesta

```text
docs/
  00_foundation/
  01_architecture/
  02_sources/
  03_engines/
  04_workflows/
  05_product/
  06_operations/
  07_templates/
  99_archive/
```

La estructura pedida se conserva y se agrega `06_operations` para despliegue/desarrollo y `07_templates` para plantillas reutilizables. Si se prefiere una version estricta, `06_operations` puede vivir dentro de `04_workflows` y `07_templates` dentro de `02_sources`.

## Criterios

- `00_foundation`: identidad, principios, confianza, vision, decisiones publicas.
- `01_architecture`: arquitectura tecnica, schema, core, repositorio, crecimiento.
- `02_sources`: fuentes oficiales, adapters, integraciones, catalogos y estrategia de fuentes.
- `03_engines`: motores existentes y modelos conceptuales de procesamiento.
- `04_workflows`: procesos paso a paso, demo, documentos oficiales, desarrollo operativo.
- `05_product`: experiencia ciudadana, UX, busqueda, biblioteca, SEO y presentacion publica.
- `06_operations`: deployment, troubleshooting, desarrollo local y comandos operativos.
- `07_templates`: plantillas reutilizables.
- `99_archive`: auditorias, primeras cargas, prototipos historicos, ideas y documentos reemplazados.

## Mapa propuesto de documentos existentes

### 00_foundation

- `DEO_CONSTITUTION.md`
- `TRUST_POLICY.md`
- `VISION.md`
- `PLATFORM_CORE_VISION.md`
- `PUBLIC_PRODUCT_IDENTITY.md`
- `LEGAL_ETHICS.md`
- `INFORMATION_POLICY.md`
- `DECISIONS.md`
- `CHANGELOG.md`
- `ROADMAP.md`
- `TECHNICAL_ROADMAP.md`
- `NEXT_PUBLIC_PHASE.md`

### 01_architecture

- `ARCHITECTURE.md`
- `architecture/ARCHITECTURE.md`
- `REAL_DATA_ARCHITECTURE.md`
- `DEPLOYMENT_ARCHITECTURE.md`
- `STUDIO_ARCHITECTURE.md`
- `REPOSITORY_STRATEGY.md`
- `PROJECT_GROWTH_PLAN.md`
- `SCHEMA.md`
- `SCHEMA_REVIEW.md`
- `API_FUTURE.md`
- `DATA_PIPELINE.md`
- `DATASET_REGISTRY.md`
- `DATASET_PLUGIN_ARCHITECTURE.md`
- `REUSABLE_ENGINES_AUDIT.md`
- `PRIVATE_ENGINES_STRATEGY.md`
- `adr/0001-postgresql-sqlalchemy-alembic.md`
- `adr/0002-etl-contracts-before-source-specific-logic.md`

### 02_sources

- `SOURCE_FACTORY.md`
- `SOURCE_INTEGRATION_PRIORITY.md`
- `SOURCE_WATCHER.md`
- `ADAPTER_GUIDELINES.md`
- `DATA_SOURCE_STRATEGY.md`
- `SOURCES.md`
- `OFFICIAL_SOURCES_CATALOG.md`
- `REAL_SOURCES_PLAN.md`
- `REAL_DATA_AUDIT.md`
- `LEGISLATIVE_SOURCE_ANALYSIS.md`
- `LEGISLATIVE_INTEGRATION_PLAN.md`
- `FIRST_LEGISLATIVE_IMPORT.md`
- `sources/README.md`
- `sources/chilecompra.md`
- `sources/contraloria.md`
- `sources/declaraciones_intereses.md`
- `sources/diario_oficial.md`
- `sources/dipres.md`
- `sources/lobby.md`
- `sources/municipalidades.md`
- `sources/registro_empresas.md`
- `sources/sanciones_procedimientos.md`
- `sources/servel.md`
- `sources/transparencia_activa.md`
- `etl/CHILECOMPRA.md`

### 03_engines

- `ACTUALIDAD_ENGINE.md`
- `AUTO_TOPIC_UPDATE.md`
- `AUTOMATIC_TIMELINE.md`
- `DOCUMENT_READING_PIPELINE.md`
- `ENTITY_RESOLUTION_ENGINE.md`
- `INVESTIGATION_KNOWLEDGE_ENGINE.md`
- `KNOWLEDGE_ENGINE.md`
- `PLATFORM_PUBLICATION_ENGINE.md`
- `STATE_EVENTS_MODEL.md`
- `OFFICIAL_DOCUMENT_PROCESSING.md`
- `LEGISLATIVE_DOCUMENT_RESOLUTION.md`

### 04_workflows

- `SOURCE_INTEGRATION_WORKFLOW.md`
- `OFFICIAL_DOCUMENT_WORKFLOW.md`
- `DOCUMENT_EXPERIENCE.md`
- `LEGISLATIVE_DOCUMENT_DISCOVERY.md`
- `LEGISLATIVE_DOCUMENT_FLOW.md`
- `FIRST_REAL_DOCUMENT_READING.md`
- `FIRST_REAL_DOCUMENTED_READING.md`
- `FIRST_REAL_CHILECOMPRA_LOAD.md`
- `DEMO_WALKTHROUGH.md`
- `LAUNCH_CHECKLIST.md`
- `DEVELOPMENT.md`

### 05_product

- `CONTENT_STRATEGY.md`
- `CITIZEN_JOURNEY.md`
- `CITIZEN_EXPERIENCE_AUDIT.md`
- `LIBRARY_V1.md`
- `PUBLIC_UX_SINGLE_READING.md`
- `SEARCH_EXPERIENCE.md`
- `SEO_STRATEGY.md`
- `THEME_EXPERIENCE.md`
- `UX_GUIDELINES.md`
- `REFLEX_PROTOTYPE.md`

### 06_operations

- `DEPLOYMENT.md`
- `deployment/WEB_ARCHITECTURE.md`
- `REFLEX_TROUBLESHOOTING.md`
- `DEVELOPMENT.md`

### 07_templates

- `templates/SOURCE_INTEGRATION_TEMPLATE.md`

### 99_archive

- `IDEAS.md`
- `recordatorios/1.txt`
- documentos de auditoria historica que hayan sido reemplazados por estandares actuales;
- prototipos que ya no representen la arquitectura vigente.


## Referencias cruzadas importantes

Algunos documentos pertenecen a una carpeta primaria, pero deben quedar enlazados desde otra familia:

- `SOURCE_INTEGRATION_WORKFLOW.md` vive en `04_workflows`, pero debe enlazarse desde `02_sources`.
- `DOCUMENT_TEMPLATE.md` vive en `07_templates`, pero debe enlazarse desde workflows de documentos.
- `DEVELOPMENT.md` vive en `06_operations`, pero puede enlazarse desde workflows de contribucion.

## Directorios a revisar

- `prompt/`: directorio existente sin archivos listados por `rg --files`; revisar antes de mover o archivar.

## Duplicados o zonas a revisar antes de mover

- `ARCHITECTURE.md` y `architecture/ARCHITECTURE.md` parecen competir como entrada de arquitectura.
- `SOURCES.md`, `sources/README.md`, `OFFICIAL_SOURCES_CATALOG.md`, `DATA_SOURCE_STRATEGY.md` y `REAL_SOURCES_PLAN.md` deben tener roles separados.
- `DOCUMENT_TEMPLATE.md` puede vivir como plantilla, pero tambien se usa como guia de workflow.
- `DEVELOPMENT.md` aparece en workflow y operations; conviene decidir si es guia operativa o proceso de contribucion.
- Documentos `FIRST_*` son utiles como historial, pero no deberian competir con estandares permanentes.

## Orden recomendado de migracion futura

1. Crear carpetas destino y un indice `docs/README.md`.
2. Mover primero documentos fundacionales y de fuentes.
3. Actualizar enlaces desde README y documentos principales.
4. Mover engines y workflows.
5. Archivar documentos historicos con nota de reemplazo.
6. Ejecutar busqueda de enlaces rotos.
7. Validar demo y tests.

## Regla de no perdida

Ningun documento debe moverse sin conservar su proposito, enlaces entrantes y relacion con el estandar vigente.