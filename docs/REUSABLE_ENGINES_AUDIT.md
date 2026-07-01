# Reusable Engines Audit

DatosEnOrden debe crecer como plataforma reutilizable sin copiar proyectos completos ni introducir dependencias innecesarias. Esta auditoria revisa proyectos locales como referencia y separa ideas reutilizables de codigo que conviene dejar fuera por ahora.

## Criterio

- Reutilizar ideas pequenas y patrones estables, no stacks completos.
- Mantener datos locales de prueba: `LOCAL_TEST_DATA` y `NOT_OFFICIAL_DATA`.
- No agregar scraping, APIs externas, envio de email, PDFs pesados ni cambios de schema.
- Mantener lenguaje neutral: evidencia, trazabilidad, fuente, estado y relacion; no acusaciones ni inferencias.
- Priorizar modulos Python tipados bajo `src/datosenorden/maintenance` y servicios JSON-safe en `src/datosenorden/web/app_services.py`.

## Proyectos revisados

### I:\Proyectos\entity_relationship_dashboard

Sirve:
- Modelo mental de entidades, eventos, transacciones y relaciones agregadas.
- Tableros separados por overview, timeline y relationship mapping.
- Agregacion de relaciones desde tablas normalizadas.

No conviene reutilizar:
- PBIX y visualizaciones Power BI como dependencia runtime.
- Campos de riesgo o monitoreo financiero que podrian contaminar el lenguaje neutral del producto.

Motor interno posible:
- Agregador de relaciones explicables para expedientes y reportes ciudadanos.

### I:\Proyectos\excel-consolidation-tool

Sirve:
- Flujo simple input -> procesamiento -> reporte consolidado.
- Log de procesamiento y salida tabular verificable.

No conviene reutilizar:
- Dependencia de Excel como formato principal del producto.
- Codigo orientado a retail, no a evidencia publica.

Motor interno posible:
- Exportador tabular opcional para auditorias locales, no prioridad para UI publica.

### I:\Proyectos\messy_data_reconstruction

Sirve:
- Normalizacion y reconciliacion de fuentes heterogeneas.
- Reporte de match rates y registros reconstruidos.

No conviene reutilizar:
- Reglas de dominio de clientes/ventas/tickets.
- Escrituras XLSX como salida principal.

Motor interno posible:
- Utilidades futuras de reconciliacion: normalizacion de nombres, conteos de match y explicacion de cobertura.

### I:\Proyectos\ocr_document_intelligence_pipeline

Sirve:
- Separar extraccion, clasificacion y resumen.
- Guardar texto/extractos en artefactos livianos.

No conviene reutilizar:
- OCR runtime, PyMuPDF/OCR y PDFs de entrada en la demo publica.
- Procesamiento pesado o documentos reales fuera del set local.

Motor interno posible:
- Estrategia documental barata: metadata, URL oficial, hash opcional, resumen/extracto y fuente.

### I:\Proyectos\pdf_intelligence_pipeline

Sirve:
- Busqueda por texto completo, pagina, archivo y excerpt.
- Exportacion de resultados con contexto cercano a la coincidencia.

No conviene reutilizar:
- Base SQLite de documentos y pipeline PDF como dependencia actual.
- Almacenar PDFs pesados en DatosEnOrden.

Motor interno posible:
- Indice futuro de extractos oficiales por metadata, no por PDF completo.

### I:\Proyectos\report-cross-reference-automation-sample

Sirve:
- Cruce entre hallazgos narrativos y documentos fuente mediante patrones buscables.
- Campos utiles: `SOURCE_DOCUMENT`, `SOURCE_PAGE`, `SCORE`, `MATCHED_FACTS`, `MATCH_CONTEXT`, `REVIEW_STATUS`.

No conviene reutilizar:
- Diccionario de fact patterns de otro dominio.
- Lenguaje de hallazgos o scoring automatico que podria parecer acusatorio.

Motor interno posible:
- Motor neutral de anclas de evidencia: secciones de reporte conectadas a fuente, pagina/extracto y estado de revision.

### I:\Proyectos\Traceflow

Sirve:
- Esencia conceptual: historial de cambios, estados, documentos, solicitudes, eventos y seguimiento.
- Separacion entre backend, servicios y dashboard.
- Vista de historial como lista ordenada por fecha.
- Patron de actualizacion auditada en `dashboard/services/update.py`: cada cambio de campo conserva valor anterior, valor nuevo, usuario y fecha.
- Patron de workflow documental en `dashboard/tabs/workflow.py`: estados cerrados de revision, responsable, observacion, documento seleccionable y metrica de pendientes.
- Patron de alertas en `dashboard/services/alerts.py` y `dashboard/tabs/sac.py`: respuestas recientes, items sin solicitud, fechas limite vencidas y solicitudes abiertas por mas de N dias.
- Patron de avance en `dashboard/tabs/sac.py`: conteos por estado, porcentaje de completitud y cobertura de items solicitados vs recibidos.
- Patron de historial en `dashboard/tabs/history.py`: lectura simple ordenada por fecha descendente, sin inferencias.
- Patron de documento asociado en `backend/services/storage_service.py` y `backend/core/process_pdf.py`: ruta/identificador, hash, tipo documental, item detectado y relacion con solicitud.
- Patron de evento/estado en `backend/core/process_pdf.py`: la solicitud pasa de pendiente/enviada a respondida cuando existe respuesta/documento enlazado.

No conviene reutilizar:
- Codigo Streamlit/SQLite/Postgres especifico.
- Mail engine, monitoreo de carpetas, ingesta de PDFs y upgrades DB.
- Rutas locales absolutas, nombres de unidades, nombres institucionales especificos y etiquetas visibles del dominio original.
- Diccionarios de clasificacion bancaria/judicial, regex de causas y reglas de contenido documental del proyecto anterior.
- Apertura local de PDFs desde UI (`os.startfile`) y escritura de archivos reales por carpeta de causa.

Motor interno posible:
- `src/datosenorden/maintenance/tracking.py` queda reforzado como TraceFlow engine interno de DatosEnOrden. El nombre visible al usuario sigue siendo `Seguimiento`.
- Integracion segura realizada: se agregaron helpers genericos para historial derivado, cobertura documental, progreso, alertas por hitos abiertos y resumen JSON-safe.
- La integracion opera sobre dataclasses locales y datos demo marcados como `LOCAL_TEST_DATA` / `NOT_OFFICIAL_DATA`; no se copian datos reales, no se toca schema y no se exponen nombres visibles del proyecto anterior en UI.

Mapeo reusable especifico:
- Estados: usar `TrackingStatus` como vocabulario generico de avance (`proposed`, `published`, `approved`, `updated`, `partially_implemented`, etc.).
- Eventos: mantener hitos fechados con fuente, evidencia, documentos y entidades relacionadas.
- Historial: derivar entradas auditables `campo / valor anterior / valor nuevo / fecha / actor` desde eventos, sin tabla nueva.
- Documentos asociados: medir cobertura entre documentos esperados y documentos enlazados en eventos.
- Responsables: conservar responsable como entidad responsable del item, no como usuario personal ni dato sensible.
- Fechas: detectar hitos abiertos antiguos contra una fecha de referencia parametrizable.
- Alertas: producir alertas neutrales de soporte faltante, hito abierto antiguo o documento sin hito enlazado.
- Timeline: ordenar eventos por fecha y usarlos como fuente primaria para vistas y exportacion.
- Exportacion: extender `tracking_to_dict()` con `overview` JSON-safe reutilizable por Reflex o API futura.
- Vistas de avance: calcular total de hitos, hitos documentados, hitos abiertos, porcentaje de avance y cobertura documental.

### I:\SecondLifeEngine

Sirve:
- Estructura de producto/reportes por dataclasses, loaders y renderers.
- Dossiers con cover, resumen, timeline, evidencia y conclusiones.
- Separacion entre engine y productos.

No conviene reutilizar:
- ReportLab/PDF como dependencia obligatoria en esta fase.
- Plantillas comerciales y lenguaje de findings/riesgos.

Motor interno posible:
- Motor de reportes ciudadanos: dataclasses locales + export HTML liviano.

### I:\portfolio-generate

Sirve:
- Generacion estatica de paginas HTML y showcases navegables.
- Separacion entre datos, generador y salida en `docs/`.

No conviene reutilizar:
- Sitio de portfolio completo, estilos comerciales y catalogo de productos.

Motor interno posible:
- Export HTML estatico de reportes y seguimientos, sin servidor adicional.

## Integrado en esta fase

- `tracking.py` funciona como TraceFlow engine interno read-only para propuestas, documentos, eventos, estados y evidencia.
- `citizen_reports.py` agrega un motor local de reportes ciudadanos basado en dataclasses.
- `app_services.py` expone funciones JSON-safe reutilizables por Reflex y por una API futura.
- `/reports` muestra reportes ciudadanos y export HTML local.

## Solo documentado por ahora

- PDF/OCR/FTS.
- Reconciliacion avanzada de nombres.
- Monitoreo de carpetas, emails y suscripciones.
- Exportadores XLSX/PDF.
- Dashboards Power BI o visualizaciones externas.
