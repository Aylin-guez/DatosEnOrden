from __future__ import annotations

import importlib
import os
from pathlib import Path
import platform
import shutil
import socket
import subprocess
import sys
from dataclasses import dataclass
from typing import Sequence

MIN_NODE_VERSION = (22, 12, 0)
PROJECT_ROOT = Path(__file__).resolve().parents[2]
REFLEX_APP_DIR = PROJECT_ROOT / "reflex_app"


@dataclass(frozen=True)
class CheckResult:
    name: str
    ok: bool
    detail: str


def parse_semver(text: str) -> tuple[int, int, int] | None:
    tokens = text.strip().split()
    if not tokens:
        return None
    cleaned = tokens[0].lstrip("v")
    parts = cleaned.split(".")
    if len(parts) < 2:
        return None
    numbers: list[int] = []
    for part in parts[:3]:
        digits = ""
        for char in part:
            if not char.isdigit():
                break
            digits += char
        if not digits:
            return None
        numbers.append(int(digits))
    while len(numbers) < 3:
        numbers.append(0)
    return tuple(numbers)  # type: ignore[return-value]


def version_at_least(found: tuple[int, int, int] | None, minimum: tuple[int, int, int]) -> bool:
    return found is not None and found >= minimum


def is_port_free(port: int, host: str = "127.0.0.1") -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.5)
        return sock.connect_ex((host, port)) != 0


def run_command(args: Sequence[str], *, cwd: Path | None = None) -> tuple[bool, str]:
    command = shutil.which(args[0])
    if command is None:
        return False, "command not found"
    resolved_args = [command, *args[1:]]
    try:
        completed = subprocess.run(
            resolved_args,
            cwd=cwd,
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except FileNotFoundError:
        return False, "command not found"
    except subprocess.TimeoutExpired:
        return False, "command timed out"
    output = (completed.stdout or completed.stderr).strip()
    return completed.returncode == 0, output or f"exit code {completed.returncode}"


def mask_database_url(url: str) -> str:
    if "@" not in url or ":" not in url:
        return url
    scheme_sep = "://"
    if scheme_sep not in url:
        return url
    prefix, rest = url.split(scheme_sep, 1)
    if "@" not in rest:
        return url
    credentials, host_part = rest.split("@", 1)
    if ":" not in credentials:
        return url
    user, _password = credentials.split(":", 1)
    return f"{prefix}{scheme_sep}{user}:***@{host_part}"


def _add_import_paths() -> None:
    for path in (PROJECT_ROOT, PROJECT_ROOT / "src"):
        text = str(path)
        if text not in sys.path:
            sys.path.insert(0, text)


def check_python() -> CheckResult:
    return CheckResult(
        "Python",
        True,
        f"{sys.executable} ({platform.python_version()})",
    )


def check_reflex_import() -> CheckResult:
    try:
        reflex = importlib.import_module("reflex")
    except Exception as exc:  # noqa: BLE001
        return CheckResult("Reflex import", False, f"{type(exc).__name__}: {exc}")
    version = getattr(reflex, "__version__", None)
    if version is None:
        try:
            from importlib.metadata import version as package_version

            version = package_version("reflex")
        except Exception:  # noqa: BLE001
            version = "version unavailable"
    return CheckResult("Reflex import", True, str(version))


def check_node() -> CheckResult:
    ok, output = run_command(("node", "--version"))
    parsed = parse_semver(output) if ok else None
    meets_minimum = version_at_least(parsed, MIN_NODE_VERSION)
    minimum_text = ".".join(str(part) for part in MIN_NODE_VERSION)
    return CheckResult(
        "Node",
        ok and meets_minimum,
        f"{output} (requires >= {minimum_text})",
    )


def check_npm() -> CheckResult:
    ok, output = run_command(("npm", "--version"))
    return CheckResult("npm", ok, output)


def check_rxconfig() -> CheckResult:
    path = PROJECT_ROOT / "rxconfig.py"
    return CheckResult("rxconfig.py", path.exists(), str(path))


def check_reflex_app_import() -> CheckResult:
    _add_import_paths()
    try:
        importlib.import_module("reflex_app.reflex_app")
    except Exception as exc:  # noqa: BLE001
        return CheckResult("Reflex app import", False, f"{type(exc).__name__}: {exc}")
    return CheckResult("Reflex app import", True, "reflex_app.reflex_app")


def check_database_url() -> CheckResult:
    _add_import_paths()
    explicit = os.getenv("DATABASE_URL") or os.getenv("DATOSENORDEN_DATABASE_URL")
    try:
        from datosenorden.core.config import get_settings

        effective = get_settings().database_url
    except Exception as exc:  # noqa: BLE001
        return CheckResult("DATABASE_URL", False, f"{type(exc).__name__}: {exc}")
    source = "environment/.env" if explicit else "default settings fallback"
    return CheckResult("DATABASE_URL explicitly set", bool(explicit), f"{source}: {mask_database_url(effective)}")


def check_postgresql_connection() -> CheckResult:
    _add_import_paths()
    try:
        from sqlalchemy import text

        from datosenorden.db.session import build_engine

        engine = build_engine()
        with engine.connect() as connection:
            connection.execute(text("select 1"))
        engine.dispose()
    except Exception as exc:  # noqa: BLE001
        return CheckResult("PostgreSQL connection", False, f"{type(exc).__name__}: {exc}")
    return CheckResult("PostgreSQL connection", True, "select 1 succeeded")


def check_port(port: int, label: str) -> CheckResult:
    free = is_port_free(port)
    return CheckResult(label, free, "free" if free else "in use")


def run_checks() -> list[CheckResult]:
    return [
        CheckResult("Current working directory", True, str(Path.cwd())),
        CheckResult("Reflex app directory exists", REFLEX_APP_DIR.exists(), str(REFLEX_APP_DIR)),
        check_python(),
        check_reflex_import(),
        check_node(),
        check_npm(),
        check_rxconfig(),
        check_reflex_app_import(),
        check_database_url(),
        check_postgresql_connection(),
        check_port(3000, "Frontend port 3000"),
        check_port(3001, "Frontend port 3001"),
        check_port(8000, "Backend port 8000"),
        check_port(8001, "Backend port 8001"),
    ]


def render_results(results: Sequence[CheckResult]) -> str:
    lines = ["DatosEnOrden Reflex environment diagnostics", ""]
    for result in results:
        marker = "OK" if result.ok else "FAIL"
        lines.append(f"[{marker}] {result.name}: {result.detail}")
    return "\n".join(lines)


def main() -> int:
    results = run_checks()
    print(render_results(results))
    return 0 if all(result.ok for result in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
