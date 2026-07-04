# Document Reading Pipeline V1

## Objetivo

El pipeline permite generar automaticamente una Lectura Documentada a partir de un documento estructurado. No usa IA, scraping, OCR, APIs externas ni cambios de schema.

```text
Documento
  -> Parser
  -> Fragmentos
  -> Knowledge Engine
  -> Lectura Documentada
  -> Publicacion
```

## Flujo

1. `Documento`: entrada estructurada local, liviana y versionable.
2. `Parser`: en V1 el parser es el contrato estructurado existente (`OfficialDocument` con secciones). No extrae PDFs ni hace OCR.
3. `Fragmentos`: cada seccion se normaliza como pagina, fragmento, ancla y cita breve.
4. `Knowledge`: Knowledge Engine conserva su responsabilidad: organizar resumen, puntos, preguntas, claims y evidencia.
5. `Experience`: `generate_document_experience(document)` empaqueta todo en `DocumentExperience`.
6. `UI`: Reflex solo renderiza el contrato publicado; no construye preguntas, claims ni contextos.
7. `Publicacion`: `publish_document_experience(document_id)` produce el objeto completo navegable. No genera HTML todavia.

## Contrato unico

`DocumentExperience` contiene:

- `document`
- `pages`
- `fragments`
- `references`
- `questions`
- `key_points`
- `claims`
- `citizen_summary`
- `connections`
- `related_expediente`
- `related_tracking`
- `related_report`
- `metrics`
- `fragment_contexts`
- `selected_context`

Este contrato es estable para la UI y para futuras superficies de DatosEnOrden Studio.

## Multiples documentos

La UI no asume un documento unico. El servicio puede publicar cualquier `document_id` disponible en el catalogo estructurado:

```python
publish_document_experience("knowledge-doc-arauco-hospital-demo-2026")
```

Tambien puede recibir un `OfficialDocument` ya construido:

```python
generate_document_experience(document)
```

## Catalogo

El catalogo liviano vive en `documents/`:

```text
documents/
  catalog.json
  document_a/
  document_b/
  document_c/
```

En V1 solo `document_a` apunta a un documento local real de muestra. `document_b` y `document_c` quedan reservados para demostrar que la arquitectura no depende de codigo por documento.

## Limites

- No IA.
- No scraping.
- No OCR.
- No APIs externas.
- No schema nuevo.
- No GraphLoader.
- No Entity Resolution.
- No paginas publicas nuevas.

## Independencia

El modulo `src/datosenorden/studio/document_reading_pipeline.py` no depende de base de datos ni de servicios web. Consume documentos estructurados y el contrato del Knowledge Engine, y devuelve una estructura serializable lista para UI o publicacion futura.
