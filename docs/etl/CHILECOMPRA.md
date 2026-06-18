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

## Flujo Fase 2.6 y 3.0

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
- `FechaEnvio`: `2026-01-01T12:00:00`
- `Comprador`:
  - `CodigoOrganismo`: `6945`
  - `NombreOrganismo`: `Direccion de Compras y Contratacion Publica`
- `Proveedor`:
  - `CodigoProveedor`: `17793`
  - `NombreProveedor`: `Camara de Comercio de Santiago A.G.`

Ese unico registro genera:

- 1 `source_record`
- 2 `claim`
- 2 `evidence`
- 2 `relationship_public`

## Persistencia real Fase 3.0

La persistencia minima real usa la misma orden de compra ya documentada.

Comando por codigo:

```powershell
python scripts/run_chilecompra_etl.py --purchase-order 2097-241-SE14
```

Alternativa por fecha con limite:

```powershell
python scripts/run_chilecompra_etl.py --date 2026-01-01 --resource purchase-orders --limit 1
```

Si la API retorna mas de un registro, `--limit 1` recorta el lote antes del mapeo y persiste solo el primer registro procesable.

Modo seguro de inspeccion del payload:

```powershell
python scripts/run_chilecompra_etl.py --purchase-order 2097-241-SE14 --debug-payload
```

Ese modo imprime solo:

- claves de primer nivel del payload
- cantidad de registros en `Listado`
- claves del primer registro
- claves de secciones como `Comprador` y `Proveedor`
- campos relevantes normalizados

No imprime ticket, contrasenas ni el contenido completo de campos sensibles.

## Verificacion SQL

Despues de la carga, revisar conteos con:

```sql
SELECT count(*) FROM source_record;
SELECT count(*) FROM claim;
SELECT count(*) FROM evidence;
SELECT count(*) FROM relationship_public;
```

Si quieres ver el registro cargado:

```sql
SELECT id, record_type, external_id, status
FROM source_record
ORDER BY created_at DESC
LIMIT 5;
```

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

## Forma de payload soportada

El mapeador de ordenes de compra acepta tanto payloads planos como payloads con secciones anidadas. La forma que valida esta fase es:

```text
Listado[0]
  Codigo
  Nombre
  FechaEnvio
  Comprador
    CodigoOrganismo
    NombreOrganismo
  Proveedor
    CodigoProveedor
    NombreProveedor
```

Reglas de mapeo:

- El codigo de la orden sale de `Codigo` o `CodigoExterno`.
- El comprador puede venir en `Comprador`, `OrganismoComprador` o `UnidadCompra`.
- El proveedor puede venir en `Proveedor`, `Empresa`, `Adjudicatario` o `DatosProveedor`.
- Si hay comprador y proveedor, se generan dos claims y dos relaciones publicas.
- Si solo hay uno de los dos, se genera el que exista y se conserva la trazabilidad.
- Si no se puede derivar ningun claim, el `source_record` queda `rejected` con `error_log` explicito en vez de quedar silenciosamente vacio.

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
python scripts/run_chilecompra_etl.py --purchase-order 2097-241-SE14
```

Ejecutar la validacion de fase:

```powershell
pytest tests/test_chilecompra_phase_26.py -q
```

Ejecutar la validacion de configuracion local:

```powershell
python -c "from sqlalchemy.engine import make_url; from datosenorden.core.config import get_settings; print(make_url(get_settings().database_url).render_as_string(hide_password=True))"
```

## Manejo de errores

Errores de extraccion abortan el recurso.

Errores de mapeo rechazan el registro y se registran en `GraphBatch.errors`.

Si existen rechazos, el `import_job` queda como `failed` aunque los registros validos puedan persistirse. Esto fuerza revision.

## Ticket faltante

Si falta `DATOSENORDEN_CHILECOMPRA_TICKET`, el script debe detenerse con un mensaje claro y seguro:

```text
Falta DATOSENORDEN_CHILECOMPRA_TICKET. Configura el ticket en .env o en PowerShell y vuelve a ejecutar.
```

No se imprime el valor del ticket ni el contenido de `DATABASE_URL`.

## Seed local sin ticket

Para validar solo la persistencia local y no la conectividad con ChileCompra, usa el seed marcado como no oficial:

```powershell
python scripts/seed_traceability_flow.py
```

Ese flujo inserta `LOCAL_TEST_DATA / NOT_OFFICIAL_DATA` y no llama a la API real.

La verificación SQL es la misma:

```sql
SELECT count(*) FROM source_record;
SELECT count(*) FROM claim;
SELECT count(*) FROM evidence;
SELECT count(*) FROM relationship_public;
```

## Helper local completo

El flujo local completo para resetear, migrar, sembrar y verificar es:

```powershell
python scripts/reset_migrate_seed_verify.py
```

Ese helper es solo para validacion local de persistencia. No usa ticket de ChileCompra ni llama a la API real.

## Inspeccion de trazabilidad persistida

Para ver la cadena oficial ya guardada en PostgreSQL para una orden de compra concreta:

```powershell
python scripts/inspect_trace.py --external-id 2097-241-SE14
```

El reporte muestra:

- `source_record` con `id`, `status`, `record_type` y `external_id`
- `claim` enlazados a ese `source_record`
- `evidence` enlazada a cada `claim`
- `relationship_public` derivada de cada `claim`
- entidades involucradas con nombre y tipo

Este comando es solo lectura y no llama a la API de ChileCompra.

## Resumen compacto de trazabilidad

Para un resumen breve de la misma orden persistida:

```powershell
python scripts/trace_summary.py --external-id 2097-241-SE14
```

Salida esperada:

- comprador
- proveedor
- nombre del contrato u orden
- URL de evidencia publica
- conteo de claims
- conteo de relaciones publicas

Este resumen solo usa PostgreSQL persistido.

Salida real observada actualmente:

```text
trace_summary: external_id=2097-241-SE14 source_records=1

source_record[1]:
  id=6a0d2d24-5fe9-4dad-adfb-db5eceedf2b4
  status=normalized
  record_type=chilecompra:purchase_order
  external_id=2097-241-SE14
  buyer organization=SERVICIO DE SALUD ARAUCO HOSPITAL DE ARAUCO
  supplier/company=MARLENE BEATRIZ FLORES PATIÑO
  contract/purchase order name=Insumos dentales especialidades
  public evidence URL=https://www.mercadopublico.cl/PurchaseOrder/Modules/PO/DetailsPurchaseOrder.aspx?qs=2097-241-SE14
  claims count=2
  public relationships count=2
```
