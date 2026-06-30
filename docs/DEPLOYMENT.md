# Deployment

DatosEnOrden esta preparado para demo local y puede publicarse como demo controlada. No desplegar con datos sensibles ni credenciales compartidas.

## Opcion 1: Demo local

Uso recomendado para presentaciones presenciales o grabaciones.

```powershell
python scripts/reset_and_load_mvp_demo.py
python -m reflex run
```

URLs:

- `http://localhost:3000/demo`
- `http://localhost:3000/investigation?id=SERVICIO+DE+SALUD+ARAUCO+HOSPITAL+DE+ARAUCO`

## Opcion 2: VPS simple

Adecuado para una demo publica con trafico bajo.

Componentes:

- Ubuntu LTS
- Python compatible con el proyecto
- PostgreSQL administrado o local
- Nginx como reverse proxy
- Servicio systemd para Reflex

Variables:

```text
DATABASE_URL=postgresql+psycopg://user:password@host:5432/datosenorden
```

Comando app:

```bash
python -m reflex run --env prod
```

Recomendaciones:

- Usar HTTPS.
- No exponer PostgreSQL a internet.
- Mantener backups antes de cargar datos nuevos.
- Separar demo local de cualquier ambiente con datos reales.

## Opcion 3: Render, Railway o Fly.io

Puede aplicar si el runtime soporta Reflex, persistencia de build y conexion PostgreSQL estable.

Requisitos:

- Servicio web Python.
- PostgreSQL externo.
- Variables de entorno configuradas en el panel.
- Comando de inicio equivalente a `python -m reflex run --env prod`.

Advertencias:

- Revisar limites de memoria y build time.
- Evitar SQLite para demo publica.
- Validar WebSocket/proxy porque Reflex depende de comunicacion cliente-servidor.

## Seguridad minima

- No publicar `.env`.
- No subir dumps con datos personales reales sin base legal.
- Marcar demos con `LOCAL_TEST_DATA` y `NOT_OFFICIAL_DATA`.
- No presentar cruces como causalidad, irregularidad ni responsabilidad.
- Agregar autenticacion si se usan datos no publicos o ambientes internos.

## Checklist antes de publicar

```powershell
python scripts/run_demo_check.py
python scripts/demo_ready_check.py
python -m pytest -q
python -m reflex compile --dry --no-rich
```
