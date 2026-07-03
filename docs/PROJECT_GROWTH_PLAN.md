# Plan de crecimiento del proyecto

Este documento propone como DatosEnOrden puede crecer sin perder orden cuando existan 20 fuentes, 50 temas, miles de eventos y cientos de documentos.

No mueve archivos, no cambia schema y no modifica motores. Es una guia de evolucion futura.

## Principio central

DEO debe crecer por contratos y carpetas estables, no por excepciones.

Cada nueva fuente, tema, evento o documento debe poder ubicarse en una estructura conocida, con evidencia cercana y responsabilidades separadas.

## Riesgos de crecimiento

Cuando el proyecto crece, los riesgos principales son:

- adapters con logica de negocio mezclada;
- documentos sin evidencia cercana;
- eventos duplicados o sin tema claro;
- temas recreados en vez de actualizados;
- fixtures grandes o dependientes de red;
- scripts puntuales que se vuelven pipelines invisibles;
- documentacion historica confundida con estandares vigentes;
- UI que muestra datos sin explicar origen;
- almacenamiento local sin convenciones de version e historial.

## Escala esperada

### 20 fuentes

Se requiere una convencion estricta por fuente:

```text
src/datosenorden/adapters/<source>/
docs/sources/<source>.md
tests/test_<source>_adapter.py
```

Cada fuente debe tener ficha, adapter, fixtures, limites y reglas de evento. Las fuentes prototipo deben distinguirse de fuentes integradas.

### 50 temas

Los temas deben tratarse como memoria persistente, no como categorias efimeras.

Cada tema necesita:

- identificador estable;
- descripcion neutral;
- fuentes relacionadas;
- tipos de evento esperados;
- reglas de clasificacion;
- limitaciones conocidas;
- cronologia construida desde eventos.

La configuracion de temas debe seguir siendo revisable y versionable.

### Miles de eventos

Los eventos deben mantenerse pequenos, deduplicables y trazables.

Cada evento debe conservar:

- fuente;
- identificador externo;
- tipo;
- fecha observada;
- documento o registro relacionado;
- tema;
- evidencia;
- hash o mecanismo equivalente para detectar cambios.

La UI no debe intentar mostrar todos los eventos al mismo tiempo. Debe agrupar por tema, fecha, fuente, importancia documental y estado.

### Cientos de documentos

Los documentos requieren ciclo de vida claro:

```text
incoming -> processing -> published -> archived
```

Cada documento debe tener metadata independiente, version, fuente, URL oficial, fechas y estado. La explicacion ciudadana nunca debe reemplazar al documento fuente.

## Evolucion futura de estructura

### Codigo

Estructura recomendada a medida que crece:

```text
src/datosenorden/
  adapters/
    <source>/
      adapter.py
      client.py
      parser.py
      mapper.py
      models.py
      README.md
  studio/
    source_watcher.py
    state_events.py
    topic_classifier.py
    topic_update.py
    daily_brief.py
    document_reading_pipeline.py
    publication_engine.py
  maintenance/
    reports, demos y herramientas locales
  datasets/
    metadata ligera por dataset o fuente
  web/
    servicios de presentacion
  models/
    contratos persistentes existentes
```

La regla es no mover logica de fuente hacia `studio/` ni logica de motores hacia `adapters/`.

### Documentacion

La documentacion deberia migrar a familias:

```text
docs/00_foundation/
docs/01_architecture/
docs/02_sources/
docs/03_engines/
docs/04_workflows/
docs/05_product/
docs/99_archive/
```

Cada nueva fuente debe agregar o actualizar:

- ficha de fuente;
- documentacion de adapter;
- limites de evidencia;
- eventos posibles;
- estado de integracion.

### Datos locales

Para crecimiento local, los datos generados deben seguir separados por funcion:

```text
data/watch_runs/
data/topic_updates/
data/state_events/
data/daily_briefs/
data/official_documents/
reports/
graph_exports/
```

No se debe mezclar salida temporal, evidencia oficial y reportes generados sin convencion clara.

## Reglas para agregar fuentes sin perder orden

- Una fuente entra con ficha antes que con codigo.
- Un adapter no cambia contratos globales.
- Un watcher observa; no publica.
- Un evento describe un cambio; no interpreta impacto.
- Un tema acumula historia; no se duplica por novedad.
- Un documento fuente tiene prioridad sobre cualquier lectura.
- Una lectura explica; no reemplaza evidencia.
- Una limitacion visible vale mas que una conclusion apresurada.

## Reglas para mantener temas

- Usar identificadores estables.
- Evitar nombres de tema demasiado coyunturales.
- Documentar criterios de entrada y salida.
- Revisar duplicados antes de crear tema nuevo.
- Mantener cronologia por eventos, no por textos manuales sueltos.
- Separar temas publicables de temas en observacion.

## Reglas para mantener eventos

- Deduplicar por fuente, identificador externo, tipo y fecha relevante.
- Conservar hash o huella cuando el contenido pueda cambiar.
- Registrar cambios de fuente como eventos nuevos o actualizaciones versionadas.
- Mantener eventos tecnicos fuera del Pulso si no tienen lectura ciudadana clara.
- No borrar historia cuando una fuente cambia.

## Reglas para mantener documentos

- Metadata obligatoria por documento.
- URL oficial y fecha de recuperacion siempre que existan.
- Version e historial cuando haya reemplazos.
- Estado claro: incoming, processing, published o archived.
- Evidencia enlazada a fragmentos o campos verificables.

## Reglas para pruebas

Cuando haya muchas fuentes, las pruebas deben mantenerse rapidas y acotadas:

- fixtures pequenos por fuente;
- pruebas unitarias de parser y mapper;
- pruebas sin red por defecto;
- pruebas de integracion separadas y explicitas;
- demo checks como verificacion de producto, no como unico control.

## Reglas para producto

La experiencia ciudadana debe escalar por comprension:

- mostrar que cambio;
- mostrar de donde viene;
- mostrar evidencia cercana;
- mostrar limitaciones;
- permitir volver al documento fuente;
- agrupar por tema y cronologia;
- evitar vistas que parezcan solo base de datos.

## Senales de que DEO esta perdiendo orden

- Una fuente requiere excepciones no documentadas.
- Un adapter empieza a decidir narrativa.
- Un evento no puede explicar su evidencia.
- Un tema aparece duplicado por nombre similar.
- Un documento publicado no tiene metadata suficiente.
- La UI muestra afirmaciones sin fuente cercana.
- La documentacion vigente y la historica se contradicen sin nota.

## Plan de evolucion por fases

### Fase A: estandarizar

- Mantener Source Factory como puerta de entrada.
- Usar plantilla de fuente para nuevas integraciones.
- Definir ubicacion futura de docs sin mover todavia.

### Fase B: ordenar

- Crear indice documental.
- Separar fuentes integradas, candidatas y archivadas.
- Identificar documentos historicos que deben pasar a archivo.

### Fase C: escalar

- Consolidar convencion por adapter.
- Separar tests por fuente.
- Medir volumen de eventos y documentos.
- Revisar rendimiento de vistas ciudadanas.

### Fase D: gobernar

- Establecer revision periodica de fuentes.
- Auditar evidencia y limitaciones.
- Marcar documentos reemplazados.
- Revisar temas obsoletos, duplicados o demasiado amplios.

## Respuesta corta

DEO crecera sin perder orden si cada crecimiento conserva la misma cadena:

```text
Fuente oficial -> Adapter -> Watcher -> Evento -> Tema -> Documento -> Evidencia -> Lectura ciudadana
```

La escala no debe cambiar la regla central: todo debe poder verificarse.