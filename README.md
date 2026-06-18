# DatosEnOrden

DatosEnOrden es una infraestructura open source para transformar datos públicos de Chile en una base de conocimiento verificable, trazable y reutilizable.

El proyecto no busca interpretar políticamente los datos. Su responsabilidad es ordenar evidencia, preservar trazabilidad y separar claramente los hechos verificables de cualquier análisis u opinión posterior.

## Principios

- Evidencia primero.
- Sin fuente no existe.
- Neutralidad de los datos.
- Opiniones separadas de los datos.
- Código y metodología públicos.
- Arquitectura preparada para crecer.

## Estado

Fase actual: fundación técnica.

La prioridad de esta fase es construir una base estable: esquema PostgreSQL, migraciones, estructura backend, documentación técnica y configuración local. No hay ETLs específicos implementados todavía.

## Stack

- Python 3.12+
- PostgreSQL 16
- SQLAlchemy 2.x
- Alembic
- FastAPI

## Estructura

```text
.
├── alembic/                 # Migraciones versionadas
├── backend/                 # Reservado para despliegue/backend app si se separa del paquete
├── data/                    # Datos locales ignorados por Git
├── database/                # SQL de referencia
├── docs/                    # Documentación técnica y decisiones
├── etl/                     # Futuros pipelines ETL, no implementados en Fase 1
├── scripts/                 # Automatización operacional futura
├── src/datosenorden/        # Código Python principal
└── tests/                   # Tests automatizados
```

## Desarrollo local

1. Crear entorno:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
```

2. Configurar variables:

```powershell
Copy-Item .env.example .env
```

3. Preparar PostgreSQL nativo:

Revisa la guia de [Desarrollo local](docs/DEVELOPMENT.md) para crear la base, configurar `DATABASE_URL` y ejecutar las migraciones.

4. Aplicar migraciones:

```powershell
alembic upgrade head
```

5. Ejecutar API base:

```powershell
uvicorn datosenorden.api.app:app --reload
```

6. Verificar:

```powershell
pytest
```

## Documentación clave

- [Visión](docs/VISION.md)
- [Roadmap técnico](docs/TECHNICAL_ROADMAP.md)
- [Arquitectura](docs/ARCHITECTURE.md)
- [Schema](docs/SCHEMA.md)
- [Crítica del schema](docs/SCHEMA_REVIEW.md)
- [Desarrollo local](docs/DEVELOPMENT.md)
- [ETL ChileCompra](docs/etl/CHILECOMPRA.md)
- [Fuentes](docs/SOURCES.md)
- [Decisiones](docs/DECISIONS.md)
- [Ideas](docs/IDEAS.md)
- [Changelog](docs/CHANGELOG.md)
- [Politica legal y etica](docs/LEGAL_ETHICS.md)

## Licencia

MIT
