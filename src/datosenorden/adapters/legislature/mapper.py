from dataclasses import asdict
from datetime import date, datetime
from typing import Any

from datosenorden.adapters.legislature.models import (
    CAMARA_SERVICE_URL,
    CONGRESS_SOURCE_NAME,
    CONGRESS_SOURCE_URL,
    LegislativeBillBundle,
    LegislativeVote,
)
from datosenorden.etl.core.contracts import (
    ClaimRecord,
    DatasetRecord,
    EntityRecord,
    EntityType,
    EvidenceRecord,
    GraphBatch,
    SourceInfo,
    SourceRecordPayload,
    WorkflowStatus,
)
from datosenorden.etl.core.hash import stable_json_hash
from datosenorden.etl.core.text import normalized_key


class LegislativePlatformMapper:
    """Translate adapter-owned legislative objects into platform ETL contracts."""

    def map_bill_bundle(self, bundle: LegislativeBillBundle) -> GraphBatch:
        retrieved_at = bundle.source_response.retrieved_at
        bill_record = self._source_record(
            external_id=bundle.bill.canonical_id,
            record_type="legislature:bill",
            raw_payload={
                "bill": _json_safe(asdict(bundle.bill)),
                "request": {
                    "url": bundle.source_response.url,
                    "params": bundle.source_response.params,
                },
            },
            retrieved_at=retrieved_at,
        )
        bill_entity = EntityRecord(
            entity_type=EntityType.PUBLIC_PROJECT,
            external_id=bundle.bill.canonical_id,
            name=f"Boletin {bundle.bill.bulletin_id}",
            normalized_key=normalized_key(bundle.bill.bulletin_id),
            metadata={
                "source": "congreso-opendata",
                "bulletin_id": bundle.bill.bulletin_id,
                "aliases": bundle.bill.aliases,
                "entity_role": "legislative_bill",
            },
        )

        source_records = [bill_record]
        evidence: list[EvidenceRecord] = []
        claims: list[ClaimRecord] = []

        for vote in bundle.votes:
            vote_record = self._vote_source_record(vote, retrieved_at)
            vote_evidence = self._vote_evidence(vote_record, vote)
            source_records.append(vote_record)
            evidence.append(vote_evidence)
            claims.append(
                ClaimRecord(
                    subject_entity=bill_entity,
                    predicate="LEGISLATIVE_BILL_HAS_VOTE",
                    source_record=vote_record,
                    evidence=vote_evidence,
                    object_value=self._vote_object_value(vote),
                    valid_from=_date(vote.date),
                    status=WorkflowStatus.VALIDATED,
                    metadata={
                        "source_vote_id": vote.source_id,
                        "source_session_id": vote.session.source_id if vote.session else None,
                    },
                )
            )

        source = SourceInfo(
            name=CONGRESS_SOURCE_NAME,
            publisher="Congreso Nacional de Chile",
            url=CONGRESS_SOURCE_URL,
            license="Datos abiertos legislativos; revisar condiciones oficiales antes de produccion",
            retrieved_at=retrieved_at,
            metadata={
                "service_url": CAMARA_SERVICE_URL,
                "operation": "getVotaciones_Boletin",
                "format": "XML",
                "request_params": bundle.source_response.params,
            },
        )
        dataset = DatasetRecord(
            source_name=CONGRESS_SOURCE_NAME,
            name="congreso-votaciones-boletin",
            description="Votaciones de Camara asociadas a un boletin legislativo indicado manualmente",
            version=bundle.bill.bulletin_id,
            dataset_url=bundle.source_response.url,
            content_hash=stable_json_hash(
                {
                    "bill": bundle.bill.bulletin_id,
                    "votes": [vote.source_id for vote in bundle.votes],
                    "xml_hash": stable_json_hash(bundle.source_response.xml_text),
                }
            ),
            loaded_at=retrieved_at,
            metadata={"manual_scope": "single_bulletin", "bulletin_id": bundle.bill.bulletin_id},
        )
        return GraphBatch(
            source=source,
            dataset=dataset,
            source_records=tuple(source_records),
            entities=(bill_entity,),
            evidence=tuple(evidence),
            claims=tuple(claims),
            public_relationships=(),
            raw_count=len(bundle.votes),
            rejected_count=0,
            errors=(),
        )

    def _vote_source_record(self, vote: LegislativeVote, retrieved_at) -> SourceRecordPayload:
        return self._source_record(
            external_id=vote.source_id,
            record_type="legislature:vote",
            raw_payload=_json_safe(asdict(vote)),
            retrieved_at=retrieved_at,
        )

    def _source_record(
        self, external_id: str, record_type: str, raw_payload: dict[str, Any], retrieved_at
    ) -> SourceRecordPayload:
        return SourceRecordPayload(
            external_id=external_id,
            record_type=record_type,
            payload_hash=stable_json_hash(raw_payload),
            raw_payload=raw_payload,
            retrieved_at=retrieved_at,
            status=WorkflowStatus.VALIDATED,
        )

    def _vote_evidence(self, source_record: SourceRecordPayload, vote: LegislativeVote) -> EvidenceRecord:
        return EvidenceRecord(
            source_record=source_record,
            source_name=CONGRESS_SOURCE_NAME,
            title=f"Votacion {vote.source_id} asociada al boletin {vote.bulletin_id}",
            url=f"{CAMARA_SERVICE_URL}/getVotacion_Detalle?prmVotacionID={vote.source_id.removeprefix('camara-votacion-')}",
            published_at=_date(vote.date),
            excerpt=self._vote_excerpt(vote),
            metadata={
                "source_operation": "getVotacion_Detalle",
                "source_vote_id": vote.source_id,
            },
        )

    def _vote_excerpt(self, vote: LegislativeVote) -> str:
        pieces = [f"Boletin {vote.bulletin_id}", f"votacion {vote.source_id}"]
        if vote.result:
            pieces.append(f"resultado {vote.result}")
        if vote.affirmative_total is not None:
            pieces.append(f"{vote.affirmative_total} afirmativos")
        if vote.negative_total is not None:
            pieces.append(f"{vote.negative_total} negativos")
        if vote.abstention_total is not None:
            pieces.append(f"{vote.abstention_total} abstenciones")
        return "; ".join(pieces)

    def _vote_object_value(self, vote: LegislativeVote) -> dict[str, Any]:
        return {
            "vote_id": vote.source_id,
            "bulletin_id": vote.bulletin_id,
            "date": vote.date.isoformat() if vote.date else None,
            "result": vote.result,
            "quorum": vote.quorum,
            "article": vote.article,
            "procedure_stage": vote.procedure_stage,
            "report": vote.report,
            "totals": {
                "affirmative": vote.affirmative_total,
                "negative": vote.negative_total,
                "abstention": vote.abstention_total,
                "excused": vote.excused_total,
            },
            "session": _json_safe(asdict(vote.session)) if vote.session else None,
        }


def _date(value) -> date | None:
    return value.date() if value else None

def _json_safe(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    return value
