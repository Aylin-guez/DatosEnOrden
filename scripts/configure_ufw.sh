#!/usr/bin/env bash
set -euo pipefail

if [[ "${1:-}" != "--confirmed-ssh" || -z "${SSH_CONNECTION:-}" ]]; then
    echo "Refusing to change firewall without --confirmed-ssh from an active SSH session." >&2
    exit 2
fi
if [[ "$(id -u)" -ne 0 ]]; then
    echo "Run as root through sudo." >&2
    exit 2
fi
command -v ufw >/dev/null 2>&1 || { echo "ufw is required." >&2; exit 1; }
if ufw status numbered | grep -Eq '(^|[^0-9])(3000|5432)([^0-9]|$)'; then
    echo "Existing UFW rules reference 3000 or 5432; remove them manually before enabling this policy." >&2
    exit 1
fi

ufw allow OpenSSH
ufw allow 80/tcp
ufw allow 443/tcp
if ! ufw status | grep -q 'OpenSSH'; then
    echo "OpenSSH rule was not confirmed; refusing to enable UFW." >&2
    exit 1
fi
ufw default deny incoming
ufw default allow outgoing
ufw --force enable
ufw status verbose
