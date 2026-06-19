from argparse import ArgumentParser
from pathlib import Path
import sys
from typing import Sequence

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from datosenorden.maintenance.db_merge import merge_dump_file_into_current_database
from datosenorden.maintenance.db_merge import render_merge_report_text


def parse_args(argv: Sequence[str] | None = None):
    parser = ArgumentParser(description="Merge a local PostgreSQL dump into the current database")
    parser.add_argument("--file", required=True, help="Path to the source dump file")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true", help="Preview the merge without committing changes")
    mode.add_argument("--confirm", action="store_true", help="Apply the merge to the current local database")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    dump_file = Path(args.file)

    if not dump_file.exists():
        print(f"No existe el dump: {dump_file.as_posix()}", file=sys.stderr)
        return 1

    if args.dry_run:
        print(
            "WARNING: dry-run no escribirá cambios en la base principal, solo mostrará el resultado.",
            file=sys.stderr,
        )
    if args.confirm:
        print(
            "WARNING: el merge insertará solo registros faltantes en la base actual.",
            file=sys.stderr,
        )

    try:
        report = merge_dump_file_into_current_database(dump_file, dry_run=args.dry_run)
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except Exception as exc:  # noqa: BLE001
        print("No se pudo fusionar la base local.", file=sys.stderr)
        print(f"Detalle: {exc}", file=sys.stderr)
        return 1

    print(render_merge_report_text(report, dry_run=args.dry_run))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
