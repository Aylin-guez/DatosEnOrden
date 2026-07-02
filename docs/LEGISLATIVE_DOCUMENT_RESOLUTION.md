# Legislative Document Resolution

Fase: First Automated Document Resolution V1.

Este flujo descubre y descarga documentos oficiales asociados a un boletin legislativo. No genera Lecturas Documentadas y no ejecuta Reading Pipeline, Knowledge Engine, Publication Engine, Actualidad Engine ni GraphLoader.

## Flujo

```text
Boletin
  |
  v
Resolver
  |
  v
Catalogo de documentos
  |
  v
Seleccion
  |
  v
Descarga
  |
  v
Workflow documental
```

## Componentes

```text
src/datosenorden/adapters/legislature/document_client.py
src/datosenorden/adapters/legislature/document_resolver.py
src/datosenorden/adapters/legislature/document_models.py
```

`document_client.py` habla solo con fuentes oficiales. Para V1 consulta Senado: `tramitacion.senado.cl` para el indice del proyecto y `www.senado.cl/appsenado` para `getDocto`.

`document_resolver.py` recibe un boletin completo, consulta la fuente oficial, valida que el XML devuelva el mismo boletin completo y produce un `LegislativeDocumentCatalog`.

`document_models.py` contiene modelos propios del adapter documental. No depende de Platform Core ni de engines.

## Descubrimiento

Comando:

```text
python scripts/discover_legislative_documents.py 8575-05
```

Salida esperada:

```text
Boletin
Documentos encontrados
Tipo
URL oficial
Formato
Estado
```

El comando no descarga documentos. Solo lista candidatos documentales.

## Descarga

Comando:

```text
python scripts/download_legislative_document.py 8575-05 --type mensaje_mocion
```

Destino:

```text
data/official_documents/incoming/<document_id>/
  document.<ext>
  metadata.json
```

La metadata generada conserva los campos requeridos por el workflow documental:

```text
id
title
organization
source_url
publication_date
retrieval_date
status
document_type
language
version
```

Tambien agrega metadata legislativa:

```text
bill_id
bulletin_id
project_url
source_document_id
source_document_kind
original_format
content_type
content_size
content_sha256
file_name
```

## Identificadores

El identificador interno del boletin conserva la forma completa:

```text
cl-congreso-boletin-8575-05
```

Para Senado, V1 consulta usando el correlativo antes del guion cuando corresponde:

```text
8575-05 -> tramitacion.php?boletin=8575
```

La respuesta oficial debe contener:

```text
<boletin>8575-05</boletin>
```

Si no coincide, el resolver falla.

## Politica V1

- No hardcodear boletines.
- No descargar todos los documentos por defecto.
- No hacer crawling.
- No publicar.
- No ejecutar engines.
- No pasar automaticamente al Reading Pipeline.

## Siguiente paso

La siguiente implementacion deberia agregar revision manual del documento descargado y validacion de metadata antes de moverlo desde `incoming` hacia `processing`.
