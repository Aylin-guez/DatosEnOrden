# DEO Ciudadano - Document Reading Extraction - 2026-07-24

## Resumen

Este sprint ejecuta la extraccion productiva segura de Document Reading sin mover Public Record y sin implementar Laboratory.

Document Reading deja de vivir como campos y handlers dentro de `AppState` y pasa a `reflex_app/features/document_reading/state.py` como `DocumentReadingState`. La capa de aplicacion publica queda en `src/datosenorden/application/document_reading/` y contiene solo orquestacion especifica del producto, view-models, helpers de presentacion y puertos publicos.

## Bloques Implementados

- Knowledge: `load_knowledge`, payload del documento, resumen, preguntas, claims, evidencia y errores.
- Lectura documental: documento publicado, fallback textual, parrafos y fuente de lectura.
- Fragment navigation: seleccion por pagina o fragmento, estado activo y contexto seleccionado.
- PDF highlighting: target honesto sin coordenadas inventadas.
- Share links: URL publica, X, WhatsApp, LinkedIn y script de copia.
- Metadata de presentacion: fechas, labels, cobertura y referencias.
- `/topic`: migrado al nuevo State con adaptador explicito hacia `get_investigation` y `build_state_graph`.

## Ownership Publico/Privado

| Bloque | Ownership | Destino |
| --- | --- | --- |
| UI Reflex y rutas documentales | PUBLIC_PRODUCT_UI | `reflex_app/features/document_reading/pages.py` + vistas existentes |
| State Reflex documental | PUBLIC_PRODUCT_UI | `reflex_app/features/document_reading/state.py` |
| Payload Knowledge | PUBLIC_PRODUCT_APPLICATION | `src/datosenorden/application/document_reading/service.py` |
| Contexto de fragmentos/PDF/share | PUBLIC_PRODUCT_APPLICATION | `src/datosenorden/application/document_reading/context.py` |
| Puertos | PUBLIC_CONTRACT | `src/datosenorden/application/document_reading/ports.py` |
| `get_investigation` y `build_state_graph` usados por `/topic` | CROSS_FEATURE adapter | `DocumentReadingState.load_topic` |
| Engines, OCR, ranking, analisis de grafos reusable | CORE_PRIVATE | No se implementan en el repo publico |

No se encontro ni se movio `DUPLICATED_PRIVATE_LOGIC`.

## Campos Antes y Despues

- Antes: `AppState` tenia 161 vars totales, incluyendo 49 `knowledge_*`, 24 `topic_*` y `topic_view_mode`.
- Despues: `AppState` queda con 88 vars.
- `DocumentReadingState` queda con 75 vars.
- Los campos `knowledge_*` y `topic_*` ya no existen en `AppState`.

## Metodos Antes y Despues

- Antes: `AppState` tenia 16 event handlers.
- Despues: `AppState` queda con 11 event handlers.
- `DocumentReadingState` expone 6 event handlers:
  - `set_topic_view_mode`
  - `load_knowledge`
  - `load_topic`
  - `open_knowledge_investigation`
  - `select_document_anchor`
  - `setvar`

## Paginas Migradas

Las rutas mantienen los mismos paths y metadata:

- `/topic`
- `/knowledge`
- `/official-document`
- `/library`

El registro `@rx.page` vive en `reflex_app/features/document_reading/pages.py`. Las vistas visuales reutilizan componentes existentes del monolito como compatibilidad temporal para no cambiar copy, estilos ni layout.

## Servicios Creados

- `src/datosenorden/application/document_reading/context.py`
  - Fragment order.
  - Fragment href.
  - PDF href.
  - Selected fragment payload.
  - Share links.
  - Lectura segura de payloads JSON locales.

- `src/datosenorden/application/document_reading/service.py`
  - `build_knowledge_payload`.
  - `knowledge_error_payload`.
  - `select_document_payload`.
  - `build_topic_payload`.
  - Helpers de presentacion de `/topic`.

## Adaptadores Temporales

- `/topic` permanece como cruce Document Reading -> Public Record porque necesita `get_investigation(TOPIC_BUDGET_2013_TARGET)`.
- `/topic` tambien consulta `build_state_graph(TOPIC_BUDGET_2013_TARGET)` para filas de presentacion del grafo.
- Las funciones visuales de Document Reading siguen ubicadas en `reflex_app/reflex_app.py` y consumen `DocumentReadingState`. Condicion de eliminacion: mover componentes documentales a `reflex_app/features/document_reading/components.py` sin cambiar DOM ni copy.

## Situacion Final de /topic

`/topic` esta registrado desde la feature y su lifecycle usa `DocumentReadingState.load_topic`. No se movio Public Record: `load_investigation`, expediente, timeline y graph de expediente permanecen en `AppState`.

## Dependencias Restantes

- `DocumentReadingState.load_topic` -> `get_investigation`.
- `DocumentReadingState.load_topic` -> `build_state_graph`.
- Componentes visuales documentales -> `DocumentReadingState`.
- Feature pages -> vistas legacy del monolito por compatibilidad temporal.

## Ciclos

Se mantiene un ciclo temporal ya conocido para registrar paginas desde feature y reutilizar vistas legacy: `reflex_app.reflex_app` importa `features.document_reading.pages`, y `pages.py` importa vistas ya definidas en `reflex_app.reflex_app`. No introduce nueva dependencia privada ni Core/Bricks. Debe eliminarse al mover componentes/vistas al paquete.

## AppState y reflex_app.py

- AppState antes: 773 lineas aproximadas, 161 vars, 16 handlers.
- AppState despues: 461 lineas, 88 vars, 11 handlers.
- `reflex_app.py` antes: 6933 lineas aproximadas.
- `reflex_app.py` despues: 6575 lineas.

## Suite

Guardrails agregados:

- `tests/test_reflex_document_reading_extraction.py`
- `tests/test_public_private_document_reading_boundary.py`

Tests actualizados:

- Caracterizacion de rutas.
- Caracterizacion de servicios de State.
- Caracterizacion de document search.
- Guardrails de Search y batch low/medium.

Resultado final de suite completa: 677 passed, 1 warning externo de `fastapi.testclient`/Starlette.

## Deuda Pendiente

- Mover componentes visuales documentales a `reflex_app/features/document_reading/components.py`.
- Eliminar ciclo temporal de paginas cuando las vistas dejen el monolito.
- Separar el adaptador de `/topic` hacia Public Record cuando se extraiga Public Record.
- Retirar helpers documentales legacy que quedaron en `reflex_app.py` solo por compatibilidad con tests anteriores.

## Siguiente Sprint Recomendado

Extraer Public Record en un sprint propio:

1. `load_investigation`.
2. estado de expediente, timeline y graph.
3. adaptadores desde Tracking, Reports, Search y Document Reading.
4. eliminacion del cruce temporal de `/topic`.

Public Record permanece en AppState en este sprint. Laboratory no fue implementado.
