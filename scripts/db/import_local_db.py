from argparse import ArgumentParser
from pathlib import Path
import sys
from typing import Sequence

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from datosenorden.maintenance.db_sync import build_pg_restore_command
from datosenorden.maintenance.db_sync import find_pg_tool
from datosenorden.maintenance.db_sync import get_connection_info
from datosenorden.maintenance.db_sync import get_database_url
from datosenorden.maintenance.db_sync import run_pg_command


def parse_args(argv: Sequence[str] | None = None):
    parser = ArgumentParser(description="Restore the local PostgreSQL database from a dump")
    parser.add_argument("--dump-file", required=True, help="Path to a pg_dump custom-format backup")
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="Required confirmation before replacing the local database",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    dump_path = Path(args.dump_file)

    if not args.confirm:
        print(
            "WARNING: import_local_db will replace the local database. Re-run with --confirm to proceed.",
            file=sys.stderr,
        )
        return 1

    if not dump_path.exists():
        print(f"No existe el dump: {dump_path.as_posix()}", file=sys.stderr)
        return 1

    try:
        database_url = get_database_url()
        connection_info = get_connection_info(database_url)
        pg_restore_path = find_pg_tool("pg_restore")
        command = build_pg_restore_command(database_url, dump_path, pg_restore_path)
        print("WARNING: restoring this dump will overwrite the current local database.", file=sys.stderr)
        run_pg_command(command, connection_info.password)
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except Exception as exc:  # noqa: BLE001
        print("No se pudo importar la base local.", file=sys.stderr)
        print(f"Detalle: {exc}", file=sys.stderr)
        return 1

    print(f"local_db_imported: dump={dump_path.as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
