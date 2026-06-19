from pathlib import Path
import sys
from typing import Sequence

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from datosenorden.db.session import SessionLocal
from datosenorden.maintenance.db_sync import collect_database_counts
from datosenorden.maintenance.db_sync import render_database_counts_text


def main(argv: Sequence[str] | None = None) -> int:
    _ = argv

    try:
        with SessionLocal() as session:
            counts = collect_database_counts(session)
    except Exception as exc:  # noqa: BLE001
        print("No se pudieron verificar los conteos de la base local.", file=sys.stderr)
        print(f"Detalle: {exc}", file=sys.stderr)
        return 1

    print(render_database_counts_text(counts))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
