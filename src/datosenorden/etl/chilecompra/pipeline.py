from dataclasses import dataclass
from datetime import date

from sqlalchemy.orm import Session

from datosenorden.etl.chilecompra.client import ChileCompraClient
from datosenorden.etl.chilecompra.mappers import ChileCompraGraphMapper
from datosenorden.etl.chilecompra.normalizers import ChileCompraNormalizer
from datosenorden.etl.core.contracts import GraphBatch
from datosenorden.etl.loaders.graph_loader import GraphLoader


@dataclass(frozen=True)
class PipelineResult:
    resource: str
    raw_count: int
    rejected_count: int
    loaded: bool
    errors: tuple[str, ...]


class ChileCompraPipeline:
    def __init__(self, client: ChileCompraClient, session: Session) -> None:
        self._client = client
        self._normalizer = ChileCompraNormalizer()
        self._mapper = ChileCompraGraphMapper()
        self._loader = GraphLoader(session)

    def run_tenders_for_day(self, day: date, status: str = "todos", dry_run: bool = False) -> PipelineResult:
        response = self._client.list_tenders(day=day, status=status)
        normalized = self._normalizer.normalize(response, query_date=day)
        batch = self._mapper.map_tenders(normalized)
        return self._load_batch("tenders", batch, dry_run)

    def run_purchase_orders_for_day(
        self, day: date, status: str = "todos", dry_run: bool = False
    ) -> PipelineResult:
        response = self._client.list_purchase_orders(day=day, status=status)
        normalized = self._normalizer.normalize(response, query_date=day)
        batch = self._mapper.map_purchase_orders(normalized)
        return self._load_batch("purchase_orders", batch, dry_run)

    def _load_batch(self, resource: str, batch: GraphBatch, dry_run: bool) -> PipelineResult:
        self._loader.load(batch, dry_run=dry_run)
        return PipelineResult(
            resource=resource,
            raw_count=batch.raw_count,
            rejected_count=batch.rejected_count,
            loaded=not dry_run,
            errors=batch.errors,
        )
