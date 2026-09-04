#!/usr/bin/env bash
set -euo pipefail

APP_ROOT="${APP_ROOT:-/opt/datosenorden}"
APP_USER="${APP_USER:-datosenorden}"
ENV_FILE="${ENV_FILE:-/etc/datosenorden/beta.env}"
PAIR_ROOT="${PAIR_ROOT:-/var/lib/datosenorden/release-pairs}"
SERVICE="${SERVICE:-datosenorden}"
previous_release="${1:-}"
current_release="$(basename "$(readlink -f "$APP_ROOT/current" 2>/dev/null || true)")"
state="$PAIR_ROOT/$current_release.active"
fail() { echo "$1" >&2; exit "${2:-1}"; }
[[ "$(id -u)" -eq 0 ]] || fail "Run as root through sudo." 2
[[ "$previous_release" =~ ^[a-f0-9]{40}$ && "$current_release" =~ ^[a-f0-9]{40}$ ]] || fail "Valid current and previous releases are required." 2
[[ -f "$state" && ! -L "$state" ]] || fail "Current release has no DATA pair rollback state."
grep -Fxq "release_id=$current_release" "$state" || fail "Pair rollback state mismatch."
grep -Fxq "previous_release=$previous_release" "$state" || fail "Requested rollback release mismatch."
previous_env="$(sed -n 's/^previous_env=//p' "$state")"
[[ "$previous_env" == "$PAIR_ROOT/$current_release.previous.env" && -f "$previous_env" && ! -L "$previous_env" ]] || fail "Previous environment snapshot is unsafe."
current_env="$PAIR_ROOT/$current_release.env"
[[ -f "$current_env" && ! -L "$current_env" ]] || fail "Current pair environment snapshot is unavailable."
for path in "$ENV_FILE.rollback" "$ENV_FILE.recover" "$APP_ROOT/current.rollback" "$APP_ROOT/current.recover" "$APP_ROOT/previous.rollback"; do
    [[ ! -e "$path" && ! -L "$path" ]] || fail "Stale rollback path blocks operation: $path"
done
restore_new_pair() {
    systemctl stop "$SERVICE" >/dev/null 2>&1 || true
    install -o root -g "$APP_USER" -m 0640 "$current_env" "$ENV_FILE.recover" || return 1
    mv -T "$ENV_FILE.recover" "$ENV_FILE" || return 1
    ln -s "$APP_ROOT/releases/$current_release" "$APP_ROOT/current.recover" || return 1
    mv -Tf "$APP_ROOT/current.recover" "$APP_ROOT/current" || return 1
    systemctl restart "$SERVICE" || return 1
    bash "$APP_ROOT/releases/$current_release/scripts/post_deploy_smoke.sh" "$current_release"
}
trap 'rm -f -- "$ENV_FILE.rollback" "$ENV_FILE.recover" "$APP_ROOT/current.rollback" "$APP_ROOT/current.recover" "$APP_ROOT/previous.rollback"' EXIT
install -o root -g "$APP_USER" -m 0640 "$previous_env" "$ENV_FILE.rollback"
ln -s "$APP_ROOT/releases/$previous_release" "$APP_ROOT/current.rollback"
systemctl stop "$SERVICE"
if ! mv -T "$ENV_FILE.rollback" "$ENV_FILE"; then
    systemctl restart "$SERVICE" || fail "Rollback configuration switch failed and the current service could not be restarted."
    fail "Rollback configuration switch failed; the current pair remains active."
fi
if ! mv -Tf "$APP_ROOT/current.rollback" "$APP_ROOT/current"; then
    restore_new_pair || fail "Rollback code pointer switch failed and current pair recovery also failed."
    fail "Rollback code pointer switch failed; the current pair was restored."
fi
if ! systemctl restart "$SERVICE" || ! bash "$APP_ROOT/releases/$previous_release/scripts/post_deploy_smoke.sh" "$previous_release"; then
    restore_new_pair || fail "Pair rollback failed and current pair recovery also failed."
    fail "Pair rollback failed; current pair was restored."
fi
if ! ln -s "$APP_ROOT/releases/$current_release" "$APP_ROOT/previous.rollback" \
    || ! mv -Tf "$APP_ROOT/previous.rollback" "$APP_ROOT/previous"; then
    restore_new_pair || fail "Rollback previous-pointer update failed and current pair recovery also failed."
    fail "Rollback previous-pointer update failed; the current pair was restored."
fi
echo "Rolled back code and database configuration to release pair $previous_release; neither database was mutated."
