# First Deploy Troubleshooting

Guia practica para usar durante el primer deploy publico en la VPS.

Regla base del stack actual:

- Ubuntu 24.04 LTS
- Python `>=3.12`
- Node `>=22.12.0`
- Reflex backend-only sobre `127.0.0.1:3000`
- Caddy sirviendo el frontend preparado y haciendo proxy de `/api` a `127.0.0.1:3000`
- PostgreSQL privado en `localhost`

## Reflex no inicia

Problema

Reflex no queda arriba o `systemd` lo reinicia.

Posible causa

- El comando usa el esquema viejo de dos puertos.
- `.env` no existe o no se carga.
- Python o Node no cumplen version minima.
- Faltan dependencias en `.venv`.

Comando para diagnosticar

```bash
sudo systemctl status datosenorden --no-pager
sudo journalctl -u datosenorden -n 100 --no-pager
sudo -u datosenorden bash -lc 'cd /opt/datosenorden && source .venv/bin/activate && python3 --version && node --version && npm --version'
```

Como solucionarlo

El release inmutable no se ejecuta ni recompila manualmente. Reinicie solamente
el servicio que consume los artefactos ya preparados:

```bash
sudo systemctl restart datosenorden
```

## PostgreSQL no responde

Problema

La app no conecta a PostgreSQL o `run_demo_check.py` falla por DB.

Posible causa

- Servicio PostgreSQL caido.
- `DATABASE_URL` incorrecta.
- Rol o base no existen.
- Migraciones no ejecutadas.

Comando para diagnosticar

```bash
sudo systemctl status postgresql --no-pager
sudo -u postgres psql -d postgres -c "\du"
sudo -u postgres psql -lqt | grep datosenorden
sudo -u datosenorden bash -lc 'cd /opt/datosenorden && set -a && source .env && set +a && source .venv/bin/activate && python3 -m alembic current'
```

Como solucionarlo

```bash
sudo systemctl restart postgresql
sudo -u datosenorden bash -lc 'cd /opt/datosenorden && set -a && source .env && set +a && source .venv/bin/activate && python3 -m alembic upgrade head && python3 scripts/reset_and_load_mvp_demo.py'
```

## Error de permisos

Problema

El servicio no puede leer `.env`, escribir reports o acceder a `/opt/datosenorden`.

Posible causa

- El repo quedo con owner `root`.
- `.pgpass` no tiene permisos `600`.
- Archivos copiados con usuario incorrecto.

Comando para diagnosticar

```bash
ls -ld /opt/datosenorden /opt/datosenorden/.venv /opt/datosenorden/.env
ls -l /home/datosenorden/.pgpass
namei -l /opt/datosenorden/.env
```

Como solucionarlo

```bash
sudo chown -R datosenorden:datosenorden /opt/datosenorden
sudo chown datosenorden:datosenorden /home/datosenorden/.pgpass
sudo chmod 600 /home/datosenorden/.pgpass
```

## Caddy devuelve 502

Problema

El dominio responde, pero Caddy devuelve `502 Bad Gateway`.

Posible causa

- Reflex no esta corriendo.
- Caddy apunta al puerto equivocado.
- El unit file sigue usando dos puertos.

Comando para diagnosticar

```bash
sudo systemctl status caddy --no-pager
sudo journalctl -u caddy -n 100 --no-pager
sudo ss -ltnp | grep -E ':80|:443|:3000'
curl -I http://127.0.0.1:3000/api/_health
```

Como solucionarlo

```bash
sudo caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile
sudo systemctl restart datosenorden
sudo caddy reload --config /etc/caddy/Caddyfile --adapter caddyfile
```

Confirma que `/etc/caddy/Caddyfile` sirva `current/.web/build/client` y haga
proxy de `/api` a `127.0.0.1:3000`.

## SSL no se genera

Problema

El sitio no obtiene certificado HTTPS.

Posible causa

- DNS aun no apunta al VPS.
- Puerto `80` o `443` bloqueado.
- Caddyfile invalido.

Comando para diagnosticar

```bash
getent hosts datosenorden.cl
getent hosts beta.datosenorden.cl
sudo ufw status
sudo journalctl -u caddy -n 100 --no-pager
sudo caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile
```

Como solucionarlo

```bash
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo systemctl restart caddy
```

Espera a que DNS propague antes de insistir con HTTPS.

## WebSocket falla

Problema

La pagina abre, pero la interaccion de Reflex se rompe o queda congelada.

Posible causa

- Caddy no esta llegando al mismo proceso Reflex que sirve `/api/_event`.
- Reflex quedo compilado o arrancado sin `.env`.
- El backend no esta vivo bajo `/api`.

Comando para diagnosticar

```bash
curl -I http://127.0.0.1:3000/api/_health
curl -I https://datosenorden.cl/api/_health
sudo journalctl -u datosenorden -n 100 --no-pager
sudo journalctl -u caddy -n 100 --no-pager
```

Como solucionarlo

```bash
sudo systemctl restart datosenorden
sudo caddy reload --config /etc/caddy/Caddyfile --adapter caddyfile
```

## Puerto ocupado

Problema

Reflex o Caddy no pueden bindear el puerto esperado.

Posible causa

- Quedo un proceso viejo.
- Otro servicio usa `3000`, `80`, `443` o `5432`.

Comando para diagnosticar

```bash
sudo ss -ltnp | grep -E ':80|:443|:3000|:5432'
sudo systemctl status datosenorden --no-pager
```

Como solucionarlo

```bash
sudo systemctl stop datosenorden
sudo pkill -f "reflex run" || true
sudo systemctl start datosenorden
```

## Error de Python

Problema

`pip install -e .` o `python3 -m alembic upgrade head` fallan por version.

Posible causa

- Ubuntu 22.04 trae Python 3.10 por defecto.
- La VPS no es Ubuntu 24.04.
- `.venv` se creo con el Python equivocado.

Comando para diagnosticar

```bash
python3 --version
which python3
/opt/datosenorden/.venv/bin/python3 --version
```

Como solucionarlo

```bash
sudo rm -rf /opt/datosenorden/.venv
sudo -u datosenorden python3 -m venv /opt/datosenorden/.venv
sudo -u datosenorden /opt/datosenorden/.venv/bin/python3 -m pip install --upgrade pip
sudo -u datosenorden /opt/datosenorden/.venv/bin/python3 -m pip install -e /opt/datosenorden
```

Si `python3 --version` es menor a `3.12`, reprovisiona en Ubuntu 24.04.

## Error de pip

Problema

`pip install -e .` termina con error.

Posible causa

- Falta conectividad saliente.
- `.venv` corrupto.
- Python fuera de rango.

Comando para diagnosticar

```bash
sudo -u datosenorden bash -lc 'cd /opt/datosenorden && source .venv/bin/activate && python3 -m pip --version'
sudo -u datosenorden bash -lc 'cd /opt/datosenorden && source .venv/bin/activate && python3 -m pip install -e .'
```

Como solucionarlo

```bash
sudo rm -rf /opt/datosenorden/.venv
sudo -u datosenorden python3 -m venv /opt/datosenorden/.venv
sudo -u datosenorden /opt/datosenorden/.venv/bin/python3 -m pip install --upgrade pip
sudo -u datosenorden /opt/datosenorden/.venv/bin/python3 -m pip install -e /opt/datosenorden
```

## Error de Git

Problema

El pull o clone falla.

Posible causa

- URL remota incorrecta.
- SSH key no cargada.
- Directorio destino ya contiene archivos.

Comando para diagnosticar

```bash
cd /opt/datosenorden
git remote -v
git status --short
```

Como solucionarlo

```bash
sudo -u datosenorden git clone <REPO_URL> /opt/datosenorden
```

Si el repo ya existe:

```bash
cd /opt/datosenorden
sudo -u datosenorden git pull --ff-only
```

## Error de systemd

Problema

`systemctl enable --now datosenorden` falla o el servicio queda en `failed`.

Posible causa

- No se hizo `daemon-reload`.
- El unit file quedo desactualizado.
- `WorkingDirectory` o `EnvironmentFile` no existen.

Comando para diagnosticar

```bash
sudo systemctl daemon-reload
sudo systemctl status datosenorden --no-pager
sudo journalctl -u datosenorden -n 100 --no-pager
systemctl cat datosenorden
```

Como solucionarlo

```bash
sudo cp /opt/datosenorden/deployment/datosenorden.service /etc/systemd/system/datosenorden.service
sudo systemctl daemon-reload
sudo systemctl enable --now datosenorden
```

## Error DNS

Problema

El dominio no llega al VPS o apunta a otra IP.

Posible causa

- Registro `A` incorrecto.
- TTL aun no expira.
- Se actualizo `www` pero no el dominio raiz, o al reves.

Comando para diagnosticar

```bash
getent hosts datosenorden.cl
getent hosts www.datosenorden.cl
getent hosts beta.datosenorden.cl
```

Como solucionarlo

Corrige el registro DNS:

```text
A      datosenorden.cl      <IP_DEL_VPS>
CNAME  www                  datosenorden.cl
A      beta.datosenorden.cl <IP_DEL_VPS>
```

## Error Healthcheck

Problema

`python3 scripts/healthcheck_public.py ...` devuelve fallos.

Posible causa

- DNS aun no esta propagado.
- Caddy responde, pero Reflex sigue caido.
- Alguna ruta publica devuelve error.

Comando para diagnosticar

```bash
cd /opt/datosenorden
sudo -u datosenorden bash -lc 'source .venv/bin/activate && python3 scripts/healthcheck_public.py https://beta.datosenorden.cl'
curl -I https://beta.datosenorden.cl/
curl -I https://beta.datosenorden.cl/topic
curl -I https://beta.datosenorden.cl/studio
curl -I https://beta.datosenorden.cl/api/_health
```

Como solucionarlo

```bash
sudo systemctl restart datosenorden
sudo caddy reload --config /etc/caddy/Caddyfile --adapter caddyfile
sudo journalctl -u datosenorden -n 100 --no-pager
sudo journalctl -u caddy -n 100 --no-pager
```
