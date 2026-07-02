from datosenorden.adapters.legislature.client import LegislativeClient
from datosenorden.adapters.legislature.mapper import LegislativePlatformMapper
from datosenorden.adapters.legislature.parser import LegislativeXmlParser, normalize_bulletin_id
from datosenorden.etl.core.contracts import GraphBatch


class LegislativeAdapter:
    """Orchestrate the minimal single-bulletin legislative adapter flow."""

    def __init__(
        self,
        client: LegislativeClient | None = None,
        parser: LegislativeXmlParser | None = None,
        mapper: LegislativePlatformMapper | None = None,
    ) -> None:
        self._client = client or LegislativeClient()
        self._parser = parser or LegislativeXmlParser()
        self._mapper = mapper or LegislativePlatformMapper()

    def load_bill(self, bulletin_id: str) -> GraphBatch:
        normalized_bulletin = normalize_bulletin_id(bulletin_id)
        response = self._client.get_votes_by_bulletin(normalized_bulletin)
        bundle = self._parser.parse_bill_votes(normalized_bulletin, response)
        return self._mapper.map_bill_bundle(bundle)
