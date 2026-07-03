# Source Watcher V1

## Por que existe

DatosEnOrden necesita dejar de depender de que Aylin elija manualmente cada tema. Source Watcher V1 crea una capa read-only para revisar fuentes oficiales acotadas y producir una lista de candidatos a revisar antes de importar, leer o publicar algo.

El objetivo no es automatizar la publicacion. El objetivo es detectar novedades oficiales y ordenar la revision humana.

## Fuente inicial

V1 usa la integracion ya existente de Datos Abiertos Legislativos Congreso Nacional, especificamente la operacion de Camara:

`getVotaciones_Boletin?prmBoletin=<boletin>`

La revision es acotada. Por defecto revisa el boletin seed actual (`8575-05`) y respeta `--limit`. No recorre historicos completos.

## Que detecta

El watcher produce `ChangeCandidate` cuando encuentra:

- Un boletin oficial que no aparece como entidad local.
- Un source record oficial nuevo.
- Un source record oficial existente cuyo hash local difiere.
- Un registro ya conocido, marcado como ignorado para dejar trazabilidad de que fue revisado.
- Una fuente temporalmente no disponible, marcada como ignorada con razon explicita.

Cada candidato incluye:

- `source_id`
- `external_id`
- `title`
- `url`
- `detected_at`
- `change_type`
- `reason`
- `priority`
- `suggested_action`

Acciones sugeridas actuales:

- `import_bill`
- `update_topic`
- `ignore`

El modelo permite despues usar acciones como `download_document` o `create_documented_reading` sin cambiar el flujo base.

## Que NO hace

Source Watcher V1 no hace:

- IA.
- Scraping agresivo.
- Crawling historico.
- Publicacion automatica.
- Descarga masiva de documentos.
- Cambios de schema.
- Cambios en PostgreSQL.
- Ejecucion de GraphLoader.
- Ejecucion del Reading Pipeline.
- Ejecucion del Knowledge Engine.
- Ejecucion del Publication Engine.
- Cambios en importaciones legislativas existentes.

## Por que no publica automaticamente

Una novedad oficial no equivale a una Lectura Documentada lista para publicar. Antes de publicar, una persona debe revisar pertinencia, contexto, evidencia, documento oficial, estado del expediente y posibles limites de interpretacion.

Por eso el watcher solo entrega candidatos y acciones sugeridas. La decision de importar, descargar documentos, crear lectura o ignorar sigue siendo humana.

## Flujo esperado

Fuente oficial

-> Watcher

-> Change Candidate

-> Import opcional

-> Lectura Documentada / Tema / Seguimiento

## Conexion posterior con el sistema existente

- Adapters: un candidato `import_bill` puede activar manualmente `scripts/load_legislative_bill.py`.
- Reading Pipeline: un candidato que apunte a documento oficial puede derivar despues en descarga y procesamiento documental, pero V1 no lo ejecuta.
- Publication Engine: una Lectura Documentada validada podria publicarse despues, pero V1 no llama al motor de publicacion.
- Actualidad Documentada: los candidatos pueden alimentar una cola editorial futura para decidir que tema entra a `/topic` o a seguimiento.

## Uso

```powershell
python scripts/watch_legislative_source.py --since 2026-07-01
python scripts/watch_legislative_source.py --limit 20
```

Tambien se puede revisar explicitamente uno o mas boletines:

```powershell
python scripts/watch_legislative_source.py --bill 8575-05 --limit 1
```

## Salida

El script imprime:

- candidatos nuevos
- candidatos actualizados
- candidatos ignorados
- acciones sugeridas
- errores no fatales si una fuente no pudo revisarse

No escribe resultados reales por defecto. Si en el futuro se guardan corridas locales, deben ir a `data/watch_runs/`, carpeta ignorada salvo `.gitkeep`.