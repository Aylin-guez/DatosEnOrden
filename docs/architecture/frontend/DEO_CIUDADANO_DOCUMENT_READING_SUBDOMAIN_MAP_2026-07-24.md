# DEO Ciudadano - Document Reading Subdomain Map

Fecha: 2026-07-24

## Alcance

Esta fase no extrae Document Reading completo. Primero separa responsabilidades reales para definir un orden seguro de extraccion posterior.

Restricciones cumplidas:

- No se mueve Public Record.
- No se implementa Laboratory.
- No se divide shell.
- No se cambian rutas, metadata, copy ni comportamiento.
- No se agregan `@rx.page`.

## Estado Actual

Medicion posterior a Search Extraction:

- `reflex_app/reflex_app.py`: 6.933 lineas.
- `AppState`: lineas 1252-2024, 773 lineas.
- `AppState.vars`: 161.
- `AppState.event_handlers`: 16.
- `AppState` metodos: 17.
- Rutas registradas: 19.

Document Reading dentro de `AppState`:

- Campos `knowledge_*`: 49.
- Campos `topic_*`: 24.
- Metodos/handlers: 7.

Metodos:

- `set_topic_view_mode` (1425-1426)
- `load_knowledge` (1491-1609)
- `load_topic` (1611-1678)
- `open_knowledge_investigation` (1683-1684)
- `select_document_anchor` (1686-1694)
- `_set_document_reading_context` (1696-1716)
- `_set_document_share_links` (1718-1728)

Rutas consumidoras:

- `/topic`
- `/knowledge`
- `/official-document`
- `/library`

## Mapa De Subdominios

| Subdominio | Campos/funciones principales | Tipo | Destino futuro | Acoplamiento |
| --- | --- | --- | --- | --- |
| Knowledge | `knowledge_documents`, `knowledge_document`, `knowledge_title`, `knowledge_summary`, `knowledge_key_points`, `knowledge_questions`, `knowledge_claims`, `knowledge_evidence`, `knowledge_notice`, `knowledge_error`, `load_knowledge` | Reflex State + Application Service | `features/document_reading/state.py` + `datosenorden/application/document_reading/service.py` | Alto |
| PDF Reading | `knowledge_document_has_pdf`, `knowledge_document_pdf_path`, `knowledge_document_pdf_href`, `knowledge_document_pdf_page_href`, `_document_pdf_href`, `official_document_pdf_viewer`, `topic_pdf_document_viewer` | State + UI + pure helper | helpers/service primero; UI despues | Medio |
| Fragment Navigation | `knowledge_fragment_contexts`, `knowledge_selected_page`, `knowledge_selected_fragment_id`, `select_document_anchor`, `_set_document_reading_context`, `document_page_button`, `document_fragment_card` | Reflex State + UI | extraer despues de helpers puros | Alto |
| Highlighting | `knowledge_pdf_highlight_target`, `knowledge_selected_excerpt`, `_pdf_highlight_target`, `PDFHighlightTarget` | pure helper + State field | service/helper reutilizable primero | Bajo/medio |
| Citation | `knowledge_citations`, `knowledge_selected_reference_label`, `knowledge_share_*`, `_set_document_share_links`, `_official_document_fragment_href` | State + pure link builder | service/helper reutilizable | Medio |
| Metadata | `knowledge_document_source_path`, `knowledge_document_source_is_fallback`, `topic_status`, `topic_updated_at`, `topic_original_url`, `topic_official_document` | State + service formatting | service puro | Medio |
| Document Navigation | `open_knowledge_investigation`, `knowledge_expediente_target`, links a `/library`, `/official-document`, `/topic` | State adapter + routing | adapter fino futuro | Alto por Public Record |
| Reading Progress | `knowledge_fragment_count`, `knowledge_total_fragment_count`, `knowledge_question_count`, `knowledge_claim_count`, `knowledge_reference_count`, `knowledge_coverage_text`, `knowledge_reference_text`, `_topic_read_time` | State + pure formatting | service puro primero | Bajo |
| Related Documents | `knowledge_documents`, `knowledge_document_card`, `/knowledge`, `/library` | State + UI | componentes feature despues | Medio |
| Evidence Candidates | `knowledge_evidence`, `knowledge_selected_evidence`, `topic_evidence_rows`, `_topic_evidence_rows`, `guide_evidence`, `topic_evidence_card` | service formatting + UI + State | service puro primero | Medio |
| Timeline | `topic_timeline_rows`, `topic_tracking_summary`, `topic_vote_summary`, `topic_vote_count`, `_topic_timeline_rows`, `_topic_tracking_summary`, `_topic_vote_summary` | service formatting + State | application service | Alto por `get_investigation` |
| Graph | `topic_state_graph_rows`, `_format_state_graph_topic_rows`, `build_state_graph`, topic system mode | service formatting + State | application service despues | Alto por StateGraph/Public Record |

## Dependencias

```text
/topic
v
load_topic
v
load_knowledge
v
get_knowledge_documents + get_knowledge_demo
v
fragment/PDF/context/share state

load_topic
v
get_investigation(TOPIC_BUDGET_2013_TARGET)
v
topic metadata + timeline + evidence candidates

load_topic
v
build_state_graph(TOPIC_BUDGET_2013_TARGET)
v
topic graph rows

/official-document, /library, /knowledge
v
load_knowledge
v
PDF viewer + fragments + citations + related document cards

open_knowledge_investigation
v
/investigation?id=...
v
Public Record (no mover en esta fase)
```

## UI Simple Vs State Vs Application Services

### Componentes UI simples

Se pueden mover despues de estabilizar imports de shell:

- `document_metric_panel`
- `document_fragment_card`
- `document_page_button`
- `official_document_pdf_viewer`
- `official_document_viewer`
- `document_fragment_panel`
- `knowledge_document_card`
- `knowledge_key_point_card`
- `knowledge_question_card`
- `knowledge_claim_card`
- `knowledge_connection_card`
- `topic_mode_button`
- `topic_mode_selector`
- `topic_reading_mode`
- `topic_system_mode`
- `topic_evidence_mode`
- `topic_mode_body`

Riesgo: muchos componentes leen `AppState` directamente, por lo que moverlos antes del state nuevo solo traslada el ciclo.

### Pertenece a Reflex State

Debe vivir junto porque representa interaccion observable:

- seleccion de fragmento;
- pagina seleccionada;
- modo de lectura;
- contexto seleccionado;
- errores de carga;
- href actual del PDF;
- share links;
- datos cargados por ruta.

### Application Services reutilizables

Candidatos para extraer antes de un `DocumentReadingState`:

- carga de fragmentos y fallback;
- conversion de fragmentos a parrafos;
- calculo de pagina por fragmento;
- target de highlight;
- share links;
- filas de evidencia;
- filas de timeline;
- filas de estado/hero;
- resumen de votos;
- metadata del documento oficial.

## Orden Recomendado De Extraccion

1. **Helpers puros de documento**
   Mover `_document_blocks`, `_looks_like_document_heading`, `_document_paragraphs_from_fragments`, `_document_pdf_href`, `_fragment_order_page`, `_pdf_highlight_target` a una frontera reusable. Riesgo bajo. No requiere Reflex.

2. **Application service de Knowledge payload**
   Crear un servicio que reciba `get_knowledge_demo()` y `get_knowledge_documents()` y devuelva un payload ya formateado para state. Riesgo medio. Mantener `AppState.load_knowledge` como consumidor temporal.

3. **Application service de selected fragment context**
   Extraer la logica de `_set_document_reading_context` como funcion pura que recibe contexts, fragment/page y devuelve campos seleccionados. Riesgo medio por router y PDF href.

4. **Application service de topic summary**
   Extraer `_topic_*` que no llama servicios. Riesgo medio por mezcla de Knowledge e Investigation.

5. **DocumentReadingState fino**
   Crear state propio solo cuando `load_knowledge` ya delegue en servicios puros. Migrar `/knowledge`, `/official-document`, `/library` primero.

6. **/topic como ultimo paso de Document Reading**
   `/topic` debe moverse despues porque `load_topic` combina Knowledge con `get_investigation` y `build_state_graph`. No mover Public Record.

7. **Componentes UI**
   Mover componentes a `features/document_reading/components.py` despues de que lean `DocumentReadingState`; antes seria una mudanza con ciclos.

## Riesgos

- `load_topic` mezcla Document Reading con `get_investigation`, timeline y StateGraph.
- `open_knowledge_investigation` cruza hacia Public Record por `/investigation`.
- `select_document_anchor` depende de vars Reflex y actualiza varios campos sincronizados.
- El visor PDF usa hrefs, fragmentos y selected state al mismo tiempo.
- `shell` y varias paginas siguen en el monolito, lo que mantiene ciclos si se mueven componentes prematuramente.

## Elementos Que No Deben Moverse Todavia

- `load_topic` completo.
- `load_knowledge` completo.
- `select_document_anchor` completo.
- `open_knowledge_investigation` hasta definir adapter de navegacion.
- `build_state_graph` y formato de grafo si implica Public Record.
- `get_investigation` y cualquier contrato de Public Record.
- Visor PDF completo si aun lee `AppState`.

## Decision De Esta Fase

No se reducen lineas de `reflex_app.py` en esta fase. La salida correcta es el mapa de responsabilidades y guardrails. La primera extraccion real recomendada para la fase siguiente son helpers puros y servicios de formateo, no state completo.
