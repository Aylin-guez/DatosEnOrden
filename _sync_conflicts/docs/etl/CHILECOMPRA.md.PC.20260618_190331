# ETL ChileCompra

> El codigo construye el sistema. La documentacion conserva la memoria.

## Objetivo

Construir el primer pipeline real de DatosEnOrden para transformar datos de compras publicas de Chile en claims verificables y relaciones publicas navegables.

Este ETL no persigue una carga rapida. Su objetivo es establecer un patron durable para futuras fuentes: extraccion controlada, normalizacion explicita, source records, claims verificables, evidencia y trazabilidad completa.

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

## Flujo Fase 2.5

```text
ChileCompra API
-> NormalizedPayload
-> source_record
-> entity
-> evidence
-> claim
-> relationship_public
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

## Manejo de errores

Errores de extraccion abortan el recurso.

Errores de mapeo rechazan el registro y se registran en `GraphBatch.errors`.

Si existen rechazos, el `import_job` queda como `failed` aunque los registros validos puedan persistirse. Esto fuerza revision.

## Ejecucion

Configurar `.env`:

```text
DATOSENORDEN_CHILECOMPRA_TICKET=...
```

Aplicar migraciones:

```powershell
alembic upgrade head
```

Ejecutar sin persistir:

```powershell
python scripts/run_chilecompra_etl.py --date 2026-06-12 --resource all --dry-run
```

Ejecutar carga:

```powershell
python scripts/run_chilecompra_etl.py --date 2026-06-12 --resource all
```
