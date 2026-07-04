# State Events Model

DatosEnOrden cambia el centro conceptual de la novedad publica: el Estado no genera temas nuevos cada dia, genera eventos. Los temas viven durante anos y acumulan eventos, documentos oficiales y evidencia.

## Flujo conceptual

```text
Estado
-> Fuentes oficiales
-> Source Watcher
-> Evento
-> Tema
-> Cronologia
-> Daily Brief
-> Ciudadano
```

## Por que eventos y no solamente documentos

Un documento oficial es la fuente verificable. Pero la vida publica no ocurre solo cuando aparece un documento completo: tambien hay votaciones, cambios de estado, informes, decretos, publicaciones y actualizaciones. Si DEO mira solo documentos, pierde continuidad. Si mira eventos, puede contar como evoluciona un tema sin inventar interpretaciones.

El documento sigue siendo protagonista cuando existe. El evento solo dice que algo ocurrio, de donde viene y como se conecta con un tema existente.

## Categoria -> Tema -> Evento -> Documento -> Evidencia

La nueva lectura se organiza asi:

- Categoria: agrupa asuntos publicos de largo plazo.
- Tema: vive durante anos y acumula historia.
- Evento: unidad de cambio detectada desde una fuente oficial.
- Documento Oficial: respaldo verificable asociado al evento cuando existe.
- Evidencia: fragmentos, referencias o IDs oficiales que permiten revisar el origen.

## Tipos de eventos

`src/datosenorden/studio/state_events.py` define tipos configurables:

- `NEW_BILL`
- `NEW_DOCUMENT`
- `NEW_VOTE`
- `NEW_REPORT`
- `NEW_DECREE`
- `LAW_PUBLISHED`
- `COMMISSION_UPDATE`
- `STATUS_CHANGED`
- `DOCUMENT_UPDATED`
- `OTHER`

La clasificacion no usa IA. Se deriva desde `ChangeCandidate` de Source Watcher y desde `TopicClassification`, usando reglas en `config/topics/topics.json`.

## Importancia

La importancia tambien es rule-based:

- `HIGH`: ley publicada, nueva votacion u otro evento de alto impacto configurado.
- `MEDIUM`: nuevo informe, documento adicional o proyecto detectado.
- `LOW`: cambios menores, updates tecnicos o eventos no clasificados.

Las reglas viven en `importance_rules` dentro de `config/topics/topics.json`.

## Topic Update

Topic Update conserva su salida local, pero ahora cada update puede incluir un `state_event`. Esto evita que el tema piense solo en updates sueltos. El tema acumula eventos y la cronologia se construye desde esos eventos.

Esta fase no ejecuta Reading Pipeline, Knowledge Engine, Publication Engine, GraphLoader ni adapters. Tampoco cambia schema ni PostgreSQL.

## Daily Brief

Daily Brief se construye desde eventos recientes. Cada entrada representa algo que ocurrio, no un tema completo.

Cada entrada contiene:

- `event_id`
- `topic`
- `category`
- `title`
- `summary`
- `importance`
- `detected_at`
- `source`
- `link_to_topic`
- `link_to_source`

El boton en Home lleva siempre al tema, porque el evento aislado no es suficiente para comprender contexto.

## Experiencia publica

Home muestra `Que cambio hoy` desde Daily Brief. `/topic` muestra `Estado del tema` y `Cronologia del tema` desde eventos locales cuando existen. Si no hay eventos generados, conserva estados vacios o fallback existente sin romper la experiencia.

## Que no hace esta fase

- no crea IA
- no crea notificaciones
- no crea newsletter
- no publica automaticamente
- no modifica pipelines
- no modifica GraphLoader
- no modifica adapters
- no cambia PostgreSQL
- no cambia schema