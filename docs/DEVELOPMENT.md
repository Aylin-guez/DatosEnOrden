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

## Demo local

Para preparar la demo de la fase 10.5:

```powershell
python scripts/demo_seed.py
python scripts/demo_status.py
streamlit run streamlit_app.py
```

Si quieres activar el modo demo en Streamlit, define `DEMO_MODE=true` en `.env` o en el entorno antes de abrir la app.

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

## Fusion segura de dos bases locales

Si trabajas en casa y en la oficina con dos bases PostgreSQL distintas, usa el merge seguro para unir una copia exportada en la base actual sin sobrescribirla:

```powershell
python scripts/db/merge_local_db.py --file private/database/backups/home.dump --dry-run
python scripts/db/merge_local_db.py --file private/database/backups/home.dump --confirm
```

Este flujo:

- restaura el dump en una base temporal
- compara por claves estables
- inserta solo registros faltantes
- preserva los IDs existentes en la base principal siempre que sea posible
- evita duplicar `source_record`, `entity`, `claim`, `evidence` y `relationship_public`

Usa el mismo comando con el dump de trabajo cuando quieras fusionar en sentido contrario.

Si quieres comprobar el resultado despues de la fusión:

```powershell
python scripts/db/verify_db_counts.py
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

## Registry de datasets

Para ver que datasets reconoce la plataforma y su estado de carga:

```powershell
python scripts/list_datasets.py
```

Para inspeccionar un dataset registrado en detalle:

```powershell
python scripts/dataset_details.py --dataset chilecompra
```

Para exportar un perfil HTML del dataset:

```powershell
python scripts/export_dataset_profile.py --dataset chilecompra
```

Estos helpers:

- usan solo PostgreSQL persistido
- no hacen llamadas a APIs externas
- describen conteos por tipo, relaciones y estadisticas de ingestion
- preparan la navegacion entre datasets futuros

## Capa amigable para humanos

Para explicar una entidad en lenguaje simple:

```powershell
python scripts/explain_entity.py --entity-id <entity_id>
```

Para explicar un dataset sin jerga tecnica:

```powershell
python scripts/explain_dataset.py --dataset chilecompra
```

Para explicar el grafo de una entidad:

```powershell
python scripts/explain_graph.py --entity-id <entity_id>
```

Estas salidas reutilizan PostgreSQL persistido y traducen terminos como `source_record`, `claim`, `relationship_public` y `entity` a lenguaje entendible.

## Explorer local con Streamlit

Para abrir el explorador local con interfaz visual:

```powershell
streamlit run streamlit_app.py
```

La interfaz:

- lee solo `DATABASE_URL` desde `.env`
- usa solo datos ya persistidos en PostgreSQL
- no llama a APIs externas desde la UI
- reutiliza los helpers de dataset, entidades, grafo y explicacion humana

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

## Phase 5.1 Entity Matching Engine

Antes de importar un dataset nuevo, puedes preguntar que entidad existente es la candidata mas probable usando el matcher reutilizable:

```powershell
python scripts/match_entity.py --type PUBLIC_ORGANIZATION --name "SERVICIO DE SALUD ARAUCO"
```

El matcher:

- normaliza mayusculas, acentos, puntuacion, espacios y stopwords comunes
- ordena candidatos por exactitud normalizada, containment y overlap de tokens
- devuelve `candidate_entity_id`, `candidate_name`, `entity_type`, `score`, `match_method` y `explanation`

Este paso no cambia la arquitectura ni agrega fuentes publicas nuevas. Solo reusa entidades ya persistidas en PostgreSQL para responder si un nombre nuevo probablemente ya existe en el grafo.

## Phase 7.0 Lobby prototype

La Fase 7.0 agrega un prototipo local de reuniones de lobby. No llama APIs reales, no scrapea y no integra una fuente publica nueva.

El sample vive en:

```text
data/sample/lobby_meeting_sample.json
```

El archivo esta marcado como:

```text
LOCAL_TEST_DATA
NOT_OFFICIAL_DATA
```

Para cargarlo:

```powershell
python scripts/load_lobby_sample.py
```

Ese comando:

- usa el sample local en `data/sample/lobby_meeting_sample.json`
- busca coincidencias normalizadas contra entidades existentes
- guarda `source_record`, `claim`, `evidence`, entidades y `relationship_public`
- crea un nodo `LOBBY_MEETING`
- conecta el organismo publico y la contraparte con la reunion de muestra

Para resumir lo cargado:

```powershell
python scripts/lobby_summary.py
```

La salida incluye:

- reuniones de lobby
- organismos involucrados
- contrapartes involucradas
- claims
- relaciones publicas
- entidades coincidentes con `match_method` y `confidence`

La navegacion minima esperada queda como:

```text
PUBLIC_ORGANIZATION
-> LOBBY_MEETING
-> COMPANY
```

Si tambien estan cargados ChileCompra y DIPRES, el grafo puede extenderse desde presupuesto y contratos hacia la contraparte:

```text
BUDGET
-> PUBLIC_ORGANIZATION
-> CONTRACT
-> COMPANY
-> LOBBY_MEETING
```

Lenguaje legal y etico:

- una reunion de lobby no implica irregularidad
- una contraparte no implica falta ni delito
- el sample no es dato oficial
- las relaciones solo muestran una reunion registrada o de muestra con evidencia

## Phase 8.0 Lobby <-> ChileCompra cross-dataset exploration

La Fase 8.0 agrega la primera exploracion entre fuentes ya persistidas: ChileCompra y Lobby.

No scrapea, no llama APIs reales de Lobby, no cambia el schema y no modifica datasets existentes. Solo lee entidades, claims, evidencias y `relationship_public` ya guardados.

Comando:

```powershell
python scripts/cross_dataset_summary.py
```

La salida muestra organismos presentes en mas de un dataset publico:

- datasets disponibles
- contratos ChileCompra
- reuniones Lobby
- evidencias
- relaciones publicas
- conexiones Lobby y ChileCompra disponibles

El conteo de evidencias deduplica IDs y considera evidencia enlazada por `claim_id`, `source_record_id` y el `evidence_id` guardado en los claims involucrados.

La lectura es informativa. El sistema presenta conexiones y registros publicos disponibles, sin inferir causalidad ni conclusiones.

## Phase 8.1 Cross-dataset demo alignment

Si `python scripts/cross_dataset_summary.py` muestra `organizations_in_multiple_datasets: 0`, usa el diagnostico:

```powershell
python scripts/debug_cross_dataset_matches.py
```

El diagnostico muestra:

- organismos ChileCompra encontrados
- organismos Lobby encontrados
- nombres normalizados
- candidatos cercanos usando el motor existente de entity matching
- la razon por la que no se detecta un organismo compartido

Para preparar una demo local segura:

```powershell
python scripts/align_lobby_sample_to_existing_org.py
python scripts/load_lobby_sample.py
python scripts/cross_dataset_summary.py
```

El helper solo edita el archivo local `data/sample/lobby_meeting_sample.json`, marcado como `LOCAL_TEST_DATA / NOT_OFFICIAL_DATA`, para usar un organismo ChileCompra ya persistido. No toca datos reales, no agrega APIs y es idempotente.

## Phase 9.0 Transparencia Activa Prototype

La Fase 9.0 agrega un prototipo local de Transparencia Activa. No scrapea, no llama APIs reales y no integra una fuente oficial nueva.

Archivo local:

```powershell
data/sample/transparencia_activa_sample.json
```

El sample esta marcado como `LOCAL_TEST_DATA / NOT_OFFICIAL_DATA`. Usa una persona ficticia llamada `PERSONA DE MUESTRA TRANSPARENCIA` y un cargo de muestra para validar conexiones administrativas con un organismo publico ya persistido.

Comandos:

```powershell
python scripts/load_transparencia_sample.py
python scripts/transparencia_summary.py
python scripts/cross_dataset_summary.py
```

El importador reutiliza la arquitectura existente:

- `source`
- `dataset`
- `source_record`
- `entity`
- `claim`
- `evidence`
- `relationship_public`

Claims creados:

- `ORGANIZATION_HAS_PUBLIC_ROLE`
- `PERSON_HOLDS_PUBLIC_ROLE`
- `ROLE_BELONGS_TO_ORGANIZATION`

Relaciones publicas creadas:

- `PUBLIC_ORGANIZATION -> ROLE`
- `ROLE -> PERSON`
- `ROLE -> PUBLIC_ORGANIZATION`

La explicacion humana usa lenguaje neutral:

- Transparencia Activa muestra informacion administrativa publicada por organismos.
- Este prototipo usa datos de muestra, no datos oficiales.
- No implica irregularidad; solo representa informacion publica o de muestra.

Si el organismo tambien existe en ChileCompra o Lobby, `cross_dataset_summary` puede mostrar `transparencia` como otro dataset disponible para ese organismo. La lectura es solo informativa y no infiere causalidad ni conclusiones.

## Timeline Explorer Fase 10.0

La Fase 10.0 agrega una cronologia unificada por entidad usando solo datos persistidos en PostgreSQL.

Comandos:

```powershell
python scripts/entity_timeline.py --entity-id <entity_id>
python scripts/export_entity_timeline.py --entity-id <entity_id>
```

El exportador escribe por defecto:

```text
reports/entity_timeline_<entity_id>.html
```

Reglas:

- usa `entity`, `claim`, `evidence`, `source_record`, `dataset` y `relationship_public`
- no llama APIs externas
- no scrapea
- no cambia el esquema ni la arquitectura de persistencia
- ordena eventos por fecha ascendente
- muestra fuente, conteo de evidencias y conteo de relaciones

La explicacion ciudadana debe mantenerse neutral:

- Esta cronologia reune los eventos publicos encontrados para esta entidad en distintas fuentes de informacion.
- El orden temporal no implica relacion causal.

## Investigacion de entidad Fase 11.0

La Fase 11.0 unifica la exploracion de una entidad en una sola vista `Investigación` dentro de Streamlit.

Esa vista junta:

- identificacion y tipo de entidad en lenguaje publico
- badges de dataset disponibles
- metricas clave
- cronologia
- grafo resumido
- contratos / procurement
- Lobby
- Transparencia
- evidencia agrupada por dataset
- explicacion ciudadana neutral

La pagina usa solo datos persistidos y no agrega nuevas fuentes, APIs ni scraping.

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
