from __future__ import annotations

import os
import shutil
import subprocess
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
RELEASE = "a" * 40


def _bash_executable() -> Path:
    if os.name == "nt":
        git = shutil.which("git")
        assert git is not None
        return Path(git).resolve().parents[1] / "bin" / "bash.exe"
    bash = shutil.which("bash")
    assert bash is not None
    return Path(bash)


BASH = _bash_executable()


def _msys(path: Path) -> str:
    if os.name != "nt":
        return str(path.resolve())
    result = subprocess.run(
        [str(BASH), "-lc", 'cygpath -u "$1"', "bash", str(path.resolve())],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def _write_command(directory: Path, name: str, payload: str) -> None:
    path = directory / name
    path.write_text("#!/usr/bin/env bash\nset -euo pipefail\n" + payload, encoding="utf-8")
    path.chmod(0o755)


def _make_current(app_root: Path, target: Path) -> None:
    current = app_root / "current"
    if os.name != "nt":
        current.symlink_to(target, target_is_directory=True)
        return
    subprocess.run(
        [
            "powershell.exe",
            "-NoProfile",
            "-NonInteractive",
            "-Command",
            f"New-Item -ItemType Junction -Path '{current}' -Target '{target}' | Out-Null",
        ],
        check=True,
    )


def _environment(tmp_path: Path, *, curl_sequence: str, service_mode: str = "active") -> dict[str, str]:
    app_root = tmp_path / "app"
    target = app_root / "releases" / RELEASE
    target.mkdir(parents=True)
    _make_current(app_root, target)
    fake_bin = tmp_path / "fake-bin"
    fake_bin.mkdir()
    bash_env = tmp_path / "bash-env.sh"
    bash_env.write_text('export PATH="$DEO_FAKE_BIN:/usr/bin:/bin"\n', encoding="utf-8")
    systemctl_count = _msys(tmp_path / "systemctl-count")
    curl_count = _msys(tmp_path / "curl-count")
    sleep_log = _msys(tmp_path / "sleep.log")
    _write_command(
        fake_bin,
        "systemctl",
        'if [[ "${1:-}" != "is-active" ]]; then exit 0; fi\n'
        'count=0; [[ -f "$SYSTEMCTL_COUNT" ]] && count="$(cat "$SYSTEMCTL_COUNT")"\n'
        'printf "%s" "$((count + 1))" > "$SYSTEMCTL_COUNT"\n'
        '[[ "$SERVICE_MODE" != "die_during_wait" || "$count" -eq 0 ]]\n',
    )
    _write_command(fake_bin, "pg_isready", "exit 0\n")
    _write_command(fake_bin, "ss", "exit 1\n")
    _write_command(fake_bin, "journalctl", "exit 0\n")
    _write_command(fake_bin, "awk", "cat >/dev/null\nprintf '9000000\\n'\n")
    _write_command(
        fake_bin,
        "curl",
        'count=0; [[ -f "$CURL_COUNT" ]] && count="$(cat "$CURL_COUNT")"\n'
        'IFS=, read -r -a statuses <<< "$CURL_SEQUENCE"\n'
        'status="${statuses[$count]:-${statuses[-1]}}"\n'
        'printf "%s" "$((count + 1))" > "$CURL_COUNT"\n'
        'printf "%s" "$status"\n'
        '[[ "$status" == 2* ]] && exit 0\n'
        '[[ "$status" == 5* ]] && exit 0\n'
        'exit 7\n',
    )
    _write_command(
        fake_bin,
        "sleep",
        'printf "%s\\n" "$1" >> "$SLEEP_LOG"\n'
        'exec /usr/bin/sleep "$1"\n',
    )
    environment = os.environ.copy()
    environment.update(
        {
            "APP_ROOT": _msys(app_root),
            "BASH_ENV": _msys(bash_env),
            "DEO_FAKE_BIN": _msys(fake_bin),
            "SERVICE": "datosenorden",
            "SYSTEMCTL_COUNT": systemctl_count,
            "CURL_COUNT": curl_count,
            "SLEEP_LOG": sleep_log,
            "CURL_SEQUENCE": curl_sequence,
            "SERVICE_MODE": service_mode,
            "READINESS_TIMEOUT_SECONDS": "3",
            "READINESS_INTERVAL_SECONDS": "1",
            "PER_ATTEMPT_TIMEOUT_SECONDS": "1",
        }
    )
    return environment


def _run_smoke(tmp_path: Path, environment: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(BASH), _msys(ROOT / "scripts" / "post_deploy_smoke.sh"), RELEASE],
        cwd=tmp_path,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
        timeout=15,
    )


def test_backend_ready_immediately_passes(tmp_path: Path) -> None:
    result = _run_smoke(tmp_path, _environment(tmp_path, curl_sequence="200"))

    assert result.returncode == 0, result.stderr
    assert "PASS backend_readiness attempts=1 status=200" in result.stdout
    assert not (tmp_path / "sleep.log").exists()


def test_backend_ready_after_polling_passes_without_busy_loop(tmp_path: Path) -> None:
    environment = _environment(tmp_path, curl_sequence="000,000,204")
    started = time.monotonic()
    result = _run_smoke(tmp_path, environment)
    elapsed = time.monotonic() - started

    assert result.returncode == 0, result.stderr
    assert "PASS backend_readiness attempts=3 status=204" in result.stdout
    assert (tmp_path / "sleep.log").read_text(encoding="utf-8").splitlines() == ["1", "1"]
    assert elapsed >= 1.8


def test_backend_never_ready_fails_with_bounded_timeout(tmp_path: Path) -> None:
    environment = _environment(tmp_path, curl_sequence="000")
    started = time.monotonic()
    result = _run_smoke(tmp_path, environment)
    elapsed = time.monotonic() - started

    assert result.returncode == 1
    assert "FAIL backend_readiness_timeout" in result.stdout
    assert (tmp_path / "sleep.log").read_text(encoding="utf-8").splitlines() == ["1", "1"]
    assert elapsed < 10.0


def test_service_death_during_readiness_fails_early(tmp_path: Path) -> None:
    environment = _environment(tmp_path, curl_sequence="000", service_mode="die_during_wait")
    started = time.monotonic()
    result = _run_smoke(
        tmp_path,
        environment,
    )
    elapsed = time.monotonic() - started

    assert result.returncode == 1
    assert "FAIL backend_service_inactive_during_readiness" in result.stdout
    assert not (tmp_path / "sleep.log").exists()
    assert elapsed < 10.0


def test_non_2xx_response_does_not_satisfy_readiness(tmp_path: Path) -> None:
    result = _run_smoke(tmp_path, _environment(tmp_path, curl_sequence="503"))

    assert result.returncode == 1
    assert "PASS backend_readiness" not in result.stdout
    assert "FAIL backend_readiness_timeout" in result.stdout


def test_bash_and_real_curl_detect_a_delayed_http_backend(tmp_path: Path) -> None:
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            self.send_response(204)
            self.end_headers()

        def log_message(self, format: str, *args: object) -> None:  # noqa: A002
            return

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    environment = _environment(tmp_path, curl_sequence="000")
    curl = shutil.which("curl.exe") or shutil.which("curl")
    assert curl is not None
    _write_command(
        tmp_path / "fake-bin",
        "curl",
        'if [[ ! -f "$CURL_COUNT" ]]; then printf "1" > "$CURL_COUNT"; printf "000"; exit 7; fi\n'
        'exec "$REAL_CURL" "$@"\n',
    )
    environment["REAL_CURL"] = _msys(Path(curl))
    environment["READINESS_URL"] = f"http://127.0.0.1:{server.server_port}/"
    thread = threading.Thread(target=lambda: (time.sleep(0.2), server.serve_forever()), daemon=True)
    thread.start()
    try:
        result = _run_smoke(tmp_path, environment)
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()

    assert result.returncode == 0, result.stderr
    assert "PASS backend_readiness attempts=2 status=204" in result.stdout
