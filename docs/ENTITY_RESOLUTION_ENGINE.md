# Entity Resolution Engine

## Objetivo

Entity Resolution Engine permite representar una entidad unica mediante multiples nombres, alias e identificadores. Es una capa generica de Platform Core: no conoce politica, salud, universidades, empresas ni ningun dominio especifico.

Su rol es responder una pregunta simple:

> Dado este texto o identificador, a que entidad canonica apunta?

## Arquitectura MVP

El motor vive en `src/datosenorden/maintenance/entity_resolution.py` y trabaja con datos locales read-only desde JSON.

Conceptos principales:

- `CanonicalEntity`: entidad unica con `id`, `canonical_name`, `aliases`, `identifiers`, `tags` y `metadata`.
- `EntityAlias`: nombre alternativo de una entidad.
- `Identifier`: identificador configurable, por ejemplo UUID, codigo interno, ID de proveedor o ID de expediente.
- `ResolutionResult`: resultado con entidad encontrada, confianza, metodo utilizado y valor que hizo match.
- `EntityRegistry`: coleccion local de entidades canonicas y punto de entrada del resolver.

No modifica schema, no reemplaza modelos actuales y no trae datos externos.

## Metodos de resolucion

El MVP es rule-based y local. Soporta:

- `exact`: match exacto contra el nombre canonico.
- `canonical`: match normalizado contra el nombre canonico, ignorando mayusculas, acentos y espacios repetidos.
- `alias`: match contra alias normalizados.
- `identifier`: match contra identificadores configurables.

No usa IA, embeddings, scraping ni APIs.

## Configuracion

La configuracion demo vive en:

`config/entity_resolution/datosenorden_demo.json`

Cada entidad declara:

- `id`
- `canonical_name`
- `aliases`
- `identifiers`
- `tags`
- `metadata`

El formato es generico para que pueda moverse a otro repositorio o producto sin depender de DatosEnOrden ciudadano.

## Integracion actual

`app_services.resolve_investigation_target()` consulta primero Entity Resolution Engine. Si encuentra una entidad, usa su `id` canonico como entrada para el flujo existente de expediente.

Si el motor no resuelve o la configuracion no esta disponible, el sistema cae al resolvedor anterior. Esto mantiene compatibilidad con el MVP actual.

## Como escalar

Nuevos resolvers pueden agregarse sin cambiar el contrato principal:

1. Resolver por reglas adicionales.
2. Resolver por similitud textual.
3. Resolver por fuente/adaptador.
4. Resolver por IA o embeddings.

Cada resolver futuro debe devolver `ResolutionResult` o un objeto equivalente con:

- entidad candidata
- confianza
- metodo
- evidencia o razon del match

## IA futura sin romper el Core

La IA no debe reemplazar la entidad canonica ni escribir directamente en modelos de negocio.

Estrategia recomendada:

- Mantener `EntityRegistry` como fuente canonica validada.
- Usar IA solo para sugerir candidatos.
- Requerir evidencia o aprobacion antes de promover un alias o identificador.
- Guardar explicaciones del match como metadata, no como verdad irreversible.

## DatosEnOrden Studio

Este motor forma parte del ecosistema de motores reutilizables de DatosEnOrden Studio. Debe poder vivir en un repositorio independiente en el futuro.

Reglas:

- No acoplarlo a expedientes, politica ni fuentes ciudadanas.
- No hardcodear vocabulario de cliente.
- No mezclar configuraciones comerciales con el core.
- Mantener configuracion por JSON u otro adaptador externo.
