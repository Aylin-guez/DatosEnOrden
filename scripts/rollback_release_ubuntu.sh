#!/usr/bin/env bash
set -euo pipefail

APP_ROOT="${APP_ROOT:-/opt/datosenorden}"
release_id="${1:-}"
[[ "$(id -u)" -eq 0 ]] || { echo "Run as root through sudo." >&2; exit 2; }
[[ "$release_id" =~ ^[A-Fa-f0-9]{40}$ && -d "$APP_ROOT/releases/$release_id" ]] || { echo "Provide an existing 40-hex release ID." >&2; exit 2; }
[[ -L "$APP_ROOT/current" ]] && ln -sfn "$(readlink "$APP_ROOT/current")" "$APP_ROOT/previous"
ln -s "$APP_ROOT/releases/$release_id" "$APP_ROOT/current.new"
mv -Tf "$APP_ROOT/current.new" "$APP_ROOT/current"
systemctl restart datosenorden
systemctl is-active --quiet datosenorden
curl --fail --silent --max-time 15 http://127.0.0.1:3000/ -o /dev/null
echo "Application rollback completed. Database state was not changed."
