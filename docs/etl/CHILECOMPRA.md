# ETL ChileCompra

> El codigo construye el sistema. La documentacion conserva la memoria.

## Objetivo

Construir el primer pipeline real de DatosEnOrden para transformar datos de compras publicas de Chile en `source_record`, `claim`, `evidence` y `relationship_public` navegables.

Esta fase no persigue volumen. Busca validar el modelo completo con un conjunto extremadamente pequeno de datos.

## Fuentes disponibles

Fuente primaria:

- API Mercado Publico de ChileCompra.
- Documentacion: `https://www.chilecompra.cl/api/`
- Base tecnica: `https://api.mercadopublico.cl/servicios/v1/publico`

Recursos relevantes:

- Licitaciones.
- Ordenes de compra.
- Organismos compradores.
- Proveedores.

Reglas operativas:

- Requiere ticket.
- El ticket nunca se persiste.
- Las consultas masivas deben respetar limites y condiciones de uso.
- Toda publicacion debe mantener atribucion clara a la fuente.

## Flujo Fase 2.6

```text
ChileCompra API
-> NormalizedPayload
-> source_record
-> claim
-> evidence
-> relationship_public
```

Regla de trazabilidad:

- Cada `claim` debe apuntar a su `source_record`.
- Cada `evidence` debe apuntar al mismo `source_record`.
- Cada `relationship_public` debe apuntar a su `claim`.
- Cada `relationship_public` debe poder reconstruirse desde el `source_record` original.

## Caso minimo de validacion

Para validar la fase se usa un conjunto minimo de una sola orden de compra:

- `Codigo`: `2097-241-SE14`
- `Nombre`: `Compra de servicios`
- `CodigoOrganismo`: `6945`
- `NombreOrganismo`: `Direccion de Compras y Contratacion Publica`
- `CodigoProveedor`: `17793`
- `NombreProveedor`: `Camara de Comercio de Santiago A.G.`
- `FechaEnvio`: `2026-01-01T12:00:00`

Ese unico registro genera:

- 1 `source_record`
- 2 `claim`
- 2 `evidence`
- 2 `relationship_public`

### Claims generados

```text
PUBLIC_ORGANIZATION ISSUES_PURCHASE_ORDER CONTRACT
COMPANY RECEIVES_CONTRACT CONTRACT
```

### Relaciones publicas derivadas

```text
PUBLIC_ORGANIZATION -> CONTRACT
COMPANY -> CONTRACT
```

## Extraccion

Implementada en `src/datosenorden/etl/chilecompra/client.py`.

Recursos:

- `list_tenders(day, status)`
- `get_tender(code)`
- `list_purchase_orders(day, status)`
- `get_purchase_order(code)`
- `list_buyers()`
- `find_supplier_by_rut(rut)`

## Normalizacion

Implementada en `src/datosenorden/etl/chilecompra/normalizers.py`.

Convierte payloads API en:

- URL de recurso.
- Parametros sin ticket.
- Version API.
- Fecha de consulta.
- Fecha de recuperacion.
- Registros.
- Hash estable del payload.

## Source records

Cada registro extraido genera un `SourceRecordPayload` con:

- `external_id`
- `record_type`
- `payload_hash`
- `raw_payload`
- `retrieved_at`
- `status`

Esto permite volver al registro original antes de mirar entidades, claims o grafo.

## Claims

Los claims son afirmaciones atomicas verificables.

### Licitaciones

Claim:

```text
PUBLIC_ORGANIZATION PUBLISHED_TENDER TENDER
```

Relacion publica derivada:

```text
PUBLIC_ORGANIZATION -> TENDER
```

### Ordenes de compra

Claims:

```text
PUBLIC_ORGANIZATION ISSUES_PURCHASE_ORDER CONTRACT
COMPANY RECEIVES_CONTRACT CONTRACT
```

Relaciones publicas derivadas:

```text
PUBLIC_ORGANIZATION -> CONTRACT
COMPANY -> CONTRACT
```

## Evidencia

La evidencia apunta a la ficha publica de Mercado Publico y conserva metadatos de registro fuente.

Regla:

- Sin evidencia no hay claim publicable.
- Sin claim no hay relacion publica.

## Validacion esperada

La fase queda validada cuando se cumple lo siguiente:

1. Se crea `source_record`.
2. Se generan `claim` verificables.
3. Se generan `evidence`.
4. Se generan `relationship_public` derivadas de `claim` validados.
5. Cada relacion publica puede trazarse hasta su `source_record` original.

## Ejecucion

Configurar `.env`:

```text
DATOSENORDEN_CHILECOMPRA_TICKET=...
DATOSENORDEN_DATABASE_URL=postgresql+psycopg://datosenorden:datosenorden@localhost:5432/datosenorden
```

Aplicar migraciones:

```powershell
alembic upgrade head
```

Ejecutar el caso minimo en modo seco:

```powershell
python scripts/run_chilecompra_etl.py --date 2026-01-01 --resource purchase-orders --dry-run
```

Ejecutar el caso minimo persistiendo datos:

```powershell
python scripts/run_chilecompra_etl.py --date 2026-01-01 --resource purchase-orders
```

Ejecutar la validacion de fase:

```powershell
pytest tests/test_chilecompra_phase_26.py -q
```

## Manejo de errores

Errores de extraccion abortan el recurso.

Errores de mapeo rechazan el registro y se registran en `GraphBatch.errors`.

Si existen rechazos, el `import_job` queda como `failed` aunque los registros validos puedan persistirse. Esto fuerza revision.
