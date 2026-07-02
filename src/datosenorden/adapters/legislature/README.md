# Legislative Adapter

Official source adapter for Datos Abiertos Legislativos:

`https://opendata.camara.cl/`

## Scope

This adapter only supports a manually provided bulletin id:

```python
from datosenorden.adapters.legislature import LegislativeAdapter

batch = LegislativeAdapter().load_bill("8575-05")
```

The adapter does not crawl Congress, does not download history, does not publish, and does not call the Reading Pipeline, Knowledge Engine, Publication Engine, Actualidad Engine, GraphLoader, or Entity Resolution.

## File responsibilities

- `client.py`: talks to the official ASMX/HTTP XML service only.
- `parser.py`: turns official XML into adapter-owned Python objects.
- `mapper.py`: maps adapter-owned objects into platform ETL contracts.
- `adapter.py`: orchestrates client, parser, and mapper for `load_bill`.
- `models.py`: adapter-owned dataclasses.

## Current operation

The first supported official operation is:

```text
GET https://opendata.camara.cl/wscamaradiputados.asmx/getVotaciones_Boletin?prmBoletin=<bulletin_id>
```

The response is XML. JSON and CSV are not part of this adapter.
