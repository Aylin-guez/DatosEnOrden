from dataclasses import replace
from datetime import date
from typing import Any

from datosenorden.etl.chilecompra.constants import (
    CHILECOMPRA_API_DOC_URL,
    LICITACION_DETAIL_URL,
    ORDEN_COMPRA_DETAIL_URL,
)
from datosenorden.etl.chilecompra.normalizers import NormalizedPayload
from datosenorden.etl.core.contracts import (
    ClaimRecord,
    DatasetRecord,
    EntityRecord,
    EntityType,
    EvidenceRecord,
    GraphBatch,
    PublicRelationshipRecord,
    RelationshipType,
    SourceInfo,
    SourceRecordPayload,
    WorkflowStatus,
)
from datosenorden.etl.core.hash import stable_json_hash
from datosenorden.etl.core.text import clean_text, normalized_key
from datosenorden.etl.core.time import parse_chilecompra_date


class ChileCompraGraphMapper:
    source_name = "ChileCompra API Mercado Publico"
    _PURCHASE_ORDER_BUYER_SECTION_KEYS = (
        "Comprador",
        "CompradorOrganismo",
        "DatosComprador",
        "OrganismoComprador",
        "UnidadCompra",
    )
    _PURCHASE_ORDER_BUYER_CODE_KEYS = (
        "CodigoOrganismo",
        "CodigoUnidadCompra",
        "CodigoComprador",
    )
    _PURCHASE_ORDER_BUYER_NAME_KEYS = (
        "NombreOrganismo",
        "NombreUnidadCompra",
        "NombreComprador",
        "RazonSocial",
    )
    _PURCHASE_ORDER_BUYER_FALLBACK_CODE_KEYS = (
        "CodigoOrganismo",
        "CodigoUnidadCompra",
        "CodigoComprador",
    )
    _PURCHASE_ORDER_BUYER_FALLBACK_NAME_KEYS = (
        "NombreOrganismo",
        "NombreUnidadCompra",
        "NombreComprador",
        "RazonSocial",
    )
    _PURCHASE_ORDER_SUPPLIER_SECTION_KEYS = (
        "Adjudicatario",
        "DatosProveedor",
        "Empresa",
        "Proveedor",
        "ProveedorAdjudicado",
    )
    _PURCHASE_ORDER_SUPPLIER_CODE_KEYS = (
        "CodigoEmpresa",
        "CodigoProveedor",
        "CodigoAdjudicatario",
        "RutProveedor",
        "RUTProveedor",
    )
    _PURCHASE_ORDER_SUPPLIER_NAME_KEYS = (
        "NombreEmpresa",
        "NombreProveedor",
        "RazonSocial",
    )
    _PURCHASE_ORDER_SUPPLIER_FALLBACK_CODE_KEYS = (
        "CodigoEmpresa",
        "CodigoProveedor",
        "CodigoAdjudicatario",
        "RutProveedor",
        "RUTProveedor",
    )
    _PURCHASE_ORDER_SUPPLIER_FALLBACK_NAME_KEYS = (
        "NombreEmpresa",
        "NombreProveedor",
        "RazonSocial",
    )

    def map_tenders(self, payload: NormalizedPayload) -> GraphBatch:
        return self._map_records(payload, dataset_name="chilecompra-licitaciones", mode="tender")

    def map_purchase_orders(self, payload: NormalizedPayload) -> GraphBatch:
        return self._map_records(payload, dataset_name="chilecompra-ordenes-compra", mode="purchase_order")

    def _map_records(self, payload: NormalizedPayload, dataset_name: str, mode: str) -> GraphBatch:
        entities: dict[tuple[str, str], EntityRecord] = {}
        source_records: dict[tuple[str, str], SourceRecordPayload] = {}
        evidence: list[EvidenceRecord] = []
        claims: list[ClaimRecord] = []
        public_relationships: list[PublicRelationshipRecord] = []
        errors: list[str] = []

        for record in payload.records:
            try:
                if mode == "tender":
                    mapped = self._map_tender_record(record, payload.retrieved_at)
                else:
                    mapped = self._map_purchase_order_record(record, payload.retrieved_at)
                source_record = mapped["source_record"]
                if not mapped["claims"]:
                    reason = source_record.error_log or (
                        f"{mode}: no claims could be derived from available fields; "
                        f"raw_keys={sorted(record.keys())}"
                    )
                    source_record = replace(
                        source_record,
                        status=WorkflowStatus.REJECTED,
                        error_log=reason,
                    )
                    mapped = {**mapped, "source_record": source_record}
                    errors.append(reason)
                source_records[
                    (mapped["source_record"].record_type, mapped["source_record"].external_id)
                ] = mapped["source_record"]
                for entity in mapped["entities"]:
                    entities[(entity.entity_type.value, entity.external_id)] = entity
                evidence.extend(mapped["evidence"])
                claims.extend(mapped["claims"])
                public_relationships.extend(mapped["public_relationships"])
            except (KeyError, ValueError, TypeError) as exc:
                errors.append(f"{mode}: {exc}; raw_keys={sorted(record.keys())}")

        source = SourceInfo(
            name=self.source_name,
            publisher="Direccion ChileCompra",
            url=CHILECOMPRA_API_DOC_URL,
            license="API publica con terminos de uso ChileCompra",
            retrieved_at=payload.retrieved_at,
            metadata={
                "api_resource_url": payload.source_url,
                "api_version": payload.api_version,
                "api_created_at": payload.api_created_at,
            },
        )
        dataset = DatasetRecord(
            source_name=self.source_name,
            name=dataset_name,
            description=f"Datos {dataset_name} extraidos desde API Mercado Publico",
            version=payload.query_date.isoformat() if payload.query_date else "adhoc",
            dataset_url=payload.source_url,
            content_hash=payload.raw_payload_hash,
            loaded_at=payload.retrieved_at,
            metadata={
                "request_params": payload.request_params,
                "api_version": payload.api_version,
                "api_created_at": payload.api_created_at,
            },
        )
        return GraphBatch(
            source=source,
            dataset=dataset,
            source_records=tuple(source_records.values()),
            entities=tuple(entities.values()),
            evidence=tuple(evidence),
            claims=tuple(claims),
            public_relationships=tuple(public_relationships),
            raw_count=len(payload.records),
            rejected_count=len(errors),
            errors=tuple(errors),
        )

    def _map_tender_record(self, record: dict[str, Any], retrieved_at) -> dict[str, list]:
        code = self._required(record, "CodigoExterno", "Codigo")
        source_record = self._source_record("chilecompra:tender", code, record, retrieved_at)
        tender_name = clean_text(record.get("Nombre")) or f"Licitacion {code}"
        buyer_code, buyer_name = self._extract_buyer_identity(record)

        tender = EntityRecord(
            entity_type=EntityType.TENDER,
            external_id=f"chilecompra:tender:{code}",
            name=tender_name,
            normalized_key=normalized_key(code),
            metadata=self._metadata(record, code=code),
        )
        entities = [tender]
        evidence = []
        claims = []
        public_relationships = []

        if buyer_code and buyer_name:
            buyer = EntityRecord(
                entity_type=EntityType.PUBLIC_ORGANIZATION,
                external_id=f"chilecompra:buyer:{buyer_code}",
                name=buyer_name,
                normalized_key=normalized_key(buyer_name),
                metadata={"chilecompra_code": buyer_code},
            )
            evidence_record = self._evidence_for_tender(source_record, code, tender_name, record)
            claim = ClaimRecord(
                subject_entity=buyer,
                predicate=RelationshipType.PUBLISHED_TENDER.value,
                object_entity=tender,
                source_record=source_record,
                evidence=evidence_record,
                valid_from=parse_chilecompra_date(record.get("FechaPublicacion")),
                status=WorkflowStatus.VALIDATED,
                metadata={"source_record_code": code},
            )
            entities.append(buyer)
            evidence.append(evidence_record)
            claims.append(claim)
            public_relationships.append(
                PublicRelationshipRecord(
                    source_entity=buyer,
                    target_entity=tender,
                    relationship_type=RelationshipType.PUBLISHED_TENDER,
                    claim=claim,
                    status=WorkflowStatus.PUBLISHED,
                    metadata={"source_record_code": code},
                )
            )

        return {
            "source_record": source_record,
            "entities": entities,
            "evidence": evidence,
            "claims": claims,
            "public_relationships": public_relationships,
        }

    def _map_purchase_order_record(self, record: dict[str, Any], retrieved_at) -> dict[str, list]:
        code = self._required(record, "Codigo", "CodigoExterno")
        source_record = self._source_record("chilecompra:purchase_order", code, record, retrieved_at)
        order_name = clean_text(record.get("Nombre")) or f"Orden de compra {code}"
        buyer_code, buyer_name = self._extract_buyer_identity(record)
        supplier_code, supplier_name = self._extract_supplier_identity(record)

        contract = EntityRecord(
            entity_type=EntityType.CONTRACT,
            external_id=f"chilecompra:purchase_order:{code}",
            name=order_name,
            normalized_key=normalized_key(code),
            metadata=self._metadata(record, code=code),
        )
        entities = [contract]
        evidence = []
        claims = []
        public_relationships = []
        published_at = parse_chilecompra_date(record.get("FechaEnvio") or record.get("FechaCreacion"))

        if buyer_code and buyer_name:
            buyer = EntityRecord(
                entity_type=EntityType.PUBLIC_ORGANIZATION,
                external_id=f"chilecompra:buyer:{buyer_code}",
                name=buyer_name,
                normalized_key=normalized_key(buyer_name),
                metadata={"chilecompra_code": buyer_code},
            )
            evidence_record = self._evidence_for_purchase_order(
                source_record, code, order_name, record, published_at
            )
            claim = ClaimRecord(
                subject_entity=buyer,
                predicate=RelationshipType.ISSUES_PURCHASE_ORDER.value,
                object_entity=contract,
                source_record=source_record,
                evidence=evidence_record,
                valid_from=published_at,
                status=WorkflowStatus.VALIDATED,
                metadata={"source_record_code": code},
            )
            entities.append(buyer)
            evidence.append(evidence_record)
            claims.append(claim)
            public_relationships.append(
                PublicRelationshipRecord(
                    source_entity=buyer,
                    target_entity=contract,
                    relationship_type=RelationshipType.ISSUES_PURCHASE_ORDER,
                    claim=claim,
                    status=WorkflowStatus.PUBLISHED,
                    metadata={"source_record_code": code},
                )
            )

        if supplier_code and supplier_name:
            supplier = EntityRecord(
                entity_type=EntityType.COMPANY,
                external_id=f"chilecompra:supplier:{supplier_code}",
                name=supplier_name,
                normalized_key=normalized_key(supplier_name),
                metadata={"chilecompra_code": supplier_code},
            )
            evidence_record = self._evidence_for_purchase_order(
                source_record, code, order_name, record, published_at
            )
            claim = ClaimRecord(
                subject_entity=supplier,
                predicate=RelationshipType.RECEIVES_CONTRACT.value,
                object_entity=contract,
                source_record=source_record,
                evidence=evidence_record,
                valid_from=published_at,
                status=WorkflowStatus.VALIDATED,
                metadata={"source_record_code": code},
            )
            entities.append(supplier)
            evidence.append(evidence_record)
            claims.append(claim)
            public_relationships.append(
                PublicRelationshipRecord(
                    source_entity=supplier,
                    target_entity=contract,
                    relationship_type=RelationshipType.RECEIVES_CONTRACT,
                    claim=claim,
                    status=WorkflowStatus.PUBLISHED,
                    metadata={"source_record_code": code},
                )
            )

        return {
            "source_record": source_record,
            "entities": entities,
            "evidence": evidence,
            "claims": claims,
            "public_relationships": public_relationships,
        }

    def _evidence_for_tender(
        self, source_record: SourceRecordPayload, code: str, name: str, record: dict[str, Any]
    ) -> EvidenceRecord:
        url = LICITACION_DETAIL_URL.format(code=code)
        return EvidenceRecord(
            source_record=source_record,
            source_name=self.source_name,
            title=f"Ficha Mercado Publico licitacion {code}",
            url=url,
            published_at=parse_chilecompra_date(record.get("FechaPublicacion")),
            excerpt=name,
            metadata={"source_record_code": code, "source_record_snapshot": record},
        )

    def _evidence_for_purchase_order(
        self,
        source_record: SourceRecordPayload,
        code: str,
        name: str,
        record: dict[str, Any],
        published_at: date | None,
    ) -> EvidenceRecord:
        url = ORDEN_COMPRA_DETAIL_URL.format(code=code)
        return EvidenceRecord(
            source_record=source_record,
            source_name=self.source_name,
            title=f"Ficha Mercado Publico orden de compra {code}",
            url=url,
            published_at=published_at,
            excerpt=name,
            metadata={"source_record_code": code, "source_record_snapshot": record},
        )

    @staticmethod
    def _required(record: dict[str, Any], *keys: str) -> str:
        value = ChileCompraGraphMapper._optional(record, *keys)
        if value is None:
            raise ValueError(f"Missing required field among {keys}")
        return value

    @staticmethod
    def _optional(record: dict[str, Any], *keys: str) -> str | None:
        for key in keys:
            value = clean_text(record.get(key))
            if value:
                return value
        return None

    def _extract_buyer_identity(self, record: dict[str, Any]) -> tuple[str | None, str | None]:
        section = self._find_section(record, self._PURCHASE_ORDER_BUYER_SECTION_KEYS)
        code = (
            self._first_text(section, self._PURCHASE_ORDER_BUYER_CODE_KEYS + ("Codigo",))
            if section is not None
            else None
        )
        name = (
            self._first_text(section, self._PURCHASE_ORDER_BUYER_NAME_KEYS + ("Nombre", "Comprador"))
            if section is not None
            else None
        )
        fallback_code = self._first_text(record, self._PURCHASE_ORDER_BUYER_FALLBACK_CODE_KEYS)
        fallback_name = self._first_text(record, self._PURCHASE_ORDER_BUYER_FALLBACK_NAME_KEYS)
        return (code or fallback_code, name or fallback_name)

    def _extract_supplier_identity(self, record: dict[str, Any]) -> tuple[str | None, str | None]:
        section = self._find_section(record, self._PURCHASE_ORDER_SUPPLIER_SECTION_KEYS)
        code = (
            self._first_text(section, self._PURCHASE_ORDER_SUPPLIER_CODE_KEYS + ("Codigo", "Rut", "RUT"))
            if section is not None
            else None
        )
        name = (
            self._first_text(section, self._PURCHASE_ORDER_SUPPLIER_NAME_KEYS + ("Nombre", "Proveedor"))
            if section is not None
            else None
        )
        fallback_code = self._first_text(record, self._PURCHASE_ORDER_SUPPLIER_FALLBACK_CODE_KEYS)
        fallback_name = self._first_text(record, self._PURCHASE_ORDER_SUPPLIER_FALLBACK_NAME_KEYS)
        return (code or fallback_code, name or fallback_name)

    @classmethod
    def _first_text(cls, record: dict[str, Any], keys: tuple[str, ...]) -> str | None:
        for key in keys:
            value = cls._find_value(record, key)
            text = clean_text(value)
            if text:
                return text
        return None

    @classmethod
    def _find_value(cls, node: Any, target_key: str) -> Any | None:
        target = normalized_key(target_key)
        if target is None:
            return None
        if isinstance(node, dict):
            for key, value in node.items():
                if normalized_key(key) == target:
                    if not isinstance(value, (dict, list)):
                        return value
                    found = cls._find_value(value, target_key)
                    if found is not None:
                        return found
            for value in node.values():
                found = cls._find_value(value, target_key)
                if found is not None:
                    return found
        elif isinstance(node, list):
            for item in node:
                found = cls._find_value(item, target_key)
                if found is not None:
                    return found
        return None

    @classmethod
    def _find_section(cls, node: Any, keys: tuple[str, ...]) -> dict[str, Any] | None:
        target_keys = {normalized_key(key) for key in keys if normalized_key(key) is not None}
        if not target_keys:
            return None
        if isinstance(node, dict):
            for key, value in node.items():
                if normalized_key(key) in target_keys and isinstance(value, dict):
                    return value
                if normalized_key(key) in target_keys and isinstance(value, list):
                    for item in value:
                        if isinstance(item, dict):
                            return item
                found = cls._find_section(value, keys)
                if found is not None:
                    return found
        elif isinstance(node, list):
            for item in node:
                found = cls._find_section(item, keys)
                if found is not None:
                    return found
        return None

    @staticmethod
    def _metadata(record: dict[str, Any], code: str) -> dict[str, Any]:
        return {"chilecompra_code": code, "raw": record}

    @staticmethod
    def _source_record(
        record_type: str,
        code: str,
        record: dict[str, Any],
        payload_retrieved_at,
    ) -> SourceRecordPayload:
        from datetime import datetime, timezone

        return SourceRecordPayload(
            external_id=code,
            record_type=record_type,
            payload_hash=stable_json_hash(record),
            raw_payload=record,
            retrieved_at=payload_retrieved_at or datetime.now(timezone.utc),
            status=WorkflowStatus.NORMALIZED,
        )
