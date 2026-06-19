# Crítica del schema v0.1 y mejoras aplicadas

## Diagnóstico

El schema inicial era correcto como punto conceptual: entidades, relaciones, fuentes, evidencia, datasets e importaciones son las piezas adecuadas para construir un grafo verificable.

El problema era que todavía parecía un boceto. Para una infraestructura pública necesita más integridad, trazabilidad operacional y reglas explícitas.

## Riesgos detectados

### 1. Timestamps sin zona horaria

`TIMESTAMP` sin zona horaria es ambiguo para datos recuperados desde distintas fuentes o procesos. Se cambió a `TIMESTAMPTZ`.

### 2. Fuentes demasiado opcionales

`source.url` y `dataset.source_id` podían ser nulos. Eso debilitaba el principio “sin fuente no existe”. Ahora son obligatorios.

### 3. Datasets sin versión obligatoria

Una carga reproducible necesita versión, URL y opcionalmente hash. Se agregó `content_hash` y `version` obligatoria.

### 4. Relaciones duplicables

El schema permitía duplicar la misma relación indefinidamente. Se agregó una restricción de unicidad por origen, destino, tipo y rango temporal.

### 5. Sin validación de rangos temporales

Una relación podía terminar antes de comenzar. Se agregó un `CHECK`.

### 6. Sin protección contra autorrelaciones accidentales

Se agregó un `CHECK` para evitar `source_entity_id = target_entity_id`.

### 7. Estados sin dominio mínimo

`status` era texto libre en entidades e importaciones. Se agregaron restricciones iniciales.

### 8. Falta de metadatos controlados

No todo dato específico de una fuente merece una columna global. Se agregaron campos JSONB de metadatos para preservar detalles sin romper el núcleo.

### 9. Auditoría incompleta

`change_log.entity_name` era ambiguo. Se cambió a `entity_table` y se mantuvo `entity_id`.

## Decisiones postergadas

### Evidencia obligatoria por relación

La regla es central, pero exigirla como constraint inmediata crea un ciclo: una relación debe existir para que exista evidencia, y evidencia debe existir para validar la relación.

Solución por fases:

- Fase 1: claves foráneas estrictas y documentación.
- Fase 2: contrato de escritura que cree relación y evidencia en una misma transacción.
- Fase 3: estado de publicación o validación diferida para impedir exposición de relaciones sin evidencia.

### Catálogos cerrados de tipos

No se crearon tablas `entity_type` o `relationship_type` todavía. En Fase 1 se mantiene texto restringible por convenciones para no bloquear descubrimiento de dominio.

Cuando haya más fuentes reales, convendrá pasar a catálogos versionados.

### Datos normalizados por dominio

No se agregaron tablas específicas para contratos, licitaciones, personas o empresas. Eso debe ocurrir después de validar contratos de datos y fuentes reales.
