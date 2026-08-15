#!/usr/bin/env bash
set -euo pipefail

status=0
warn() { printf 'WARNING %s\n' "$1"; }
fail() { printf 'FAIL %s\n' "$1"; status=1; }
pass() { printf 'PASS %s\n' "$1"; }
unknown() { printf 'UNKNOWN %s\n' "$1"; }

# The minimum profile supports one low-traffic Reflex service, local PostgreSQL,
# and sequential build/migration/backup operations.  The recommended profile
# retains additional headroom for temporary service overlap and heavier builds.
minimum_cpu_count=2
recommended_cpu_count=3
minimum_memory_kib=3600000
recommended_memory_kib=7600000
recommended_swap_kib=1048576

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
if (( cpu_count < minimum_cpu_count )); then
    fail capacity_blocking_cpu
elif (( cpu_count < recommended_cpu_count )); then
    warn capacity_cpu_below_recommended
else
    pass capacity_cpu
fi
mem_kib="$(awk '/MemTotal:/ {print $2}' /proc/meminfo 2>/dev/null || echo 0)"
printf 'INFO memory_kib=%s\n' "$mem_kib"
if (( mem_kib < minimum_memory_kib )); then
    fail capacity_blocking_memory
elif (( mem_kib < recommended_memory_kib )); then
    warn capacity_memory_below_recommended
else
    pass capacity_memory
fi
swap_kib="$(awk '/SwapTotal:/ {print $2}' /proc/meminfo 2>/dev/null || echo 0)"
printf 'INFO swap_kib=%s\n' "$swap_kib"
if (( mem_kib < recommended_memory_kib )); then
    if (( swap_kib >= recommended_swap_kib )); then
        pass capacity_swap_for_minimum_profile
    else
        warn capacity_swap_below_recommended
    fi
fi
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
