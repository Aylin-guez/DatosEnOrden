# Deployment

DatosEnOrden puede publicarse como MVP publico/demo con Reflex actual. La recomendacion inicial es no migrar framework todavia: estabilizar dominio, demo, base de datos, backups y monitoreo basico.

## Opcion Recomendada: VPS Simple

Adecuado para MVP con trafico bajo y control de archivos, logs y proxy.

Componentes:

- Ubuntu LTS.
- Python `>=3.12`.
- PostgreSQL local privado o PostgreSQL gestionado.
- Nginx o Caddy como reverse proxy.
- Servicio systemd para Reflex.
- Dominio con HTTPS.

Ventajas:

- Control claro del proceso Reflex y WebSocket.
- Backups simples con `pg_dump`.
- Menos sorpresas con build/runtime que en PaaS.

Costos:

- Requiere administrar actualizaciones, firewall, logs y certificados.

## Alternativa: Render, Railway o Fly.io

Puede funcionar si el proveedor soporta:

- Servicio web Python persistente.
- WebSocket estable.
- PostgreSQL gestionado.
- Variables de entorno.
- Comando start custom.

Usar esta opcion si se prefiere menor administracion de servidor. Validar primero en staging porque Reflex depende de comunicacion cliente-servidor.

## Base De Datos

Produccion demo debe usar PostgreSQL. Evitar SQLite para dominio publico.

Variable requerida:

```text
DATABASE_URL=postgresql+psycopg://user:password@host:5432/datosenorden
```

En VPS, PostgreSQL puede ser local si no se expone a internet. Para menor operacion, usar PostgreSQL gestionado con firewall/IP allowlist.

## Instalacion En VPS

```bash
git clone <repo> DatosEnOrden
cd DatosEnOrden
python -m venv .venv
source .venv/bin/activate
python -m pip install -e .
```

Crear `.env` en el servidor con `DATABASE_URL`.

## Cargar Demo Seed

```bash
python scripts/reset_and_load_mvp_demo.py
python scripts/verify_mvp_demo.py
python scripts/demo_ready_check.py
```

Si no se quiere resetear la DB, usar solo:

```bash
python scripts/load_complete_demo_case.py
python scripts/verify_mvp_demo.py
```

## Validar Prelaunch

```bash
python scripts/prelaunch_check.py
python scripts/run_demo_check.py
python -m pytest -q --basetemp .pytest-tmp-launch
python -m reflex compile --dry --no-rich
```

## Comando Start

Comando base:

```bash
python -m reflex run --env prod --backend-host 0.0.0.0
```

Si el proveedor exige puerto:

```bash
python -m reflex run --env prod --backend-host 0.0.0.0 --backend-port ${PORT:-8000}
```

Mantener `DATABASE_URL` configurado en el ambiente del proceso.

## Reverse Proxy

Exponer solo HTTPS publico:

- `https://dominio.cl/` -> Reflex frontend.
- Verificar que WebSocket/backend de Reflex funcione detras del proxy.
- Redirigir HTTP a HTTPS.

Puertos habituales:

- Publico: `80`, `443`.
- Interno Reflex frontend: `3000`.
- Interno Reflex backend: `8000`.
- PostgreSQL: privado.

## Health Check

Health check simple para MVP:

```bash
curl -I https://dominio.cl/
```

Validaciones funcionales:

```bash
python scripts/prelaunch_check.py
python scripts/demo_ready_check.py
```

URLs manuales:

- `/`
- `/demo`
- `/knowledge`
- `/tracking`
- `/reports`
- `/investigation?id=SERVICIO%20DE%20SALUD%20ARAUCO%20HOSPITAL%20DE%20ARAUCO`

## Backups

Antes de deploy o recarga demo:

```bash
pg_dump "$DATABASE_URL" > backups/datosenorden_$(date +%Y%m%d_%H%M%S).sql
```

Guardar backups fuera del repo y probar restauracion periodicamente.

## Logs

En VPS, usar systemd:

```bash
journalctl -u datosenorden -f
```

No activar debug en produccion salvo diagnostico temporal:

```text
DATOSENORDEN_DEBUG_INVESTIGATION=0
```

## Notas De Seguridad

- No publicar `.env`.
- No exponer PostgreSQL.
- No cargar datos reales sensibles en esta fase.
- Mantener avisos `LOCAL_TEST_DATA` / `NOT_OFFICIAL_DATA`.
- No afirmar causalidad, irregularidad ni responsabilidad.
