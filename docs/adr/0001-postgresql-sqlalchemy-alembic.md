# ADR 0001 - PostgreSQL, SQLAlchemy y Alembic como fundación

## Estado

Aceptada.

## Contexto

DatosEnOrden necesita una base verificable, trazable y reproducible. El sistema debe crecer hacia ETLs, API pública, exploración visual y análisis histórico sin sacrificar integridad.

## Decisión

Usar PostgreSQL como base de datos principal, SQLAlchemy como capa de modelos Python y Alembic como mecanismo obligatorio de migraciones.

## Consecuencias

Ventajas:

- Integridad referencial desde el inicio.
- Migraciones reproducibles.
- JSONB disponible para metadatos variables.
- Compatibilidad futura con API, ETL y análisis.
- Menor complejidad operativa que introducir un motor de grafos en Fase 1.

Costos:

- Algunas reglas de grafo requieren validación de aplicación o procesos diferidos.
- Las consultas complejas de grafo pueden necesitar optimización posterior.

## Alternativas consideradas

### Solo SQL manual

Simple al inicio, pero frágil para crecimiento y colaboración.

### Motor de grafos dedicado

Atractivo para exploración de relaciones, pero prematuro para una fundación que necesita trazabilidad, migraciones y ETLs reproducibles.

### ORM sin migraciones

No aceptable. Un proyecto público necesita historial explícito de cambios de schema.
