#!/usr/bin/env bash
set -euo pipefail

APP_ROOT="${APP_ROOT:-/opt/datosenorden}"
APP_USER="${APP_USER:-datosenorden}"
ENV_FILE="${ENV_FILE:-/etc/datosenorden/beta.env}"
PAIR_ROOT="${PAIR_ROOT:-/var/lib/datosenorden/release-pairs}"
release_id="" package="" expected_sha="" package_id="" target_database="" current_database="" prepare=0 plan=0
while [[ $# -gt 0 ]]; do
    case "$1" in
        --prepare) prepare=1; shift ;;
        --plan) plan=1; shift ;;
        --release-id) release_id="$2"; shift 2 ;;
        --package) package="$2"; shift 2 ;;
        --sha256) expected_sha="$2"; shift 2 ;;
        --package-id) package_id="$2"; shift 2 ;;
        --target-database) target_database="$2"; shift 2 ;;
        --confirm-current-database) current_database="$2"; shift 2 ;;
        *) echo "Unknown argument: $1" >&2; exit 2 ;;
    esac
done
fail() { echo "$1" >&2; exit "${2:-1}"; }
[[ "$(id -u)" -eq 0 ]] || fail "Run as root through sudo." 2
(( prepare + plan == 1 )) || fail "Select exactly one explicit mode: --prepare or --plan." 2
[[ "$release_id" =~ ^[a-f0-9]{40}$ ]] || fail "A lowercase 40-hex release ID is required." 2
[[ "$expected_sha" =~ ^[a-f0-9]{64}$ && -f "$package" ]] || fail "Package and SHA-256 are required." 2
[[ "$package_id" =~ ^DEO-PROD-DATA-[0-9]{4}-[a-f0-9]{16}$ ]] || fail "Package ID is invalid." 2
[[ "$current_database" =~ ^[a-z][a-z0-9_]{0,62}$ ]] || fail "Current database confirmation is invalid." 2
target="$APP_ROOT/releases/$release_id"
python="$target/.venv/bin/python"
config_tool="$target/scripts/release_pair_config.py"
[[ -d "$target" && ! -L "$target" && -x "$python" && -f "$target/.deo-release-ready" ]] || fail "Prepared code release is unavailable."
[[ -f "$ENV_FILE" && ! -L "$ENV_FILE" ]] || fail "Active environment must be a regular non-symlink file."
[[ "$(stat -c '%a:%U' "$ENV_FILE")" == "640:root" ]] || fail "Active environment permissions are unsafe."
[[ "$(sha256sum "$package" | awk '{print $1}')" == "$expected_sha" ]] || fail "DATA package SHA-256 mismatch."
derived_database="$($python "$config_tool" database-name --release-id "$release_id")"
[[ "$target_database" == "$derived_database" ]] || fail "Target database is not the deterministic release database."
active_database="$($python "$config_tool" field --env-file "$ENV_FILE" --name database)"
[[ "$active_database" == "$current_database" ]] || fail "Current database confirmation mismatch."
[[ "$target_database" != "$active_database" && "$target_database" != "postgres" && "$target_database" != "template0" && "$target_database" != "template1" ]] || fail "Unsafe target database."
[[ "$($python "$config_tool" field --env-file "$ENV_FILE" --name host)" =~ ^(127\.0\.0\.1|::1|localhost)$ ]] || fail "PostgreSQL must be loopback/local."
db_user="$($python "$config_tool" field --env-file "$ENV_FILE" --name username)"
[[ "$db_user" =~ ^[a-z][a-z0-9_]{0,62}$ ]] || fail "Database owner identity is unsafe."
current_release="$(readlink -f "$APP_ROOT/current" 2>/dev/null || true)"
[[ "$(dirname "$current_release")" == "$APP_ROOT/releases" && "$(basename "$current_release")" =~ ^[a-f0-9]{40}$ ]] || fail "Current code release is unsafe."
candidate_env="$PAIR_ROOT/$release_id.env"
ready_marker="$PAIR_ROOT/$release_id.ready"
pending_marker="$ready_marker.pending"
[[ ! -e "$candidate_env" && ! -L "$candidate_env" && ! -e "$ready_marker" && ! -L "$ready_marker" && ! -e "$pending_marker" && ! -L "$pending_marker" ]] || fail "Snapshot preparation state already exists."
if sudo -u postgres psql -Atqc "select 1 from pg_database where datname='$target_database'" | grep -qx 1; then
    fail "Target release database already exists; refusing reuse."
fi
if (( plan )); then
    printf 'Snapshot plan: release=%s package=%s current_database=%s target_database=%s; active pair will remain untouched.\n' "$release_id" "$package_id" "$current_database" "$target_database"
    exit 0
fi
install -d -o root -g "$APP_USER" -m 0750 "$PAIR_ROOT"
$python "$config_tool" render --env-file "$ENV_FILE" --output "$candidate_env" --expected-current-database "$current_database" --target-database "$target_database"
chown root:"$APP_USER" "$candidate_env"
chmod 0640 "$candidate_env"
sudo -u postgres createdb -O "$db_user" "$target_database"
sudo -u postgres psql -v ON_ERROR_STOP=1 -d postgres -c "REVOKE ALL ON DATABASE $target_database FROM PUBLIC; GRANT CONNECT, TEMPORARY ON DATABASE $target_database TO $db_user;"
run_candidate() {
    sudo -u "$APP_USER" bash -c 'set -a; . "$1"; set +a; cd "$2"; shift 2; exec "$@"' -- "$candidate_env" "$target" "$@"
}
run_candidate "$python" -m alembic upgrade head
run_candidate "$python" scripts/import_production_data.py --package "$package" --sha256 "$expected_sha" --expected-database "$target_database" --target-environment production --code-release "$release_id" --confirm-production "$package_id"
run_candidate "$python" scripts/verify_production_snapshot.py --package "$package" --sha256 "$expected_sha" --expected-database "$target_database" --code-release "$release_id"
run_candidate "$python" scripts/deploy_check.py
run_candidate "$python" scripts/prelaunch_public_check.py --read-only
umask 077
printf 'release_id=%s\ntarget_database=%s\npackage_id=%s\npackage_sha256=%s\nprevious_release=%s\nprevious_database=%s\n' "$release_id" "$target_database" "$package_id" "$expected_sha" "$(basename "$current_release")" "$current_database" > "$pending_marker"
chown root:"$APP_USER" "$pending_marker"
chmod 0640 "$pending_marker"
mv -T "$pending_marker" "$ready_marker"
echo "Prepared isolated DATA snapshot $package_id for code release $release_id; active pair unchanged."
