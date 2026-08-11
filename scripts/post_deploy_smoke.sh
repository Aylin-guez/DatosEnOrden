#!/usr/bin/env bash
set -euo pipefail

APP_ROOT="${APP_ROOT:-/opt/datosenorden}"
SERVICE="${SERVICE:-datosenorden}"
MIN_MEMORY_KIB="${MIN_MEMORY_KIB:-1500000}"
MIN_DISK_KIB="${MIN_DISK_KIB:-5000000}"
expected_release="${1:-}"
failures=0
check() { if "$@"; then echo "PASS $*"; else echo "FAIL $*"; failures=1; fi; }
[[ "$expected_release" =~ ^[A-Fa-f0-9]{40}$ ]] || { echo "Usage: $0 RELEASE_ID" >&2; exit 2; }
check systemctl is-active --quiet postgresql
check systemctl is-active --quiet caddy
check systemctl is-active --quiet "$SERVICE"
check curl --fail --silent --max-time 15 http://127.0.0.1:3000/ -o /dev/null
check pg_isready -h 127.0.0.1 -p 5432
[[ "$(readlink -f "$APP_ROOT/current" 2>/dev/null || true)" == "$APP_ROOT/releases/$expected_release" ]] || { echo "FAIL current_release"; failures=1; }
if ss -ltn | grep -Eq '(^|\s)(0\.0\.0\.0|\[::\]):(3000|5432)\s'; then echo "FAIL private_ports"; failures=1; else echo "PASS private_ports"; fi
available_kib="$(awk '/MemAvailable:/ {print $2}' /proc/meminfo)"; disk_kib="$(df -Pk "$APP_ROOT" | awk 'NR==2 {print $4}')"
echo "INFO memory_available_kib=$available_kib disk_available_kib=$disk_kib"
(( available_kib >= MIN_MEMORY_KIB )) || { echo "FAIL available_memory"; failures=1; }
(( disk_kib >= MIN_DISK_KIB )) || { echo "FAIL available_disk"; failures=1; }
if journalctl -u "$SERVICE" -n 200 --no-pager | grep -q 'Traceback'; then echo "WARNING traceback_in_recent_logs"; fi
exit "$failures"
