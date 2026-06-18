from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from datosenorden.db.session import SessionLocal
from datosenorden.etl.local_seed import persist_local_traceability_seed


def main() -> int:
    try:
        with SessionLocal() as session:
            result = persist_local_traceability_seed(session)
    except Exception as exc:  # noqa: BLE001
        print("No se pudo persistir el seed local en PostgreSQL.", file=sys.stderr)
        print(f"Detalle: {exc}", file=sys.stderr)
        return 1

    print(
        "local_seed: "
        f"source_records={result.source_records} "
        f"claims={result.claims} "
        f"evidences={result.evidences} "
        f"relationship_public={result.relationship_public}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
