# Real Sources Plan

DatosEnOrden debe pasar de datos locales de prueba a fuentes reales de forma gradual, verificable y sin scraping agresivo.

## ChileCompra

Estado actual:

- Existe ETL en `src/datosenorden/etl/chilecompra`.
- El flujo normaliza respuestas ChileCompra, las mapea a entidades, claims, evidencia y relaciones, y las carga con `GraphLoader`.
- El nuevo script `scripts/load_chilecompra_file.py` permite cargar un archivo JSON local exportado o preparado manualmente.

Entrada esperada:

- JSON con forma compatible con ChileCompra, idealmente objeto con `Listado`.
- También acepta una lista directa de registros; el script la envuelve como `Listado`.
- Los archivos de prueba deben marcarse como `LOCAL_TEST_DATA` y `NOT_OFFICIAL_DATA`.

Comando:

```bash
python scripts/load_chilecompra_file.py data/sample/chilecompra_purchase_orders_sample.json --dry-run
```

Flujo esperado:

```text
ChileCompra local file -> normalizer -> mapper -> source_records/entities/relationships/evidence -> Entity Resolution -> Expediente
```

## Reglas

- No inventar datos oficiales.
- No descargar PDFs pesados en esta fase.
- No usar APIs externas sin contrato claro.
- Mantener trazabilidad hacia archivo local, fecha de carga y fuente declarada.

## Siguiente paso público

Preparar una primera carga real controlada desde archivo exportado, revisar resultados en `/search` y abrir el expediente canónico desde `/investigation?id=...`.
