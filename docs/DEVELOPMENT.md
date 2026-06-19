# Desarrollo local

## Requisitos

- Python 3.12 o superior.
- PostgreSQL instalado de forma nativa en Windows.
- Git.

## Instalacion

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
Copy-Item .env.example .env
```

## PostgreSQL nativo en Windows

1. Instalar PostgreSQL desde el instalador oficial de Windows.
2. Asegurarse de que el servicio de PostgreSQL este iniciado.
3. Verificar que `psql` este disponible en la terminal:

```powershell
psql --version
```

4. Crear el usuario y la base local si no existen:

```powershell
psql -U postgres -h localhost -d postgres
```

Dentro de `psql`:

```sql
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'datosenorden') THEN
        CREATE ROLE datosenorden LOGIN PASSWORD 'datosenorden';
    END IF;
END
$$;

CREATE DATABASE datosenorden OWNER datosenorden;
\q
```

5. Confirmar que `.env` contiene `DATABASE_URL`:

```text
DATABASE_URL=postgresql+psycopg://datosenorden:datosenorden@localhost:5432/datosenorden
```

6. Aplicar migraciones:

```powershell
alembic upgrade head
```

## Verificacion segura de configuracion

Para confirmar que la aplicacion esta leyendo `.env` sin mostrar contrasenas:

```powershell
python -c "from sqlalchemy.engine import make_url; from datosenorden.core.config import get_settings; print(make_url(get_settings().database_url).render_as_string(hide_password=True))"
```

La salida debe mostrar el usuario, host y base de datos, pero ocultar la contrasena.

## Crear o resetear la base local

Crear desde cero:

```powershell
psql -U postgres -h localhost -d postgres -c "CREATE ROLE datosenorden LOGIN PASSWORD 'datosenorden';"
psql -U postgres -h localhost -d postgres -c "CREATE DATABASE datosenorden OWNER datosenorden;"
```

Si la base ya existe y quieres resetearla:

```powershell
psql -U postgres -h localhost -d postgres -c "DROP DATABASE IF EXISTS datosenorden;"
psql -U postgres -h localhost -d postgres -c "DROP ROLE IF EXISTS datosenorden;"
psql -U postgres -h localhost -d postgres -c "CREATE ROLE datosenorden LOGIN PASSWORD 'datosenorden';"
psql -U postgres -h localhost -d postgres -c "CREATE DATABASE datosenorden OWNER datosenorden;"
```

## API local

```powershell
uvicorn datosenorden.api.app:app --reload
```

Endpoint de salud:

```text
GET http://127.0.0.1:8000/health
```

## Tests y calidad

```powershell
pytest
ruff check .
```

## Migraciones

Crear una migracion nueva:

```powershell
alembic revision --autogenerate -m "descripcion"
```

Aplicar migraciones:

```powershell
alembic upgrade head
```

Revertir una migracion:

```powershell
alembic downgrade -1
```

## Troubleshooting

### Error de autenticacion con PostgreSQL

Si `alembic upgrade head` falla con `password authentication failed`:

- Verifica que `DATABASE_URL` apunte al usuario correcto.
- Confirma que el servicio de PostgreSQL este iniciado.
- Revisa si el usuario `datosenorden` existe y tiene la contrasena esperada.
- Si cambiaste la contrasena, actualiza `.env` y vuelve a ejecutar `alembic upgrade head`.
- Prueba la conexion manual:

```powershell
psql -U datosenorden -h localhost -d datosenorden
```

- Usa la verificacion segura anterior para comprobar que `.env` se esta leyendo correctamente sin exponer secretos.

### Error de rol o base inexistente

Si el usuario o la base no existen, recrea ambos con los comandos de esta guia y vuelve a ejecutar:

```powershell
alembic upgrade head
```

## Seed local sin ticket

Mientras no exista `DATOSENORDEN_CHILECOMPRA_TICKET`, puedes validar persistencia local con un seed marcado como no oficial:

```powershell
python scripts/seed_traceability_flow.py
```

Ese comando inserta `LOCAL_TEST_DATA / NOT_OFFICIAL_DATA` en la base local para probar la cadena de persistencia sin llamar a ChileCompra.

Verifica los conteos con:

```sql
SELECT count(*) FROM source_record;
SELECT count(*) FROM claim;
SELECT count(*) FROM evidence;
SELECT count(*) FROM relationship_public;
```

## Helper local completo

Cuando quieras limpiar la base local, aplicar migraciones, sembrar el seed y verificar conteos en una sola pasada:

```powershell
python scripts/reset_migrate_seed_verify.py
```

Este helper:

- usa `DATABASE_URL` desde `.env`
- ejecuta `alembic downgrade base`
- ejecuta `alembic upgrade head`
- ejecuta `scripts/seed_traceability_flow.py`
- imprime conteos finales sin revelar secretos

Salida esperada:

```text
local_reset_migrate_seed_verify: source_record=1 claim=1 evidence=1 relationship_public=1
```

Si quieres inspeccionar la base manualmente después:

```sql
SELECT count(*) FROM source_record;
SELECT count(*) FROM claim;
SELECT count(*) FROM evidence;
SELECT count(*) FROM relationship_public;
```

## Inspeccion de trazabilidad persistida

Para revisar una compra ya persistida sin llamar a ChileCompra:

```powershell
python scripts/inspect_trace.py --external-id 2097-241-SE14
```

Este comando:

- usa `DATABASE_URL` desde `.env`
- solo lee PostgreSQL
- imprime `source_record`, `claim`, `evidence` y `relationship_public`
- no muestra secretos ni consulta la API externa

## Resumen compacto de trazabilidad

Para ver un resumen legible y breve de una orden persistida:

```powershell
python scripts/trace_summary.py --external-id 2097-241-SE14
```

Este comando:

- usa `DATABASE_URL` desde `.env`
- solo lee PostgreSQL
- muestra comprador, proveedor, nombre del contrato, URL de evidencia y conteos
- no llama a la API externa ni imprime secretos

## Exportacion de grafo visible

Para generar el primer grafo visible en HTML:

```powershell
python scripts/export_trace_graph.py --external-id 2097-241-SE14
```

Por defecto escribe:

```text
graph_exports/2097-241-SE14.html
```

Este archivo se genera solo con datos ya persistidos en PostgreSQL. No consulta la API de ChileCompra y no expone secretos.

## Expansion inicial del dataset

Para cargar un conjunto pequeno pero util de ordenes de compra usando la integracion existente:

```powershell
python scripts/load_sample_purchase_orders.py --limit 100
```

El comando recorre un ventana reciente de dias hacia atras hasta alcanzar el limite o agotar la ventana de busqueda. Al terminar imprime:

- `source_records count`
- `claims count`
- `evidences count`
- `relationship_public count`
- `distinct buyers count`
- `distinct suppliers count`

Para resumir el dataset persistido:

```powershell
python scripts/dataset_summary.py
```

Ese resumen muestra:

- total purchase orders
- total public organizations
- total suppliers
- total claims
- total relationships

## Explorador de entidades

La Fase 4.2 agrega una primera capa de exploracion centrada en entidades persistidas. Todos los comandos son de solo lectura, usan `DATABASE_URL` desde `.env` y no llaman a la API de ChileCompra.

Buscar proveedores:

```powershell
python scripts/search_supplier.py "SKY"
```

Buscar compradores:

```powershell
python scripts/search_buyer.py "EJERCITO"
```

Ver el detalle navegable de una entidad:

```powershell
python scripts/entity_details.py --entity-id <entity_id>
```

Exportar perfil HTML de una entidad:

```powershell
python scripts/export_entity_profile.py --entity-id <entity_id>
```

Por defecto escribe:

```text
profiles/<entity_id>.html
```

El perfil muestra resumen de entidad, claims, relaciones publicas, evidencias y entidades relacionadas para navegar manualmente el grafo persistido.

## Navegacion de grafo Fase 4.3

La Fase 4.3 agrega la primera capa navegable de grafo sobre datos ya persistidos en PostgreSQL.

Todos los comandos son de solo lectura, no agregan fuentes nuevas, no usan IA y no cambian la arquitectura.

Ver vecinos directos de una entidad:

```powershell
python scripts/entity_neighbors.py --entity-id <entity_id>
```

Recorrer el grafo con profundidad configurable:

```powershell
python scripts/entity_graph.py --entity-id <entity_id> --depth 2
```

Exportar un HTML del grafo:

```powershell
python scripts/export_entity_graph.py --entity-id <entity_id>
```

Por defecto escribe:

```text
graph_exports/entity_<entity_id>.html
```

Ver un resumen global de tipos de relaciones:

```powershell
python scripts/relationship_summary.py
```

Los perfiles de entidad ahora incluyen:

- vecinos directos
- conteos por tipo de relacion
- enlaces de navegacion hacia perfiles y grafos relacionados

## Helpers de inspeccion del dataset

Para descubrir rapidamente que entidades existen en PostgreSQL y obtener IDs validos para navegacion:

Listar compradores por cantidad de ordenes de compra:

```powershell
python scripts/list_buyers.py
```

Listar proveedores por cantidad de ordenes de compra:

```powershell
python scripts/list_suppliers.py
```

Listar entidades generales con limite configurable:

```powershell
python scripts/list_entities.py --limit 50
```

Listar contratos:

```powershell
python scripts/list_contracts.py
```

Estas utilidades son de solo lectura, usan solo PostgreSQL persistido y reutilizan `entity_explorer`.

## Phase 5.0 DIPRES prototype

Para probar el primer enlace entre dos datasets locales, carga el sample DIPRES marcado como `LOCAL_TEST_DATA / NOT_OFFICIAL_DATA`:

```powershell
python scripts/load_dipres_sample.py
```

Ese comando:

- usa el sample local en `data/sample/dipres_budget_sample.json`
- busca una coincidencia por nombre de organizacion normalizado contra entidades ya persistidas
- guarda `source_record`, `claim`, `evidence`, `entities` y `relationship_public`
- crea un nodo `BUDGET` que apunta a la organizacion compartida

Despues puedes inspeccionar el resumen presupuestario y navegar el grafo:

```powershell
python scripts/budget_summary.py
python scripts/list_entities.py --limit 50
python scripts/entity_graph.py --entity-id <budget-entity-id> --depth 3
python scripts/export_entity_graph.py --entity-id <budget-entity-id>
```

La navegacion queda encadenada como:

```text
BUDGET
-> PUBLIC_ORGANIZATION
-> CONTRACT
-> COMPANY
```

El objetivo de esta fase es demostrar que DatosEnOrden ya puede conectar informacion de dos datasets distintos usando entidades compartidas persistidas en PostgreSQL.

## sync DB from home to work

Flujo local para copiar la base de datos entre PCs usando un dump privado en `private/database/backups/` o un folder local/USB.

En la computadora de origen:

```powershell
python scripts\db\export_local_db.py
```

Eso crea un dump timestamped en `private/database/backups/`.

Copia el archivo `.dump` al USB o al folder local que uses para moverlo.

En la computadora de destino:

```powershell
python scripts\db\import_local_db.py --dump-file <ruta-al-dump> --confirm
```

El script muestra un warning antes de reemplazar la base local. Si falta `--confirm`, no ejecuta el restore.

Verifica el resultado:

```powershell
python scripts\db\verify_db_counts.py
```

## sync DB from work to home

El flujo es el mismo en sentido inverso:

1. En la computadora de trabajo, exporta con `python scripts\db\export_local_db.py`.
2. Copia el dump privado al USB o folder local.
3. En la computadora de casa, restaura con `python scripts\db\import_local_db.py --dump-file <ruta-al-dump> --confirm`.
4. Verifica los conteos con `python scripts\db\verify_db_counts.py`.

Si `pg_dump` o `pg_restore` no estan en `PATH`, agrega la carpeta `bin` de PostgreSQL, por ejemplo `C:\Program Files\PostgreSQL\16\bin`.

## Regla de trabajo

Ningun cambio de modelo persistente debe hacerse solo en SQLAlchemy o solo en SQL. La fuente operativa de evolucion es Alembic.
