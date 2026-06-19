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

Si la API retorna mas de un registro, `--limit 1` recorta el listado antes de pedir detalles y persiste solo el primer registro procesable.

Para ordenes de compra, la consulta por fecha se usa como descubrimiento de codigos. Cada codigo del listado se hidrata con `get_purchase_order(codigo)` antes de normalizar y mapear, de modo que el batch usa el mismo payload detallado que el flujo single `--purchase-order`.

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

## Prototipo DIPRES de enlace cruzado

La fase 5.0 introduce un sample local de DIPRES para demostrar que el grafo puede unir datos de dos datasets distintos usando una entidad compartida ya persistida en ChileCompra.

Flujo:

```text
DIPRES sample
-> source_record
-> claim
-> evidence
-> BUDGET entity
-> matched PUBLIC_ORGANIZATION entity
-> existing purchase order / supplier graph
```

El sample local genera dos claims de presupuesto:

```text
PUBLIC_ORGANIZATION HAS_APPROVED_BUDGET value
PUBLIC_ORGANIZATION HAS_EXECUTED_BUDGET value
```

Tambien genera un claim de enlace cruzado desde un nodo `BUDGET` hacia la organizacion compartida. Ese enlace queda marcado con coincidencia normalizada y una confidence exploratoria. El resultado es un primer grafo navegable que mezcla DIPRES y ChileCompra en el mismo espacio persistido.

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
- En carga batch, si el detalle por codigo falla o no trae registros, se conserva el registro resumen como `source_record` rechazado con `error_log`.

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

## Primer grafo exportable

Para generar un HTML visible con el primer grafo persistido:

```powershell
python scripts/export_trace_graph.py --external-id 2097-241-SE14
```

El archivo resultante queda en:

```text
graph_exports/2097-241-SE14.html
```

Ese HTML representa:

- comprador
- orden de compra
- proveedor

con datos ya persistidos en PostgreSQL.

## Expansion inicial del dataset

Para pasar de una sola orden de compra a un conjunto pequeno usando la integracion existente:

```powershell
python scripts/load_sample_purchase_orders.py --limit 100
```

El comando recorre una ventana reciente de dias hacia atras y persiste los registros hasta alcanzar el limite o agotar la ventana.

Por cada fecha escaneada imprime progreso:

```text
sample_purchase_orders_progress: date=YYYY-MM-DD raw_found=N loaded=N rejected=N claims=N relationships=N
```

Donde:

- `raw_found`: registros encontrados en el listado por fecha despues de aplicar el limite pendiente.
- `loaded`: `source_record` persistidos o actualizados para esa fecha.
- `rejected`: registros marcados `rejected` por no poder generar claims.
- `claims`: claims generados desde los detalles de ordenes de compra.
- `relationships`: `relationship_public` derivadas de esos claims.

Al finalizar imprime:

- `raw_found`
- `source_records count`
- `rejected`
- `claims count`
- `evidences count`
- `relationship_public count`
- `distinct buyers count`
- `distinct suppliers count`

Para ver un resumen del dataset persistido:

```powershell
python scripts/dataset_summary.py
```

El resumen muestra:

- total purchase orders
- total public organizations
- total suppliers
- total claims
- total relationships

## Exploracion del dataset Fase 4.1

Antes de agregar nuevas fuentes, la Fase 4.1 inspecciona el dataset ChileCompra ya persistido.

Reglas:

- Solo lectura.
- No llama a la API de ChileCompra.
- No requiere ticket.
- Usa solo PostgreSQL y los modelos actuales.
- No crea ni modifica `source_record`, `claim`, `evidence` ni `relationship_public`.

Para imprimir la exploracion en consola:

```powershell
python scripts/explore_dataset.py
```

La salida incluye:

- top buyers by purchase orders
- top suppliers by purchase orders
- purchase orders by status
- rejected source_records grouped by error_log
- claims grouped by predicate
- relationship_public grouped by relationship_type

Para generar un reporte HTML local:

```powershell
python scripts/export_dataset_report.py
```

El archivo generado queda en:

```text
reports/dataset_report.html
```

El reporte incluye:

- metricas resumen
- tablas
- graficos simples de barras
- timestamp de generacion

## Explorador de entidades Fase 4.2

La Fase 4.2 permite pasar de estadisticas de dataset a exploracion centrada en entidades.

Reglas:

- Solo lectura.
- No llama a la API de ChileCompra.
- No agrega nuevas fuentes.
- No modifica la arquitectura ni el schema.
- Usa solo entidades, claims, evidencias y `relationship_public` ya persistidos.

Buscar proveedores por nombre, sin distinguir mayusculas/minusculas:

```powershell
python scripts/search_supplier.py "SKY"
```

La salida muestra cada proveedor encontrado con:

- `name`
- `external_id`
- `id`
- `purchase_orders`
- `claims`
- `relationships`

Buscar compradores:

```powershell
python scripts/search_buyer.py "EJERCITO"
```

Ver detalle de una entidad concreta:

```powershell
python scripts/entity_details.py --entity-id <entity_id>
```

El detalle muestra:

- entidad base
- claims donde participa como sujeto u objeto
- relaciones publicas donde participa como origen o destino
- evidencia enlazada a sus claims
- entidades relacionadas

Exportar perfil HTML:

```powershell
python scripts/export_entity_profile.py --entity-id <entity_id>
```

El archivo generado queda en:

```text
profiles/<entity_id>.html
```

Ese perfil usa el mismo estilo visual base que `reports/dataset_report.html` y permite revisar manualmente claims, relaciones, evidencias y entidades relacionadas.

## Navegacion de grafo Fase 4.3

La Fase 4.3 agrega la primera capa de navegacion entre entidades ya persistidas.

Nuevos comandos:

```powershell
python scripts/entity_neighbors.py --entity-id <entity_id>
python scripts/entity_graph.py --entity-id <entity_id> --depth 2
python scripts/export_entity_graph.py --entity-id <entity_id>
python scripts/relationship_summary.py
```

Reglas:

- usan solo PostgreSQL persistido
- no crean ni modifican `source_record`, `claim`, `evidence` ni `relationship_public`
- no agregan nuevas fuentes ni IA
- no cambian el esquema ni la arquitectura

El perfil HTML de una entidad ahora enlaza vecinos directos y rutas de navegacion para que el grafo deje de sentirse aislado.

## Prototipo local de Lobby en el grafo

La Fase 7.0 agrega un sample local de Lobby para probar enlaces con entidades ya persistidas desde ChileCompra. No llama la API real de Lobby, no scrapea y no debe leerse como dato oficial.

El sample queda marcado como `LOCAL_TEST_DATA / NOT_OFFICIAL_DATA` y genera:

```text
PUBLIC_ORGANIZATION ORGANIZATION_HELD_LOBBY_MEETING LOBBY_MEETING
COMPANY COUNTERPARTY_PARTICIPATED_IN_LOBBY LOBBY_MEETING
LOBBY_MEETING LOBBY_MEETING_ABOUT_SUBJECT value
```

Ejemplo de recorrido minimo:

```text
PUBLIC_ORGANIZATION
-> LOBBY_MEETING
-> COMPANY
```

Ejemplo de recorrido extendido cuando tambien existen contratos y presupuesto:

```text
BUDGET
-> PUBLIC_ORGANIZATION
-> CONTRACT
-> COMPANY
-> LOBBY_MEETING
```

La relacion es descriptiva: una reunion registrada o de muestra conecta un organismo publico con una contraparte. No implica corrupcion, irregularidad ni wrongdoing.
