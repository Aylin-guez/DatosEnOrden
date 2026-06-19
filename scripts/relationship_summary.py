from pathlib import Path
import sys
from typing import Sequence

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from datosenorden.db.session import SessionLocal
from datosenorden.maintenance.entity_explorer import render_relationship_summary_text
from datosenorden.maintenance.entity_explorer import summarize_relationship_counts


def main(argv: Sequence[str] | None = None) -> int:
    _ = argv

    try:
        with SessionLocal() as session:
            rows = summarize_relationship_counts(session)
    except Exception as exc:  # noqa: BLE001
        print("No se pudo resumir relationship_public.", file=sys.stderr)
        print(f"Detalle: {exc}", file=sys.stderr)
        return 1

    print(render_relationship_summary_text(rows))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
