# Source Factory Standard v1

Source Factory es el estandar oficial para incorporar nuevas fuentes publicas a DatosEnOrden.

No es un motor nuevo. No ejecuta IA. No modifica Reading Pipeline, Knowledge Engine, Publication Engine, Source Watcher, State Events, Daily Brief, GraphLoader, PostgreSQL ni schema. Es una regla de arquitectura y operacion para que cada fuente futura entre al sistema de forma repetible, verificable y documentada.

## Objetivo

El objetivo de Source Factory es que agregar una fuente oficial no sea una reinvencion. Cada integracion debe responder las mismas preguntas, reutilizar los mismos componentes y producir los mismos tipos de salida verificable.

Una fuente nueva entra a DEO solo si puede transformarse en evidencia trazable para el ciudadano.

## Flujo oficial

```text
Fuente Oficial
-> Adapter
-> Watcher
-> State Event
-> Topic
-> Documento Fuente
-> Evidencia
-> Pulso del Estado
-> Lectura
-> Ciudadano
```

Este flujo define orden conceptual, no una obligacion de automatizar cada paso. Algunas integraciones pueden partir de forma manual y acotada, pero no deben saltarse trazabilidad, evidencia ni revision.

## Que necesita una fuente para entrar a DEO

Una fuente candidata necesita:

- un organismo o institucion responsable identificable;
- una URL oficial o punto de acceso verificable;
- condiciones de uso, licencia o permiso de reutilizacion revisado;
- documentacion oficial o descripcion suficiente del formato;
- tipo de acceso definido: API, XML, JSON, CSV, XLS, PDF, HTML oficial, descarga puntual u otro;
- identificadores estables o una estrategia documentada para construirlos;
- fechas relevantes: publicacion, actualizacion, observacion o recuperacion;
- eventos posibles que puedan describirse sin opinion;
- documentos fuente o registros que puedan enlazarse;
- evidencia que permita verificar afirmaciones;
- limites conocidos antes de integrarla.

Si una fuente no permite verificacion, no esta lista para entrar a DEO.

## Etapas oficiales

### 1. Identificacion

Se define que fuente existe, que organismo la publica, que cubre y por que puede aportar memoria documental al Estado.

Resultado esperado: ficha inicial usando `docs/templates/SOURCE_INTEGRATION_TEMPLATE.md`.

### 2. Revision legal y documental

Se revisan condiciones de uso, licencia, acceso, documentacion oficial, limites tecnicos y riesgos de interpretacion.

Resultado esperado: decision documentada sobre si la fuente puede usarse y bajo que limites.

### 3. Clasificacion de acceso

Se identifica como se obtiene la informacion: API, XML, JSON, CSV, XLS, PDF, HTML oficial, descarga manual u otro formato.

Resultado esperado: patron de acceso minimo, acotado y testeable.

### 4. Adapter

Se implementa o especifica un Adapter que traduce el formato externo a contratos internos existentes.

El Adapter debe seguir `docs/ADAPTER_GUIDELINES.md`. Debe ser pequeno, reemplazable y testeable con fixtures. No decide significado publico, no publica, no llama motores y no cambia schema.

Resultado esperado: datos normalizados, metadatos de fuente y trazabilidad tecnica.

### 5. Watcher

La fuente se conecta al patron de Source Watcher cuando corresponde detectar cambios o novedades.

El Watcher observa cambios y produce candidatos o entradas equivalentes. No publica automaticamente y no ejecuta pipelines posteriores.

Resultado esperado: cambios detectables con `source_id`, `external_id`, titulo, URL, fecha de deteccion, tipo de cambio, razon, prioridad y accion sugerida cuando aplique.

### 6. State Event

Cada cambio oficial relevante se representa como evento. Un evento dice que algo ocurrio, desde que fuente, cuando fue observado y con que evidencia.

Resultado esperado: evento descriptivo, no inferencial.

### 7. Topic

El evento se asocia a un tema existente o a un tema nuevo propuesto. Los temas acumulan historia y no mueren: se actualizan.

Resultado esperado: clasificacion por tema con reglas conocidas y revisables.

### 8. Documento Fuente

Cuando existe documento, registro o expediente de origen, se enlaza como documento fuente. El documento tiene prioridad sobre cualquier resumen.

Resultado esperado: documento o registro de origen con URL, identificador, organismo y fechas.

### 9. Evidencia

Se valida que la afirmacion publica tenga evidencia cercana: documento, fragmento, campo, identificador, URL o registro oficial.

Resultado esperado: evidencia suficiente para verificar lo que DEO afirma.

### 10. Pulso del Estado

Los eventos recientes pueden alimentar el Pulso del Estado si tienen evidencia, tema y estado claro.

Resultado esperado: cambio reciente presentado como observacion documentada, no como opinion.

### 11. Lectura

Una Lectura Documentada puede construirse despues de revisar evidencia, documento fuente, limitaciones y contexto ciudadano.

Resultado esperado: explicacion reutilizable que no reemplaza al documento.

### 12. Validacion completa

Antes de considerar una fuente integrada, deben pasar pruebas y revisiones documentales.

Resultado esperado: adapter probado, evidencia validada, limites marcados y flujo demo sin romper.

## Componentes que reutiliza

Source Factory reutiliza componentes existentes:

- `docs/ADAPTER_GUIDELINES.md` para estructura y limites de adapters;
- Source Watcher para deteccion acotada de cambios;
- State Events para representar cambios oficiales;
- Topic Classifier y Topic Update para asociar eventos a temas;
- Daily Brief y Pulso del Estado para mostrar cambios recientes;
- Official Document Workflow para documentos fuente;
- Trust Policy para evidencia, incertidumbre y contradicciones;
- Reading Pipeline solo cuando una fase posterior y validada construya una lectura documentada.

No se crea una capa paralela.

## Que produce

Una integracion completa produce:

- ficha documentada de fuente;
- decision de uso y limites;
- adapter acotado o especificacion de adapter;
- fixtures y tests del adapter;
- reglas de observacion para watcher;
- tipos de evento posibles;
- asociacion a temas;
- enlaces a documento fuente o registro oficial;
- evidencia verificable;
- entradas candidatas para Pulso del Estado;
- base reutilizable para Lecturas Documentadas;
- registro de validacion.

## Que nunca debe hacer

Source Factory nunca debe:

- crear motores nuevos;
- crear IA;
- modificar Reading Pipeline;
- modificar Knowledge Engine;
- modificar Publication Engine;
- modificar Source Watcher;
- modificar State Events;
- modificar Daily Brief;
- modificar GraphLoader;
- modificar PostgreSQL;
- cambiar schema;
- romper adapters existentes;
- publicar automaticamente;
- hacer scraping agresivo o crawling historico no autorizado;
- mezclar opinion con evidencia;
- crear conclusiones sin respaldo documental;
- ocultar limitaciones de la fuente.

## Checklist oficial

```text
[ ] Fuente identificada
[ ] Organismo responsable identificado
[ ] URL oficial registrada
[ ] Licencia revisada
[ ] Documentacion oficial encontrada
[ ] Tipo de acceso identificado (API/XML/JSON/CSV/PDF/HTML/XLS/etc.)
[ ] Frecuencia de actualizacion conocida o marcada como desconocida
[ ] Identificadores oficiales definidos
[ ] Limites de la fuente documentados
[ ] Adapter implementado o especificado
[ ] Tests del adapter
[ ] Fixtures pequenos disponibles
[ ] Watcher conectado o razon para no conectarlo documentada
[ ] Eventos definidos
[ ] Clasificacion por temas definida
[ ] Documento fuente enlazado
[ ] Evidencia validada
[ ] Contradicciones o incertidumbre marcadas si existen
[ ] Pulso actualizado o criterio de exclusion documentado
[ ] Lectura reutilizable posible o limitacion documentada
[ ] Validacion completa ejecutada
```

## Criterio de entrada

Una fuente puede entrar a DEO cuando existe evidencia suficiente para observarla sin inventar significado.

## Criterio de salida

Una fuente se considera integrada cuando el equipo puede responder:

```text
Que cambio oficial detectamos, desde que documento o registro, con que evidencia, asociado a que tema, y como puede verificarlo un ciudadano?
```