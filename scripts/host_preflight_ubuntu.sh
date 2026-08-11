#!/usr/bin/env bash
set -euo pipefail

status=0
warn() { printf 'WARNING %s\n' "$1"; }
fail() { printf 'FAIL %s\n' "$1"; status=1; }
pass() { printf 'PASS %s\n' "$1"; }
unknown() { printf 'UNKNOWN %s\n' "$1"; }

if [[ -r /etc/os-release ]]; then
    . /etc/os-release
    printf 'INFO distro=%s version=%s\n' "${ID:-unknown}" "${VERSION_ID:-unknown}"
    [[ "${ID:-}" == "ubuntu" && "${VERSION_ID:-}" == "24.04" ]] && pass ubuntu_24_04 || fail ubuntu_24_04
else
    unknown os_release
fi

printf 'INFO kernel=%s architecture=%s timezone=%s\n' "$(uname -r)" "$(uname -m)" "$(timedatectl show -p Timezone --value 2>/dev/null || echo unknown)"
cpu_count="$(nproc 2>/dev/null || echo 0)"
printf 'INFO cpu_count=%s\n' "$cpu_count"
(( cpu_count >= 3 )) && pass cpu_count || fail cpu_count
mem_kib="$(awk '/MemTotal:/ {print $2}' /proc/meminfo 2>/dev/null || echo 0)"
printf 'INFO memory_kib=%s\n' "$mem_kib"
(( mem_kib >= 7600000 )) && pass memory_capacity || warn memory_capacity
root_avail_kib="$(df -Pk / | awk 'NR==2 {print $4}')"
printf 'INFO root_available_kib=%s\n' "$root_avail_kib"
(( root_avail_kib >= 50000000 )) && pass root_storage || fail root_storage
printf 'INFO filesystems\n'; df -hT /
printf 'INFO interfaces\n'; ip -brief address 2>/dev/null || unknown interfaces
printf 'INFO listening_ports\n'; ss -ltn 2>/dev/null || unknown listening_ports
for command in systemctl python3 node psql caddy ufw; do
    if command -v "$command" >/dev/null 2>&1; then
        pass "command_${command}"
    else
        unknown "command_${command}"
    fi
done
if [[ -e /var/run/reboot-required ]]; then warn reboot_required; else pass reboot_not_required; fi
exit "$status"
