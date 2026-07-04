# Sprint UX: Una sola lectura

## Alcance

Este sprint rediseña la experiencia publica reutilizando componentes y servicios existentes. No agrega motores, adapters, IA, schema, PostgreSQL, Reading Pipeline, Knowledge Engine, Publication Engine, importaciones legislativas ni GraphLoader.

## Decision principal

`/topic` pasa a ser la lectura canonica. La persona debe poder entender el tema completo sin saltar entre paginas. Las rutas avanzadas permanecen, pero dejan de ser pasos obligatorios del recorrido.

## Estructura implementada en `/topic`

1. Documento oficial visible desde el primer viewport.
2. Cobertura documental cerca del inicio.
3. Que propone.
4. Que cambia.
5. Que NO cambia.
6. Que sigue.
7. Evidencia.
8. Expediente resumido.
9. Historia del tema.
10. Seguimiento resumido.
11. Mas lecturas documentadas.
12. Documento original.
13. Compartir.
14. Continuar: suscripcion, sugerir tema y apoyo discreto.

## Documento oficial como protagonista

Desktop usa dos columnas:

- Izquierda: visor de documento sticky reutilizando `official_document_viewer()`.
- Derecha: lectura editorial del tema.

Las tarjetas que citan evidencia usan `reference_button()` y `AppState.select_document_anchor()`, de modo que la seleccion de evidencia actualiza el fragmento activo del documento sin abrir otra pagina.

## Rutas que permanecen como vistas avanzadas

- `/official-document`: visor avanzado/permalink de documento y fragmentos.
- `/investigation`: expediente completo.
- `/tracking`: historia completa de seguimiento.
- `/reports`: coleccion avanzada de reportes.
- `/library`: catalogo avanzado.

## Navegacion principal

El navbar conserva las rutas publicas centrales:

- Inicio
- Tema
- Descubre
- Expediente
- Documento Oficial
- Fuentes
- Proyecto

`Reportes`, `Biblioteca` y `Seguimiento` salen del menu superior porque ahora son secciones integradas o vistas avanzadas, no pasos principales.

## Componentes reutilizados

- `official_document_viewer()`
- `reading_context_bar()`
- `reference_button()`
- `tracking_event_card()`
- `citizen_report_section_card()`
- `topic_evidence_card()`
- `topic_summary_card()`
- `summary_metric_card()`

## Datos reutilizados

`AppState.load_topic()` sigue usando `load_knowledge()` y `get_investigation()` como base. Tambien reutiliza `get_tracking_demo()` y `get_citizen_report_demo()` para integrar seguimiento y reporte dentro de la lectura, sin exportar ni generar contenido nuevo.

## Secciones preparadas sin backend

- Compartir: enlace, imagen, carrusel y PDF aparecen como espacios preparados.
- Suscribirse: correo y seguir proyecto quedan deshabilitados.
- Apoyar DatosEnOrden: seccion discreta, no protagonista.
- Sugerir proximo tema: entrada visual deshabilitada.