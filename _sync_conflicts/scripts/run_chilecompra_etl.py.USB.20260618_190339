from argparse import ArgumentParser
from argparse import ArgumentTypeError
from datetime import date
from pathlib import Path
import sys
from typing import Sequence

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from datosenorden.db.session import SessionLocal
from datosenorden.etl.chilecompra.client import ChileCompraClient
from datosenorden.etl.chilecompra.config import get_chilecompra_settings
from datosenorden.etl.chilecompra.debug import summarize_normalized_record, summarize_payload_shape
from datosenorden.etl.chilecompra.normalizers import ChileCompraNormalizer
from datosenorden.etl.chilecompra.pipeline import ChileCompraPipeline


def _positive_int(value: str) -> int:
    parsed = int(value)
    if parsed < 1:
        raise ArgumentTypeError("--limit debe ser mayor que cero")
    return parsed


def parse_args(argv: Sequence[str] | None = None):
    parser = ArgumentParser(description="Run ChileCompra ETL")
    scope = parser.add_mutually_exclusive_group(required=True)
    scope.add_argument("--date", help="Fecha de consulta en formato YYYY-MM-DD")
    scope.add_argument("--purchase-order", dest="purchase_order", help="Codigo de orden de compra")
    parser.add_argument(
        "--resource",
        choices=["tenders", "purchase-orders", "all"],
        default="all",
        help="Recurso a cargar",
    )
    parser.add_argument("--status", default="todos", help="Estado segun nomenclatura de la API")
    parser.add_argument(
        "--limit",
        type=_positive_int,
        default=None,
        help="Maximo de registros a procesar desde consultas por fecha",
    )
    parser.add_argument(
        "--debug-payload",
        action="store_true",
        help="Imprime claves y forma del payload sin mostrar secretos",
    )
    parser.add_argument("--dry-run", action="store_true", help="Ejecuta sin persistir cambios")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)

    if args.purchase_order and args.resource == "tenders":
        print("--purchase-order solo puede usarse con purchase-orders o all", file=sys.stderr)
        return 2

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

    with SessionLocal() as session:
        pipeline = ChileCompraPipeline(client=client, session=session)
        results = []
        if args.purchase_order:
            response = client.get_purchase_order(args.purchase_order)
            if args.debug_payload:
                print(summarize_payload_shape(response.payload))
                normalized_preview = ChileCompraNormalizer().normalize(response)
                if normalized_preview.records:
                    print(summarize_normalized_record(normalized_preview.records[0]))
            results.append(pipeline.run_purchase_order_response(response, dry_run=args.dry_run))
        else:
            day = date.fromisoformat(args.date)
            if args.resource in ("tenders", "all"):
                results.append(pipeline.run_tenders_for_day(day, status=args.status, dry_run=args.dry_run))
            if args.resource in ("purchase-orders", "all"):
                results.append(
                    pipeline.run_purchase_orders_for_day(
                        day,
                        status=args.status,
                        dry_run=args.dry_run,
                        limit=args.limit,
                    )
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

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
