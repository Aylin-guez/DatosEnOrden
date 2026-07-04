# First Real Document Reading

Fase: First Real Documented Reading V1.

Esta fase ejecuta por primera vez el flujo completo con un documento oficial real ya descargado y procesado. No usa IA, no vuelve a leer el `.doc`, no crea motores nuevos y no modifica conceptualmente Reading Pipeline, Knowledge Engine ni Publication Engine.

## Flujo

```text
Documento oficial
  |
  v
Processing
  |
  v
Reading Pipeline
  |
  v
Knowledge
  |
  v
Publication
  |
  v
Official Document
```

## Entrada

```text
data/official_documents/processing/senado-docto-9000-mensaje_mocion/
  document.json
  fragments.json
  metadata.json
  extracted.txt
```

El script de lectura no lee `original.doc`.

## Salida

```text
data/official_documents/published/senado-docto-9000-mensaje_mocion/
  reading.json
  knowledge.json
  publication.json
```

`reading.json` conserva documento, fragmentos, orden y referencias trazables.

`knowledge.json` es la salida del Knowledge Engine existente sobre un `OfficialDocument` construido desde los fragmentos procesados.

`publication.json` contiene los artefactos de publicacion, incluyendo `document_view`, `citizen_summary`, `references` y `evidence`.

## Politica

- No OCR.
- No IA.
- No inferencias editoriales nuevas.
- Toda referencia conserva `fragment_id`.
- Toda evidencia sale de fragmentos existentes.
- Si el documento procesado no tiene paginas reales, `reading.json` conserva `page: null`.

## Limitacion conocida

El Knowledge Engine existente todavia contiene textos genericos de demo en algunas salidas. Esta fase no modifica ese motor; por eso `knowledge.json` y `publication.json` explicitan la limitacion mientras preservan trazabilidad real al documento oficial.

## Visualizacion

`/official-document` carga `publication.json` cuando existe. Si no existe, mantiene el demo anterior.
