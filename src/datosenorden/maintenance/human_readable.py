from __future__ import annotations

from dataclasses import dataclass
from html import escape
from typing import Any
from uuid import UUID

from sqlalchemy import distinct, select
from sqlalchemy.orm import Session

from datosenorden.etl.core.contracts import RelationshipType
from datosenorden.models import Claim
from datosenorden.models import Dataset
from datosenorden.models import Entity
from datosenorden.models import RelationshipPublic
from datosenorden.models import SourceRecord

TECHNICAL_LABELS = {
    "source_record": "Fuente",
    "claim": "Afirmación verificable",
    "relationship_public": "Relación pública",
    "entity": "Entidad",
}

ENTITY_TYPE_LABELS = {
    "PUBLIC_ORGANIZATION": "organismo público",
    "COMPANY": "proveedor",
    "CONTRACT": "contrato",
    "BUDGET": "presupuesto",
    "PERSON": "persona",
    "ROLE": "cargo publico",
    "LOBBY_MEETING": "reunión de lobby",
}

ENTITY_TYPE_DISPLAY_LABELS = {
    "PUBLIC_ORGANIZATION": "Organismo",
    "COMPANY": "Proveedor",
    "CONTRACT": "Contrato",
    "BUDGET": "Presupuesto",
    "PERSON": "Persona",
    "ROLE": "Cargo publico",
    "LOBBY_MEETING": "Reunión de lobby",
}

DATASET_NAME_LABELS = {
    "chilecompra-licitaciones": "ChileCompra",
    "chilecompra-ordenes-compra": "ChileCompra",
    "dipres-budget-sample": "DIPRES Prototype",
    "lobby-meeting-sample": "Lobby",
    "transparencia-activa-sample": "Transparencia Activa",
}


@dataclass(frozen=True)
class EntityExplanation:
    entity_id: str
    entity_name: str
    entity_type: str
    public_contracts: int
    suppliers: int
    source_names: tuple[str, ...]


@dataclass(frozen=True)
class DatasetExplanation:
    name: str
    summary: str
    contracts: int
    organizations: int
    suppliers: int


@dataclass(frozen=True)
class GraphExplanation:
    labels: tuple[str, ...]
    meaning: str


def human_label(identifier: str) -> str:
    return TECHNICAL_LABELS.get(identifier, identifier.replace("_", " ").strip().title())


def entity_type_label(entity_type: str) -> str:
    return ENTITY_TYPE_LABELS.get(entity_type, entity_type.replace("_", " ").lower())


def entity_type_display_label(entity_type: str) -> str:
    return ENTITY_TYPE_DISPLAY_LABELS.get(entity_type, entity_type.replace("_", " ").title())


def explain_entity(session: Session, entity_id: str) -> EntityExplanation | None:
    entity = session.get(Entity, UUID(entity_id))
    if entity is None:
        return None

    source_names = _entity_source_names(session, entity.id)
    public_contracts, suppliers = _entity_connection_counts(session, entity)
    return EntityExplanation(
        entity_id=str(entity.id),
        entity_name=entity.name,
        entity_type=entity.entity_type,
        public_contracts=public_contracts,
        suppliers=suppliers,
        source_names=source_names,
    )


def explain_dataset(details: Any) -> DatasetExplanation:
    contracts = _count_dataset_type(details, "CONTRACT")
    organizations = _count_dataset_type(details, "PUBLIC_ORGANIZATION")
    suppliers = _count_dataset_type(details, "COMPANY")
    return DatasetExplanation(
        name=details.name,
        summary=_dataset_summary_text(details.name),
        contracts=contracts,
        organizations=organizations,
        suppliers=suppliers,
    )


def explain_graph(root: Any) -> GraphExplanation:
    chain = _graph_chain(root)
    labels = tuple(entity_type_display_label(entity_type) for entity_type in chain)
    meaning = _graph_meaning_for_chain(chain)
    return GraphExplanation(labels=labels, meaning=meaning)


def render_entity_explanation_text(explanation: EntityExplanation) -> str:
    lines = [
        _entity_intro_sentence(explanation),
        f"Se relaciona con {explanation.suppliers} proveedores.",
        ]
    if explanation.source_names:
        lines.append(f"La información proviene de {', '.join(explanation.source_names)}.")
    lines.extend(
        [
            "",
            "¿Qué significa esto?",
            f"{human_label('source_record')}: registro original cargado en PostgreSQL.",
            f"{human_label('claim')}: dato derivado desde una fuente.",
            f"{human_label('relationship_public')}: conexión entre entidades guardadas.",
            f"{human_label('entity')}: organismo, contrato, proveedor o presupuesto.",
        ]
    )
    return "\n".join(lines)


def render_dataset_explanation_text(explanation: DatasetExplanation) -> str:
    lines = [
        explanation.summary,
        "Este conjunto de datos incluye:",
        f"* {explanation.contracts} contratos",
        f"* {explanation.organizations} organismos",
        f"* {explanation.suppliers} proveedores",
        "",
        "¿Qué significa esto?",
        f"{human_label('source_record')}: registro original cargado en PostgreSQL.",
        f"{human_label('claim')}: dato derivado desde una fuente.",
        f"{human_label('relationship_public')}: conexión entre entidades guardadas.",
        f"{human_label('entity')}: organismo, contrato, proveedor o presupuesto.",
    ]
    return "\n".join(lines)


def render_graph_explanation_text(explanation: GraphExplanation) -> str:
    lines = [
        "Este gráfico muestra cómo se conectan las fuentes públicas.",
        *[f"→ {label}" if index else label for index, label in enumerate(explanation.labels)],
        "",
        "Esto significa:",
        explanation.meaning,
    ]
    return "\n".join(lines)


def render_human_labels_legend_text() -> str:
    return "\n".join(
        [
            "¿Qué significa esto?",
            f"{human_label('source_record')}: registro original cargado en PostgreSQL.",
            f"{human_label('claim')}: dato derivado desde una fuente.",
            f"{human_label('relationship_public')}: conexión entre entidades guardadas.",
            f"{human_label('entity')}: organismo, contrato, proveedor o presupuesto.",
        ]
    )


def render_human_labels_legend_html() -> str:
    return (
        '<section class="wide explain">'
        "<h2>¿Qué significa esto?</h2>"
        '<p>Esta página usa lenguaje simple para que cualquier persona pueda entender el gráfico.</p>'
        "<ul>"
        f"<li><strong>{escape(human_label('source_record'))}</strong>: registro original cargado en PostgreSQL.</li>"
        f"<li><strong>{escape(human_label('claim'))}</strong>: dato derivado desde una fuente.</li>"
        f"<li><strong>{escape(human_label('relationship_public'))}</strong>: conexión entre entidades guardadas.</li>"
        f"<li><strong>{escape(human_label('entity'))}</strong>: organismo, contrato, proveedor o presupuesto.</li>"
        "</ul>"
        "</section>"
    )


def render_dataset_explanation_html(explanation: DatasetExplanation) -> str:
    return (
        '<section class="wide explain">'
        "<h2>¿Qué significa esto?</h2>"
        f"<p>{escape(explanation.summary)}</p>"
        "<p>Este conjunto de datos incluye:</p>"
        "<ul>"
        f"<li>{explanation.contracts} contratos</li>"
        f"<li>{explanation.organizations} organismos</li>"
        f"<li>{explanation.suppliers} proveedores</li>"
        "</ul>"
        "</section>"
    )


def render_entity_explanation_html(explanation: EntityExplanation) -> str:
    source_text = ""
    if explanation.source_names:
        source_text = f"<p>La información proviene de {escape(', '.join(explanation.source_names))}.</p>"
    return (
        '<section class="wide explain">'
        "<h2>¿Qué significa esto?</h2>"
        f"<p>{escape(_entity_intro_sentence(explanation))}</p>"
        f"<p>Se relaciona con {explanation.suppliers} proveedores.</p>"
        f"{source_text}"
        "</section>"
    )


def render_graph_explanation_html(explanation: GraphExplanation) -> str:
    path_html = "<br/>".join(
        escape(label) if index == 0 else f"&rarr; {escape(label)}"
        for index, label in enumerate(explanation.labels)
    )
    return (
        '<section class="wide explain">'
        "<h2>¿Qué significa esto?</h2>"
        f"<p>Este gráfico muestra:<br/>{path_html}</p>"
        f"<p><strong>Esto significa:</strong> {escape(explanation.meaning)}</p>"
        "</section>"
    )


def _dataset_summary_text(dataset_name: str) -> str:
    if dataset_name == "Transparencia Activa":
        return "Transparencia Activa muestra informacion administrativa publicada por organismos. Este prototipo usa datos de muestra, no datos oficiales. No implica irregularidad; solo representa informacion publica o de muestra."
    if dataset_name == "ChileCompra":
        return "ChileCompra contiene información de compras públicas."
    if dataset_name == "DIPRES Prototype":
        return "DIPRES Prototype contiene información de presupuesto de muestra. Actualmente incluye ejemplos de ministerios, servicios, presupuestos aprobados, presupuestos ejecutados y año fiscal."
    if dataset_name == "Lobby":
        return "Lobby contiene reuniones de lobby de muestra. El sample local no es dato oficial y solo valida conexiones entre organismos públicos, contrapartes y evidencia."
    return f"{dataset_name} contiene datos públicos guardados en el sistema."


def _count_dataset_type(details: Any, entity_type: str) -> int:
    for row in details.entities_by_type:
        if row.label == entity_type:
            return row.count
    return 0


def _entity_intro_sentence(explanation: EntityExplanation) -> str:
    if explanation.entity_type == "PUBLIC_ORGANIZATION":
        prefix = "Este organismo"
    elif explanation.entity_type == "COMPANY":
        prefix = "Este proveedor"
    elif explanation.entity_type == "CONTRACT":
        prefix = "Este contrato"
    elif explanation.entity_type == "BUDGET":
        prefix = "Este presupuesto"
    elif explanation.entity_type == "ROLE":
        return "Este cargo publico aparece como informacion administrativa de muestra."
    elif explanation.entity_type == "PERSON":
        return "Esta persona aparece en un registro administrativo de muestra."
    elif explanation.entity_type == "LOBBY_MEETING":
        return (
            "Esta reunión de lobby conecta un organismo público con una contraparte registrada. "
            "La relación no implica irregularidad; solo muestra una reunión registrada o de muestra."
        )
    else:
        prefix = "Esta entidad"
    return f"{prefix} aparece en {explanation.public_contracts} contratos públicos."


def _entity_source_names(session: Session, entity_id: UUID) -> tuple[str, ...]:
    statement = (
        select(distinct(Dataset.name))
        .select_from(Claim)
        .join(SourceRecord, Claim.source_record_id == SourceRecord.id)
        .join(Dataset, SourceRecord.dataset_id == Dataset.id)
        .where(
            Claim.subject_entity_id == entity_id,
        )
        .order_by(Dataset.name.asc())
    )
    rows = session.execute(statement).scalars().all()
    labels: list[str] = []
    for name in rows:
        label = _dataset_display_name(str(name))
        if label not in labels:
            labels.append(label)
    return tuple(labels)


def _entity_connection_counts(session: Session, entity: Entity) -> tuple[int, int]:
    entity_id = entity.id
    if entity.entity_type == "BUDGET":
        organization_ids = session.execute(
            select(RelationshipPublic.target_entity_id)
            .join(Claim, RelationshipPublic.claim_id == Claim.id)
            .where(
                RelationshipPublic.source_entity_id == entity_id,
                RelationshipPublic.relationship_type == RelationshipType.BUDGET_ALLOCATED_TO.value,
            )
        ).scalars().all()
        if not organization_ids:
            return 0, 0
        contract_ids = session.execute(
            select(distinct(Claim.object_entity_id))
            .where(
                Claim.subject_entity_id.in_(organization_ids),
                Claim.predicate == "ISSUES_PURCHASE_ORDER",
            )
        ).scalars().all()
        if not contract_ids:
            return 0, 0
        suppliers = session.execute(
            select(distinct(Claim.subject_entity_id))
            .where(
                Claim.predicate == "RECEIVES_CONTRACT",
                Claim.object_entity_id.in_(contract_ids),
            )
        ).scalars().all()
        return len(contract_ids), len(suppliers)

    if entity.entity_type != "PUBLIC_ORGANIZATION":
        return 0, 0

    contract_ids = session.execute(
        select(distinct(Claim.object_entity_id))
        .where(
            Claim.subject_entity_id == entity_id,
            Claim.predicate == "ISSUES_PURCHASE_ORDER",
        )
    ).scalars().all()
    if not contract_ids:
        return 0, 0
    suppliers = session.execute(
        select(distinct(Claim.subject_entity_id))
        .where(
            Claim.predicate == "RECEIVES_CONTRACT",
            Claim.object_entity_id.in_(contract_ids),
        )
    ).scalars().all()
    return len(contract_ids), len(suppliers)


def _graph_chain(root: Any) -> tuple[str, ...]:
    chain = [root.entity.entity_type]
    current = root
    seen = {root.entity.id}
    while current.children:
        next_node = current.children[0]
        if next_node.entity.id in seen:
            break
        chain.append(next_node.entity.entity_type)
        seen.add(next_node.entity.id)
        current = next_node
    return tuple(chain)


def _graph_meaning_for_chain(chain: tuple[str, ...]) -> str:
    if chain[:3] == ("PUBLIC_ORGANIZATION", "ROLE", "PERSON"):
        return "Transparencia Activa muestra informacion administrativa publicada por organismos. Este prototipo usa datos de muestra, no datos oficiales. No implica irregularidad; solo representa informacion publica o de muestra."
    if chain[:5] == ("BUDGET", "PUBLIC_ORGANIZATION", "CONTRACT", "COMPANY", "LOBBY_MEETING"):
        return "El organismo se conecta con presupuesto, contratos, una contraparte y una reunión de lobby registrada o de muestra. La relación no implica irregularidad."
    if chain[:4] == ("BUDGET", "PUBLIC_ORGANIZATION", "CONTRACT", "COMPANY"):
        return "El organismo recibió una asignación presupuestaria y luego emitió compras que conectan contratos con proveedores."
    if chain[:3] == ("PUBLIC_ORGANIZATION", "LOBBY_MEETING", "COMPANY"):
        return "Esta reunión de lobby conecta un organismo público con una contraparte registrada. La relación no implica irregularidad; solo muestra una reunión registrada o de muestra."
    if chain[:3] == ("COMPANY", "LOBBY_MEETING", "PUBLIC_ORGANIZATION"):
        return "Esta contraparte aparece conectada a una reunión de lobby con un organismo público. La relación es descriptiva y no implica irregularidad."
    if chain[:3] == ("PUBLIC_ORGANIZATION", "CONTRACT", "COMPANY"):
        return "El organismo emite compras públicas que conectan contratos y proveedores."
    if not chain:
        return "Este gráfico muestra cómo se conectan las entidades a través de registros públicos."
    readable = " → ".join(entity_type_display_label(entity_type) for entity_type in chain)
    return f"Este gráfico muestra cómo {readable} se conectan a través de registros públicos."


def _dataset_display_name(dataset_name: str) -> str:
    if dataset_name in DATASET_NAME_LABELS:
        return DATASET_NAME_LABELS[dataset_name]
    return dataset_name
