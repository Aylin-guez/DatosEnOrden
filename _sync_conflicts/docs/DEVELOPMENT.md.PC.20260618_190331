# Desarrollo local

## Requisitos

- Python 3.12 o superior.
- Docker Desktop o PostgreSQL local.
- Git.

## Instalación

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
Copy-Item .env.example .env
```

## Base de datos

```powershell
docker compose up -d postgres
alembic upgrade head
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

Crear una migración nueva:

```powershell
alembic revision --autogenerate -m "descripcion"
```

Aplicar migraciones:

```powershell
alembic upgrade head
```

Revertir una migración:

```powershell
alembic downgrade -1
```

## Regla de trabajo

Ningún cambio de modelo persistente debe hacerse solo en SQLAlchemy o solo en SQL. La fuente operativa de evolución es Alembic.
