from argparse import ArgumentParser
from datetime import date
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from datosenorden.db.session import SessionLocal
from datosenorden.etl.chilecompra.client import ChileCompraClient
from datosenorden.etl.chilecompra.config import get_chilecompra_settings
from datosenorden.etl.chilecompra.pipeline import ChileCompraPipeline


def parse_args():
    parser = ArgumentParser(description="Run ChileCompra ETL")
    parser.add_argument("--date", required=True, help="Fecha de consulta en formato YYYY-MM-DD")
    parser.add_argument(
        "--resource",
        choices=["tenders", "purchase-orders", "all"],
        default="all",
        help="Recurso a cargar",
    )
    parser.add_argument("--status", default="todos", help="Estado segun nomenclatura de la API")
    parser.add_argument("--dry-run", action="store_true", help="Ejecuta sin persistir cambios")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    day = date.fromisoformat(args.date)
    settings = get_chilecompra_settings()
    client = ChileCompraClient(settings)

    with SessionLocal() as session:
        pipeline = ChileCompraPipeline(client=client, session=session)
        results = []
        if args.resource in ("tenders", "all"):
            results.append(pipeline.run_tenders_for_day(day, status=args.status, dry_run=args.dry_run))
        if args.resource in ("purchase-orders", "all"):
            results.append(
                pipeline.run_purchase_orders_for_day(day, status=args.status, dry_run=args.dry_run)
            )

    for result in results:
        print(
            f"{result.resource}: raw={result.raw_count} rejected={result.rejected_count} "
            f"loaded={result.loaded} source_records={result.source_record_count} "
            f"claims={result.claim_count} evidences={result.evidence_count} "
            f"public_relationships={result.public_relationship_count}"
        )
        for error in result.errors:
            print(f"ERROR: {error}")


if __name__ == "__main__":
    main()
