# DatosEnOrden - Changelog

> El codigo construye el sistema. La documentacion conserva la memoria.

## 2026-06-20

### Agregado

- Fase 11.0 Entity Investigation View con la pagina `Investigación` en Streamlit, que unifica cronologia, conexiones, contratos, Lobby, Transparencia, evidencia y explicacion en una sola vista publica.
- Nuevo ensamblador `src/datosenorden/maintenance/investigation_view.py` para componer la investigacion usando solo datos persistidos.
- Pruebas para la vista unificada de investigacion y su flujo de navegacion sin pestañas internas.
- Fase 10.5 Demo Readiness Pack con `scripts/demo_seed.py`, `scripts/demo_status.py` y `docs/DEMO_WALKTHROUGH.md` para preparar y validar una demo local sin nuevas fuentes.
- Modo demo opcional en Streamlit con banner, panel inicial guiado y resolucion por nombre de la entidad recomendada sin hardcodear IDs.
- Pruebas para el pack de demo, el estado listo/faltante, el banner de Streamlit y la resolucion de la entidad de demo.
- Fase 9.0 Transparencia Activa Prototype con sample local en `data/sample/transparencia_activa_sample.json`, marcado `LOCAL_TEST_DATA / NOT_OFFICIAL_DATA`.
- Importador `scripts/load_transparencia_sample.py` y resumen `scripts/transparencia_summary.py` para cargar y revisar roles administrativos de muestra sin APIs reales ni scraping.
- Entidades `PERSON` y `ROLE` en el contrato local del grafo, usando el almacenamiento existente basado en texto y sin cambiar la arquitectura persistente.
- Claims y relaciones neutrales `ORGANIZATION_HAS_PUBLIC_ROLE`, `PERSON_HOLDS_PUBLIC_ROLE` y `ROLE_BELONGS_TO_ORGANIZATION`.
- Registry de datasets actualizado para mostrar Transparencia Activa como activa cuando el sample local queda cargado.
- Grafo local capaz de mostrar `PUBLIC_ORGANIZATION -> ROLE -> PERSON` para el prototipo.
- `cross_dataset_summary` reconoce `transparencia` como dataset adicional cuando el mismo organismo tambien aparece en ChileCompra o Lobby.
- Explicaciones humanas neutrales para Transparencia Activa, indicando que el prototipo usa datos de muestra y no datos oficiales.
- Pruebas para carga del sample, idempotencia, matching, claims, relaciones, registry, grafo, resumen cruzado, scripts y explicacion humana.

## 2026-06-19

### Agregado

- Fase 8.1 Cross-Dataset Demo Alignment con `scripts/debug_cross_dataset_matches.py` para diagnosticar por que no aparecen organismos compartidos.
- Helper idempotente `scripts/align_lobby_sample_to_existing_org.py` para alinear el sample local de Lobby a un organismo ChileCompra existente sin tocar datos reales.
- Pruebas para diagnostico sin match, candidatos cercanos, alineacion local, idempotencia y resumen cruzado con un organismo compartido.
- Fase 8.0 Lobby <-> ChileCompra Cross-Dataset Exploration con `src/datosenorden/maintenance/cross_dataset_explorer.py` y `scripts/cross_dataset_summary.py`.
- Seccion Streamlit "Conexiones entre fuentes" para organismos presentes en ChileCompra y Lobby, con conteos de contratos, reuniones Lobby, evidencia y relaciones publicas.
- Bloque de perfil "Presente en multiples fuentes" y badges de dataset en grafo sin cambiar la logica de traversal.
- Pruebas unitarias, de script y de integracion Streamlit para la exploracion cruzada y su lenguaje neutral.
- Fase 7.0 Lobby Prototype con sample local en `data/sample/lobby_meeting_sample.json`, importador `scripts/load_lobby_sample.py` y resumen `scripts/lobby_summary.py`.
- Enlace neutral `PUBLIC_ORGANIZATION -> LOBBY_MEETING <- COMPANY` usando el matcher de entidades existente para conectar reuniones de lobby de muestra con organismos y contrapartes ya persistidas.
- Registry de datasets actualizado para mostrar Lobby como activo cuando el sample local queda cargado.
- Explicaciones humanas para lobby con lenguaje neutral: reunion registrada, contraparte, organismo publico y evidencia, sin implicar irregularidad.
- Pruebas para carga del sample Lobby, matching, claims, `relationship_public`, resumen, traversal de grafo y explicacion humana.
- Fase 7.0 Local Python Explorer con Streamlit en `streamlit_app.py`, reutilizando PostgreSQL persistido para home, datasets, busqueda de entidades, perfiles, grafo y explicaciones humanas.
- Documentacion para iniciar el explorador local con `streamlit run streamlit_app.py`.
- Fase 6.5 Human-Friendly Layer con comandos `scripts/explain_entity.py`, `scripts/explain_dataset.py` y `scripts/explain_graph.py` para interpretar entidades, datasets y grafos en lenguaje simple.
- Perfiles HTML de entidad, dataset y grafo enriquecidos con secciones `What does this mean?`.
- Mapeo de etiquetas tecnicas a lenguaje humano para `source_record`, `claim`, `relationship_public` y `entity`.
- Fase 10.0 Timeline Explorer con `src/datosenorden/maintenance/timeline_explorer.py`, CLI `scripts/entity_timeline.py` y exportador `scripts/export_entity_timeline.py`.
- Export HTML `reports/entity_timeline_<entity_id>.html` con cronologia vertical, agrupacion por ano, badges de dataset y conteos de evidencia/relaciones.
- Nueva seccion `Cronologia` en Streamlit para mostrar eventos fechados por entidad sin inferir causalidad.
- Fase 6.0 Dataset Registry con `src/datosenorden/maintenance/dataset_registry.py`, CLI `scripts/list_datasets.py`, `scripts/dataset_details.py` y `scripts/export_dataset_profile.py` para explorar datasets como entidades de primera clase.
- Perfil HTML de dataset `reports/dataset_<slug>.html` con conteos, salud, tipos de entidades, tipos de claims y tipos de relaciones.
- Pruebas para el registry de datasets y sus comandos de exploracion/exportacion.
- Fase 5.1 Entity Matching Engine con normalizacion reutilizable, ranking por exact match, contains y token overlap, CLI `scripts/match_entity.py` y pruebas dedicadas para coincidencia y no coincidencia.
- Fase 5.0 DIPRES Prototype con sample local en `data/sample/dipres_budget_sample.json`, importador `scripts/load_dipres_sample.py`, resumen presupuestario `scripts/budget_summary.py` y enlace cruzado Budget -> Organization -> Purchase Orders -> Suppliers.
- Mantenimiento del grafo para admitir el nodo `BUDGET`, claims de presupuesto y coincidencias normalizadas con entidades de ChileCompra ya persistidas.
- Pruebas para el sample DIPRES, el importador, el resumen presupuestario y la navegacion del grafo desde un nodo presupuestario.
- Fase 4.3 Entity Graph Navigation con vecinos directos, recorrido configurable del grafo y exportacion HTML en `graph_exports/entity_<entity_id>.html`.
- Modulo de mantenimiento extendido para exponer vecinos, recorridos de grafo, conteo de tipos de relacion y enlaces de navegacion en perfiles de entidad.
- Scripts `entity_neighbors.py`, `entity_graph.py`, `export_entity_graph.py` y `relationship_summary.py` para navegar el grafo persistido solo con PostgreSQL.
- Perfiles HTML de entidad enriquecidos con vecinos directos, conteos de relaciones y enlaces a perfiles/grafos relacionados.
- Pruebas para lookup de vecinos, traversal de grafo, export HTML y resumen de relaciones.
- Helpers locales privados de sincronizacion de base con `pg_dump`/`pg_restore` en `scripts/db/`, dumpes timestamped en `private/database/backups/` y verificacion de conteos para mover la base entre home y work sin exponer secretos.
- Flujo seguro de fusion local con `scripts/db/merge_local_db.py`, restaurando primero a una base temporal y luego insertando solo registros faltantes en la base principal sin duplicar entidades.

## 2026-06-18

### Agregado

- Fase 4.2 Entity Explorer con busqueda de proveedores y compradores, detalle de entidad y exportacion HTML en `profiles/<entity_id>.html`.
- Modulo `src/datosenorden/maintenance/entity_explorer.py` para centralizar consultas read-only de entidades, claims, evidencias y `relationship_public`.
- Scripts `search_supplier.py`, `search_buyer.py`, `entity_details.py` y `export_entity_profile.py` para explorar manualmente el grafo persistido sin nuevas fuentes ni API externa.

- Expansion inicial del dataset con `python scripts/load_sample_purchase_orders.py --limit 100` y resumen persistido con `python scripts/dataset_summary.py`.
- Conteos finales para `source_records`, `claims`, `evidences`, `relationship_public`, compradores y proveedores distintos.

- Exportador HTML `python scripts/export_trace_graph.py --external-id ...` para generar `graph_exports/<external-id>.html` con el primer grafo visible de trazabilidad.

- Resumen compacto de trazabilidad `python scripts/trace_summary.py --external-id ...` para revisar comprador, proveedor, evidencia y conteos persistidos.

- Inspector de trazabilidad de solo lectura `python scripts/inspect_trace.py --external-id ...` para revisar la cadena persistida sin llamar a ChileCompra.
- Documentacion de inspeccion persistida en `docs/DEVELOPMENT.md` y `docs/etl/CHILECOMPRA.md`.

- Modo seguro `--debug-payload` para inspeccionar la forma del payload de ChileCompra sin exponer ticket ni valores sensibles.
- Mapeo robusto de ordenes de compra con soporte para secciones anidadas `Comprador` y `Proveedor`.
- Rechazo explicito cuando un registro no puede derivar ningun claim, en vez de persistir un lote vacio sin explicacion.

### Agregado

- Helper local `reset_migrate_seed_verify` para resetear PostgreSQL, migrar, sembrar el seed local y verificar conteos.
- Documentacion de uso del helper en Windows sin Docker.

### Agregado

- Fase 3.1 con seed local marcado como `LOCAL_TEST_DATA / NOT_OFFICIAL_DATA` para validar persistencia sin ticket de ChileCompra.
- Comando `python scripts/seed_traceability_flow.py`.
- Verificacion SQL de conteos para `source_record`, `claim`, `evidence` y `relationship_public`.

### Agregado

- Fase 3.0 con ruta de carga persistida para ChileCompra por codigo de orden y por limite.
- Verificacion segura de `DATABASE_URL` sin exponer contrasenas.
- Carga de `.env` fijada al root del repositorio en Windows.
- Pruebas de configuracion para carga de `.env` y prioridad de `DATABASE_URL`.

### Agregado

- Validacion Fase 2.6 con el primer caso minimo de ChileCompra.
- Resumen de pipeline con conteos de `source_record`, `claim`, `evidence` y `relationship_public`.
- Test de cadena completa para un conjunto minimo de datos de compra publica.

### Agregado

- Schema v0.3 con `source_record`, `claim` y `relationship_public`.
- Migracion Alembic de Fase 2.5.
- Politica legal y etica minima.
- Documentacion obligatoria: `SOURCES.md`, `DECISIONS.md`, `IDEAS.md`, `CHANGELOG.md`.
- Adaptacion del ETL ChileCompra para emitir source records, claims y relaciones publicas derivadas.

### Cambiado

- `evidence` deja de depender solo de relaciones y pasa a vincularse con source, dataset, source_record y claim.
- `relationship_public` reemplaza a `relationship` como grafo navegable.

### No agregado

- No se agregaron nuevos ETLs.
- No se agrego MinIO/S3, Redis, OpenSearch, Neo4j, blockchain, IA, microservicios ni Kubernetes.
