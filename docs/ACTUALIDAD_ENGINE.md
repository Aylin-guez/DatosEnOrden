# Actualidad Documentada Engine V1

## Responsabilidad

Actualidad Documentada no es una seccion de noticias. DatosEnOrden no genera noticias: publica temas oficiales actualmente analizados desde documentacion oficial.

El motor no interpreta documentos, no genera conocimiento, no hace OCR y no llama APIs externas. Toma artefactos ya producidos por el Platform Publication Engine y construye un objeto publico reutilizable.

```text
Documento
  -> Reading Pipeline
  -> Knowledge Engine
  -> Publication Engine
  -> Actualidad Engine
  -> Home
  -> Lectura Documentada
  -> Expediente
  -> Seguimiento
```

## Contrato

`CurrentTopic` es completamente serializable y contiene:

- `id`
- `slug`
- `title`
- `subtitle`
- `summary`
- `organization`
- `date`
- `status`
- `primary_document`
- `related_expedientes`
- `related_reports`
- `related_tracking`
- `main_questions`
- `key_points`
- `references`
- `tags`
- `published_at`
- `updated_at`
- `href`
- `artifacts`

## Funciones

- `build_current_topic(document_id)`
- `publish_current_topic(document_id)`
- `list_current_topics()`
- `get_current_topic(slug)`

## Integracion

Home consume `get_current_topics(limit=3)` desde `app_services`. No se crea una pagina nueva. La seccion pequena `Actualidad Documentada` muestra temas oficiales actualmente analizados por DatosEnOrden y enlaza a la lectura documentada existente.

## Que NO hace

- No usa IA.
- No hace scraping.
- No usa OCR.
- No llama APIs externas.
- No cambia schema.
- No toca GraphLoader.
- No toca Entity Resolution.
- No duplica la logica del Reading Pipeline, Knowledge Engine ni Publication Engine.

## Preparacion futura

El mismo objeto `CurrentTopic` permitira publicar mas adelante:

- ultimos documentos publicados
- cambios recientes
- proyectos de ley
- decretos
- presupuestos
- licitaciones
- informes
- RSS
- newsletter
- redes sociales

La regla arquitectonica se mantiene: esos canales deben reutilizar el mismo objeto y no modificar Reading Pipeline, Knowledge Engine ni Publication Engine.
