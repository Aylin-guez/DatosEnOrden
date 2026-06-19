from datetime import datetime
from pathlib import Path
import sys
from typing import Sequence

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from datosenorden.maintenance.db_sync import BACKUPS_DIR
from datosenorden.maintenance.db_sync import build_dump_path
from datosenorden.maintenance.db_sync import build_pg_dump_command
from datosenorden.maintenance.db_sync import find_pg_tool
from datosenorden.maintenance.db_sync import get_connection_info
from datosenorden.maintenance.db_sync import get_database_url
from datosenorden.maintenance.db_sync import run_pg_command


def main(argv: Sequence[str] | None = None) -> int:
    _ = argv

    try:
        database_url = get_database_url()
        connection_info = get_connection_info(database_url)
        pg_dump_path = find_pg_tool("pg_dump")
        dump_path = build_dump_path(datetime.now())
        dump_path = BACKUPS_DIR / dump_path.name
        dump_path.parent.mkdir(parents=True, exist_ok=True)
        command = build_pg_dump_command(database_url, dump_path, pg_dump_path)
        run_pg_command(command, connection_info.password)
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except Exception as exc:  # noqa: BLE001
        print("No se pudo exportar la base local.", file=sys.stderr)
        print(f"Detalle: {exc}", file=sys.stderr)
        return 1

    print(f"local_db_exported: path={dump_path.as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
