# Platform Publication Engine V1

## Responsabilidad

El Platform Publication Engine decide que productos publicos deben actualizarse cuando cambia una fuente documental. No genera conocimiento, no analiza documentos y no reemplaza motores existentes.

```text
Documento
  -> Reading Pipeline
  -> Knowledge Engine
  -> Publication Engine
  -> Biblioteca
  -> Reporte ciudadano
  -> Expediente
  -> Seguimiento
  -> Buscador
  -> Documento Oficial
  -> Noticias / Lecturas Documentadas
```

## Que publica

El motor produce un `PublicationPlan` y una lista de artefactos publicables. En V1 los destinos activos son:

- Biblioteca
- Reporte ciudadano
- Expediente
- Seguimiento
- Buscador
- Documento Oficial

Noticias queda planificado pero apagado por defecto.

## Que NO publica

No hace estas tareas:

- No crea conocimiento.
- No resume documentos.
- No interpreta evidencia.
- No ejecuta IA.
- No hace scraping.
- No llama APIs externas.
- No cambia schema.
- No toca GraphLoader.
- No toca Entity Resolution.
- No crea rutas publicas nuevas.

## Conexion con Reading Pipeline

`publish_document(document)` usa el Reading Pipeline para obtener la experiencia documental navegable. Esa experiencia ya viene con paginas, fragmentos, referencias, preguntas, puntos importantes, claims, resumen ciudadano, conexiones y contextos de lectura.

El Publication Engine no modifica esa experiencia; solo decide que superficies deben recibirla.

## Conexion con Knowledge Engine

Knowledge Engine conserva su responsabilidad: organizar conocimiento desde documentos estructurados. El Publication Engine consume el resultado ya preparado por el Reading Pipeline, que a su vez usa Knowledge Engine.

La direccion de dependencia es:

```text
Knowledge Engine -> Reading Pipeline -> Publication Engine -> UI/Productos
```

Los motores inferiores no conocen al Publication Engine.

## Contratos principales

- `PublicationPlan`: banderas de publicacion por superficie.
- `PublicationArtifact`: destino, `document_id` y payload para una superficie.
- `PublicationResult`: plan completo mas artefactos activos.

Funciones publicas:

- `build_publication_plan(document)`
- `publish_document(document)`
- `publish_library(plan, experience)`
- `publish_report(plan, experience)`
- `publish_investigation(plan, experience)`
- `publish_tracking(plan, experience)`
- `publish_search(plan, experience)`
- `publish_document_view(plan, experience)`
- `publish_news(plan, experience)`

## Preparacion futura

El plan ya deja espacio para activar nuevos productos sin modificar Reading Pipeline ni Knowledge Engine:

- Noticias / Lecturas documentadas
- Dashboards ciudadanos
- Exportaciones PDF
- API publica
- RSS
- Newsletter
- Dataset publico
- Widgets embebibles

Para agregar un producto futuro se debe sumar una bandera al plan, un publicador de artefacto y una superficie consumidora. La generacion de conocimiento permanece abajo.
