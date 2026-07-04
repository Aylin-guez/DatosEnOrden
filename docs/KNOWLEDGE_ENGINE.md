# Knowledge Engine

Knowledge Engine es una primera version local y read-only para transformar documentos oficiales o registros publicos de prueba en conocimiento estructurado reutilizable por expedientes, seguimiento y reportes ciudadanos.

## Alcance

- Carga JSON local desde `data/sample/official_documents_sample.json`.
- Normaliza metadata ya presente en el archivo.
- Genera resumen ciudadano rule-based.
- Genera puntos importantes por seccion.
- Genera preguntas ciudadanas sugeridas.
- Genera claims verificables enlazados a evidencia.
- Conecta cada documento con expediente, seguimiento, reporte ciudadano y fuente publica.
- Exporta un HTML local de demostracion.

No implementa LLM, scraping, APIs externas, suscripciones, ingesta de PDFs ni almacenamiento pesado.

## Modelo

- `OfficialDocument`: metadata del documento, fuente, fecha, URL local, conexiones y secciones.
- `DocumentSection`: seccion textual liviana usada para resumen, puntos y evidencia.
- `KeyPoint`: punto importante derivado de una seccion.
- `CitizenQuestion`: pregunta sugerida para orientar revision ciudadana.
- `KnowledgeClaim`: afirmacion verificable con evidencia asociada y nota de revision.
- `EvidenceAnchor`: ancla a documento, seccion, fuente, URL y excerpt.
- `KnowledgeDigest`: paquete reutilizable por UI, servicios, reportes y exportacion.

## Caso Demo

El caso local esta relacionado con:

`SERVICIO DE SALUD ARAUCO HOSPITAL DE ARAUCO`

El documento demo esta marcado como:

- `LOCAL_TEST_DATA`
- `NOT_OFFICIAL_DATA`

Esto evita confundir la muestra con datos oficiales reales.

## Tono y Seguridad

El motor mantiene lenguaje neutral:

- No afirma irregularidad.
- No infiere culpabilidad.
- No calcula scoring de riesgo.
- Cada claim incluye una nota para revisar la evidencia original.

## Servicios

`src/datosenorden/web/app_services.py` expone:

- `get_knowledge_demo()`
- `get_knowledge_digest(document_id)`
- `get_knowledge_documents()`

Todas las respuestas son JSON-safe.

## UI

La ruta Reflex `/knowledge` muestra:

- documentos locales disponibles
- resumen ciudadano
- puntos importantes
- preguntas sugeridas
- claims verificables
- conexiones reutilizables
- evidencia asociada

## Scripts

```powershell
python scripts/knowledge_demo_summary.py
python scripts/export_knowledge_demo_report.py
```

El exportador escribe `reports/knowledge_demo_arauco.html`.
