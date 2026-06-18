from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from datosenorden.maintenance.local_workflow import run_local_reset_migrate_seed_verify


def main() -> int:
    try:
        counts = run_local_reset_migrate_seed_verify()
    except Exception as exc:  # noqa: BLE001
        print("No se pudo completar el flujo local reset + migrate + seed + verify.", file=sys.stderr)
        print(f"Detalle: {exc}", file=sys.stderr)
        return 1

    print(
        "local_reset_migrate_seed_verify: "
        f"source_record={counts.source_record} "
        f"claim={counts.claim} "
        f"evidence={counts.evidence} "
        f"relationship_public={counts.relationship_public}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
