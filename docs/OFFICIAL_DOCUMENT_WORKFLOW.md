# Official Document Workflow

## Objetivo

Preparar DatosEnOrden para recibir el primer documento oficial real sin IA, scraping, OCR, APIs externas, cambios de schema, GraphLoader ni Entity Resolution.

## Estructura

```text
data/official_documents/
  incoming/
  processing/
  published/
  archived/
  metadata.schema.json
```

## Contrato de metadata

Cada documento real debe tener metadata JSON independiente del archivo original:

```json
{
  "id": "...",
  "title": "...",
  "organization": "...",
  "source_url": "https://...",
  "publication_date": "YYYY-MM-DD",
  "retrieval_date": "YYYY-MM-DD",
  "status": "incoming",
  "document_type": "...",
  "language": "es",
  "version": 1
}
```

## Flujo manual inicial

1. Descargar o guardar manualmente el documento oficial desde su fuente original.
2. Crear `metadata.json` con el contrato requerido.
3. Ejecutar validacion manual:

```powershell
python scripts/import_official_document.py documento.pdf metadata.json
```

4. Si la validacion pasa, revisar el par documento/metadata en `incoming`.
5. Pasar manualmente a `processing` para extraccion controlada de texto.
6. Dividir texto en paginas, secciones y fragmentos.
7. Crear anclas y referencias.
8. Preparar resumen ciudadano, preguntas y puntos importantes.
9. Publicar como Lectura Documentada en `published`.
10. Archivar versiones reemplazadas o retiradas en `archived`.

## Validaciones del import manual

El script verifica:

- existe metadata
- existe documento
- metadata valida
- `id` unico entre carpetas del flujo
- fechas en formato `YYYY-MM-DD`
- organizacion presente
- URL oficial `http(s)`
- version entera mayor o igual a 1
- idioma `es` para el primer flujo

## Restricciones

- No IA.
- No scraping.
- No OCR.
- No GraphLoader.
- No Entity Resolution.
- No mover archivos automaticamente todavia.
- No publicar documentos reales sin revision manual.
