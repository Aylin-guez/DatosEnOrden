#!/usr/bin/env bash
set -euo pipefail

APP_ROOT="${APP_ROOT:-/opt/datosenorden}"
release_id="${1:-}"
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
bash "$SCRIPT_DIR/activate_release_ubuntu.sh" \
    --release-id "$release_id" \
    --confirm-ready "$release_id"
echo "Application rollback completed. Database state was not changed."
