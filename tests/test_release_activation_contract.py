from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import tarfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
R1 = "1" * 40
R2 = "2" * 40


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


def _base_environment(tmp_path: Path) -> tuple[dict[str, str], Path, Path]:
    app_root = tmp_path / "app"
    env_file = tmp_path / "beta.env"
    env_file.write_text("DATOSENORDEN_ENV=production\n", encoding="utf-8")
    fake_bin = tmp_path / "fake-bin"
    fake_bin.mkdir()
    bash_env = tmp_path / "bash-env.sh"
    bash_env.write_text(
        'export PATH="$DEO_FAKE_BIN:/usr/bin:/bin"\n',
        encoding="utf-8",
    )
    environment = os.environ.copy()
    environment.update(
        {
            "APP_ROOT": _msys(app_root),
            "BASH_ENV": _msys(bash_env),
            "DEO_FAKE_BIN": _msys(fake_bin),
            "ENV_FILE": _msys(env_file),
            "SERVICE": "datosenorden",
            "SYSTEMCTL_LOG": _msys(tmp_path / "systemctl.log"),
            "SMOKE_LOG": _msys(tmp_path / "smoke.log"),
            "PREPARE_CWD_LOG": _msys(tmp_path / "prepare-cwd.log"),
        }
    )
    _write_command(fake_bin, "id", '[[ "${1:-}" == "-u" ]] && echo 0\n')
    return environment, app_root, fake_bin


def _run(script: str, args: list[str], environment: dict[str, str], cwd: Path):
    return subprocess.run(
        [str(BASH), _msys(ROOT / script), *args],
        cwd=cwd,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )


def _activation_args(release_id: str) -> list[str]:
    return ["--release-id", release_id, "--confirm-ready", release_id]


def _artifact(tmp_path: Path) -> tuple[Path, str]:
    content = tmp_path / "artifact-content"
    (content / "scripts").mkdir(parents=True)
    (content / "pyproject.toml").write_text("[project]\nname='probe'\n", encoding="utf-8")
    (content / "scripts" / "post_deploy_smoke.sh").write_text(
        "#!/usr/bin/env bash\nexit 0\n", encoding="utf-8"
    )
    archive = tmp_path / "release.tar.gz"
    with tarfile.open(archive, "w:gz") as stream:
        stream.add(content / "pyproject.toml", arcname="pyproject.toml")
        stream.add(content / "scripts", arcname="scripts")
    return archive, hashlib.sha256(archive.read_bytes()).hexdigest()


def _install_prepare_fakes(fake_bin: Path, log: Path) -> None:
    _write_command(
        fake_bin,
        "install",
        'target="${!#}"\nmkdir -p "$target"\nchmod 0755 "$target"\n',
    )
    _write_command(fake_bin, "chown", "exit 0\n")
    _write_command(
        fake_bin,
        "runuser",
        f'printf "%s\\n" "$*" >> "{_msys(log)}"\n'
        'while (($#)) && [[ "$1" != "--" ]]; do shift; done\n'
        '[[ "${1:-}" == "--" ]] && shift\n'
        'if [[ "${1:-}" == "bash" ]]; then exec "$@"; fi\n'
        "while (($#)); do\n"
        "  if [[ \"$1\" == \"venv\" ]]; then\n"
        "    target=\"$2\"\n"
        "    mkdir -p \"$target/bin\"\n"
        "    printf '#!/usr/bin/env bash\\nif [[ \"${1:-}\" == \"-m\" && \"${2:-}\" == \"reflex\" ]]; then pwd > \"$PREPARE_CWD_LOG\"; fi\\nexit 0\\n' > \"$target/bin/python\"\n"
        "    printf '#!/usr/bin/env bash\\nexit 0\\n' > \"$target/bin/reflex\"\n"
        "    chmod 0755 \"$target/bin/python\" \"$target/bin/reflex\"\n"
        "    exit 0\n"
        "  fi\n"
        "  shift\n"
        "done\n",
    )
    _write_command(
        fake_bin,
        "find",
        'if [[ -n "${DEO_FIND_VIOLATION:-}" ]]; then\n'
        '  [[ " $* " == *" -type f "* && " $* " == *" -type d "* ]] || exit 99\n'
        '  printf "%s\\n" "$DEO_FIND_VIOLATION"\n'
        '  exit 0\n'
        'fi\n'
        'exec /usr/bin/find "$@"\n',
    )


def _prepared_release(app_root: Path, release_id: str) -> Path:
    target = app_root / "releases" / release_id
    (target / ".venv" / "bin").mkdir(parents=True)
    (target / "scripts").mkdir()
    executables = (
        target / ".venv" / "bin" / "python",
        target / ".venv" / "bin" / "reflex",
    )
    for executable in executables:
        executable.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
        executable.chmod(0o755)
    (target / ".deo-release-ready").write_text(
        f"release_id={release_id}\nartifact_sha256={'a' * 64}\n", encoding="utf-8"
    )
    smoke = target / "scripts" / "post_deploy_smoke.sh"
    smoke.write_text(
        "#!/usr/bin/env bash\n"
        'active="$(basename "$(readlink -f "$APP_ROOT/current")")"\n'
        'printf "smoke:%s\\n" "$active" >> "$SMOKE_LOG"\n'
        '[[ "$active" != "${FAIL_SMOKE_RELEASE:-}" ]]\n',
        encoding="utf-8",
    )
    smoke.chmod(0o755)
    return target


def _install_activation_fakes(fake_bin: Path) -> None:
    if os.name == "nt":
        _write_command(
            fake_bin,
            "ln",
            '[[ "$1" == "-s" && $# -eq 3 ]]\n'
            'target="$(cygpath -w "$2")"\n'
            'link="$(cygpath -w "$3")"\n'
            'DEO_JUNCTION_LINK="$link" DEO_JUNCTION_TARGET="$target" '
            "MSYS2_ARG_CONV_EXCL='*' "
            "/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe "
            "-NoProfile -NonInteractive -Command "
            "'New-Item -ItemType Junction -Path $env:DEO_JUNCTION_LINK "
            "-Target $env:DEO_JUNCTION_TARGET | Out-Null'\n",
        )
    _write_command(
        fake_bin,
        "systemctl",
        'printf "%s\\n" "$*" >> "$SYSTEMCTL_LOG"\n'
        'case "${1:-}" in\n'
        "  daemon-reload) exit 0 ;;\n"
        "  restart)\n"
        '    active="$(basename "$(readlink -f "$APP_ROOT/current")")"\n'
        '    if [[ "$active" == "${FAIL_RESTART_RELEASE:-}" ]]; then '
        'rm -f "$APP_ROOT/.service-active"; exit 1; fi\n'
        '    touch "$APP_ROOT/.service-active"; exit 0 ;;\n'
        '  is-active) [[ -f "$APP_ROOT/.service-active" ]] ;;\n'
        '  stop) rm -f "$APP_ROOT/.service-active"; exit 0 ;;\n'
        "  *) exit 0 ;;\n"
        "esac\n",
    )


def test_prepare_is_single_use_and_never_activates(tmp_path: Path) -> None:
    environment, app_root, fake_bin = _base_environment(tmp_path)
    runuser_log = tmp_path / "runuser.log"
    _install_prepare_fakes(fake_bin, runuser_log)
    archive, digest = _artifact(tmp_path)
    args = [
        "--prepare",
        "--artifact",
        _msys(archive),
        "--sha256",
        digest,
        "--release-id",
        R1,
    ]

    first = _run("scripts/deploy_release_ubuntu.sh", args, environment, tmp_path)

    assert first.returncode == 0, first.stderr
    target = app_root / "releases" / R1
    assert (target / ".deo-release-ready").read_text(encoding="utf-8").splitlines() == [
        f"release_id={R1}",
        f"artifact_sha256={digest}",
    ]
    assert not (app_root / "current").exists()
    prepare_calls = runuser_log.read_text(encoding="utf-8")
    assert " -m venv " in f" {prepare_calls} "
    assert "pip install" in prepare_calls
    assert "reflex compile --dry" in prepare_calls
    assert (tmp_path / "prepare-cwd.log").read_text(encoding="utf-8").strip() == _msys(target)

    second = _run("scripts/deploy_release_ubuntu.sh", args, environment, tmp_path)

    assert second.returncode != 0
    assert "Release already exists" in second.stderr
    assert runuser_log.read_text(encoding="utf-8") == prepare_calls


def test_prepare_immutability_gate_excludes_symlinks_but_checks_files_and_directories() -> None:
    deploy = (ROOT / "scripts" / "deploy_release_ubuntu.sh").read_text(encoding="utf-8")

    assert 'find "$target" -xdev \\( -type f -o -type d \\) -perm /022' in deploy


@pytest.mark.parametrize(
    "violation",
    ("group-writable-regular-file", "group-writable-directory", "other-writable-regular-file"),
)
def test_prepare_rejects_writable_files_and_directories_without_marker(
    tmp_path: Path, violation: str
) -> None:
    environment, app_root, fake_bin = _base_environment(tmp_path)
    _install_prepare_fakes(fake_bin, tmp_path / "runuser.log")
    environment["DEO_FIND_VIOLATION"] = violation
    archive, digest = _artifact(tmp_path)

    failed = _run(
        "scripts/deploy_release_ubuntu.sh",
        [
            "--prepare",
            "--artifact",
            _msys(archive),
            "--sha256",
            digest,
            "--release-id",
            R1,
        ],
        environment,
        tmp_path,
    )

    target = app_root / "releases" / R1
    assert failed.returncode != 0
    assert "Prepared release remains writable" in failed.stderr
    assert not (target / ".deo-release-ready").exists()


def test_first_second_and_repeated_activation_preserve_pointers(tmp_path: Path) -> None:
    environment, app_root, fake_bin = _base_environment(tmp_path)
    _install_activation_fakes(fake_bin)
    first_release = _prepared_release(app_root, R1)
    second_release = _prepared_release(app_root, R2)

    first = _run("scripts/activate_release_ubuntu.sh", _activation_args(R1), environment, tmp_path)
    assert first.returncode == 0, first.stderr
    assert (app_root / "current").resolve() == first_release.resolve()
    assert not (app_root / "previous").exists()

    second = _run("scripts/activate_release_ubuntu.sh", _activation_args(R2), environment, tmp_path)
    assert second.returncode == 0, second.stderr
    assert (app_root / "current").resolve() == second_release.resolve()
    assert (app_root / "previous").resolve() == first_release.resolve()
    systemctl_log = (tmp_path / "systemctl.log").read_text(encoding="utf-8")
    restarts = systemctl_log.count("restart datosenorden")

    repeated = _run(
        "scripts/activate_release_ubuntu.sh",
        _activation_args(R2),
        environment,
        tmp_path,
    )
    assert repeated.returncode == 0, repeated.stderr
    assert "already active" in repeated.stdout
    assert (app_root / "current").resolve() == second_release.resolve()
    assert (app_root / "previous").resolve() == first_release.resolve()
    final_log = (tmp_path / "systemctl.log").read_text(encoding="utf-8")
    assert final_log.count("restart datosenorden") == restarts


def test_activation_rejects_missing_and_incomplete_release(tmp_path: Path) -> None:
    environment, app_root, fake_bin = _base_environment(tmp_path)
    _install_activation_fakes(fake_bin)

    unconfirmed = _run(
        "scripts/activate_release_ubuntu.sh",
        ["--release-id", R1],
        environment,
        tmp_path,
    )
    assert unconfirmed.returncode == 2
    assert "Readiness confirmation" in unconfirmed.stderr

    missing = _run(
        "scripts/activate_release_ubuntu.sh",
        _activation_args(R1),
        environment,
        tmp_path,
    )
    assert missing.returncode != 0
    assert "does not exist" in missing.stderr

    incomplete = app_root / "releases" / R1
    incomplete.mkdir(parents=True)
    rejected = _run(
        "scripts/activate_release_ubuntu.sh",
        _activation_args(R1),
        environment,
        tmp_path,
    )
    assert rejected.returncode != 0
    assert "readiness marker is missing" in rejected.stderr
    assert not (app_root / "current").exists()


def test_failed_update_restores_old_current_and_previous(tmp_path: Path) -> None:
    environment, app_root, fake_bin = _base_environment(tmp_path)
    _install_activation_fakes(fake_bin)
    first_release = _prepared_release(app_root, R1)
    _prepared_release(app_root, R2)
    initial = _run(
        "scripts/activate_release_ubuntu.sh",
        _activation_args(R1),
        environment,
        tmp_path,
    )
    assert initial.returncode == 0, initial.stderr
    environment["FAIL_SMOKE_RELEASE"] = R2

    failed = _run("scripts/activate_release_ubuntu.sh", _activation_args(R2), environment, tmp_path)

    assert failed.returncode != 0
    assert "rolled back" in failed.stderr
    assert (app_root / "current").resolve() == first_release.resolve()
    assert not (app_root / "previous").exists()
    assert (app_root / ".service-active").exists()


def test_failed_first_activation_stops_service_and_removes_current(tmp_path: Path) -> None:
    environment, app_root, fake_bin = _base_environment(tmp_path)
    _install_activation_fakes(fake_bin)
    _prepared_release(app_root, R1)
    environment["FAIL_RESTART_RELEASE"] = R1

    failed = _run("scripts/activate_release_ubuntu.sh", _activation_args(R1), environment, tmp_path)

    assert failed.returncode != 0
    assert "service restart failed" in failed.stderr
    assert not (app_root / "current").exists()
    assert not (app_root / "previous").exists()
    assert not (app_root / ".service-active").exists()


def test_activation_contains_no_build_or_database_mutation() -> None:
    activate = (ROOT / "scripts" / "activate_release_ubuntu.sh").read_text(encoding="utf-8")
    forbidden_commands = (
        "pip install",
        "reflex compile",
        "tar -xf",
        "alembic",
        "psql",
        "import_production_data",
    )
    for forbidden in forbidden_commands:
        assert forbidden not in activate
    assert 'mv -Tf "$current_new" "$current"' in activate
    assert "post_deploy_smoke.sh" in activate
