#!/usr/bin/env bash
set -euo pipefail
umask 077

BACKUP_DIR="${BACKUP_DIR:-/var/backups/datosenorden}"
KEEP_BACKUPS="${KEEP_BACKUPS:-7}"
PGHOST="${PGHOST:-localhost}"
PGPORT="${PGPORT:-5432}"
PGUSER="${PGUSER:-datosenorden}"
PGDATABASE="${PGDATABASE:-datosenorden}"

if ! command -v pg_dump >/dev/null 2>&1; then
    echo "pg_dump is not installed or not on PATH."
    exit 1
fi

install -d -m 0700 "${BACKUP_DIR}"

TIMESTAMP="$(date -u +%Y%m%dT%H%M%SZ)"
ARCHIVE_PATH="${BACKUP_DIR}/postgres-${PGDATABASE}-${TIMESTAMP}.sql.gz"

echo "Writing PostgreSQL backup to ${ARCHIVE_PATH}"
echo "Use .pgpass or PGPASSWORD in the environment. Do not hardcode passwords in this script."

pg_dump \
    --host="${PGHOST}" \
    --port="${PGPORT}" \
    --username="${PGUSER}" \
    --dbname="${PGDATABASE}" \
    --no-owner \
    --no-privileges \
    | gzip -9 > "${ARCHIVE_PATH}"

gzip -t "${ARCHIVE_PATH}"
sha256sum "${ARCHIVE_PATH}" > "${ARCHIVE_PATH}.sha256"

mapfile -t BACKUP_FILES < <(find "${BACKUP_DIR}" -maxdepth 1 -type f -name "postgres-${PGDATABASE}-*.sql.gz" | sort)

if [ "${#BACKUP_FILES[@]}" -gt "${KEEP_BACKUPS}" ]; then
    REMOVE_COUNT=$((${#BACKUP_FILES[@]} - KEEP_BACKUPS))
    printf '%s\n' "${BACKUP_FILES[@]}" | head -n "${REMOVE_COUNT}" | while IFS= read -r old_backup; do
        rm -f -- "${old_backup}"
        echo "Removed old backup: ${old_backup}"
    done
fi

echo "Backup complete."
