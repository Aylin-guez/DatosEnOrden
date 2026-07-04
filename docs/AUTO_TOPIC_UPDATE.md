# Auto Topic Update V1

Auto Topic Update existe para simplificar el flujo de novedades oficiales sin crear una bandeja editorial obligatoria. La capa toma candidatos detectados por Source Watcher, los clasifica con reglas locales y genera un estado de tema para que `/topic` pueda mostrar ultimos cambios sin abandonar la lectura principal.

## Flujo

```text
Fuente oficial
-> Source Watcher
-> Topic Classifier
-> Topic Update
-> Timeline / Seguimiento
-> /topic muestra ultimos cambios
```

La salida se guarda como JSON local en `data/topic_updates/`. Es una capa de estado operativo, no una publicacion automatica.

## Como clasifica

`src/datosenorden/studio/topic_classifier.py` usa reglas configurables en `config/topics/topics.json`. Cada regla puede mirar:

- `source_id`
- prefijos de `external_id`
- keywords del titulo y la razon
- tipo documental declarado como texto
- `suggested_action`
- keywords de categoria

El resultado es una clasificacion con:

- `category_id`
- `topic_id`
- `confidence`
- `reason`

No usa IA ni modelos externos. Si ninguna regla calza, usa el topic fallback configurado con baja confianza.

## Como actualiza temas

`src/datosenorden/studio/topic_update.py` convierte cada `ChangeCandidate` clasificado en un `TopicUpdate` con:

- `topic_id`
- `title`
- `source_id`
- `external_id`
- `detected_at`
- `summary`
- `suggested_action`
- `timeline_event`
- `status`

El script `scripts/update_topics_from_sources.py` ejecuta un watcher legislativo acotado, clasifica los candidatos, genera updates y los escribe en `data/topic_updates/`.

Ejemplo:

```powershell
python scripts/update_topics_from_sources.py --limit 10
```

## Integracion con la experiencia publica

`/topic` lee los JSON locales y muestra una seccion `Ultimos cambios detectados` cerca del inicio. Si hay updates para el tema, tambien aparecen como eventos derivados en `Seguimiento resumido` antes del timeline existente.

Si no hay updates, la pagina muestra un estado vacio claro. No se consulta PostgreSQL para esta capa y no se cambia schema.

## Que NO hace

Auto Topic Update V1 no hace lo siguiente:

- no crea IA
- no ejecuta Reading Pipeline
- no ejecuta Knowledge Engine
- no ejecuta Publication Engine
- no descarga documentos completos
- no importa automaticamente expedientes completos
- no publica interpretaciones
- no crea CMS
- no cambia PostgreSQL
- no cambia schema
- no modifica importaciones legislativas ni GraphLoader

## Por que no publica automaticamente

Una novedad oficial detectada no equivale a una Lectura Documentada lista. La publicacion requiere comprobar documento, fragmentos, evidencia, contexto y trazabilidad. Esta fase solo deja una novedad visible como estado del tema y como evento de seguimiento, para que la lectura principal avise que algo cambio sin convertirlo en interpretacion editorial automatica.

## Conexion futura

Despues, estos updates podran alimentar un flujo opcional:

1. revisar el candidato detectado
2. importar o descargar documento si corresponde
3. ejecutar adapters existentes
4. procesar Reading Pipeline
5. actualizar Knowledge Engine
6. publicar una Lectura Documentada completa
7. consolidar seguimiento en Publication Engine

Esa conexion futura debe reutilizar motores existentes. V1 solo prepara la capa rule-based y la visibilidad publica minima.
## Relacion con State Events

Desde State Events V1, Auto Topic Update no solo genera updates locales. Cada candidato clasificado puede producir un evento de Estado asociado al tema. El update conserva compatibilidad operativa, pero la cronologia publica y el Daily Brief deben preferir eventos.
