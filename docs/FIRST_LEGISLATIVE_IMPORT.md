# First Legislative Import

Esta guia documenta la primera ingestion oficial legislativa de DatosEnOrden.
El alcance actual es manual y minimo: un boletin del Congreso se consulta desde
el adapter legislativo, se transforma a `GraphBatch` y se carga con `GraphLoader`
en PostgreSQL.

## Importar un boletin

Ejecuta primero un ensayo sin escritura:

```powershell
python scripts/load_legislative_bill.py --dry-run 8575-05
```

Para cargarlo en la base:

```powershell
python scripts/load_legislative_bill.py 8575-05
```

Tambien se puede usar:

```powershell
python scripts/load_legislative_bill.py --bill 8575-05
```

El flujo usado es:

```text
Boletin
-> LegislativeAdapter
-> LegislativePlatformMapper
-> GraphBatch
-> GraphLoader
-> PostgreSQL
```

No se invoca Reading Pipeline, Knowledge Engine, Publication Engine,
Actualidad Engine, UI, scheduler ni automatizacion.

## Verificar la importacion

Despues de cargar, ejecuta:

```powershell
python scripts/verify_legislative_bill.py 8575-05
```

El verificador responde si existe el boletin, si el `external_id` esperado fue
resuelto, y cuantos objetos quedaron asociados: entidades, claims, evidencias,
source records y documentos. En esta primera version, "documentos" corresponde
a las evidencias oficiales derivadas de las votaciones encontradas.

## Eliminar una prueba

Si la carga fue solo una prueba, elimina primero los objetos dependientes del
dataset `congreso-votaciones-boletin` y version del boletin. Ejemplo SQL:

```sql
BEGIN;

WITH target_dataset AS (
  SELECT id
  FROM dataset
  WHERE name = 'congreso-votaciones-boletin'
    AND version = '8575-05'
),
target_entity AS (
  SELECT id
  FROM entity
  WHERE entity_type = 'PUBLIC_PROJECT'
    AND external_id = 'cl-congreso-boletin-8575-05'
)
DELETE FROM relationship_public
WHERE claim_id IN (
  SELECT id FROM claim WHERE subject_entity_id IN (SELECT id FROM target_entity)
);

WITH target_dataset AS (
  SELECT id
  FROM dataset
  WHERE name = 'congreso-votaciones-boletin'
    AND version = '8575-05'
)
UPDATE evidence
SET claim_id = NULL
WHERE dataset_id IN (SELECT id FROM target_dataset);

WITH target_entity AS (
  SELECT id
  FROM entity
  WHERE entity_type = 'PUBLIC_PROJECT'
    AND external_id = 'cl-congreso-boletin-8575-05'
)
DELETE FROM claim
WHERE subject_entity_id IN (SELECT id FROM target_entity);

WITH target_dataset AS (
  SELECT id
  FROM dataset
  WHERE name = 'congreso-votaciones-boletin'
    AND version = '8575-05'
)
DELETE FROM evidence
WHERE dataset_id IN (SELECT id FROM target_dataset);

WITH target_dataset AS (
  SELECT id
  FROM dataset
  WHERE name = 'congreso-votaciones-boletin'
    AND version = '8575-05'
)
DELETE FROM source_record
WHERE dataset_id IN (SELECT id FROM target_dataset);

WITH target_dataset AS (
  SELECT id
  FROM dataset
  WHERE name = 'congreso-votaciones-boletin'
    AND version = '8575-05'
)
DELETE FROM import_job
WHERE dataset_id IN (SELECT id FROM target_dataset);

DELETE FROM dataset
WHERE name = 'congreso-votaciones-boletin'
  AND version = '8575-05';

DELETE FROM entity
WHERE entity_type = 'PUBLIC_PROJECT'
  AND external_id = 'cl-congreso-boletin-8575-05'
  AND id NOT IN (SELECT subject_entity_id FROM claim)
  AND id NOT IN (SELECT source_entity_id FROM relationship_public)
  AND id NOT IN (SELECT target_entity_id FROM relationship_public);

COMMIT;
```

## Limitaciones actuales

- Solo se carga un boletin indicado manualmente.
- El adapter consulta `getVotaciones_Boletin`; no rastrea todas las etapas de
  tramitacion legislativa.
- No descarga ni procesa documentos PDF.
- No publica contenido ni genera Lectura Documentada.
- No corre resolucion avanzada de entidades.
- La disponibilidad depende del servicio oficial de Datos Abiertos Legislativos.

## Reutilizacion

La integracion queda expresada como adapter oficial que produce `GraphBatch` y
loader generico que persiste el grafo. El mismo patron se puede reutilizar para
ChileCompra, Diario Oficial, LeyChile, DIPRES e InfoLobby cambiando el adapter
que construye los objetos de plataforma.
