from __future__ import annotations

from typing import Iterable

from datosenorden.datasets import dataset_label_for_name


RELATIONSHIP_EXPLANATIONS = {
    "ORGANIZATION_HAS_PUBLIC_ROLE": "El organismo aparece asociado a un cargo publico.",
    "PERSON_HOLDS_PUBLIC_ROLE": "La persona aparece asociada a un cargo publico.",
    "ROLE_BELONGS_TO_ORGANIZATION": "El cargo publico pertenece a un organismo.",
    "AUTHORITY_ELECTED_TO_OFFICE": "La autoridad aparece asociada a un cargo electo o de representacion.",
    "AUTHORITY_REPRESENTS_TERRITORY": "La autoridad aparece asociada a un territorio de representacion.",
    "OFFICE_BELONGS_TO_MUNICIPALITY": "El cargo o puesto pertenece a un municipio.",
    "AUTHORITY_HAS_ELECTORAL_PERIOD": "La autoridad aparece asociada a un periodo electoral.",
    "PERSON_APPOINTED_TO_PUBLIC_OFFICE": "La persona aparece asociada a un nombramiento o designacion en un cargo publico.",
    "PERSON_RESIGNED_FROM_PUBLIC_OFFICE": "La persona aparece asociada a una renuncia o cese de cargo publico.",
    "DECREE_APPLIES_TO_ORGANIZATION": "La publicacion oficial aparece asociada a una organizacion.",
    "OFFICIAL_PUBLICATION_REFERENCES_ENTITY": "La publicacion oficial hace referencia a una entidad.",
    "PUBLIC_OFFICE_BELONGS_TO_ORGANIZATION": "El cargo publico pertenece a una organizacion.",
    "BUDGET_ALLOCATED_TO": "El presupuesto aparece asignado a un organismo.",
    "AWARDS_CONTRACT": "El organismo adjudica un contrato.",
    "COUNTERPARTY_PARTICIPATED_IN_LOBBY": "La contraparte aparece asociada a una reunion de lobby.",
    "ISSUES_PURCHASE_ORDER": "El organismo emite una orden de compra.",
    "ORGANIZATION_HELD_LOBBY_MEETING": "El organismo aparece asociado a una reunion de lobby.",
    "PUBLISHED_TENDER": "El organismo publica una licitacion.",
    "RECEIVES_CONTRACT": "La entidad recibe un contrato.",
    "ORGANIZATION_HAS_CONTROL_REPORT": "El organismo aparece asociado a un informe de control.",
    "CONTROL_REPORT_HAS_OBSERVATION": "El informe contiene observaciones registradas.",
    "MUNICIPALITY_EXECUTES_PROJECT": "El municipio aparece asociado a un proyecto publico.",
    "MUNICIPALITY_SPENDS_ON": "El municipio aparece asociado a un gasto o item de gasto.",
}

EVENT_EXPLANATIONS = {
    "ISSUES_PURCHASE_ORDER": "Se registro una orden de compra asociada.",
    "RECEIVES_CONTRACT": "Se registro un contrato asociado.",
    "HAS_APPROVED_BUDGET": "Se registro presupuesto aprobado asociado.",
    "HAS_EXECUTED_BUDGET": "Se registro ejecucion presupuestaria asociada.",
    "MATCHED_TO_ORGANIZATION": "Se registro una coincidencia con un organismo.",
    "ORGANIZATION_HELD_LOBBY_MEETING": "Se registro una reunion de lobby asociada.",
    "COUNTERPARTY_PARTICIPATED_IN_LOBBY": "Se registro una contraparte en una reunion de lobby.",
    "LOBBY_MEETING_ABOUT_SUBJECT": "Se registro la materia de una reunion de lobby.",
    "ORGANIZATION_HAS_PUBLIC_ROLE": "Se registro un cargo publico asociado.",
    "PERSON_HOLDS_PUBLIC_ROLE": "Se registro una persona asociada a un cargo publico.",
    "ROLE_BELONGS_TO_ORGANIZATION": "Se registro un cargo vinculado a un organismo.",
    "AUTHORITY_ELECTED_TO_OFFICE": "Se registro una autoridad vinculada a un cargo electo.",
    "AUTHORITY_REPRESENTS_TERRITORY": "Se registro una autoridad vinculada a un territorio de representacion.",
    "OFFICE_BELONGS_TO_MUNICIPALITY": "Se registro un cargo vinculado a un municipio.",
    "AUTHORITY_HAS_ELECTORAL_PERIOD": "Se registro un periodo electoral asociado a la autoridad.",
    "ORGANIZATION_HAS_CONTROL_REPORT": "Se registro un informe de control asociado.",
    "CONTROL_REPORT_HAS_OBSERVATION": "Se registro una observacion asociada al informe.",
    "MUNICIPALITY_EXECUTES_PROJECT": "Se registro la ejecucion de un proyecto.",
    "MUNICIPALITY_SPENDS_ON": "Se registro un gasto municipal asociado.",
    "PERSON_APPOINTED_TO_PUBLIC_OFFICE": "Se registro un nombramiento en un cargo publico.",
    "PERSON_RESIGNED_FROM_PUBLIC_OFFICE": "Se registro una renuncia a un cargo publico.",
    "DECREE_APPLIES_TO_ORGANIZATION": "Se registro una publicacion oficial asociada a una organizacion.",
    "OFFICIAL_PUBLICATION_REFERENCES_ENTITY": "Se registro una publicacion oficial que referencia una entidad.",
    "PUBLIC_OFFICE_BELONGS_TO_ORGANIZATION": "Se registro un cargo publico vinculado a una organizacion.",
}


def dataset_display_name(dataset_name: str) -> str:
    return dataset_label_for_name(dataset_name)


def relationship_explanation(relationship_type: str) -> str:
    return RELATIONSHIP_EXPLANATIONS.get(
        relationship_type,
        f"La relacion {relationship_type} fue registrada en el sistema.",
    )


def relationship_label(relationship_type: str) -> str:
    return RELATIONSHIP_EXPLANATIONS.get(
        relationship_type,
        relationship_type.replace("_", " ").title(),
    )


def event_explanation(predicate: str) -> str:
    return EVENT_EXPLANATIONS.get(
        predicate,
        "Se registro un evento publico asociado a esta entidad.",
    )


def graph_explanation_for_chain(chain: tuple[str, ...]) -> str:
    if "ELECTORAL_PERIOD" in chain or chain[:3] == ("PERSON", "ROLE", "MUNICIPALITY"):
        return "SERVEL muestra autoridades electas, cargos publicos, territorios y periodos electorales de muestra. Este prototipo usa datos de muestra, no datos oficiales. No implica irregularidad."
    if chain[:3] == ("PUBLIC_ORGANIZATION", "ROLE", "PERSON"):
        return "Transparencia Activa muestra informacion administrativa publicada por organismos. Este prototipo usa datos de muestra, no datos oficiales. No implica irregularidad; solo representa informacion publica o de muestra."
    if chain[:3] in {("PERSON", "ROLE", "PUBLIC_ORGANIZATION"), ("PUBLIC_ORGANIZATION", "ROLE", "PERSON")}:
        return "Diario Oficial muestra nombramientos, renuncias y cargos publicos vinculados con una publicacion oficial. La relacion es descriptiva y no implica juicio alguno."
    if chain[:5] == ("BUDGET", "PUBLIC_ORGANIZATION", "CONTRACT", "COMPANY", "LOBBY_MEETING"):
        return "El organismo se conecta con presupuesto, contratos, una contraparte y una reunion de lobby registrada o de muestra. La relacion no implica irregularidad."
    if chain[:4] == ("BUDGET", "PUBLIC_ORGANIZATION", "CONTRACT", "COMPANY"):
        return "El organismo recibio una asignacion presupuestaria y luego emitio compras que conectan contratos con proveedores."
    if chain[:3] == ("PUBLIC_ORGANIZATION", "LOBBY_MEETING", "COMPANY"):
        return "Esta reunion de lobby conecta un organismo publico con una contraparte registrada. La relacion no implica irregularidad; solo muestra una reunion registrada o de muestra."
    if chain[:3] == ("COMPANY", "LOBBY_MEETING", "PUBLIC_ORGANIZATION"):
        return "Esta contraparte aparece conectada a una reunion de lobby con un organismo publico. La relacion es descriptiva y no implica irregularidad."
    if chain[:3] == ("PUBLIC_ORGANIZATION", "CONTRACT", "COMPANY"):
        return "El organismo emite compras publicas que conectan contratos y proveedores."
    if chain[:3] == ("PUBLIC_ORGANIZATION", "CONTROL_REPORT", "PUBLIC_OBSERVATION"):
        return "El organismo aparece vinculado a un informe de control y una observacion registrada. La relacion es descriptiva y no implica irregularidad."
    if chain[:3] == ("MUNICIPALITY", "PUBLIC_PROJECT", "SPENDING_ITEM"):
        return "El municipio aparece vinculado a un proyecto publico y a un gasto registrado. La relacion es descriptiva y no implica irregularidad."
    if not chain:
        return "Este grafico muestra como se conectan las entidades a traves de registros publicos."
    readable = " -> ".join(chain)
    return f"Este grafico muestra como {readable} se conectan a traves de registros publicos."
