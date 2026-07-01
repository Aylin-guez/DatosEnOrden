# Data Pipeline

El pipeline comun permite que cada fuente implemente solo su adaptador y que el Core no conozca detalles de negocio.

## Interfaz

Modulo: `src/datosenorden/etl/core/pipeline.py`

Funciones principales:

- `load_dataset(session, adapter, request)`
- `validate(adapter, request)`
- `normalize(adapter, request)`
- `resolve_entities(batch)`
- `build_relationships(adapter, normalized)`
- `build_evidence(batch)`
- `publish(session, batch, dry_run=False)`

## Adaptador

Cada fuente implementa:

- `validate(request)`
- `normalize(request)`
- `build_relationships(normalized)`

El resultado de `build_relationships` debe ser un `GraphBatch` compatible con `GraphLoader`.

## ChileCompra

`scripts/load_chilecompra_file.py` ya usa el pipeline comun mediante `ChileCompraFileAdapter`.

Comando:

```bash
python scripts/load_chilecompra_file.py data/sample/chilecompra_purchase_orders_sample.json --dry-run
```

## Lo que no hace

- No descarga datasets.
- No llama APIs externas.
- No agenda ejecuciones.
- No cambia schema.

## Migracion gradual

Los loaders de sample pueden migrarse uno por uno al contrato de adaptador. Mientras tanto, siguen funcionando como scripts actuales.
