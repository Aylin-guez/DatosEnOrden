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
app_group="$(id -gn "$APP_USER")"
[[ "$(sha256sum "$artifact" | awk '{print $1}')" == "${expected_sha,,}" ]] || { echo "ARTIFACT_INTEGRITY_FAILURE" >&2; exit 1; }
target="$APP_ROOT/releases/$release_id"
safe_path="$target/.venv/bin:$app_home/.bun/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
run_as_app() {
    runuser -u "$APP_USER" -- env -i \
        HOME="$app_home" \
        USER="$APP_USER" \
        LOGNAME="$APP_USER" \
        BUN_INSTALL="$app_home/.bun" \
        XDG_CACHE_HOME="$app_home/.cache" \
        PATH="$safe_path" \
        "$@"
}
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
install -d -o "$APP_USER" -g "$app_group" -m 0750 "$app_home/.bun"
install -d -o "$APP_USER" -g "$app_group" -m 0750 "$app_home/.bun/install"
install -d -o "$APP_USER" -g "$app_group" -m 0750 "$app_home/.bun/install/cache"
if find "$app_home/.bun" -xdev ! -user "$APP_USER" -print -quit | grep -q .; then
    echo "Bun runtime tree contains entries not owned by $APP_USER; remediate the cache before preparing." >&2
    exit 1
fi
tar -xf "$artifact" -C "$target" --no-same-owner --no-same-permissions
chown -R "$APP_USER:$APP_USER" "$target"
run_as_app python3 -m venv "$target/.venv"
run_as_app "$target/.venv/bin/python" -m pip install --upgrade pip
run_as_app "$target/.venv/bin/python" -m pip install "$target"
run_as_app "$target/.venv/bin/python" -m pip check
run_as_app bash -c '
    set -euo pipefail
    env_file="$1"; target="$2"; python="$3"; app_home="$4"; app_user="$5"; safe_path="$6"
    set -a
    . "$env_file"
    set +a
    export HOME="$app_home" USER="$app_user" LOGNAME="$app_user"
    export BUN_INSTALL="$app_home/.bun" XDG_CACHE_HOME="$app_home/.cache" PATH="$safe_path"
    cd "$target"
    export REFLEX_WEB_WORKDIR="$target/.web"
    export REFLEX_STATES_WORKDIR="$target/.states"
    export REFLEX_CHECK_LATEST_VERSION=false
    exec "$python" -m reflex export --no-zip --env prod --no-ssr
' -- "$ENV_FILE" "$target" "$target/.venv/bin/python" "$app_home" "$APP_USER" "$safe_path"
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
