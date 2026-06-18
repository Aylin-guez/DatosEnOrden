# DatosEnOrden - Changelog

> El codigo construye el sistema. La documentacion conserva la memoria.

## 2026-06-18

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
