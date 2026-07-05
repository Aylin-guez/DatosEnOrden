# VPS Go Live Steps

Guia practica para desplegar DatosEnOrden en una VPS Ubuntu 24.04 LTS con Caddy, PostgreSQL local privado y systemd.

Supuestos de esta guia:

- El repo se desplegara en `/opt/datosenorden`.
- El servicio correra como usuario `datosenorden`.
- Reflex correra en modo `single-port` en `127.0.0.1:3000`.
- API y WebSocket de Reflex viviran bajo `/api` en ese mismo puerto.
- Caddy publicara el sitio y enviara todo el trafico al proceso Reflex local.
- En el servidor se usan comandos `python3`, no `py -3.14`.

## 1. Comprar una VPS Ubuntu 24.04 LTS

Elige una VPS Ubuntu 24.04 LTS con al menos:

- 2 vCPU
- 4 GB RAM
- 40 GB SSD

No uses Ubuntu 22.04 para este pack salvo que aprovisiones Python 3.12+ manualmente antes de seguir.

## 2. Obtener la IP publica

Guarda la IP publica que te entregue el proveedor. La vas a usar en DNS y SSH.

Ejemplo:

```text
203.0.113.10
```

## 3. Entrar por SSH desde Windows PowerShell

En Windows PowerShell:

```powershell
ssh root@203.0.113.10
```

Si tu proveedor usa usuario inicial `ubuntu`, usa:

```powershell
ssh ubuntu@203.0.113.10
```

## 4. Actualizar el servidor

Una vez dentro de la VPS:

```bash
sudo apt update
sudo apt upgrade -y
sudo reboot
```

Vuelve a entrar por SSH despues del reinicio.

## 5. Crear el usuario del sistema

Si todavia no existe el usuario de la app:

```bash
sudo useradd --system --create-home --shell /bin/bash datosenorden
```

Confirma:

```bash
id datosenorden
```

## 6. Clonar el repo

Instala Git si hace falta y clona el repo en la carpeta final:

```bash
sudo mkdir -p /opt/datosenorden
sudo chown -R datosenorden:datosenorden /opt/datosenorden
sudo -u datosenorden git clone <REPO_URL> /opt/datosenorden
cd /opt/datosenorden
```

Si el repo ya existe:

```bash
cd /opt/datosenorden
sudo -u datosenorden git pull --ff-only
```

## 7. Copiar el .env productivo

Usa el template nuevo:

```bash
cd /opt/datosenorden
sudo -u datosenorden cp deployment/production.env.example .env
sudo -u datosenorden nano .env
```

Cambia como minimo:

- `DATOSENORDEN_PUBLIC_BASE_URL=https://beta.datosenorden.cl` para la etapa beta
- `API_URL=https://beta.datosenorden.cl`
- `REFLEX_API_URL=https://beta.datosenorden.cl`
- ambos `CHANGE_ME` de PostgreSQL

Advertencias:

- Nunca commitear `.env`.
- PostgreSQL debe quedar privado en `localhost`.
- Cuando pases de beta a produccion, cambia `beta.datosenorden.cl` por `datosenorden.cl` y reinicia el servicio.

## 8. Crear la base de datos y el usuario PostgreSQL

Instala la base, Caddy y Node si todavia no lo hiciste:

```bash
cd /opt/datosenorden
sudo bash scripts/server_setup_ubuntu.sh
```

Crea o actualiza el rol de PostgreSQL:

```bash
sudo -u postgres psql -d postgres -c "DO \$\$ BEGIN IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'datosenorden') THEN CREATE ROLE datosenorden LOGIN PASSWORD 'CHANGE_ME'; ELSE ALTER ROLE datosenorden WITH LOGIN PASSWORD 'CHANGE_ME'; END IF; END \$\$;"
```

Crea la base si no existe:

```bash
sudo -u postgres psql -tAc "SELECT 1 FROM pg_database WHERE datname='datosenorden'" | grep -q 1 || sudo -u postgres createdb -O datosenorden datosenorden
```

Opcional pero recomendado para backups sin exponer password en comandos:

```bash
sudo -u datosenorden bash -c 'printf "localhost:5432:datosenorden:datosenorden:%s\n" "CHANGE_ME" > /home/datosenorden/.pgpass && chmod 600 /home/datosenorden/.pgpass'
```

Confirma versiones minimas del host:

```bash
python3 --version
node --version
npm --version
```

`python3` debe ser `>= 3.12` y `node` debe ser `>= 22.12.0`.

## 9. Crear el entorno virtual

```bash
cd /opt/datosenorden
sudo -u datosenorden python3 -m venv .venv
sudo -u datosenorden /opt/datosenorden/.venv/bin/python3 -m pip install --upgrade pip
```

## 10. Instalar dependencias

```bash
cd /opt/datosenorden
sudo -u datosenorden /opt/datosenorden/.venv/bin/python3 -m pip install -e .
```

Si necesitas conversion DOC a PDF en el servidor, deja `libreoffice-writer` instalado.

## 11. Migrar y cargar la demo base

En una base limpia, el deploy publico no puede saltarse migraciones ni seed inicial:

```bash
cd /opt/datosenorden
sudo -u datosenorden bash -lc 'set -a && source .env && set +a && source .venv/bin/activate && python3 -m alembic upgrade head && python3 scripts/reset_and_load_mvp_demo.py'
```

## 12. Ejecutar checks

```bash
cd /opt/datosenorden
sudo -u datosenorden bash -lc 'set -a && source .env && set +a && source .venv/bin/activate && python3 --version && node --version && npm --version && python3 scripts/deploy_check.py && python3 scripts/prelaunch_public_check.py && python3 scripts/run_demo_check.py && python3 scripts/content_readiness.py && python3 -m pytest -q --basetemp .pytest-tmp-go-live-pack && python3 -m reflex compile --dry --no-rich'
```

Si alguno falla, no sigas al dominio publico hasta corregirlo.

## 13. Probar Reflex local en el servidor

Primero carga el `.env` y corre Reflex manualmente:

```bash
cd /opt/datosenorden
sudo -u datosenorden bash -lc 'set -a && source .env && set +a && source .venv/bin/activate && python3 -m reflex run --env prod --single-port --frontend-port 3000 --backend-host 127.0.0.1'
```

En otra sesion SSH, revisa que el mismo proceso responda HTML y healthcheck:

```bash
curl -I http://127.0.0.1:3000
curl -I http://127.0.0.1:3000/api/_health
```

Cuando termines, vuelve a la primera sesion y presiona `Ctrl+C`.

## 14. Instalar el service de systemd

```bash
cd /opt/datosenorden
sudo cp deployment/datosenorden.service /etc/systemd/system/datosenorden.service
sudo chown -R datosenorden:datosenorden /opt/datosenorden
sudo systemctl daemon-reload
sudo systemctl enable --now datosenorden
sudo systemctl status datosenorden --no-pager
```

## 15. Configurar Caddy

```bash
cd /opt/datosenorden
sudo cp deployment/Caddyfile /etc/caddy/Caddyfile
sudo caddy validate --config /etc/caddy/Caddyfile
sudo systemctl reload caddy
sudo systemctl status caddy --no-pager
```

## 16. Apuntar beta.datosenorden.cl al VPS

Crea el registro DNS beta:

```text
A    beta.datosenorden.cl    203.0.113.10
```

Verifica propagacion:

```powershell
nslookup beta.datosenorden.cl 1.1.1.1
```

## 17. Probar healthcheck

Cuando el DNS beta resuelva al VPS:

```bash
cd /opt/datosenorden
sudo -u datosenorden bash -lc 'source .venv/bin/activate && python3 scripts/healthcheck_public.py https://beta.datosenorden.cl'
```

Revisa manualmente tambien:

- `https://beta.datosenorden.cl/`
- `https://beta.datosenorden.cl/topic`
- `https://beta.datosenorden.cl/search`
- `https://beta.datosenorden.cl/sources`
- `https://beta.datosenorden.cl/support`
- `https://beta.datosenorden.cl/studio`
- `https://beta.datosenorden.cl/chronology`

## 18. Apuntar datosenorden.cl cuando beta este estable

Actualiza `.env`:

```bash
cd /opt/datosenorden
sudo -u datosenorden nano .env
```

Cambia:

- `DATOSENORDEN_PUBLIC_BASE_URL=https://datosenorden.cl`
- `API_URL=https://datosenorden.cl`
- `REFLEX_API_URL=https://datosenorden.cl`

Reinicia:

```bash
sudo systemctl restart datosenorden
```

Configura DNS final:

```text
A      datosenorden.cl      203.0.113.10
CNAME  www                  datosenorden.cl
```

Vuelve a correr:

```bash
cd /opt/datosenorden
sudo -u datosenorden bash -lc 'source .venv/bin/activate && python3 scripts/healthcheck_public.py https://datosenorden.cl'
```

## 19. Comandos para ver logs

```bash
sudo journalctl -u datosenorden -f
sudo journalctl -u caddy -f
sudo journalctl -u postgresql -f
sudo systemctl status datosenorden --no-pager
sudo ss -ltnp | grep -E ":80|:443|:3000|:5432"
```

## 20. Comandos para rollback

Volver al commit anterior:

```bash
cd /opt/datosenorden
sudo -u datosenorden git log --oneline -n 5
sudo -u datosenorden git checkout <PREVIOUS_COMMIT>
sudo -u datosenorden /opt/datosenorden/.venv/bin/python3 -m pip install -e .
sudo systemctl restart datosenorden
```

Restaurar una copia de PostgreSQL:

```bash
gunzip -c /var/backups/datosenorden/postgres-datosenorden-<TIMESTAMP>.sql.gz | psql -h localhost -U datosenorden -d datosenorden
```

Si el problema es DNS o HTTPS, deja `beta.datosenorden.cl` activo y no cambies el dominio raiz hasta estabilizar.

## 21. Comandos para backup

Backup manual:

```bash
cd /opt/datosenorden
sudo -u datosenorden env PGHOST=localhost PGPORT=5432 PGUSER=datosenorden PGDATABASE=datosenorden /opt/datosenorden/scripts/backup_postgres.sh
```

Ver backups:

```bash
sudo ls -lh /var/backups/datosenorden
```

Cron diario simple a las 03:15:

```bash
sudo crontab -e
```

Agregar:

```cron
15 3 * * * sudo -u datosenorden env PGHOST=localhost PGPORT=5432 PGUSER=datosenorden PGDATABASE=datosenorden /opt/datosenorden/scripts/backup_postgres.sh >> /var/log/datosenorden/backup.log 2>&1
```