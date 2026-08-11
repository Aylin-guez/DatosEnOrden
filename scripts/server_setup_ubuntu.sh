#!/usr/bin/env bash
set -euo pipefail

APP_USER="${APP_USER:-datosenorden}"
APP_GROUP="${APP_GROUP:-${APP_USER}}"
APP_DIR="${APP_DIR:-/opt/datosenorden}"
BACKUP_DIR="${BACKUP_DIR:-/var/backups/datosenorden}"
INSTALL_LIBREOFFICE="${INSTALL_LIBREOFFICE:-0}"
NODE_MAJOR="${NODE_MAJOR:-22}"
MIN_NODE_VERSION="${MIN_NODE_VERSION:-22.12.0}"

if [ "$(id -u)" -ne 0 ]; then
    echo "Run this script with sudo or as root."
    exit 1
fi

export DEBIAN_FRONTEND=noninteractive

apt-get update
apt-get install -y \
    ca-certificates \
    curl \
    gnupg \
    ufw \
    build-essential \
    python3 \
    python3-venv \
    python3-pip \
    python3-dev \
    libpq-dev \
    postgresql \
    postgresql-contrib \
    caddy

install -d -m 0755 /etc/apt/keyrings
if [ ! -f /etc/apt/keyrings/nodesource.gpg ]; then
    curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key | gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg
fi
echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_${NODE_MAJOR}.x nodistro main" > /etc/apt/sources.list.d/nodesource.list
apt-get update
apt-get install -y nodejs

if [ "${INSTALL_LIBREOFFICE}" = "1" ]; then
    apt-get install -y libreoffice-writer
fi

if ! python3 - <<'PY'
import sys

raise SystemExit(0 if sys.version_info >= (3, 12) else 1)
PY
then
    echo "Installed python3 is too old: $(python3 --version 2>/dev/null || echo unavailable)" >&2
    echo "DatosEnOrden requires Python >= 3.12. Use Ubuntu 24.04 LTS or provision Python 3.12+ before continuing." >&2
    exit 1
fi

if ! python3 - "${MIN_NODE_VERSION}" <<'PY'
import re
import subprocess
import sys

minimum = tuple(int(part) for part in sys.argv[1].split("."))
raw = subprocess.check_output(["node", "--version"], text=True).strip()
match = re.match(r"v?(\d+)\.(\d+)\.(\d+)", raw)
if match is None:
    raise SystemExit(1)
found = tuple(int(part) for part in match.groups())
raise SystemExit(0 if found >= minimum else 1)
PY
then
    echo "Installed node version $(node --version 2>/dev/null || echo unavailable) is below required ${MIN_NODE_VERSION}." >&2
    exit 1
fi

if ! getent group "${APP_GROUP}" >/dev/null; then
    groupadd --system "${APP_GROUP}"
fi

if ! id -u "${APP_USER}" >/dev/null 2>&1; then
    useradd --system --create-home --gid "${APP_GROUP}" --shell /bin/bash "${APP_USER}"
fi

install -d -o root -g root -m 0755 "${APP_DIR}"
install -d -o "${APP_USER}" -g "${APP_GROUP}" -m 0755 "${APP_DIR}/releases"
install -d -o "${APP_USER}" -g "${APP_GROUP}" -m 0755 "${APP_DIR}/shared"
install -d -o root -g "${APP_GROUP}" -m 0750 /etc/datosenorden
install -d -o "${APP_USER}" -g "${APP_GROUP}" -m 0700 "${BACKUP_DIR}"

systemctl enable --now postgresql

cat <<EOF
Ubuntu base setup finished.

Manual follow-up still required:
1. Run the verified release artifact deployment; do not clone or pull a mutable worktree.
2. Create /etc/datosenorden/beta.env with restricted permissions and replace placeholders.
3. Create the PostgreSQL beta role/database and keep PostgreSQL private.
4. Run scripts/configure_ufw.sh only from a confirmed SSH session.
5. Install deployment/datosenorden.service and deployment/Caddyfile after local checks pass.
6. Enable Caddy only after its configuration has passed caddy validate.

If LibreOffice is not needed on this VPS, rerun with:
  sudo INSTALL_LIBREOFFICE=0 bash scripts/server_setup_ubuntu.sh
EOF
