#!/usr/bin/env bash
set -euo pipefail

APP_ROOT="${APP_ROOT:-/opt/datosenorden}"
APP_USER="${APP_USER:-datosenorden}"
ENV_FILE="${ENV_FILE:-/etc/datosenorden/beta.env}"
artifact="" expected_sha="" release_id="" activate=0
while [[ $# -gt 0 ]]; do
    case "$1" in
        --artifact) artifact="$2"; shift 2 ;;
        --sha256) expected_sha="$2"; shift 2 ;;
        --release-id) release_id="$2"; shift 2 ;;
        --activate) activate=1; shift ;;
        *) echo "Unknown argument: $1" >&2; exit 2 ;;
    esac
done
[[ "$(id -u)" -eq 0 ]] || { echo "Run as root through sudo." >&2; exit 2; }
[[ -f "$artifact" && "$expected_sha" =~ ^[A-Fa-f0-9]{64}$ && "$release_id" =~ ^[A-Fa-f0-9]{40}$ ]] || { echo "artifact, SHA-256, and 40-hex release ID are required." >&2; exit 2; }
[[ -f "$ENV_FILE" ]] || { echo "Missing external environment file: $ENV_FILE" >&2; exit 1; }
[[ "$(sha256sum "$artifact" | awk '{print $1}')" == "${expected_sha,,}" ]] || { echo "ARTIFACT_INTEGRITY_FAILURE" >&2; exit 1; }
target="$APP_ROOT/releases/$release_id"
[[ ! -e "$target" ]] || { echo "Release already exists: $target" >&2; exit 1; }
if ! entries="$(tar -tf "$artifact")"; then
    echo "Unable to inspect artifact archive." >&2
    exit 1
fi
if printf '%s\n' "$entries" | grep -Eq '(^/|(^|/)\.\.(/|$))'; then
    echo "Archive contains unsafe paths." >&2
    exit 1
fi
install -d -o "$APP_USER" -g "$APP_USER" -m 0755 "$APP_ROOT/releases"
install -d -o "$APP_USER" -g "$APP_USER" -m 0755 "$target"
tar -xf "$artifact" -C "$target" --no-same-owner --no-same-permissions
chown -R "$APP_USER:$APP_USER" "$target"
runuser -u "$APP_USER" -- python3 -m venv "$target/.venv"
runuser -u "$APP_USER" -- "$target/.venv/bin/python" -m pip install --upgrade pip
runuser -u "$APP_USER" -- "$target/.venv/bin/python" -m pip install "$target"
runuser -u "$APP_USER" -- "$target/.venv/bin/python" -m pip check
runuser -u "$APP_USER" -- bash -c 'set -a; . "$1"; set +a; exec "$2" -m reflex compile --dry --no-rich' -- "$ENV_FILE" "$target/.venv/bin/python"
if (( activate )); then
    [[ -L "$APP_ROOT/current" ]] && ln -sfn "$(readlink "$APP_ROOT/current")" "$APP_ROOT/previous"
    ln -s "$target" "$APP_ROOT/current.new"
    mv -Tf "$APP_ROOT/current.new" "$APP_ROOT/current"
    systemctl daemon-reload
    echo "Activated release $release_id."
else
    echo "Prepared release $release_id; not activated."
fi
