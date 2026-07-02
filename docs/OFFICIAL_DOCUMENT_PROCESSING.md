# Official Document Processing

Fase: First Official Document Processing.

Este flujo convierte un documento oficial descargado a una estructura uniforme en `processing/`. No resume, no interpreta, no responde preguntas y no ejecuta Reading Pipeline, Knowledge Engine, Publication Engine ni Actualidad Engine.

## Flujo

```text
incoming
  |
  v
validacion
  |
  v
extraccion de texto
  |
  v
deteccion de paginas si aplica
  |
  v
fragmentacion
  |
  v
generacion de metadata
  |
  v
processing
  |
  v
Reading Pipeline
```

## Entrada

Documento usado en la primera ejecucion:

```text
data/official_documents/incoming/senado-docto-9000-mensaje_mocion/document.doc
```

Metadata de entrada:

```text
data/official_documents/incoming/senado-docto-9000-mensaje_mocion/metadata.json
```

## Salida

```text
data/official_documents/processing/senado-docto-9000-mensaje_mocion/
  original.doc
  extracted.txt
  document.json
  fragments.json
  metadata.json
```

`original.doc` es una copia del documento oficial descargado. `extracted.txt` contiene el texto extraido fielmente. `document.json` contiene el contrato normalizado independiente del formato original. `fragments.json` contiene fragmentos ordenados. `metadata.json` conserva la metadata oficial y agrega estado de procesamiento.

## Contrato document.json

Campos principales:

```text
document_id
source
title
language
mime_type
total_fragments
total_characters
pages_detected
extraction_date
original_filename
extracted_text_filename
fragments_filename
```

## Contrato fragments.json

Cada fragmento incluye:

```text
fragment_id
order
text
page
heading
character_count
```

Si el formato original no entrega paginas identificables, `page` queda en `null`. No se inventan paginas.

## Politica

- No OCR.
- No IA.
- No resumen.
- No clasificacion editorial.
- No publicacion.
- No ejecucion automatica del Reading Pipeline.

## Siguiente paso

Despues de revision manual, el Reading Pipeline deberia consumir `document.json`, `fragments.json`, `metadata.json` y `extracted.txt` como documento normalizado. Ese paso debe ser explicito y separado.
