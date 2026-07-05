# Public Launch Checklist

Checklist minimo para publicar DatosEnOrden en `datosenorden.cl` como MVP publico con Reflex. Esta version asume una demo controlada, sin login, pagos, scraping productivo ni cargas masivas de documentos.

## Estado Actual Auditado

- `pyproject.toml`: paquete Python `>=3.12`, dependencias Reflex/FastAPI/SQLAlchemy/PostgreSQL.
- `rxconfig.py`: app Reflex `reflex_app` con sitemap y Tailwind.
- `reflex_app/`: UI publica principal y rutas Reflex.
- `assets/`: contiene `favicon.ico`; PDFs publicos deben copiarse aqui para ser servidos por Reflex.
- `.env.example`: define variables de ambiente locales y PostgreSQL.
- `deployment/` y `docs/DEPLOYMENT.md`: ya documentan VPS, reverse proxy y comandos base.
- `scripts/prelaunch_check.py`: valida demo, DB y exportaciones.
- `scripts/content_readiness.py`: valida artefactos editoriales y documento oficial publicado.
- `scripts/run_demo_check.py`: valida la demo end to end y compila Reflex.

## Dominio

- DNS `datosenorden.cl` apuntando al hosting elegido.
- Redireccion HTTP -> HTTPS.
- Certificado TLS activo antes de anunciar publicamente.
- Probar manualmente `/`, `/topic`, `/search`, `/ecosystem`, `/project`, `/investigation`, `/reports`, `/tracking`.

## Hosting

Opcion minima recomendada: VPS Ubuntu LTS con Python 3.12+, PostgreSQL privado y Nginx/Caddy.

Alternativa: Render, Railway o Fly.io solo si soporta WebSocket estable, puerto backend configurable y PostgreSQL gestionado.

Comandos base:

```bash
python -m pip install -e .
python -m reflex compile --dry --no-rich
python -m reflex run --env prod --backend-host 0.0.0.0
```

Si el proveedor asigna puerto:

```bash
python -m reflex run --env prod --backend-host 0.0.0.0 --backend-port ${PORT:-8000}
```

## Variables

Minimas:

```text
DATOSENORDEN_ENV=production
DATABASE_URL=postgresql+psycopg://user:password@host:5432/datosenorden
DATOSENORDEN_DATABASE_URL=postgresql+psycopg://user:password@host:5432/datosenorden
```

Opcionales/controladas:

```text
DATOSENORDEN_DEBUG_INVESTIGATION=0
DATOSENORDEN_CHILECOMPRA_TICKET=
```

No publicar `.env`, tokens, dumps, backups ni datos privados.

## Base De Datos

- Usar PostgreSQL, no SQLite, para dominio publico.
- PostgreSQL debe ser privado: firewall, red interna o allowlist.
- Cargar solo la demo aprobada.
- Verificar antes del deploy:

```bash
python scripts/prelaunch_check.py
python scripts/run_demo_check.py
```

## Assets

- `assets/favicon.ico` debe existir.
- Si se genera `document.pdf`, mantener dos copias:
  - Canonica/versionable: `data/official_documents/published/senado-docto-9000-mensaje_mocion/document.pdf`.
  - Servible por Reflex: `assets/official_documents/senado-docto-9000-mensaje_mocion/document.pdf`.
- Para mas documentos o PDFs pesados, usar object storage futuro. No convertir `assets/` en repositorio de archivos masivos.

## Documentos Oficiales

Requeridos para el MVP actual:

- `data/official_documents/published/senado-docto-9000-mensaje_mocion/reading.json`
- `data/official_documents/published/senado-docto-9000-mensaje_mocion/document_view.json`

Opcional:

- `data/official_documents/published/senado-docto-9000-mensaje_mocion/document.pdf`

Si no hay PDF, `/topic` debe caer a `document_view.json` y seguir funcionando.

## Seguridad Basica

- HTTPS obligatorio.
- No exponer PostgreSQL.
- No activar debug publico salvo diagnostico temporal.
- No publicar `incoming/`, `processing/`, dumps ni backups.
- Mantener lenguaje neutral: no afirmar causalidad, irregularidad ni responsabilidad.
- Revisar que datos demo esten marcados como muestra cuando corresponda.

## Backups

Antes de deploy, recarga demo o migracion:

```bash
pg_dump "$DATABASE_URL" > backups/datosenorden_$(date +%Y%m%d_%H%M%S).sql
```

Guardar backups fuera del repo y probar restauracion en staging/local.

## Logs

- VPS: `journalctl -u datosenorden -f`.
- PaaS: usar logs del proveedor.
- No imprimir credenciales ni payloads sensibles.
- Rotar logs si se usa VPS.

## Monitoreo

Minimo para MVP:

- Health check HTTP a `https://datosenorden.cl/`.
- Revision manual diaria de `/topic` y `/search` durante la primera semana.
- Alerta basica si el proceso Reflex cae.
- Backups verificados.

## Rollback

- Mantener release anterior o commit anterior disponible.
- Guardar backup DB previo al deploy.
- Si falla Reflex: volver al release anterior y reiniciar servicio.
- Si falla DB: restaurar backup y mantener sitio en mantenimiento.
- Si falla documento PDF: retirar PDF y dejar fallback `document_view.json`.

## Que NO Publicar Todavia

- Login, roles o cuentas ciudadanas.
- Pagos, donaciones o suscripciones.
- Scraping o consumo masivo de APIs externas.
- Datos reales sensibles sin revision legal/editorial.
- PDFs/documentos masivos dentro del repo.
- APIs publicas productivas.
- Promesas de deteccion de irregularidades o causalidad.

## Apoyo Futuro

No implementar pagos/donaciones todavia. Si se decide despues, ubicarlo discretamente en:

- footer;
- pagina `Proyecto`;
- bloque de apoyo al final de `Lectura`.

## Validacion Final

```bash
python scripts/prelaunch_public_check.py
python scripts/run_demo_check.py
python scripts/content_readiness.py
python -m pytest -q --basetemp .pytest-tmp-public-launch
python -m reflex compile --dry --no-rich
```
