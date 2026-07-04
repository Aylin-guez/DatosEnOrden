# First Real ChileCompra Load

Objetivo: cargar un archivo local real o realista de ChileCompra sin scraping, sin llamadas externas desde DatosEnOrden y sin subir datos reales al repositorio.

## Formato esperado

`scripts/load_chilecompra_file.py` espera JSON local con una de estas formas:

```json
{
  "Version": "opcional",
  "FechaCreacion": "opcional",
  "Listado": [
    {
      "Codigo": "OC-123",
      "Nombre": "Orden de compra",
      "FechaEnvio": "2026-01-15",
      "Comprador": {
        "CodigoOrganismo": "1234",
        "NombreOrganismo": "Organismo comprador"
      },
      "Proveedor": {
        "CodigoEmpresa": "999",
        "NombreEmpresa": "Proveedor"
      }
    }
  ]
}
```

Tambien acepta una lista directa:

```json
[
  {
    "Codigo": "OC-123",
    "Comprador": {"CodigoOrganismo": "1234", "NombreOrganismo": "Organismo comprador"},
    "Proveedor": {"CodigoEmpresa": "999", "NombreEmpresa": "Proveedor"}
  }
]
```

## Campos minimos

- `Codigo` o `CodigoExterno`: identifica la orden de compra.
- Comprador:
  - seccion `Comprador`, `CompradorOrganismo`, `DatosComprador`, `OrganismoComprador` o `UnidadCompra`;
  - codigo: `CodigoOrganismo`, `CodigoUnidadCompra` o `CodigoComprador`;
  - nombre: `NombreOrganismo`, `NombreUnidadCompra`, `NombreComprador` o `RazonSocial`.
- Proveedor:
  - seccion `Proveedor`, `Adjudicatario`, `DatosProveedor`, `Empresa` o `ProveedorAdjudicado`;
  - codigo: `CodigoEmpresa`, `CodigoProveedor`, `CodigoAdjudicatario`, `RutProveedor` o `RUTProveedor`;
  - nombre: `NombreEmpresa`, `NombreProveedor` o `RazonSocial`.

Fechas recomendadas:

- `FechaEnvio`
- `FechaCreacion`
- `FechaContrato`
- `FechaPublicacion`

## Donde poner archivos reales

Usar:

```text
data/real_imports/
```

La carpeta esta ignorada por git salvo `.gitkeep`.

## Como obtener/exportar archivo real manualmente

1. Obtener un archivo desde una via publica permitida por ChileCompra o una exportacion manual autorizada.
2. Guardarlo localmente en `data/real_imports/`.
3. No subir el archivo al repositorio.
4. Si el formato viene en CSV, convertirlo manualmente a JSON compatible antes de cargarlo. Esta fase no implementa parser CSV.

## Validar

```bash
python scripts/validate_chilecompra_file.py data/real_imports/<archivo>.json
```

Con limite:

```bash
python scripts/validate_chilecompra_file.py data/real_imports/<archivo>.json --limit 100
```

## Cargar

Prueba sin escribir:

```bash
python scripts/load_chilecompra_file.py data/real_imports/<archivo>.json --dry-run --limit 100 --source-label "ChileCompra export manual"
```

Carga marcada como oficial provista por operador:

```bash
python scripts/load_chilecompra_file.py data/real_imports/<archivo>.json --limit 100 --official-data --source-label "ChileCompra export manual"
```

Carga marcada como test/local:

```bash
python scripts/load_chilecompra_file.py data/real_imports/<archivo>.json --limit 100 --test-data --source-label "ChileCompra sample local"
```

## Verificar post-carga

```bash
python scripts/verify_real_chilecompra_load.py
python scripts/real_data_readiness.py
```

Luego revisar:

- `/ecosystem`: panel interno de datos reales.
- `/search?q=<comprador o proveedor>`
- `/investigation?id=<id de entidad>`

## Idempotencia

El schema actual tiene unicidad por dataset, tipo de registro e identificador externo para `source_record`, y unicidad por tipo/ID externo para entidades. Esto reduce duplicados si el archivo conserva los mismos codigos. Si el archivo cambia codigos o versionado, se debe revisar manualmente antes de recargar.
