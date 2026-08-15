#!/usr/bin/env bash
set -euo pipefail

APP_ROOT="${APP_ROOT:-/opt/datosenorden}"
ENV_FILE="${ENV_FILE:-/etc/datosenorden/beta.env}"
SERVICE="${SERVICE:-datosenorden}"
release_id="" ready_confirmation=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --release-id) release_id="$2"; shift 2 ;;
        --confirm-ready) ready_confirmation="$2"; shift 2 ;;
        *) echo "Unknown argument: $1" >&2; exit 2 ;;
    esac
done

fail() { echo "$1" >&2; exit "${2:-1}"; }
[[ "$(id -u)" -eq 0 ]] || fail "Run as root through sudo." 2
[[ "$release_id" =~ ^[A-Fa-f0-9]{40}$ ]] || fail "A 40-hex release ID is required." 2
[[ "$ready_confirmation" == "$release_id" ]] || fail "Readiness confirmation must equal release ID." 2

target="$APP_ROOT/releases/$release_id"
current="$APP_ROOT/current"
previous="$APP_ROOT/previous"
ready_marker="$target/.deo-release-ready"
current_new="$APP_ROOT/current.new"
previous_new="$APP_ROOT/previous.new"
rollback_new="$APP_ROOT/current.rollback"

cleanup() { rm -f -- "$current_new" "$previous_new" "$rollback_new"; }
trap cleanup EXIT

[[ -d "$target" && ! -L "$target" ]] || fail "Prepared release does not exist: $target"
[[ -f "$ready_marker" && ! -L "$ready_marker" ]] || fail "Release is incomplete: readiness marker is missing."
grep -Fxq "release_id=$release_id" "$ready_marker" || fail "Release readiness marker does not match release ID."
grep -Eq '^artifact_sha256=[A-Fa-f0-9]{64}$' "$ready_marker" || fail "Release readiness marker has no artifact SHA-256."
[[ -x "$target/.venv/bin/python" && -x "$target/.venv/bin/reflex" ]] || fail "Release virtual environment is incomplete."
[[ -f "$target/scripts/post_deploy_smoke.sh" ]] || fail "Release post-deploy smoke script is missing."
if find "$target" -xdev -perm /022 -print -quit | grep -q .; then
    fail "Prepared release is writable by its runtime user or group."
fi
[[ -f "$ENV_FILE" ]] || fail "Missing external environment file: $ENV_FILE"
systemctl cat "$SERVICE" >/dev/null 2>&1 || fail "Systemd service unit is not installed."
[[ ! -e "$current_new" && ! -L "$current_new" ]] || fail "Stale current.new blocks atomic activation."
[[ ! -e "$previous_new" && ! -L "$previous_new" ]] || fail "Stale previous.new blocks atomic activation."
[[ ! -e "$rollback_new" && ! -L "$rollback_new" ]] || fail "Stale current.rollback blocks atomic activation."
[[ ! -e "$current" || -L "$current" ]] || fail "Current path exists but is not a symlink."
[[ ! -e "$previous" || -L "$previous" ]] || fail "Previous path exists but is not a symlink."

old_current=""
if [[ -L "$current" ]]; then
    old_current="$(readlink -f "$current")" || fail "Current symlink cannot be resolved."
    old_name="$(basename "$old_current")"
    [[ "$(dirname "$old_current")" == "$APP_ROOT/releases" && "$old_name" =~ ^[A-Fa-f0-9]{40}$ && -d "$old_current" ]] || fail "Current symlink is outside the immutable release store."
elif [[ -L "$previous" ]]; then
    fail "Previous cannot exist when current is absent."
fi

if [[ "$old_current" == "$target" ]]; then
    systemctl is-active --quiet "$SERVICE" || fail "Release is current but service is not active."
    bash "$target/scripts/post_deploy_smoke.sh" "$release_id" || fail "Current release failed post-activation smoke."
    echo "Release $release_id is already active; no rebuild or symlink change performed."
    exit 0
fi

restore_old_current() {
    systemctl stop "$SERVICE" >/dev/null 2>&1 || true
    if [[ -n "$old_current" ]]; then
        ln -s "$old_current" "$rollback_new" || return 1
        mv -Tf "$rollback_new" "$current" || return 1
        old_release_id="$(basename "$old_current")"
        if ! systemctl restart "$SERVICE" \
            || ! systemctl is-active --quiet "$SERVICE" \
            || ! bash "$old_current/scripts/post_deploy_smoke.sh" "$old_release_id"; then
            systemctl stop "$SERVICE" >/dev/null 2>&1 || true
        fi
    else
        [[ -L "$current" ]] && rm -f -- "$current"
    fi
}

ln -s "$target" "$current_new"
mv -Tf "$current_new" "$current"

activation_failure=""
if ! systemctl daemon-reload; then
    activation_failure="systemd daemon reload failed"
elif ! systemctl restart "$SERVICE"; then
    activation_failure="service restart failed"
elif ! systemctl is-active --quiet "$SERVICE"; then
    activation_failure="service did not become active"
elif ! bash "$target/scripts/post_deploy_smoke.sh" "$release_id"; then
    activation_failure="post-activation smoke failed"
fi

if [[ -n "$activation_failure" ]]; then
    restore_old_current || true
    fail "Activation failed and was rolled back: $activation_failure"
fi

if [[ -n "$old_current" ]]; then
    if ! ln -s "$old_current" "$previous_new" || ! mv -Tf "$previous_new" "$previous"; then
        restore_old_current || true
        fail "Activation failed while preserving previous; current was rolled back."
    fi
fi

echo "Activated prepared release $release_id; database state was not changed."
