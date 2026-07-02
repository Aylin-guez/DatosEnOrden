# Document Experience V1

## Objetivo

DatosEnOrden debe explicar documentos oficiales sin romper trazabilidad. Toda afirmacion importante mostrada al ciudadano debe conservar una referencia navegable al documento, pagina, seccion, fragmento y cita breve que la respalda.

Esta fase no agrega scraping, IA, extraccion PDF ni almacenamiento de archivos pesados. Usa un documento demo local y prepara el contrato para conectar extractores reales mas adelante.

## Flujo de informacion

```text
Documento
  -> Knowledge
  -> Evidence
  -> Citizen Summary
  -> Viewer
  -> Referencias
```

1. `Documento`: metadata liviana y secciones locales. En V1 vive en `data/sample/official_documents_sample.json`.
2. `Knowledge`: `src/datosenorden/maintenance/knowledge_engine.py` organiza el documento y genera una lectura rule-based desde campos existentes.
3. `Evidence`: cada punto importante, pregunta o afirmacion se enlaza a evidencia con documento, pagina, seccion, fragmento y cita breve.
4. `Citizen Summary`: el resumen ciudadano acompana al documento; no reemplaza el texto original.
5. `Viewer`: el componente Reflex `official_document_viewer(...)` muestra paginas y fragmentos, y permite resaltar el ancla seleccionada.
6. `Referencias`: resumen -> documento y documento -> resumen usan los mismos IDs de fragmento y cita.

## Contrato preparado para PDFs reales

Las interfaces principales son:

- `DocumentReference`: identidad del documento, fuente, tipo, fecha, URL/ubicacion y estado.
- `PageReference`: pagina navegable dentro de un documento.
- `DocumentFragment`: texto extraido o declarado para una pagina/seccion.
- `FragmentAnchor`: ancla estable para abrir un fragmento especifico.
- `Citation`: cita breve usada por una afirmacion ciudadana.
- `EvidenceAnchor`: referencia enriquecida visible en UI y reportes.

Cuando exista extraccion PDF, el extractor debe poblar esas estructuras sin cambiar la responsabilidad de Knowledge Engine.

## Navegacion

Desde el resumen ciudadano:

```text
Punto importante / Pregunta / Afirmacion
  -> referencia visible: Pagina N
  -> select_document_anchor(page, fragment_id)
  -> visor resalta el fragmento
```

Desde el documento:

```text
Fragmento
  -> Este parrafo respalda
  -> Punto importante / Pregunta / Resumen ciudadano
```

El modelo evita duplicar documentos: las afirmaciones solo guardan IDs, pagina, fragmento y cita breve.

## UI V2: document-first

La seccion visible `/official-document`, rotulada como `Documento Oficial`, funciona como experiencia de lectura. El documento domina el ancho y la guia de lectura acompana en una columna lateral.

La pantalla muestra:

- titulo editorial del documento
- fuente/organismo
- fecha
- estado
- referencia local
- barra de estado de lectura
- paginas y fragmentos del documento
- resumen relacionado al fragmento seleccionado
- pregunta relacionada
- claim relacionado
- evidencia utilizada
- enlaces a Expediente, Seguimiento, Reporte ciudadano y Biblioteca

La navegacion ocurre sin recargar la pagina: seleccionar una pregunta, punto, claim, referencia, pagina o fragmento actualiza `page`, `fragment_id`, resaltado y panel lateral.

## Preparacion para Document Experience Engine

No se implementa un motor nuevo en esta fase. La organizacion queda preparada para que mas adelante exista un componente reutilizable llamado `Document Experience Engine`.

El limite propuesto es:

- Knowledge Engine sigue generando y organizando conocimiento.
- Evidence conserva referencias y citas breves.
- La UI de documento consume estructuras ya normalizadas: paginas, fragmentos, anclas, citas y conexiones.
- Un futuro Document Experience Engine podria empaquetar seleccion, contexto lateral, metricas de lectura y navegacion entre fragmentos para reutilizarlo en DatosEnOrden Studio.

La fase V2 solo desacopla la presentacion: la experiencia de lectura depende de `document_id`, `page`, `fragment_id`, `citation_id` y listas de relaciones ya calculadas, sin schema nuevo.

## Limites deliberados

- No scraping.
- No IA.
- No PDFs oficiales reales en esta fase.
- No archivos pesados.
- No cambios de responsabilidad en Knowledge Engine.
- No inferencias de irregularidad, riesgo o causalidad.

## Reutilizacion futura

El mismo modelo de referencias podra alimentar ThirdLifeEngine u otros canales sin duplicar evidencia:

- reportes ciudadanos
- newsletters
- publicaciones
- comparativas
- contenido educativo

La condicion es que cada pieza reutilizada mantenga `document_id`, `page`, `section_id`, `fragment_id` y `citation_id`.
