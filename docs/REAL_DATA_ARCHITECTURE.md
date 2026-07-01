# Real Data Architecture

DatosEnOrden debe crecer agregando fuentes reales sin modificar el Core.

## Flujo objetivo

```text
Dataset Publico
-> Loader
-> Normalizacion
-> Entity Resolution
-> Knowledge Engine
-> Timeline
-> Expediente
-> Reportes
-> Biblioteca
```

## Principios

- No scraping.
- No APIs externas sin contrato claro.
- Preferir datasets publicos descargables.
- No cambiar schema si el modelo actual puede representar la fuente.
- Los demos quedan como ejemplos, no como camino principal.

## Capas

- Dataset Registry: declara fuentes, formato esperado, loader, cobertura y estado.
- Dataset Adapter: conoce el formato de una fuente especifica.
- Common Pipeline: ejecuta validacion, normalizacion, relaciones/evidencia y publicacion.
- Core: entidades, claims, evidencia, relaciones, timeline, Knowledge Engine y reportes.
- Producto: UI ciudadana, busqueda, expediente, biblioteca y reportes.

## Separacion demo / datos publicos

Los samples siguen existiendo para desarrollo y presentacion, marcados como `LOCAL_TEST_DATA` y `NOT_OFFICIAL_DATA`. Cuando una fuente real este cargada, los expedientes deben abrir desde los datos persistidos y no desde rutas demo obligatorias.

## Preparacion para cron futuro

Un cron futuro deberia ejecutar comandos equivalentes a:

```text
download/export dataset fuera de la app
python scripts/load_<fuente>_file.py <archivo>
python scripts/real_data_readiness.py
python scripts/run_demo_check.py
```

El scheduler no se implementa en esta fase.
