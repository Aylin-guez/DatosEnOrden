# Launch Checklist

Checklist para publicar DatosEnOrden como MVP publico/demo con Reflex actual. No cubre datos reales sensibles, login, pagos, scraping ni APIs externas.

## Requisitos Para Publicar

- Repositorio limpio o con cambios revisados.
- Python compatible con `pyproject.toml` (`>=3.12`).
- Dependencias instaladas desde el proyecto.
- PostgreSQL disponible y no expuesto directamente a internet.
- Demo local cargada con datos marcados como `LOCAL_TEST_DATA` / `NOT_OFFICIAL_DATA`.
- Reflex compila en modo dry run.
- Dominio apuntando al servidor o proveedor.
- HTTPS activo.
- Backups definidos antes de publicar.

## Variables De Entorno

Minimas:

```text
DATABASE_URL=postgresql+psycopg://user:password@host:5432/datosenorden
```

Opcionales:

```text
DATOSENORDEN_DEBUG_INVESTIGATION=0
```

No publicar `.env`, dumps, credenciales ni datos personales reales.

## Build Y Run

Validacion:

```powershell
python scripts/prelaunch_check.py
python scripts/run_demo_check.py
python scripts/demo_ready_check.py
python -m pytest -q --basetemp .pytest-tmp-launch
python -m reflex compile --dry --no-rich
```

Ejecucion local:

```powershell
python -m reflex run
```

Ejecucion recomendada para MVP en servidor:

```bash
python -m reflex run --env prod --backend-host 0.0.0.0
```

## Base De Datos

- Usar PostgreSQL para demo publica.
- Cargar demo con:

```powershell
python scripts/reset_and_load_mvp_demo.py
```

- Verificar:

```powershell
python scripts/verify_mvp_demo.py
python scripts/demo_ready_check.py
```

## Puertos

- Reflex frontend: `3000`.
- Reflex backend: `8000` por defecto.
- Nginx/Caddy debe exponer solo `80/443` al publico.
- PostgreSQL debe quedar privado.

## Dominio Y SSL

- Crear DNS `A` o `CNAME` hacia el servidor/proveedor.
- Activar HTTPS con Let's Encrypt, Caddy o TLS gestionado del proveedor.
- Redirigir HTTP a HTTPS.
- Verificar WebSocket/proxy para Reflex.

## Backups

- Backup de PostgreSQL antes de cada carga demo o deploy.
- Guardar backups fuera del repo.
- Probar restauracion en ambiente local o staging.
- No subir `private/`, dumps ni `.env`.

## Logs

- Capturar logs del proceso Reflex con systemd, proveedor o contenedor.
- Rotar logs si se usa VPS.
- No imprimir credenciales ni payloads sensibles.
- Mantener `DATOSENORDEN_DEBUG_INVESTIGATION` apagado en publico salvo diagnostico temporal.

## Seguridad Minima

- HTTPS obligatorio.
- `.env` fuera de Git.
- DB cerrada a internet.
- Usuario DB con permisos acotados.
- Firewall con puertos publicos minimos.
- Avisos visibles de demo/no oficial.
- Tono neutral: no afirmar causalidad, irregularidad ni responsabilidad.

## No Esta Listo Todavia

- Login y roles.
- Pagos, donaciones o suscripciones.
- Scraping o APIs externas en produccion.
- Pipeline de PDFs pesados.
- Moderacion editorial para datos reales.
- Observabilidad avanzada.
- CDN y cache fino.
- Estrategia legal completa para publicar datos no demo.
