#!/usr/bin/env bash
set -euo pipefail

APP_USER="${APP_USER:-datosenorden}"
APP_GROUP="${APP_GROUP:-${APP_USER}}"
APP_DIR="${APP_DIR:-/opt/datosenorden}"
LOG_DIR="${LOG_DIR:-/var/log/datosenorden}"
BACKUP_DIR="${BACKUP_DIR:-/var/backups/datosenorden}"
INSTALL_LIBREOFFICE="${INSTALL_LIBREOFFICE:-1}"

if [ "$(id -u)" -ne 0 ]; then
    echo "Run this script with sudo or as root."
    exit 1
fi

export DEBIAN_FRONTEND=noninteractive

apt-get update
apt-get install -y \
    ca-certificates \
    git \
    curl \
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

if [ "${INSTALL_LIBREOFFICE}" = "1" ]; then
    apt-get install -y libreoffice-writer
fi

if ! getent group "${APP_GROUP}" >/dev/null; then
    groupadd --system "${APP_GROUP}"
fi

if ! id -u "${APP_USER}" >/dev/null 2>&1; then
    useradd --system --create-home --gid "${APP_GROUP}" --shell /bin/bash "${APP_USER}"
fi

install -d -o "${APP_USER}" -g "${APP_GROUP}" -m 0755 "${APP_DIR}"
install -d -o "${APP_USER}" -g "${APP_GROUP}" -m 0755 "${LOG_DIR}"
install -d -o "${APP_USER}" -g "${APP_GROUP}" -m 0755 "${BACKUP_DIR}"

systemctl enable --now postgresql
systemctl enable --now caddy

ufw allow OpenSSH
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable

cat <<EOF
Ubuntu base setup finished.

Manual follow-up still required:
1. Clone the repository into ${APP_DIR}.
2. Copy deployment/production.env.example to ${APP_DIR}/.env and replace CHANGE_ME values.
3. Create the PostgreSQL role/database and keep PostgreSQL private.
4. Create ${APP_DIR}/.venv and install the Python dependencies.
5. Install deployment/datosenorden.service and deployment/Caddyfile.

If LibreOffice is not needed on this VPS, rerun with:
  sudo INSTALL_LIBREOFFICE=0 bash scripts/server_setup_ubuntu.sh
EOF
