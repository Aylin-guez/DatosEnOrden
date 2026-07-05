# Deployment para datosenorden.cl

## Opcion recomendada

La opcion principal para el MVP publico es un VPS barato con Ubuntu LTS, Caddy o Nginx, PostgreSQL privado y un servicio systemd para Reflex.

Se recomienda VPS por tres razones:

- Reflex usa backend persistente y WebSocket; en VPS se controla proxy, puertos y logs sin restricciones del PaaS.
- El MVP necesita servir artefactos locales publicados, incluyendo `assets/official_documents/.../document.pdf`.
- Los backups con `pg_dump`, rollback y observabilidad basica son mas directos.

Render, Fly o Railway pueden funcionar como alternativa si soportan WebSocket estable, puerto backend configurable, PostgreSQL gestionado y almacenamiento de assets en build. Para el primer dominio publico conviene reducir variables operacionales.

## Como corre hoy

La app publica es Reflex:

```bash
python -m reflex run --env prod --single-port --frontend-port ${PORT:-3000} --backend-host 0.0.0.0
```

Validacion de build:

```bash
python -m reflex compile --dry --no-rich
```

Checks previos:

```bash
python scripts/prelaunch_public_check.py
python scripts/deploy_check.py
python scripts/run_demo_check.py
python scripts/content_readiness.py
```

## Variables requeridas

```text
DATOSENORDEN_ENV=production
DATOSENORDEN_PUBLIC_BASE_URL=https://datosenorden.cl
DATOSENORDEN_SUPPORT_URL=https://link.mercadopago.cl/datosenorden
DATABASE_URL=postgresql+psycopg://user:password@host:5432/datosenorden
DATOSENORDEN_DATABASE_URL=postgresql+psycopg://user:password@host:5432/datosenorden
DATOSENORDEN_DEBUG_INVESTIGATION=0
```

`DATOSENORDEN_DATABASE_URL` queda como alias compatible. La app debe leer `DATABASE_URL` como fuente principal.

## Artefactos publicados necesarios

La UI publica no debe depender de `incoming/` ni `processing/` para el dominio. Para el documento demo deben existir:

```text
data/official_documents/published/senado-docto-9000-mensaje_mocion/reading.json
data/official_documents/published/senado-docto-9000-mensaje_mocion/document_view.json
data/official_documents/published/senado-docto-9000-mensaje_mocion/document.pdf
assets/official_documents/senado-docto-9000-mensaje_mocion/document.pdf
```

`document.pdf` en `data/official_documents/published` es el artefacto canonico. La copia en `assets/` es la version servible por Reflex.

## Comandos de servidor

```bash
git clone <repo> DatosEnOrden
cd DatosEnOrden
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
cp .env.example .env
```

Editar `.env` con credenciales reales. No commitear `.env`.

Validar:

```bash
python scripts/prelaunch_public_check.py
python scripts/deploy_check.py
python scripts/run_demo_check.py
python -m reflex compile --dry --no-rich
```

Levantar:

```bash
python -m reflex run --env prod --single-port --frontend-port ${PORT:-3000} --backend-host 0.0.0.0
```

## DNS, HTTPS y WebSocket

DNS minimo:

```text
A     datosenorden.cl      <IP_DEL_VPS>
CNAME www                  datosenorden.cl
```

Proxy:

- Redirigir HTTP a HTTPS.
- Mantener WebSocket habilitado.
- No exponer PostgreSQL.
- Publicar `/` y `/api/*` desde el mismo proceso Reflex.

Con Caddy, usar `datosenorden.cl` como host y proxy hacia el puerto unico de Reflex. Con Nginx, incluir headers `Upgrade` y `Connection` para WebSocket.

## Seguridad minima

- `.env` solo en servidor.
- PostgreSQL privado o con allowlist.
- `DATOSENORDEN_DEBUG_INVESTIGATION=0`.
- Backups fuera del repo.
- No trackear caches, `.pytest_cache`, `.bun-cache`, `__pycache__` ni dumps.
- No subir documentos masivos al repo; para escala usar object storage.

## Rollback

1. Mantener release anterior como tag o carpeta previa.
2. Antes de recargar demo, ejecutar `pg_dump "$DATABASE_URL"` fuera del repo.
3. Si falla PDF, retirar solo el asset PDF y usar fallback `document_view.json`.
4. Si falla app, volver al commit anterior y reiniciar systemd.
5. Si falla DB, restaurar backup y dejar sitio en mantenimiento temporal.