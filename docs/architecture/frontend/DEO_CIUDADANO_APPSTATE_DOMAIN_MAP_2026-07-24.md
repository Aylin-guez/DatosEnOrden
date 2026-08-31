# DEO Ciudadano - AppState Domain Map

Fecha de ejecucion: 2026-07-24

## Resumen

Esta auditoria cubre `reflex_app/reflex_app.py` despues de las Fases 1 a 11. No implementa Laboratory, no divide `AppState` completamente y no inicia Fase 13.

Tamano actual:

- `reflex_app/reflex_app.py`: 7.420 lineas.
- `AppState`: lineas 1258-2454, 1.197 lineas.
- Campos declarados en fuente: 228.
- Vars Reflex importadas en la clase: 230, incluyendo vars internas de Reflex como `router`.
- Computed vars / cached vars: 0.
- Metodos definidos en `AppState`: 32.
- Event handlers registrados por Reflex: 31, incluyendo `setvar`; los 2 helpers privados no son handlers publicos.
- Rutas registradas: exactamente 19.

## Dominios

| Dominio | Campos | Metodos | Riesgo dominante | Consumidores principales |
| --- | ---: | ---: | --- | --- |
| `SHELL_STATE` | 4 | 5 | `UI_CRITICAL` | shell, sidebar, header search |
| `NAVIGATION_STATE` | 0 | 0 | `PURE_STATE` | `reflex_app/navigation/config.py` |
| `GLOBAL_ERROR_STATE` | 1 | 0 | `CROSS_FEATURE_CRITICAL` | shell global |
| `SEARCH_STATE` | 19 | 8 | `HIGH_COUPLING` | `/search`, `/discover`, `/`, cards de descubrimiento |
| `DOCUMENT_READING_STATE` | 73 | 7 | `HIGH_COUPLING` | `/topic`, `/knowledge`, `/official-document`, `/library` |
| `SOURCES_STATE` | 15 | 1 | `MEDIUM_COUPLING` | `/ecosystem`, `/sources` |
| `PUBLIC_RECORD_STATE` | 69 | 4 | `CROSS_FEATURE_CRITICAL` | `/investigation`, enlaces desde search/topic/reports/tracking |
| `TRACKING_STATE` | 13 | 2 | `SERVICE_CRITICAL` | `/tracking`, `/chronology` |
| `CHRONOLOGY_STATE` | 0 | 0 | `ROUTING_CRITICAL` | Alias de `TRACKING_STATE` |
| `REPORTS_STATE` | 11 | 2 | `SERVICE_CRITICAL` | `/reports` |
| `DASHBOARD_STATE` | 18 | 2 | `SERVICE_CRITICAL` | `/`, `/dashboard` |
| `INSTITUTIONAL_STATE` | 0 | 0 | `PURE_STATE` | `/project`, `/studio`, `/support` sin estado propio |
| `DEMO_STATE` | 5 | 1 | `SERVICE_CRITICAL` | `/demo`, checks de portada |
| `SESSION_STATE` | 0 | 0 | `LEGACY_OR_UNKNOWN` | No hay sesion frontend explicita |
| `CROSS_FEATURE_STATE` | 0 | 0 | `CROSS_FEATURE_CRITICAL` | Representado por uso cruzado, no por campos dedicados |
| `LEGACY_OR_UNKNOWN` | 0 | 0 | `DO_NOT_MOVE_YET` | Sin simbolos sin clasificar |

## Inventario De Campos

Formato: `nombre (linea, tipo, default)`.

### SHELL_STATE

- `header_search_open` (1266, `bool`, `False`)
- `header_search_query` (1267, `str`, `''`)
- `sidebar_collapsed` (1268, `bool`, `True`)
- `advanced_nav_open` (1269, `bool`, `False`)

Destino propuesto: `reflex_app/shell/state.py` o substate de shell solo despues de caracterizar `shell()` y `app_sidebar()`.

### GLOBAL_ERROR_STATE

- `error_message` (1265, `str`, `''`)

Destino propuesto: mantener en `AppState` por ahora; lo leen varias rutas mediante el shell.

### SEARCH_STATE

- `query` (1259, `str`, `''`)
- `results` (1260, `list[dict]`, `[]`)
- `workspace_matches` (1261, `list[dict]`, `[]`)
- `guided_search_title` (1262, `str`, `''`)
- `discovery_case_rows` (1290, `list[dict]`, `[]`)
- `discovery_case_preview` (1291, `list[dict]`, `[]`)
- `current_topic_rows` (1292, `list[dict]`, `[]`)
- `guided_question_rows` (1293, `list[dict]`, `[]`)
- `guided_category_rows` (1294, `list[dict]`, `[]`)
- `selected_guided_category_id` (1295, `str`, `''`)
- `selected_guided_category_title` (1296, `str`, `''`)
- `selected_guided_category_description` (1297, `str`, `''`)
- `selected_guided_category_examples` (1298, `list[str]`, `[]`)
- `selected_guided_category_sources` (1299, `list[str]`, `[]`)
- `selected_guided_category_query` (1300, `str`, `''`)
- `selected_guided_category_cta` (1301, `str`, `''`)
- `selected_guided_category_href` (1302, `str`, `'/search'`)
- `selected_guided_category_path` (1303, `str`, `''`)
- `guided_option_rows` (1304, `list[dict]`, `[]`)

Destino propuesto: no mover en Fase 12. Primero extraer casos de uso de busqueda y discovery como funciones/servicios de aplicacion sin `self`.

### DOCUMENT_READING_STATE

- `topic_view_mode` (1270, `str`, `'lectura'`)
- `knowledge_documents`, `knowledge_document`, `knowledge_title`, `knowledge_summary`, `knowledge_key_points`, `knowledge_questions`, `knowledge_claims`, `knowledge_evidence`, `knowledge_pages`, `knowledge_fragments`, `knowledge_document_paragraphs` (1410-1420)
- `knowledge_document_source_path`, `knowledge_document_source_is_fallback`, `knowledge_document_has_pdf`, `knowledge_document_pdf_path`, `knowledge_document_pdf_href`, `knowledge_document_pdf_page_href` (1421-1426)
- `knowledge_citations`, `knowledge_connections`, `knowledge_notice`, `knowledge_expediente_target` (1427-1430)
- `knowledge_selected_page`, `knowledge_selected_fragment_id`, `knowledge_selected_reference_label`, `knowledge_selected_excerpt`, `knowledge_selected_summary`, `knowledge_selected_questions`, `knowledge_selected_claims`, `knowledge_selected_evidence`, `knowledge_selected_connections` (1431-1439)
- `knowledge_pdf_highlight_target`, `knowledge_selected_page_is_approximate`, `knowledge_pdf_location_notice`, `knowledge_fragment_contexts`, `knowledge_fragment_count`, `knowledge_total_fragment_count`, `knowledge_question_count`, `knowledge_claim_count`, `knowledge_reference_count` (1440-1448)
- `knowledge_coverage_text`, `knowledge_reference_text`, `knowledge_share_path`, `knowledge_share_url`, `knowledge_share_title`, `knowledge_share_x_url`, `knowledge_share_whatsapp_url`, `knowledge_share_linkedin_url`, `knowledge_share_copy_script`, `knowledge_error` (1449-1458)
- `topic_title`, `topic_status`, `topic_read_time`, `topic_document_count`, `topic_updated_at`, `topic_organizations_text`, `topic_official_document`, `topic_proposes_rows`, `topic_changes_rows`, `topic_no_changes_rows`, `topic_timeline_rows`, `topic_evidence_rows`, `topic_state_graph_rows`, `topic_reading_rows`, `topic_expediente_title`, `topic_expediente_summary`, `topic_expediente_metrics`, `topic_tracking_summary`, `topic_vote_summary`, `topic_vote_count`, `topic_status_rows`, `topic_hero_answer_rows`, `topic_original_url` (1459-1481)

Destino propuesto: `features/document_reading/state/` mas una capa de aplicacion para lectura/PDF. No mover todavia porque `load_topic` llama `load_knowledge`, `get_investigation` y `build_state_graph`.

### SOURCES_STATE

- `ecosystem_sources`, `ecosystem_active_sources`, `ecosystem_prototype_sources`, `ecosystem_planned_sources`, `ecosystem_concepts`, `ecosystem_roadmap` (1273-1278)
- `ecosystem_active_count`, `ecosystem_prototype_count`, `ecosystem_planned_count`, `ecosystem_concept_count` (1279-1282)
- `real_data_sources`, `real_data_ready_count`, `real_data_partial_count`, `real_data_demo_count`, `real_data_without_loader_count` (1283-1287)

Destino propuesto: primer candidato real para Fase 13, con adaptador temporal porque `features/sources/pages.py` aun importa `AppState`.

### PUBLIC_RECORD_STATE

- Seleccion: `selected_entity_id`, `selected_entity_name` (1263-1264)
- Resumen: `entity_name`, `entity_summary`, `dataset_badges`, `contracts`, `suppliers`, `lobby_meetings`, `evidence_count`, `relationship_count`, `datasets_involved`, `connected_entities`, `connection_summary` (1322-1333)
- Evidencia y relaciones: `story_cards`, `procurement_rows`, `lobby_rows`, `transparencia_rows`, `registry_rows`, `relationship_rows`, `evidence_rows`, `technical_details`, `neutral_explanation` (1332-1344)
- StateGraph: `state_graph_connection_rows`, `state_graph_source_rows`, `state_graph_summary_text`, `graph_summary`, `graph_dataset_nodes`, `graph_relationship_nodes`, `graph_evidence_nodes` (1340-1342, 1365-1368)
- Story: `story_headline`, `story_summary`, `story_key_findings`, `story_important_connections`, `story_timeline_highlights`, `story_questions`, `citizen_summary`, `citizen_narrative` (1345-1355, 1376)
- Timeline: `timeline_rows`, `timeline_overflow_rows`, `timeline_year_rows`, `timeline_older_year_rows` (1351-1352, 1369-1370)
- Trace/comparison: `source_trace_sources`, `source_trace_left_rows`, `source_trace_right_rows`, `comparison_summary`, `comparison_observations`, `comparison_overlap_areas`, `comparison_dataset_rows`, `source_trace_overlap_summary`, `source_trace_notice`, `source_contribution_rows`, `source_coverage_rows`, `relationship_journey_rows`, `related_entity_group_rows` (1356-1374)
- Informe del expediente: `report_path`, `investigation_key_points`, `investigation_questions`, `investigation_limitations`, `investigation_neutrality_notice`, `canonical_investigation_link` (1375-1381)
- Estado de carga: `investigation_status_message`, `investigation_status`, `requested_investigation_target`, `last_loaded_investigation_target`, `last_valid_investigation_target`, `investigation_loaded`, `investigation_loading` (1482-1488)

Destino propuesto: `features/public_record/state/` solo despues de separar coordinacion de servicios. Es el grupo con mayor acoplamiento.

### TRACKING_STATE

- `tracking_items`, `tracking_item`, `tracking_title`, `tracking_summary`, `tracking_current_status`, `tracking_expediente_target`, `tracking_events`, `tracking_documents`, `tracking_evidence`, `tracking_follow_targets`, `tracking_related_sources`, `tracking_status_label`, `tracking_error` (1397-1409)

Destino propuesto: extraer despues de reports/sources; depende de servicios y de apertura de expediente.

### REPORTS_STATE

- `citizen_reports`, `citizen_report`, `citizen_report_title`, `citizen_report_summary`, `citizen_report_subject`, `citizen_report_status`, `citizen_report_sources`, `citizen_report_sections`, `citizen_report_evidence_refs`, `citizen_report_path`, `citizen_report_error` (1386-1396)

Destino propuesto: `features/reports/state/` con servicios de reporte fuera de componentes.

### DASHBOARD_STATE

- `dataset_rows`, `connection_rows`, `connection_rows_preview`, `total_datasets`, `active_datasets`, `total_claims`, `total_relationships` (1272, 1288-1289, 1306-1309)
- `dashboard_title`, `dashboard_summary`, `dashboard_budget_total`, `dashboard_budget_currency`, `dashboard_contracts`, `dashboard_suppliers`, `dashboard_meetings`, `dashboard_authorities`, `dashboard_budget_rows`, `dashboard_featured_entities`, `dashboard_discovery_cases` (1310-1320)

Destino propuesto: `features/dashboard/state/` despues de aislar portada (`load_home`) de dashboard.

### DEMO_STATE

- `demo_missing` (1305, `list[str]`, `[]`)
- `demo_sources_ready`, `demo_investigation_ready`, `demo_report_ready`, `demo_report_path` (1382-1385)

Destino propuesto: mantener por ahora; comparte servicios con dashboard, reports y public_record.

## Inventario De Metodos

| Metodo | Lineas | Dominio | Lee | Modifica | Servicios | Riesgo | Destino propuesto |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `toggle_header_search` | 1490-1493 | `SHELL_STATE` | `header_search_open` | `header_search_open`, `header_search_query` | - | `UI_CRITICAL` | Shell state futuro |
| `toggle_sidebar` | 1495-1496 | `SHELL_STATE` | `sidebar_collapsed` | `sidebar_collapsed` | - | `UI_CRITICAL` | Shell state futuro |
| `toggle_advanced_nav` | 1498-1499 | `SHELL_STATE` | `advanced_nav_open` | `advanced_nav_open` | - | `LOW_COUPLING` | Shell state futuro |
| `set_topic_view_mode` | 1501-1502 | `DOCUMENT_READING_STATE` | - | `topic_view_mode` | - | `HIGH_COUPLING` | Document reading state futuro |
| `set_header_search_query` | 1504-1505 | `SHELL_STATE` | - | `header_search_query` | - | `UI_CRITICAL` | Shell state futuro |
| `submit_header_search` | 1507-1514 | `SHELL_STATE`/`SEARCH_STATE` | `header_search_query`, `query` | `query`, `header_search_open`, `header_search_query` | - | `CROSS_FEATURE_CRITICAL` | Separar coordinador shell -> search |
| `submit_main_search` | 1516-1519 | `SEARCH_STATE` | `query`, `header_search_query` | `query` | - | `HIGH_COUPLING` | Search state futuro |
| `load_home` | 1521-1589 | `DASHBOARD_STATE`/`SEARCH_STATE` | previews y categorias | metricas, discovery, error | `get_dataset_summary`, `get_demo_status`, `get_cross_dataset_connections`, `get_current_topics`, `get_discovery_cases`, `get_guided_questions`, `get_guided_discovery_options` | `SERVICE_CRITICAL` | Separar portada como coordinador |
| `load_discover` | 1591-1605 | `SEARCH_STATE` | categorias seleccionadas | opcion guiada seleccionada | `get_guided_discovery_options` | `HIGH_COUPLING` | Search state futuro |
| `load_search` | 1607-1628 | `SEARCH_STATE` | `router`, `run_search` | query/resultados/categoria | - | `ROUTING_CRITICAL` | Search state futuro con router adapter |
| `load_ecosystem` | 1630-1701 | `SOURCES_STATE` | listas sources | sources, counts, error | `get_data_ecosystem`, `get_real_data_readiness` | `MEDIUM_COUPLING` | Primer candidato de extraccion |
| `set_query` | 1703-1705 | `SEARCH_STATE` | - | `query`, `guided_search_title` | - | `LOW_COUPLING` | Search state futuro |
| `run_search` | 1707-1734 | `SEARCH_STATE` | `query`, `workspace_matches` | `results`, `workspace_matches`, error | `search_workspace` | `SERVICE_CRITICAL` | Caso de uso + state delgado |
| `explore_discovery_case` | 1736-1740 | `SEARCH_STATE` | - | `query`, `guided_search_title` | - | `LOW_COUPLING` | Search state futuro |
| `explore_guided_question` | 1742-1754 | `SEARCH_STATE` | - | categoria/query/opciones | `get_guided_discovery_options` | `HIGH_COUPLING` | Search state futuro |
| `select_guided_category` | 1756-1774 | `SEARCH_STATE` | categorias | categoria/query/opciones | `get_guided_discovery_options` | `HIGH_COUPLING` | Search state futuro |
| `load_dashboard` | 1776-1814 | `DASHBOARD_STATE` | - | dashboard y error | `get_citizen_dashboard` | `SERVICE_CRITICAL` | Dashboard state futuro |
| `load_demo` | 1816-1835 | `DEMO_STATE` | `demo_report_path` | flags demo y error | `get_dataset_summary`, `resolve_investigation_target`, `get_investigation`, `export_investigation_report` | `SERVICE_CRITICAL` | Demo coordinator |
| `load_tracking` | 1837-1870 | `TRACKING_STATE` | `tracking_error` | tracking y error | `get_tracking_items`, `get_tracking_demo` | `SERVICE_CRITICAL` | Tracking state futuro |
| `load_knowledge` | 1872-1990 | `DOCUMENT_READING_STATE` | `router`, contexto PDF | knowledge, PDF, share, error | `get_knowledge_documents`, `get_knowledge_demo` | `HIGH_COUPLING` | No mover todavia |
| `load_topic` | 1992-2059 | `DOCUMENT_READING_STATE`/`PUBLIC_RECORD_STATE` | knowledge, topic | topic, error | `get_investigation`, `build_state_graph` | `CROSS_FEATURE_CRITICAL` | Separar despues de knowledge |
| `load_reports` | 2061-2095 | `REPORTS_STATE` | `citizen_report_error` | reportes y error | `get_citizen_reports`, `get_citizen_report_demo`, `export_citizen_report_demo` | `SERVICE_CRITICAL` | Reports state futuro |
| `select_result` | 2098-2102 | `SEARCH_STATE`/`PUBLIC_RECORD_STATE` | `results` | - | - | `CROSS_FEATURE_CRITICAL` | Search coordinator -> public_record |
| `open_investigation` | 2104-2105 | `PUBLIC_RECORD_STATE` | - | - | - | `ROUTING_CRITICAL` | Public record navigation adapter |
| `open_tracking_investigation` | 2107-2108 | `TRACKING_STATE`/`PUBLIC_RECORD_STATE` | `tracking_expediente_target` | - | - | `ROUTING_CRITICAL` | Tracking navigation adapter |
| `open_knowledge_investigation` | 2110-2111 | `DOCUMENT_READING_STATE`/`PUBLIC_RECORD_STATE` | `knowledge_expediente_target` | - | - | `ROUTING_CRITICAL` | Document navigation adapter |
| `select_document_anchor` | 2113-2121 | `DOCUMENT_READING_STATE` | fragmentos | pagina seleccionada/contexto | - | `UI_CRITICAL` | No mover todavia |
| `_set_document_reading_context` | 2123-2143 | `DOCUMENT_READING_STATE` | fragmentos/seleccion | seleccion, claims, evidencia, PDF | - | `DO_NOT_MOVE_YET` | Helper privado dentro de future document state |
| `_set_document_share_links` | 2145-2155 | `DOCUMENT_READING_STATE` | seleccion/share | URLs y script share | - | `DO_NOT_MOVE_YET` | Helper puro posible solo si recibe datos |
| `open_report_investigation` | 2157-2158 | `REPORTS_STATE`/`PUBLIC_RECORD_STATE` | `citizen_report_subject` | - | - | `ROUTING_CRITICAL` | Reports navigation adapter |
| `open_canonical_investigation` | 2160-2167 | `PUBLIC_RECORD_STATE` | seleccion | seleccion/ultimo target | `resolve_canonical_expediente_target` | `CROSS_FEATURE_CRITICAL` | Public record state futuro |
| `load_investigation` | 2169-2454 | `PUBLIC_RECORD_STATE` | router, seleccion, estado previo | 80+ campos de expediente | `resolve_investigation_target`, `get_investigation`, `get_investigation_knowledge`, `get_source_trace`, `get_entity_comparison`, `get_investigation_graph`, `get_investigation_timeline`, `get_source_contributions`, `get_investigation_story`, `export_investigation_report`, `build_state_graph` | `DO_NOT_MOVE_YET` | Ultimo grupo a mover |

## Dependencias Cruzadas

```text
Shell
v
header_search_* -> submit_header_search -> query -> /search

Home
v
dataset_rows / connection_rows / discovery previews
v
get_dataset_summary, get_demo_status, get_cross_dataset_connections,
get_current_topics, get_discovery_cases, get_guided_questions,
get_guided_discovery_options
v
/, /search

Sources
v
ecosystem_* / real_data_*
v
load_ecosystem
v
get_data_ecosystem, get_real_data_readiness
v
/ecosystem, /sources

Document Reading
v
knowledge_* + topic_*
v
load_knowledge -> load_topic -> select_document_anchor
v
get_knowledge_documents, get_knowledge_demo, get_investigation, build_state_graph
v
/topic, /knowledge, /official-document, /library

Public Record
v
selected_entity_* + entity/relationship/evidence/story/trace/graph fields
v
open_canonical_investigation -> load_investigation
v
resolve_investigation_target, get_investigation*, get_source_trace,
get_entity_comparison, get_investigation_graph, get_investigation_timeline,
get_source_contributions, get_investigation_story, export_investigation_report,
build_state_graph
v
/investigation, plus entry points from search/topic/reports/tracking
```

Dependencias cruzadas explicitas:

- `submit_header_search` mezcla shell y search.
- `load_home` mezcla portada, dashboard, discovery y fuentes de actualidad.
- `load_discover` depende de `load_home`.
- `load_search` lee `router` y llama `run_search`.
- `select_result` y `open_*_investigation` mezclan dominios con navegacion a expediente.
- `load_topic` depende de `load_knowledge`, `get_investigation` y `build_state_graph`.
- `load_investigation` concentra public record, reports, timeline, graph, trace y export.
- `error_message` es transversal y se muestra desde shell.

## Servicios Y Persistencia

`AppState` llama servicios desde `datosenorden.web.app_services` y `datosenorden.web.entity_engine`. Esos servicios son la frontera actual hacia PostgreSQL/archivos/datos locales; `AppState` no abre conexiones PostgreSQL directamente, pero si coordina cargas criticas que dependen de esos servicios.

Servicios usados:

- Search/discovery/home: `search_workspace`, `get_guided_questions`, `get_guided_discovery_options`, `get_discovery_cases`, `get_current_topics`, `get_cross_dataset_connections`.
- Sources: `get_data_ecosystem`, `get_real_data_readiness`.
- Dashboard/demo: `get_dataset_summary`, `get_demo_status`, `get_citizen_dashboard`.
- Document reading: `get_knowledge_documents`, `get_knowledge_demo`, `get_investigation`, `build_state_graph`.
- Tracking: `get_tracking_items`, `get_tracking_demo`.
- Reports: `get_citizen_reports`, `get_citizen_report_demo`, `export_citizen_report_demo`.
- Public record: `resolve_canonical_expediente_target`, `resolve_investigation_target`, `get_investigation`, `get_investigation_knowledge`, `get_source_trace`, `get_entity_comparison`, `get_investigation_graph`, `get_investigation_timeline`, `get_source_contributions`, `get_investigation_story`, `export_investigation_report`, `build_state_graph`.

## Que Podria Extraerse Primero

Orden recomendado:

1. `SOURCES_STATE`: menor superficie, una ruta canonical ya esta en feature, un loader principal.
2. `REPORTS_STATE`: grupo acotado, pero requiere aislar export y enlace a expediente.
3. `TRACKING_STATE`: acotado, con dependencia de navegacion a expediente.
4. `SHELL_STATE`: pequeno, pero UI critical; conviene hacerlo cuando shell tenga contrato propio.
5. `DASHBOARD_STATE`/home: separar portada de dashboard antes de mover.
6. `SEARCH_STATE`: alto acoplamiento por router, discovery y expediente.
7. `DOCUMENT_READING_STATE`: alto acoplamiento por PDF, share, topic y expediente.
8. `PUBLIC_RECORD_STATE`: ultimo; demasiados servicios y campos derivados.

No mover todavia:

- `load_investigation`.
- `load_knowledge` y `load_topic`.
- `run_search` y `load_search`.
- shell completo.
- rutas y registro de paginas.
- coordinacion PostgreSQL/servicios.
- estado global de error.

## Estrategia Futura De State

Evaluacion:

- A. Substates heredados: posible, pero requiere validar registro de eventos y serializacion de Reflex contra rutas actuales. Riesgo medio-alto si se aplica masivamente.
- B. States independientes por feature: adecuado para features nuevas como Laboratory. Menor riesgo cuando no hay consumidores legacy.
- C. Mixins de comportamiento: util para helpers puros, pero riesgoso si oculta campos y eventos de Reflex.
- D. Servicios de aplicacion + State delgado: recomendado como primer paso para dominios con servicios criticos.
- E. Combinacion gradual: patron mas seguro para este codigo.

Recomendacion concreta: usar combinacion gradual. Para features nuevas, states independientes por feature. Para el monolito existente, extraer primero servicios/casos de uso y view-model builders sin `self`, luego mover grupos pequenos de state cuando las paginas consumidoras ya vivan bajo su feature.

## Frontera De Laboratory

Laboratory sera una feature independiente.

Reglas obligatorias:

- Toda feature nueva debe nacer bajo `reflex_app/features/<feature>/`.
- Laboratory no agregara campos al `AppState` monolitico salvo un adaptador temporal minimo, explicito y documentado.
- No importara DEO Core.
- No llamara Bricks desde componentes.
- Las paginas llamaran a State o casos de uso de Laboratory.
- El State de Laboratory llamara a una capa de aplicacion o cliente.
- El cliente utilizara URLs configurables.
- El frontend no conoce API keys, RapidAPI, Apify, puertos internos ni detalles de Gateway.
- La navegacion se agregara mediante la configuracion declarativa existente.
- Las rutas se registraran mediante imports explicitos.
- No se permitira duplicar modelos de Expediente, Hipotesis, Evidencia o Indicador dentro de una sola pagina.
- El Laboratorio debera poder crecer sin aumentar `reflex_app/reflex_app.py` salvo imports o reexports minimos.
- nuevas entidades de dominio no deben definirse en `reflex_app/reflex_app.py`.

Estructura esperada cuando se implemente:

```text
reflex_app/features/laboratory/
├── pages/
├── components/
├── models/
├── state/
└── client/
```

No se crearon carpetas ni archivos vacios de Laboratory en Fase 12.

## Guardrails Para Features Nuevas

Reglas documentadas y ejecutables por `tests/test_reflex_state_architecture_phase_12.py`:

- Nuevas paginas deben vivir bajo `reflex_app/features/<feature>/`.
- Nuevos componentes especificos deben vivir bajo su feature.
- Nuevas entidades de dominio no deben definirse en `reflex_app/reflex_app.py`.
- Nuevas integraciones no deben incluir secretos ni URLs hardcodeadas.
- No debe aparecer un paquete Laboratory vacio.
- No debe agregarse una ruta Laboratory antes de implementar la feature.
- La navegacion declarativa sigue siendo fuente de verdad.
- `reflex_app.py` solo puede registrar/importar/reexportar features nuevas.

## Diagrama Conceptual

```text
reflex_app/reflex_app.py
├── AppState legacy
│   ├── shell/search/document/public_record/report/tracking/dashboard fields
│   └── handlers coordinadores actuales
├── imports explicitos de features extraidas
│   ├── features/institutional/pages.py
│   └── features/sources/pages.py
└── rx.App + style global

features/<feature> futura
├── pages
├── components
├── models
├── state
└── client/application services
```
