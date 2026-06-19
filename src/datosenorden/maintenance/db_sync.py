from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import os
from pathlib import Path
import shutil
import subprocess

from sqlalchemy import func, select
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from datosenorden.core.config import get_settings
from datosenorden.models import Claim, Entity, Evidence, RelationshipPublic, SourceRecord

PROJECT_ROOT = Path(__file__).resolve().parents[3]
BACKUPS_DIR = PROJECT_ROOT / "private" / "database" / "backups"


@dataclass(frozen=True)
class PgConnectionInfo:
    host: str | None
    port: int | None
    username: str | None
    password: str | None
    database: str


@dataclass(frozen=True)
class DatabaseCounts:
    entity: int
    source_record: int
    claim: int
    evidence: int
    relationship_public: int


def get_database_url() -> str:
    return get_settings().database_url


def get_connection_info(database_url: str | None = None) -> PgConnectionInfo:
    url = make_url(database_url or get_database_url())
    if not url.database:
        raise ValueError("DATABASE_URL must include a database name")
    return PgConnectionInfo(
        host=url.host,
        port=url.port,
        username=url.username,
        password=url.password,
        database=url.database,
    )


def render_database_url_safe(database_url: str | None = None) -> str:
    return make_url(database_url or get_database_url()).render_as_string(hide_password=True)


def find_pg_tool(tool_name: str) -> Path:
    binary_name = f"{tool_name}.exe" if os.name == "nt" else tool_name
    path = shutil.which(binary_name) or shutil.which(tool_name)
    if path:
        return Path(path)

    if os.name == "nt":
        for env_var in ("PROGRAMFILES", "PROGRAMFILES(X86)", "PROGRAMW6432"):
            root = os.getenv(env_var)
            if not root:
                continue
            postgres_root = Path(root) / "PostgreSQL"
            if not postgres_root.exists():
                continue
            for candidate in postgres_root.glob(f"*/bin/{binary_name}"):
                if candidate.exists():
                    return candidate

    raise FileNotFoundError(
        f"{tool_name} was not found. Add the PostgreSQL bin directory to PATH, "
        "for example C:\\Program Files\\PostgreSQL\\16\\bin."
    )


def build_dump_path(timestamp: datetime | None = None) -> Path:
    stamp = timestamp or datetime.now()
    return BACKUPS_DIR / f"datosenorden_local_{stamp:%Y%m%d_%H%M%S}.dump"


def build_pg_dump_command(database_url: str, dump_path: Path, pg_dump_path: Path) -> list[str]:
    info = get_connection_info(database_url)
    command = [
        str(pg_dump_path),
        "--format=custom",
        "--file",
        str(dump_path),
        "--no-owner",
        "--no-privileges",
    ]
    if info.host:
        command.extend(["--host", info.host])
    if info.port is not None:
        command.extend(["--port", str(info.port)])
    if info.username:
        command.extend(["--username", info.username])
    command.append(info.database)
    return command


def build_pg_restore_command(
    database_url: str,
    dump_path: Path,
    pg_restore_path: Path,
    *,
    clean: bool = True,
) -> list[str]:
    info = get_connection_info(database_url)
    command = [str(pg_restore_path), "--no-owner", "--no-privileges", "--single-transaction"]
    if clean:
        command[1:1] = ["--clean", "--if-exists"]
    if info.host:
        command.extend(["--host", info.host])
    if info.port is not None:
        command.extend(["--port", str(info.port)])
    if info.username:
        command.extend(["--username", info.username])
    command.extend(["--dbname", info.database, str(dump_path)])
    return command


def build_createdb_command(database_url: str, db_name: str, createdb_path: Path) -> list[str]:
    info = get_connection_info(database_url)
    command = [str(createdb_path)]
    if info.host:
        command.extend(["--host", info.host])
    if info.port is not None:
        command.extend(["--port", str(info.port)])
    if info.username:
        command.extend(["--username", info.username])
    command.append(db_name)
    return command


def build_dropdb_command(database_url: str, db_name: str, dropdb_path: Path) -> list[str]:
    info = get_connection_info(database_url)
    command = [str(dropdb_path)]
    if info.host:
        command.extend(["--host", info.host])
    if info.port is not None:
        command.extend(["--port", str(info.port)])
    if info.username:
        command.extend(["--username", info.username])
    command.append(db_name)
    return command


def build_database_url_with_name(database_url: str, database_name: str) -> str:
    url = make_url(database_url)
    return str(url.set(database=database_name))


def build_subprocess_env(password: str | None) -> dict[str, str]:
    env = os.environ.copy()
    if password:
        env["PGPASSWORD"] = password
    return env


def run_pg_command(command: list[str], password: str | None) -> None:
    subprocess.run(command, check=True, env=build_subprocess_env(password))


def collect_database_counts(session: Session) -> DatabaseCounts:
    return DatabaseCounts(
        entity=_scalar_count(session, select(func.count()).select_from(Entity)),
        source_record=_scalar_count(session, select(func.count()).select_from(SourceRecord)),
        claim=_scalar_count(session, select(func.count()).select_from(Claim)),
        evidence=_scalar_count(session, select(func.count()).select_from(Evidence)),
        relationship_public=_scalar_count(session, select(func.count()).select_from(RelationshipPublic)),
    )


def render_database_counts_text(counts: DatabaseCounts) -> str:
    return "\n".join(
        [
            "database_counts:",
            f"entity={counts.entity}",
            f"source_record={counts.source_record}",
            f"claim={counts.claim}",
            f"evidence={counts.evidence}",
            f"relationship_public={counts.relationship_public}",
        ]
    )


def _scalar_count(session: Session, statement) -> int:  # type: ignore[no-untyped-def]
    return int(session.scalar(statement) or 0)
