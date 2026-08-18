#!/usr/bin/env bash
set -euo pipefail

APP_ROOT="${APP_ROOT:-/opt/datosenorden}"
SERVICE="${SERVICE:-datosenorden}"
MIN_MEMORY_KIB="${MIN_MEMORY_KIB:-1500000}"
MIN_DISK_KIB="${MIN_DISK_KIB:-5000000}"
READINESS_TIMEOUT_SECONDS="${READINESS_TIMEOUT_SECONDS:-45}"
READINESS_INTERVAL_SECONDS="${READINESS_INTERVAL_SECONDS:-1}"
PER_ATTEMPT_TIMEOUT_SECONDS="${PER_ATTEMPT_TIMEOUT_SECONDS:-3}"
READINESS_URL="${READINESS_URL:-http://127.0.0.1:3000/}"
expected_release="${1:-}"
failures=0
check() { if "$@"; then echo "PASS $*"; else echo "FAIL $*"; failures=1; fi; }
[[ "$expected_release" =~ ^[A-Fa-f0-9]{40}$ ]] || { echo "Usage: $0 RELEASE_ID" >&2; exit 2; }
for value in "$READINESS_TIMEOUT_SECONDS" "$READINESS_INTERVAL_SECONDS" "$PER_ATTEMPT_TIMEOUT_SECONDS"; do
    [[ "$value" =~ ^[1-9][0-9]*$ ]] || { echo "Readiness values must be positive integer seconds." >&2; exit 2; }
done

wait_for_backend_readiness() {
    local deadline=$((SECONDS + READINESS_TIMEOUT_SECONDS))
    local attempts=0 status=""
    while true; do
        if ! systemctl is-active --quiet "$SERVICE"; then
            echo "FAIL backend_service_inactive_during_readiness attempts=$attempts"
            return 1
        fi
        attempts=$((attempts + 1))
        if status="$(curl --fail --silent --show-error \
            --connect-timeout "$PER_ATTEMPT_TIMEOUT_SECONDS" \
            --max-time "$PER_ATTEMPT_TIMEOUT_SECONDS" \
            --output /dev/null --write-out '%{http_code}' "$READINESS_URL")" \
            && [[ "$status" =~ ^2[0-9]{2}$ ]]; then
            echo "PASS backend_readiness attempts=$attempts status=$status"
            return 0
        fi
        if (( SECONDS >= deadline )); then
            echo "FAIL backend_readiness_timeout attempts=$attempts timeout_seconds=$READINESS_TIMEOUT_SECONDS last_status=${status:-connection_error}"
            return 1
        fi
        sleep "$READINESS_INTERVAL_SECONDS"
    done
}

check systemctl is-active --quiet postgresql
check systemctl is-active --quiet caddy
check systemctl is-active --quiet "$SERVICE"
wait_for_backend_readiness || failures=1
check pg_isready -h 127.0.0.1 -p 5432
[[ "$(readlink -f "$APP_ROOT/current" 2>/dev/null || true)" == "$APP_ROOT/releases/$expected_release" ]] || { echo "FAIL current_release"; failures=1; }
if ss -ltn | grep -Eq '(^|\s)(0\.0\.0\.0|\[::\]):(3000|5432)\s'; then echo "FAIL private_ports"; failures=1; else echo "PASS private_ports"; fi
available_kib="$(awk '/MemAvailable:/ {print $2}' /proc/meminfo)"; disk_kib="$(df -Pk "$APP_ROOT" | awk 'NR==2 {print $4}')"
echo "INFO memory_available_kib=$available_kib disk_available_kib=$disk_kib"
(( available_kib >= MIN_MEMORY_KIB )) || { echo "FAIL available_memory"; failures=1; }
(( disk_kib >= MIN_DISK_KIB )) || { echo "FAIL available_disk"; failures=1; }
if journalctl -u "$SERVICE" -n 200 --no-pager | grep -q 'Traceback'; then echo "WARNING traceback_in_recent_logs"; fi
exit "$failures"
