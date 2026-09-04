from __future__ import annotations

import argparse
import os
import re
import shlex
import tempfile
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

_ASSIGNMENT = re.compile(r"^(?P<name>[A-Z][A-Z0-9_]*)=(?P<value>.*)$")
_RELEASE_DATABASE = re.compile(r"^datosenorden_rel_[0-9a-f]{16}$")
_DATABASE_KEYS = ("DATABASE_URL", "DATOSENORDEN_DATABASE_URL")
_LOOPBACK_HOSTS = {"127.0.0.1", "::1", "localhost"}


def parse_environment(path: Path) -> tuple[list[str], dict[str, str]]:
    if path.is_symlink() or not path.is_file():
        raise ValueError("environment file must be a regular non-symlink file")
    lines = path.read_text(encoding="utf-8").splitlines()
    values: dict[str, str] = {}
    for line in lines:
        match = _ASSIGNMENT.fullmatch(line)
        if match is None:
            continue
        tokens = shlex.split(match.group("value"), posix=True)
        if len(tokens) != 1:
            raise ValueError(f"environment assignment is not a single value: {match.group('name')}")
        values[match.group("name")] = tokens[0]
    for key in _DATABASE_KEYS:
        if not values.get(key):
            raise ValueError(f"missing required database setting: {key}")
    return lines, values


def database_identity(path: Path) -> dict[str, str]:
    _, values = parse_environment(path)
    identities = [_parse_database_url(values[key]) for key in _DATABASE_KEYS]
    if identities[0] != identities[1]:
        raise ValueError("database settings do not identify the same target")
    parsed = urlsplit(values[_DATABASE_KEYS[0]])
    return {
        "database": identities[0][3],
        "host": identities[0][0],
        "port": str(identities[0][1]),
        "username": identities[0][2],
        "scheme": parsed.scheme,
    }


def release_database_name(release_id: str) -> str:
    if not re.fullmatch(r"[0-9a-f]{40}", release_id):
        raise ValueError("release ID must be 40 lowercase hexadecimal characters")
    return f"datosenorden_rel_{release_id[:16]}"


def render_candidate_environment(
    source: Path,
    destination: Path,
    *,
    expected_current_database: str,
    target_database: str,
) -> None:
    if not _RELEASE_DATABASE.fullmatch(target_database):
        raise ValueError("target database is not a release-specific database name")
    if target_database in {"postgres", "template0", "template1", expected_current_database}:
        raise ValueError("target database must be new and non-administrative")
    lines, values = parse_environment(source)
    identity = database_identity(source)
    if identity["database"] != expected_current_database:
        raise ValueError("current database confirmation mismatch")
    replacements = {
        key: shlex.quote(_replace_database(values[key], target_database)) for key in _DATABASE_KEYS
    }
    rendered: list[str] = []
    seen: set[str] = set()
    for line in lines:
        match = _ASSIGNMENT.fullmatch(line)
        if match is not None and match.group("name") in replacements:
            key = match.group("name")
            rendered.append(f"{key}={replacements[key]}")
            seen.add(key)
        else:
            rendered.append(line)
    if seen != set(_DATABASE_KEYS):
        raise ValueError("database settings were not both rendered")
    if destination.exists() or destination.is_symlink():
        raise FileExistsError("candidate environment already exists")
    destination.parent.mkdir(parents=True, exist_ok=True)
    source_stat = source.stat()
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{destination.name}.", dir=destination.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
            stream.write("\n".join(rendered) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temporary, 0o640)
        try:
            os.chown(temporary, source_stat.st_uid, source_stat.st_gid)
        except (AttributeError, PermissionError):
            pass
        os.replace(temporary, destination)
    finally:
        if temporary.exists():
            temporary.unlink()


def _parse_database_url(value: str) -> tuple[str, int, str, str]:
    parsed = urlsplit(value)
    if parsed.scheme not in {"postgresql", "postgresql+psycopg"}:
        raise ValueError("database URL must use PostgreSQL")
    host = parsed.hostname or ""
    if host not in _LOOPBACK_HOSTS:
        raise ValueError("database host must be loopback/local")
    database = parsed.path.removeprefix("/")
    username = parsed.username or ""
    if not database or not username:
        raise ValueError("database URL must include user and database")
    return host, parsed.port or 5432, username, database


def _replace_database(value: str, target_database: str) -> str:
    parsed = urlsplit(value)
    _parse_database_url(value)
    return urlunsplit(
        (parsed.scheme, parsed.netloc, f"/{target_database}", parsed.query, parsed.fragment)
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate and render release-pair database config."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    field = subparsers.add_parser("field")
    field.add_argument("--env-file", type=Path, required=True)
    field.add_argument("--name", choices=("database", "host", "port", "username"), required=True)
    name = subparsers.add_parser("database-name")
    name.add_argument("--release-id", required=True)
    render = subparsers.add_parser("render")
    render.add_argument("--env-file", type=Path, required=True)
    render.add_argument("--output", type=Path, required=True)
    render.add_argument("--expected-current-database", required=True)
    render.add_argument("--target-database", required=True)
    args = parser.parse_args(argv)
    if args.command == "field":
        print(database_identity(args.env_file)[args.name])
    elif args.command == "database-name":
        print(release_database_name(args.release_id))
    else:
        render_candidate_environment(
            args.env_file,
            args.output,
            expected_current_database=args.expected_current_database,
            target_database=args.target_database,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
