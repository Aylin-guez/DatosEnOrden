# Roadmap técnico

## Fase 1: Fundación

Objetivo: dejar una base profesional, migrable y mantenible antes de escribir ETLs específicos.

Entregables:

- Estructura de repositorio.
- Paquete Python bajo `src/`.
- Configuración local con PostgreSQL.
- Modelos SQLAlchemy.
- Migración inicial Alembic.
- SQL de referencia.
- Documentación técnica.
- API base con endpoint de salud.
- Tests mínimos de arranque.

Criterio de salida:

- `alembic upgrade head` crea la base desde cero.
- `pytest` valida que la aplicación base carga.
- El schema y sus decisiones están documentados.

## Fase 2: Contratos de datos

Objetivo: definir cómo entran datos al sistema sin acoplarse todavía a una fuente específica.

Entregables:

- Convenciones de identificadores externos.
- Contratos para entidades, relaciones, fuentes, evidencias, datasets e import jobs.
- Reglas de validación.
- Política de errores y reintentos.
- Guía para crear ETLs.
- Primer pipeline ChileCompra estructurado.

Estado: implementado como base inicial en `src/datosenorden/etl`.

## Fase 2.5: Nucleo de trazabilidad y claims

Objetivo: evitar que el grafo publico sea la unica fuente de verdad.

Entregables:

- `source_record`.
- `claim`.
- `evidence` vinculada a fuente, dataset, source_record y claim.
- `relationship_public` como proyeccion navegable.
- Politica legal y etica minima.
- Documentacion obligatoria de memoria permanente.

Restriccion:

- No avanzar a nuevos ETLs.
- No introducir infraestructura pesada antes de validar contratos.

## Fase 3: Primer ETL real

Objetivo: implementar el primer pipeline con una fuente pública acotada.

Restricción:

- El ETL debe seguir los contratos de Fase 2.
- No debe modificar el schema sin migración.
- Cada relación creada debe tener evidencia.

## Fase 4: API pública inicial

Objetivo: exponer lectura básica del grafo.

Endpoints candidatos:

- Entidades por tipo.
- Detalle de entidad.
- Relaciones por entidad.
- Evidencias por relación.
- Fuentes y datasets.

## Fase 5: Exploración visual

Objetivo: permitir navegación humana del grafo y la evidencia.

Opciones:

- Streamlit para exploración temprana.
- Frontend dedicado cuando los contratos de API sean estables.

## Fase 6: Versionado histórico avanzado

Objetivo: reconstrucción temporal y auditoría de cambios.

Entregables:

- Estrategia de snapshots.
- Auditoría por tabla.
- Políticas de retención.
- Exportaciones reproducibles.
