# Data Source Strategy

Fase: Official Sources Discovery V1.

La estrategia de fuentes oficiales para DatosEnOrden debe separar el tipo civico de cada fuente antes de pensar en conectores. Una fuente puede pertenecer a mas de una categoria, pero cada integracion futura debe declarar su uso principal.

## Principios

- Priorizar fuentes oficiales con identificadores estables.
- Preferir datos estructurados descargables o APIs documentadas.
- Evitar scraping y descargas masivas.
- No mezclar dominios sin trazabilidad: normativa, compras, presupuesto, lobby y elecciones deben conservar origen propio.
- Separar documento oficial, registro transaccional, dato estadistico y evento de seguimiento.
- Mantener lenguaje informativo, sin inferencias automaticas sobre conducta, causalidad o responsabilidad.

## Fuentes documentales

Fuentes cuyo valor principal es conservar evidencia, contexto o texto oficial.

- Diario Oficial: publicaciones con CVE, PDFs/EPUB y fecha oficial.
- Biblioteca del Congreso Nacional: informes, historia politica, recursos legislativos y documentos.
- Contraloria: dictamenes, oficios, auditorias e informes en HTML/PDF.
- Ministerios: planes, resoluciones, informes, memorias y documentos sectoriales.
- SERVEL: documentos electorales, padrones publicados, documentos presupuestarios y archivo historico.

Uso DEO recomendado:

- Biblioteca y expedientes con evidencia verificable.
- Referencias de contexto, no datos derivados automaticos.
- Extraccion futura solo con permisos y contratos claros.

## Fuentes transaccionales

Fuentes con registros de operaciones o actos repetidos con actores, fechas y montos.

- ChileCompra: licitaciones, ordenes de compra, compradores, proveedores.
- DIPRES / Presupuesto Abierto: ejecucion presupuestaria, transacciones o reportes de gasto cuando el dataset lo permita.
- Portal de Transparencia: solicitudes, casos y respuestas cuando esten estructurados.
- InfoLobby: audiencias, viajes, donativos, sujetos pasivos y activos.
- Ministerios: transferencias, convenios, compras y programas cuando existan datasets oficiales.

Uso DEO recomendado:

- Expedientes por entidad, organismo, proveedor, programa o periodo.
- Timelines con eventos oficiales.
- Cruces solo descriptivos y trazables, sin inferencias no documentadas.

## Fuentes normativas

Fuentes que establecen reglas, publican normas o documentan su tramitacion.

- LeyChile: texto vigente, metadatos y XML de normas.
- Diario Oficial: publicacion primaria de leyes, decretos y resoluciones.
- Datos Abiertos Legislativos: proyectos de ley, tramites y votaciones.
- Senado y Camara: sesiones, comisiones, votaciones y actividad legislativa.
- Contraloria: jurisprudencia administrativa y toma de razon.

Uso DEO recomendado:

- Vincular norma publicada, historia legislativa y actos administrativos.
- Mantener distincion entre proyecto, norma vigente, publicacion y dictamen.
- Usar numero de boletin, id de norma, CVE y numero de dictamen como claves.

## Fuentes estadisticas

Fuentes orientadas a agregados, indicadores, series o visualizaciones.

- DIPRES: ejecucion presupuestaria por periodo y clasificacion.
- SERVEL: resultados historicos, estadisticas electorales y participacion.
- Datos.gob.cl: datasets sectoriales agregados.
- Consejo para la Transparencia: estudios nacionales y bases historicas.
- Ministerios: indicadores sectoriales por territorio, programa o periodo.

Uso DEO recomendado:

- Paneles ciudadanos y comparaciones simples con fecha y fuente.
- Metricas agregadas por organismo, periodo o territorio.
- Evitar mezclar estadisticas con casos individuales sin contrato explicito.

## Fuentes historicas

Fuentes que permiten reconstruir cambios en el tiempo.

- Diario Oficial: ediciones historicas desde 1877 y edicion electronica desde 2016.
- BCN: historia de la ley, historia politica y colecciones legislativas.
- Datos Abiertos Legislativos: tramitacion y periodos legislativos.
- SERVEL: resultados electorales historicos desde procesos antiguos publicados.
- DIPRES: series presupuestarias y ejecucion por periodo.
- Contraloria: dictamenes e informes por fecha.

Uso DEO recomendado:

- Lineas de tiempo oficiales.
- Versionado por fecha, periodo legislativo o proceso electoral.
- Separar dato historico digitalizado de dato nativamente estructurado.

## Fuentes de seguimiento

Fuentes utiles para observar actividad publica recurrente sin convertirla en juicio automatico.

- InfoLobby: agendas publicas, audiencias, viajes y donativos.
- ChileCompra: cambios de estado de licitaciones y ordenes.
- Congreso/Senado/Camara: movimientos de proyectos, sesiones y votaciones.
- Portal de Transparencia/CPLT: estados de casos, solicitudes y decisiones.
- Diario Oficial: publicaciones diarias con CVE.
- SERVEL: hitos de procesos electorales.

Uso DEO recomendado:

- Alertas informativas y timeline de actividad oficial.
- Filtros por organismo, fecha, territorio y tipo de acto.
- Texto neutral: "registro", "publicacion", "actualizacion", "audiencia", "orden", "votacion".

## Secuencia estrategica sugerida

1. Normativa estructurada: LeyChile + Datos Abiertos Legislativos.
2. Transaccional estructurada: ChileCompra y luego InfoLobby.
3. Transparencia: CPLT Datos Abiertos y Portal de Transparencia.
4. Presupuesto: DIPRES/Presupuesto Abierto con diccionario cerrado.
5. Documental primaria: Diario Oficial por CVE y documentos acotados.
6. Control y electoral: Contraloria y SERVEL con auditorias separadas.
7. Ministerios: solo por casos de uso concretos.

## Decision de arquitectura para fases futuras

Cada fuente futura deberia entrar como declaracion de dataset antes que como codigo:

- fuente oficial y URL;
- institucion responsable;
- licencia o condiciones;
- identificador unico;
- formato;
- frecuencia;
- ejemplo minimo;
- riesgos;
- campos candidatos;
- estado DEO.

Solo despues de aprobar esa ficha deberia existir loader, conector o proceso de ingestion.
