#!/usr/bin/env bash
set -euo pipefail

APP_ROOT="${APP_ROOT:-/opt/datosenorden}"
APP_USER="${APP_USER:-datosenorden}"
ENV_FILE="${ENV_FILE:-/etc/datosenorden/beta.env}"
PAIR_ROOT="${PAIR_ROOT:-/var/lib/datosenorden/release-pairs}"
SERVICE="${SERVICE:-datosenorden}"
release_id="" package_id="" confirmation=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --release-id) release_id="$2"; shift 2 ;;
        --package-id) package_id="$2"; shift 2 ;;
        --confirm-ready) confirmation="$2"; shift 2 ;;
        *) echo "Unknown argument: $1" >&2; exit 2 ;;
    esac
done
fail() { echo "$1" >&2; exit "${2:-1}"; }
[[ "$(id -u)" -eq 0 ]] || fail "Run as root through sudo." 2
[[ "$release_id" =~ ^[a-f0-9]{40}$ && "$confirmation" == "$release_id" ]] || fail "Release confirmation mismatch." 2
[[ "$package_id" =~ ^DEO-PROD-DATA-[0-9]{4}-[a-f0-9]{16}$ ]] || fail "Package ID is invalid." 2
target="$APP_ROOT/releases/$release_id"
ready="$PAIR_ROOT/$release_id.ready"
candidate_env="$PAIR_ROOT/$release_id.env"
previous_env="$PAIR_ROOT/$release_id.previous.env"
active_state="$PAIR_ROOT/$release_id.active"
[[ -f "$ready" && ! -L "$ready" && -f "$candidate_env" && ! -L "$candidate_env" ]] || fail "Prepared pair state is unavailable."
grep -Fxq "release_id=$release_id" "$ready" || fail "Pair marker release mismatch."
grep -Fxq "package_id=$package_id" "$ready" || fail "Pair marker package mismatch."
previous_release="$(sed -n 's/^previous_release=//p' "$ready")"
previous_database="$(sed -n 's/^previous_database=//p' "$ready")"
target_database="$(sed -n 's/^target_database=//p' "$ready")"
[[ "$previous_release" =~ ^[a-f0-9]{40}$ && "$previous_database" =~ ^[a-z][a-z0-9_]{0,62}$ && "$target_database" =~ ^datosenorden_rel_[a-f0-9]{16}$ ]] || fail "Pair marker identities are unsafe."
[[ "$(readlink -f "$APP_ROOT/current")" == "$APP_ROOT/releases/$previous_release" ]] || fail "Current code changed since pair preparation."
old_previous=""
if [[ -L "$APP_ROOT/previous" ]]; then
    old_previous="$(readlink -f "$APP_ROOT/previous")"
    [[ "$(dirname "$old_previous")" == "$APP_ROOT/releases" && "$(basename "$old_previous")" =~ ^[a-f0-9]{40}$ ]] || fail "Previous release pointer is unsafe."
elif [[ -e "$APP_ROOT/previous" ]]; then
    fail "Previous release path is not a symlink."
fi
[[ -d "$target" && ! -L "$target" && -f "$target/.deo-release-ready" ]] || fail "Prepared code target is unavailable."
config_tool="$target/scripts/release_pair_config.py"
python="$target/.venv/bin/python"
[[ "$($python "$config_tool" field --env-file "$ENV_FILE" --name database)" == "$previous_database" ]] || fail "Current database changed since pair preparation."
[[ "$($python "$config_tool" field --env-file "$candidate_env" --name database)" == "$target_database" ]] || fail "Candidate database identity mismatch."
for path in "$ENV_FILE.new" "$ENV_FILE.restore" "$APP_ROOT/current.new" "$APP_ROOT/current.rollback" "$PAIR_ROOT/$release_id.active.pending" "$APP_ROOT/previous.new" "$APP_ROOT/previous.restore" "$previous_env" "$active_state"; do
    [[ ! -e "$path" && ! -L "$path" ]] || fail "Stale transition path blocks activation: $path"
done
install -o root -g "$APP_USER" -m 0640 "$ENV_FILE" "$previous_env"
install -o root -g "$APP_USER" -m 0640 "$candidate_env" "$ENV_FILE.new"
ln -s "$target" "$APP_ROOT/current.new"
restore_old_pair() {
    systemctl stop "$SERVICE" >/dev/null 2>&1 || true
    install -o root -g "$APP_USER" -m 0640 "$previous_env" "$ENV_FILE.restore" || return 1
    mv -T "$ENV_FILE.restore" "$ENV_FILE" || return 1
    ln -s "$APP_ROOT/releases/$previous_release" "$APP_ROOT/current.rollback" || return 1
    mv -Tf "$APP_ROOT/current.rollback" "$APP_ROOT/current" || return 1
    if [[ -n "$old_previous" ]]; then
        ln -s "$old_previous" "$APP_ROOT/previous.restore" || return 1
        mv -Tf "$APP_ROOT/previous.restore" "$APP_ROOT/previous" || return 1
    elif [[ -L "$APP_ROOT/previous" ]]; then
        rm -f -- "$APP_ROOT/previous" || return 1
    fi
    systemctl reset-failed "$SERVICE" >/dev/null 2>&1 || true
    systemctl restart "$SERVICE" || return 1
    bash "$APP_ROOT/releases/$previous_release/scripts/post_deploy_smoke.sh" "$previous_release"
}
trap 'rm -f -- "$ENV_FILE.new" "$ENV_FILE.restore" "$APP_ROOT/current.new" "$APP_ROOT/current.rollback" "$PAIR_ROOT/$release_id.active.pending" "$APP_ROOT/previous.new" "$APP_ROOT/previous.restore"' EXIT
restart_old_without_switch() {
    systemctl reset-failed "$SERVICE" >/dev/null 2>&1 || true
    systemctl restart "$SERVICE" || return 1
    bash "$APP_ROOT/releases/$previous_release/scripts/post_deploy_smoke.sh" "$previous_release"
}
systemctl stop "$SERVICE"
if ! mv -T "$ENV_FILE.new" "$ENV_FILE"; then
    restart_old_without_switch || fail "Candidate database configuration switch failed and the old service could not be restarted."
    fail "Candidate database configuration switch failed; the old pair remains active."
fi
if ! mv -Tf "$APP_ROOT/current.new" "$APP_ROOT/current"; then
    restore_old_pair || fail "Code pointer switch failed and old pair recovery failed."
    fail "Code pointer switch failed; the old pair was restored."
fi
failure=""
if ! systemctl daemon-reload; then failure="systemd daemon reload failed"
elif ! systemctl restart "$SERVICE"; then failure="service restart failed"
elif ! systemctl is-active --quiet "$SERVICE"; then failure="service inactive"
elif ! systemd-analyze verify "/etc/systemd/system/${SERVICE}.service"; then failure="systemd verification failed"
elif ! bash "$target/scripts/post_deploy_smoke.sh" "$release_id"; then failure="pair smoke failed"
fi
if [[ -n "$failure" ]]; then
    restore_old_pair || fail "Pair activation failed and old pair recovery failed: $failure"
    fail "Pair activation failed and old pair was restored: $failure"
fi
if ! ln -s "$APP_ROOT/releases/$previous_release" "$APP_ROOT/previous.new" || ! mv -Tf "$APP_ROOT/previous.new" "$APP_ROOT/previous"; then
    restore_old_pair || fail "Previous-release pointer update failed and old pair recovery failed."
    fail "Previous-release pointer update failed; the old pair was restored."
fi
if ! printf 'release_id=%s\ndatabase=%s\npackage_id=%s\nprevious_release=%s\nprevious_database=%s\nprevious_env=%s\n' "$release_id" "$target_database" "$package_id" "$previous_release" "$previous_database" "$previous_env" > "$PAIR_ROOT/$release_id.active.pending" \
    || ! chown root:"$APP_USER" "$PAIR_ROOT/$release_id.active.pending" \
    || ! chmod 0640 "$PAIR_ROOT/$release_id.active.pending" \
    || ! mv -T "$PAIR_ROOT/$release_id.active.pending" "$active_state"; then
    restore_old_pair || fail "Active-pair state persistence failed and old pair recovery failed."
    fail "Active-pair state persistence failed; the old pair was restored."
fi
echo "Activated code and DATA snapshot as one release pair: $release_id / $package_id"
