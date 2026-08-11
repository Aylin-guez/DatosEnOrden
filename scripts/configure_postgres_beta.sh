#!/usr/bin/env bash
set -euo pipefail

APP_USER="${APP_USER:-datosenorden}"
DB_NAME="${DB_NAME:-datosenorden_beta}"
DB_USER="${DB_USER:-datosenorden_beta}"
PASSWORD_FILE="${1:-}"

if [[ "$(id -u)" -ne 0 ]]; then echo "Run as root through sudo." >&2; exit 2; fi
if [[ -z "$PASSWORD_FILE" || ! -f "$PASSWORD_FILE" || ! -r "$PASSWORD_FILE" ]]; then
    echo "Usage: sudo scripts/configure_postgres_beta.sh /root/secure-beta-password" >&2
    exit 2
fi
[[ "$DB_NAME" =~ ^[a-z][a-z0-9_]*$ && "$DB_USER" =~ ^[a-z][a-z0-9_]*$ ]] || { echo "Database and role names must be lowercase identifiers." >&2; exit 2; }
if [[ "$(stat -c '%a' "$PASSWORD_FILE")" != "600" ]]; then
    echo "Password file must have mode 0600." >&2
    exit 2
fi
password="$(<"$PASSWORD_FILE")"
[[ -n "$password" ]] || { echo "Password file is empty." >&2; exit 2; }
trap 'rm -f -- "$PASSWORD_FILE"' EXIT

sudo -u postgres psql -v ON_ERROR_STOP=1 -d postgres -c "ALTER SYSTEM SET listen_addresses = '127.0.0.1';"
systemctl restart postgresql
if ss -ltn | grep -Eq '(^|\s)(0\.0\.0\.0|\[::\]):5432\s'; then
    echo "PostgreSQL is publicly bound; refusing beta database setup." >&2
    exit 1
fi

if ! sudo -u postgres psql -tAc "SELECT 1 FROM pg_roles WHERE rolname = '$DB_USER'" | grep -qx 1; then
    sudo -u postgres psql -v ON_ERROR_STOP=1 -c "CREATE ROLE $DB_USER LOGIN;"
fi
escaped_password="${password//\'/\'\'}"
printf "ALTER ROLE %s PASSWORD '%s';\n" "$DB_USER" "$escaped_password" | sudo -u postgres psql -v ON_ERROR_STOP=1
if ! sudo -u postgres psql -tAc "SELECT 1 FROM pg_database WHERE datname = '$DB_NAME'" | grep -qx 1; then
    sudo -u postgres createdb -O "$DB_USER" "$DB_NAME"
fi
sudo -u postgres psql -v ON_ERROR_STOP=1 -d "$DB_NAME" -c "REVOKE ALL ON DATABASE $DB_NAME FROM PUBLIC; GRANT CONNECT, TEMPORARY ON DATABASE $DB_NAME TO $DB_USER;"
echo "PostgreSQL beta role and database are ready; password file removed."
