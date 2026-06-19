# ADR 0002 - Contratos ETL antes de lógica específica de fuente

## Estado

Aceptada.

## Contexto

DatosEnOrden crecerá con múltiples fuentes públicas. Si cada fuente implementa extracción, normalización, mapeo y carga de forma distinta, el proyecto se volverá difícil de auditar y mantener.

## Decisión

Crear contratos internos para ETL:

- `SourceRecord`
- `DatasetRecord`
- `EntityRecord`
- `RelationshipRecord`
- `EvidenceRecord`
- `GraphBatch`

Cada fuente debe transformar sus payloads a esos contratos antes de cargar datos.

## Consecuencias

Ventajas:

- Separación clara entre fuente externa y modelo interno.
- Tests de mapeo sin base de datos.
- Loader reusable.
- Mejor trazabilidad.
- Menor riesgo de código desechable.

Costos:

- Más archivos y capas desde el inicio.
- Requiere disciplina para no saltarse contratos en ETLs futuros.

## Regla

Ningún ETL debe escribir directamente tablas del grafo sin pasar por contratos normalizados o una abstracción equivalente revisada.
