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

### Error de rol o base inexistente

Si el usuario o la base no existen, recrea ambos con los comandos de esta guia y vuelve a ejecutar:

```powershell
alembic upgrade head
```

## Regla de trabajo

Ningun cambio de modelo persistente debe hacerse solo en SQLAlchemy o solo en SQL. La fuente operativa de evolucion es Alembic.
