"""Read-only public collections over already published REAL entities."""
from __future__ import annotations

from dataclasses import dataclass
from sqlalchemy import select
from sqlalchemy.orm import Session

from datosenorden.models import Entity


@dataclass(frozen=True)
class PublicCollectionDefinition:
    key: str
    title: str
    description: str
    entity_types: tuple[str, ...]


COLLECTIONS = (
    PublicCollectionDefinition("organisms", "Organismos públicos", "Organismos con información pública incorporada.", ("PUBLIC_ORGANIZATION",)),
    PublicCollectionDefinition("companies", "Empresas proveedoras", "Proveedores identificados en órdenes de compra incorporadas.", ("COMPANY",)),
    PublicCollectionDefinition("contracts", "Contratos y órdenes", "Órdenes de compra públicas incorporadas.", ("CONTRACT",)),
)


def public_collection(session: Session, key: str) -> dict[str, object]:
    definition = next((item for item in COLLECTIONS if item.key == key), None)
    if definition is None:
        return {"found": False, "items": []}
    entities = session.scalars(select(Entity).where(Entity.entity_type.in_(definition.entity_types)).order_by(Entity.name)).all()
    return {
        "found": True, "key": definition.key, "title": definition.title,
        "description": definition.description,
        "items": [_item(entity) for entity in entities],
    }


def public_collection_counts(session: Session) -> dict[str, int]:
    """Return published collection totals without creating or modifying data."""
    return {
        definition.key: len(
            session.scalars(
                select(Entity.id).where(Entity.entity_type.in_(definition.entity_types))
            ).all()
        )
        for definition in COLLECTIONS
    }


def _item(entity: Entity) -> dict[str, object]:
    is_contract = entity.entity_type == "CONTRACT"
    return {
        "public_id": entity.external_id or str(entity.id),
        "title": entity.name,
        "object_type": "Orden de compra" if is_contract else "Organismo público" if entity.entity_type == "PUBLIC_ORGANIZATION" else "Empresa proveedora",
        "context": "Información incorporada desde ChileCompra." if str(entity.external_id or "").startswith("chilecompra:") else "Información pública incorporada.",
        "sources": ["ChileCompra"] if str(entity.external_id or "").startswith("chilecompra:") else [],
        "sources_text": "ChileCompra" if str(entity.external_id or "").startswith("chilecompra:") else "",
        "classification": "REAL",
        "target": f"/investigation?id={entity.external_id or entity.id}",
    }
