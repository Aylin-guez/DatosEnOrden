from argparse import ArgumentParser
from argparse import ArgumentTypeError
from pathlib import Path
import sys
from typing import Sequence

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from datosenorden.db.session import SessionLocal
from datosenorden.etl.chilecompra.client import ChileCompraClient
from datosenorden.etl.chilecompra.config import get_chilecompra_settings
from datosenorden.maintenance.dataset_metrics import load_sample_purchase_orders
from datosenorden.maintenance.dataset_metrics import read_purchase_order_dataset_counts
from datosenorden.maintenance.dataset_metrics import render_purchase_order_dataset_counts


def _positive_int(value: str) -> int:
    parsed = int(value)
    if parsed < 1:
        raise ArgumentTypeError("--limit debe ser mayor que cero")
    return parsed


def parse_args(argv: Sequence[str] | None = None):
    parser = ArgumentParser(description="Load a small sample of ChileCompra purchase orders")
    parser.add_argument("--limit", type=_positive_int, default=100, help="Maximo de source records a cargar")
    return parser.parse_args(argv)


def _print_progress(progress) -> None:  # noqa: ANN001
    print(
        "sample_purchase_orders_progress: "
        f"date={progress.scanned_date.isoformat()} raw_found={progress.raw_found} "
        f"loaded={progress.loaded} rejected={progress.rejected} "
        f"claims={progress.claims} relationships={progress.relationships}"
    )


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)

    try:
        settings = get_chilecompra_settings()
    except ValueError as exc:
        print(
            "Falta DATOSENORDEN_CHILECOMPRA_TICKET. "
            "Configura el ticket en .env o en PowerShell y vuelve a ejecutar.",
            file=sys.stderr,
        )
        print(f"Detalle: {exc}", file=sys.stderr)
        return 1

    client = ChileCompraClient(settings)

    try:
        with SessionLocal() as session:
            load_counts = load_sample_purchase_orders(
                client,
                session,
                limit=args.limit,
                progress_callback=_print_progress,
            )
            dataset_counts = read_purchase_order_dataset_counts(session)
    except Exception as exc:  # noqa: BLE001
        print("No se pudo cargar el dataset de muestra de ChileCompra.", file=sys.stderr)
        print(f"Detalle: {exc}", file=sys.stderr)
        return 1

    print(
        f"sample_purchase_orders_loaded: source_records={load_counts.source_records} "
        f"claims={load_counts.claims} evidences={load_counts.evidences} "
        f"relationship_public={load_counts.relationship_public} days_scanned={load_counts.days_scanned} "
        f"raw_found={load_counts.raw_found} rejected={load_counts.rejected}"
    )
    print(render_purchase_order_dataset_counts(dataset_counts))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
