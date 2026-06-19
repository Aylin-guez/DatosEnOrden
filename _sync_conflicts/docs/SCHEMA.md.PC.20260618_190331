# DatosEnOrden - Schema v0.3

> El codigo construye el sistema. La documentacion conserva la memoria.

Schema v0.3 introduce el nucleo de trazabilidad y claims. El objetivo es evitar que el grafo publico sea la unica fuente de verdad.

## Tablas principales

```text
source
dataset
import_job
source_record
entity
claim
evidence
relationship_public
change_log
```

## `source`

Sistema u organismo origen.

Campos principales:

- `id`
- `name`
- `publisher`
- `url`
- `license`
- `retrieved_at`
- `source_metadata`
- `created_at`

## `dataset`

Recurso o ventana de carga asociada a una fuente.

Campos principales:

- `id`
- `source_id`
- `name`
- `description`
- `version`
- `dataset_url`
- `content_hash`
- `loaded_at`
- `dataset_metadata`
- `created_at`

## `import_job`

Ejecucion operativa de una carga.

Campos principales:

- `id`
- `dataset_id`
- `started_at`
- `finished_at`
- `status`
- `records_processed`
- `error_log`
- `job_metadata`
- `created_at`

## `source_record`

Registro extraido desde la fuente antes de convertirlo en entidad, claim o relacion publica.

Campos minimos:

- `id`
- `source_id`
- `dataset_id`
- `external_id`
- `record_type`
- `payload_hash`
- `raw_payload`
- `retrieved_at`
- `processed_at`
- `status`
- `error_log`
- `created_at`

Regla: todo claim debe poder volver a un `source_record`.

## `entity`

Entidad canonica reutilizable.

Campos principales:

- `id`
- `entity_type`
- `name`
- `description`
- `external_id`
- `normalized_key`
- `status`
- `entity_metadata`
- `created_at`
- `updated_at`

## `claim`

Afirmacion atomica verificable.

Campos minimos:

- `id`
- `subject_entity_id`
- `predicate`
- `object_entity_id`
- `object_value`
- `source_record_id`
- `evidence_id`
- `valid_from`
- `valid_to`
- `confidence`
- `status`
- `created_at`

Reglas:

- Debe tener sujeto.
- Debe tener objeto como entidad o valor.
- Debe apuntar a source_record.
- Debe apuntar a evidencia.
- No debe mezclar dato con opinion.

## `evidence`

Evidencia verificable.

Campos principales:

- `id`
- `source_id`
- `dataset_id`
- `source_record_id`
- `claim_id`
- `title`
- `url`
- `published_at`
- `excerpt`
- `evidence_metadata`
- `created_at`

La evidencia puede respaldar claims y conservar trazabilidad hacia fuente, dataset y registro original.

## `relationship_public`

Proyeccion navegable derivada desde claims validados.

Campos minimos:

- `id`
- `source_entity_id`
- `target_entity_id`
- `relationship_type`
- `claim_id`
- `published_at`
- `status`
- `relationship_metadata`
- `created_at`

Regla: `relationship_public` no es fuente de verdad. Si hay conflicto, manda el claim y su evidencia.

## Estados

Estados de datos publicables:

- `ingested`: recibido desde una fuente.
- `normalized`: convertido a contrato interno.
- `validated`: paso reglas minimas.
- `published`: disponible para API/grafo publico.
- `rejected`: descartado por error o regla.
- `disputed`: cuestionado o pendiente de revision.
- `withdrawn`: retirado de publicacion.

## Pregunta de trazabilidad

Todo dato publicado debe responder:

```text
source -> dataset -> import_job -> source_record -> claim -> evidence -> relationship_public
```
