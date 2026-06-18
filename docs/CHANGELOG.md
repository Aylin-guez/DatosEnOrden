# DatosEnOrden - Changelog

> El codigo construye el sistema. La documentacion conserva la memoria.

## 2026-06-18

### Agregado

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
