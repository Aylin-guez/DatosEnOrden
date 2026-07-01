# Dataset Registry

El registry central vive en `src/datosenorden/maintenance/dataset_registry.py`.

## Dos usos

1. Registry persistido/derivado:
   - `list_datasets(session)`
   - `get_dataset_details(session, dataset_slug)`
   - usado por exploracion y reportes actuales.

2. Registry de preparacion real:
   - `list_real_dataset_registry()`
   - `get_real_dataset_entry(dataset_id)`
   - `summarize_real_dataset_registry(session=None)`

## Campos del registry real

- `id`
- `display_name`
- `description`
- `status`
- `official_url`
- `expected_format`
- `loader_script`
- `last_loaded`
- `supports_incremental`
- `entity_types`
- `coverage`
- `demo_available`
- `sample_dataset`

## Estados actuales

- `connected_file_loader`: existe ruta local ejecutable para cargar un archivo.
- `prototype_sample_loader`: existe sample y loader local de prototipo.
- `planned`: fuente documentada sin loader operativo.

## Uso operativo

```bash
python scripts/real_data_readiness.py
```

Este comando separa:

- fuentes listas;
- fuentes parciales;
- fuentes demo;
- fuentes sin loader.
