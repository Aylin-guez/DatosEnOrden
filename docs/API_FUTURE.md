# API Future

DatosEnOrden todavia no expone una API publica. La UI Reflex consume funciones locales de `src/datosenorden/web/app_services.py`, y esa capa queda como contrato interno reutilizable para una futura API HTTP o una UI Next.js.

## Estado actual

- No hay servidor API publico.
- No se agregan endpoints en esta fase.
- No se abren APIs externas ni scraping.
- Las respuestas internas deben seguir siendo JSON-safe.
- Los datos demo siguen marcados como `LOCAL_TEST_DATA` y `NOT_OFFICIAL_DATA`.

## Endpoints futuros propuestos

### GET /api/v1/investigations

Listaria expedientes disponibles o destacados.

Respuesta futura:
- `id`
- `name`
- `entity_type`
- `sources`
- `evidence_count`
- `relationship_count`
- `canonical_url`

Servicio interno relacionado:
- `search_workspace(query)`
- `get_home_navigation_examples()`

### GET /api/v1/investigations/{id}

Devolveria un expediente reconstruible desde un id o nombre canonico.

Respuesta futura:
- `entity`
- `summary`
- `compact_metrics`
- `timeline`
- `connections`
- `evidence`
- `technical_details`

Servicio interno relacionado:
- `resolve_investigation_target(value)`
- `get_investigation(entity_id)`
- `get_investigation_story(entity_id)`
- `get_investigation_graph(entity_id)`
- `get_investigation_timeline(entity_id)`

### GET /api/v1/sources

Listaria fuentes, estado de cobertura, conceptos y contribuciones.

Respuesta futura:
- `sources`
- `concepts`
- `roadmap`
- `totals`

Servicio interno relacionado:
- `get_data_ecosystem()`
- `get_dataset_summary()`

### GET /api/v1/reports

Listaria reportes ciudadanos disponibles.

Respuesta futura:
- `id`
- `title`
- `subject`
- `summary`
- `sources`
- `related_expediente_target`
- `export_url`

Servicio interno relacionado:
- `get_citizen_reports()`
- `get_citizen_report(report_id)`
- `export_citizen_report_demo()`

### GET /api/v1/tracking

Listaria items de seguimiento, estados y timelines.

Respuesta futura:
- `item`
- `events`
- `documents`
- `evidence`
- `follow_targets`

Servicio interno relacionado:
- `get_tracking_items()`
- `get_tracking_item(item_id)`
- `get_tracking_timeline(item_id)`

## Reglas de contrato

- Los endpoints futuros no deben devolver objetos ORM ni dataclasses crudas.
- La fuente de verdad para expediente debe seguir siendo: URL/id -> backend -> vista JSON-safe -> render.
- Las respuestas deben incluir aclaraciones cuando sean datos locales de prueba.
- No usar campos acusatorios o de riesgo si no existe base juridica y editorial para ello.
