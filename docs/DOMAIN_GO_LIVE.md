# Go Live de datosenorden.cl

## 1. Dominio

- Comprar o usar `datosenorden.cl`.
- Definir si `www.datosenorden.cl` redirige a dominio raiz.
- Configurar DNS con TTL bajo durante el primer lanzamiento.

DNS sugerido:

```text
A     datosenorden.cl      <IP_DEL_VPS>
CNAME www                  datosenorden.cl
```

## 2. Hosting

Opcion principal: VPS Ubuntu LTS barato.

Instalar:

```bash
sudo apt update
sudo apt install -y python3 python3-venv git postgresql-client
```

Instalar Caddy o Nginx para HTTPS y reverse proxy.

## 3. Codigo y dependencias

```bash
git clone <repo> DatosEnOrden
cd DatosEnOrden
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
```

## 4. Variables de entorno

Crear `.env` en el servidor, no en Git:

```text
DATOSENORDEN_ENV=production
DATOSENORDEN_PUBLIC_BASE_URL=https://datosenorden.cl
DATOSENORDEN_SUPPORT_URL=https://link.mercadopago.cl/datosenorden
DATABASE_URL=postgresql+psycopg://user:password@host:5432/datosenorden
DATOSENORDEN_DATABASE_URL=postgresql+psycopg://user:password@host:5432/datosenorden
DATOSENORDEN_DEBUG_INVESTIGATION=0
```

## 5. Base de datos

- Usar PostgreSQL privado o gestionado.
- No exponer puerto 5432 a internet publico.
- Si se usa demo local, cargar datos antes de abrir dominio.

Carga demo si aplica:

```bash
python scripts/reset_and_load_mvp_demo.py
python scripts/run_demo_check.py
```

Si no corresponde resetear:

```bash
python scripts/run_demo_check.py
```

## 6. Documentos oficiales publicados

Antes del go-live confirmar:

```bash
python scripts/prelaunch_public_check.py
python scripts/deploy_check.py
```

Deben existir:

- `reading.json`
- `document_view.json`
- `document.pdf` publicado
- copia servible en `assets/official_documents/.../document.pdf`

La UI publica no debe depender de `incoming/` ni `processing/`.

## 7. Build y prelaunch

```bash
python scripts/prelaunch_public_check.py
python scripts/deploy_check.py
python scripts/content_readiness.py
python -m pytest -q --basetemp .pytest-tmp-public-domain
python -m reflex compile --dry --no-rich
```

## 8. Levantar app

```bash
python -m reflex run --env prod --single-port --frontend-port ${PORT:-3000} --backend-host 0.0.0.0
```

Para systemd, usar el mismo comando dentro del entorno virtual y reiniciar con:

```bash
sudo systemctl restart datosenorden
sudo journalctl -u datosenorden -f
```

## 9. Verificacion publica

Abrir manualmente:

- `https://datosenorden.cl/`
- `https://datosenorden.cl/topic`
- `https://datosenorden.cl/official-document`
- `https://datosenorden.cl/search`
- `https://datosenorden.cl/ecosystem`
- `https://datosenorden.cl/project`
- `https://datosenorden.cl/support`
- `https://datosenorden.cl/studio`

Verificar:

- HTTPS activo.
- WebSocket Reflex estable.
- Buscador responde.
- Expediente demo abre.
- El documento oficial se ve como PDF.
- Link de apoyo apunta a Mercado Pago.

## 10. Rollback

- Guardar backup previo con `pg_dump "$DATABASE_URL"` fuera del repo.
- Mantener release anterior identificada por commit/tag.
- Si falla frontend, volver al commit anterior y reiniciar servicio.
- Si falla DB, restaurar backup.
- Si falla PDF, retirar temporalmente el asset PDF y dejar fallback `document_view.json`.
- Si falla DNS/HTTPS, volver el proxy a la version anterior o pausar el cambio de DNS.

## Que no publicar todavia

- `.env`.
- Dumps de PostgreSQL.
- Caches de build o test.
- Documentos masivos sin estrategia de almacenamiento.
- Datos sensibles o no verificables.
- Automatizaciones de scraping agresivo.