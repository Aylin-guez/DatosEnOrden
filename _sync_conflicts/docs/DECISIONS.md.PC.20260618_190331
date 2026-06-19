# DatosEnOrden - Decisiones

> El codigo construye el sistema. La documentacion conserva la memoria.

Este archivo resume decisiones tecnicas y de producto. Las decisiones extensas deben tener ADR en `docs/adr/`.

## 2026-06-18 - Fase 2.5: claims antes de nuevos ETLs

Decision:

- No avanzar a nuevos ETLs.
- Introducir `source_record`.
- Introducir `claim`.
- Reemplazar `relationship` como verdad por `relationship_public` como proyeccion.
- Permitir que `evidence` respalde claims y preserve trazabilidad a fuente, dataset y registro original.

Razon:

- El modelo `entity/relationship` era util, pero demasiado generico como unica verdad.
- Se necesitaba una arquitectura evolutiva sin sobreingenieria.

Consecuencia:

- Los ETLs deben generar source_records, claims, evidence y relaciones publicas derivadas.
- El grafo publico deja de ser fuente de verdad.

## 2026-06-18 - No incorporar infraestructura pesada todavia

Decision:

- No agregar MinIO/S3, Redis, OpenSearch, Neo4j, blockchain, IA, microservicios ni Kubernetes en Fase 2.5.

Razon:

- El proyecto necesita avanzar durante los proximos 30 dias sin destruir el futuro.
- La complejidad operacional debe entrar despues de validar contratos de datos.
