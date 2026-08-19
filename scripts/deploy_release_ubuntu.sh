#!/usr/bin/env bash
set -euo pipefail

APP_ROOT="${APP_ROOT:-/opt/datosenorden}"
APP_USER="${APP_USER:-datosenorden}"
ENV_FILE="${ENV_FILE:-/etc/datosenorden/beta.env}"
artifact="" expected_sha="" release_id="" prepare=0
while [[ $# -gt 0 ]]; do
    case "$1" in
        --artifact) artifact="$2"; shift 2 ;;
        --sha256) expected_sha="$2"; shift 2 ;;
        --release-id) release_id="$2"; shift 2 ;;
        --prepare) prepare=1; shift ;;
        *) echo "Unknown argument: $1" >&2; exit 2 ;;
    esac
done
[[ "$(id -u)" -eq 0 ]] || { echo "Run as root through sudo." >&2; exit 2; }
(( prepare )) || { echo "Explicit --prepare mode is required." >&2; exit 2; }
[[ -f "$artifact" && "$expected_sha" =~ ^[A-Fa-f0-9]{64}$ && "$release_id" =~ ^[A-Fa-f0-9]{40}$ ]] || { echo "artifact, SHA-256, and 40-hex release ID are required." >&2; exit 2; }
[[ -f "$ENV_FILE" ]] || { echo "Missing external environment file: $ENV_FILE" >&2; exit 1; }
app_home="$(getent passwd "$APP_USER" | awk -F: '{print $6}')"
[[ -n "$app_home" && -d "$app_home" && -x "$app_home" ]] || { echo "Runtime user home is unavailable: $APP_USER" >&2; exit 1; }
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
install -d -o root -g "$APP_USER" -m 0755 "$APP_ROOT/releases"
install -d -o "$APP_USER" -g "$APP_USER" -m 0755 "$target"
tar -xf "$artifact" -C "$target" --no-same-owner --no-same-permissions
chown -R "$APP_USER:$APP_USER" "$target"
runuser -u "$APP_USER" -- python3 -m venv "$target/.venv"
runuser -u "$APP_USER" -- "$target/.venv/bin/python" -m pip install --upgrade pip
runuser -u "$APP_USER" -- "$target/.venv/bin/python" -m pip install "$target"
runuser -u "$APP_USER" -- "$target/.venv/bin/python" -m pip check
set -a
. "$ENV_FILE"
set +a
runuser -u "$APP_USER" --preserve-environment -- env HOME="$app_home" bash -c '
    set -euo pipefail
    target="$1"; python="$2"
    cd "$target"
    export REFLEX_WEB_WORKDIR="$target/.web"
    export REFLEX_STATES_WORKDIR="$target/.states"
    export REFLEX_CHECK_LATEST_VERSION=false
    exec "$python" -m reflex export --no-zip --env prod --no-ssr
' -- "$target" "$target/.venv/bin/python"
[[ -s "$target/.web/backend/stateful_pages.json" ]] || { echo "Prepared Reflex backend marker is missing." >&2; exit 1; }
[[ -f "$target/.web/build/client/index.html" ]] || { echo "Prepared Reflex frontend artifact is missing." >&2; exit 1; }
pending_marker="$target/.deo-release-ready.pending"
ready_marker="$target/.deo-release-ready"
printf 'release_id=%s\nartifact_sha256=%s\n' "$release_id" "${expected_sha,,}" > "$pending_marker"
chown -R root:"$APP_USER" "$target"
chmod -R go-w "$target"
if find "$target" -xdev \( -type f -o -type d \) -perm /022 -print -quit | grep -q .; then
    echo "Prepared release remains writable by its runtime user or group." >&2
    exit 1
fi
mv -T "$pending_marker" "$ready_marker"
echo "Prepared immutable release $release_id; not activated."
