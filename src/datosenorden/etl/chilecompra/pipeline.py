from dataclasses import dataclass
from dataclasses import replace
from datetime import date

from sqlalchemy.orm import Session

from datosenorden.etl.chilecompra.client import ApiResponse
from datosenorden.etl.chilecompra.client import ChileCompraClient
from datosenorden.etl.chilecompra.mappers import ChileCompraGraphMapper
from datosenorden.etl.chilecompra.normalizers import ChileCompraNormalizer, NormalizedPayload
from datosenorden.etl.core.contracts import GraphBatch
from datosenorden.etl.loaders.graph_loader import GraphLoader


@dataclass(frozen=True)
class PipelineResult:
    resource: str
    raw_count: int
    rejected_count: int
    loaded: bool
    source_record_count: int
    claim_count: int
    evidence_count: int
    public_relationship_count: int
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
        self,
        day: date,
        status: str = "todos",
        dry_run: bool = False,
        limit: int | None = None,
    ) -> PipelineResult:
        response = self._client.list_purchase_orders(day=day, status=status)
        normalized = self._normalizer.normalize(response, query_date=day)
        normalized = self._limit_records(normalized, limit)
        batch = self._mapper.map_purchase_orders(normalized)
        return self._load_batch("purchase_orders", batch, dry_run)

    def run_purchase_order_by_code(self, code: str, dry_run: bool = False) -> PipelineResult:
        response = self._client.get_purchase_order(code)
        return self.run_purchase_order_response(response, dry_run=dry_run)

    def run_purchase_order_response(self, response: ApiResponse, dry_run: bool = False) -> PipelineResult:
        normalized = self._normalizer.normalize(response)
        batch = self._mapper.map_purchase_orders(normalized)
        return self._load_batch("purchase_order", batch, dry_run)

    def _load_batch(self, resource: str, batch: GraphBatch, dry_run: bool) -> PipelineResult:
        self._loader.load(batch, dry_run=dry_run)
        return PipelineResult(
            resource=resource,
            raw_count=batch.raw_count,
            rejected_count=batch.rejected_count,
            loaded=not dry_run,
            source_record_count=len(batch.source_records),
            claim_count=len(batch.claims),
            evidence_count=len(batch.evidence),
            public_relationship_count=len(batch.public_relationships),
            errors=batch.errors,
        )

    @staticmethod
    def _limit_records(normalized: NormalizedPayload, limit: int | None) -> NormalizedPayload:
        if limit is None:
            return normalized
        if limit < 1:
            raise ValueError("limit must be greater than zero")
        return replace(normalized, records=normalized.records[:limit])
